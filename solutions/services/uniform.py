"""Uniform Compliance Check domain logic. Pure functions: Django never
stores an inspection between requests — every operation receives (and
returns) the slice of state it needs; see ``core.state`` and
``docs/implementation-notes.md``.

``compute_score`` here is the *authoritative* implementation of the score
formula (server always recomputes it — the client-side preview in
``static/js/solutions/uniform.js`` is UX only). See
``mock_data.uniform`` module docstring for why that module keeps its own
private mirror instead of importing this one (mock_data must not depend on
solutions.services).
"""

from datetime import datetime, timedelta

from mock_data.people import eligible_population
from mock_data.reference import SITE_BY_SLUG
from mock_data.uniform import (
    CHECKLIST_ITEM_LABELS,
    CHECKLIST_ITEM_SLUGS,
    DEFAULT_ROLE_SLUG,
    INSPECTOR_POOL,
    ITEM_STATUS_SLUGS,
    ROLE_BY_SLUG,
    SHIFT_SLUGS,
    employee_roles,
)

from .common import ValidationError, Validator, history_entry, next_id, now_iso, sanitize_text

SITE_SLUGS = list(SITE_BY_SLUG.keys())

# "requiere seguimiento" transition graph: a followup is either open or
# resolved. No reopen edge — unlike Security's controls, a demo corrective
# action closed out does not need to resurface; a fresh inspection would
# generate a fresh followup if the problem repeats.
FOLLOWUP_TRANSITIONS = {"pendiente": {"resuelto"}, "resuelto": set()}


def compute_score(items: list[dict]) -> float | None:
    """Score = conformes / aplicables × 100, excluyendo elementos en estado
    'no_aplica'. Si no hay elementos aplicables (todos 'no_aplica'), el
    resultado es None y la UI debe mostrar 'Sin evaluación' — nunca dividir
    por cero. Debe coincidir exactamente con el preview del cliente en
    static/js/solutions/uniform.js::computeScorePreview."""
    applicable = [it for it in items if it.get("status") != "no_aplica"]
    if not applicable:
        return None
    conformes = sum(1 for it in applicable if it.get("status") == "conforme")
    return round(conformes / len(applicable) * 100, 1)


def status_for_score(score: float | None) -> str:
    """Demo approval guide (never presented as an official ARRISE policy in
    the UI, see templates/solutions/uniform/home.html): 100% of applicable
    items conforme -> 'conforme'; any other evaluable result -> 'seguimiento'
    (requiere seguimiento); no applicable items at all -> 'sin_evaluacion'."""
    if score is None:
        return "sin_evaluacion"
    if score == 100:
        return "conforme"
    return "seguimiento"


def _add_business_days(start: datetime, n: int) -> datetime:
    d = start
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


def _pick_responsible(site_slug: str, exclude_employee_id: str):
    """Responsible for a followup: a Supervisor de piso colleague based in
    the same country as the inspection's site, when one exists in the
    eligible population; otherwise a fixed area placeholder. Deterministic
    (no RNG at request time — Django has no per-request seed here) but
    spread across candidates using the employee id's numeric suffix so
    repeated demo inspections don't all land on the same one person."""
    country = SITE_BY_SLUG[site_slug]["country"]
    roles = employee_roles()
    population = eligible_population("uniform")
    candidates = [
        e
        for e in population
        if roles.get(e["id"]) == "supervisor_piso" and e["country"] == country and e["id"] != exclude_employee_id
    ]
    if not candidates:
        candidates = [
            e for e in population if roles.get(e["id"]) == "supervisor_piso" and e["id"] != exclude_employee_id
        ]
    if not candidates:
        return None, "Coordinador de Operaciones Demo"
    try:
        seed_n = int(str(exclude_employee_id).split("-")[-1])
    except ValueError:
        seed_n = 0
    chosen = candidates[seed_n % len(candidates)]
    return chosen["id"], chosen["name"]


def create_inspection(payload: dict) -> dict:
    v = Validator()
    population = eligible_population("uniform")
    population_by_id = {e["id"]: e for e in population}

    v.id_ref(payload, "employee_id", set(population_by_id.keys()), label="Colaborador")
    site = v.choice(payload, "site", SITE_SLUGS, label="Sede")
    shift = v.choice(payload, "shift", SHIFT_SLUGS, label="Turno")
    inspector = v.choice(payload, "inspector", INSPECTOR_POOL, label="Inspector")
    observations = v.text(
        payload, "observations", label="Observaciones", max_length=800, min_length=0, required=False
    )
    evidence_filename = v.text(
        payload, "evidence_filename", label="Evidencia (nombre de archivo)", max_length=120, min_length=3
    )
    v.raise_if_errors()

    employee_id = payload.get("employee_id")
    employee = population_by_id[employee_id]

    items_payload = payload.get("items")
    if not isinstance(items_payload, dict):
        raise ValidationError({"items": "El checklist es obligatorio."})

    role_slug = employee_roles().get(employee_id, DEFAULT_ROLE_SLUG)
    role = ROLE_BY_SLUG.get(role_slug, ROLE_BY_SLUG[DEFAULT_ROLE_SLUG])

    items = []
    item_errors = {}
    for slug in CHECKLIST_ITEM_SLUGS:
        status_value = items_payload.get(slug)
        if status_value not in ITEM_STATUS_SLUGS:
            item_errors[f"items.{slug}"] = "Selecciona un estado válido para este elemento."
            continue
        label = role["role_item_label"] if slug == "elementos_rol" else CHECKLIST_ITEM_LABELS[slug]
        items.append({"slug": slug, "label": label, "status": status_value})
    if item_errors:
        raise ValidationError(item_errors)

    score = compute_score(items)
    status = status_for_score(score)

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("INSP", existing_ids)
    actor = sanitize_text(inspector)
    now = now_iso()

    history = [history_entry("created", "Inspección registrada.", actor=actor)]

    record = {
        "id": new_id,
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "role": role_slug,
        "role_label": role["label"],
        "site": v.cleaned["site"],
        "shift": v.cleaned["shift"],
        "inspector": actor,
        "items": items,
        "score": score,
        "status": status,
        "observations": sanitize_text(observations),
        "evidence_filename": sanitize_text(evidence_filename),
        "created_at": now,
        "history": history,
        "followup_id": None,
    }

    followup = None
    if status == "seguimiento":
        existing_followup_ids = payload.get("existing_followup_ids") or []
        followup_id = next_id("FUP", existing_followup_ids)
        issues = [
            {"slug": it["slug"], "label": it["label"], "status": it["status"]}
            for it in items
            if it["status"] in ("faltante", "danado")
        ]
        responsible_id, responsible_name = _pick_responsible(site, employee_id)
        created_dt = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
        due_dt = _add_business_days(created_dt, 5)
        due_date = due_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        followup = {
            "id": followup_id,
            "inspection_id": new_id,
            "employee_id": employee_id,
            "employee_name": employee["name"],
            "site": site,
            "issues": issues,
            "responsible_id": responsible_id,
            "responsible_name": responsible_name,
            "due_date": due_date,
            "status": "pendiente",
            "created_at": now,
            "history": [
                history_entry(
                    "created", f"Seguimiento correctivo generado tras la inspección {new_id}.", actor=actor
                )
            ],
        }
        record["followup_id"] = followup_id
        record["history"].append(
            history_entry(
                "followup_generated",
                f"Seguimiento correctivo {followup_id} generado (score {score}%).",
                actor=actor,
            )
        )

    return {"inspection": record, "followup": followup}


def resolve_followup(payload: dict) -> dict:
    followup_id = payload.get("id")
    if not followup_id:
        raise ValidationError({"id": "Falta el identificador del seguimiento."})
    current_status = payload.get("current_status")
    if current_status not in FOLLOWUP_TRANSITIONS:
        raise ValidationError({"status": "Estado actual desconocido."})
    if "resuelto" not in FOLLOWUP_TRANSITIONS[current_status]:
        raise ValidationError({"status": "Solo se pueden resolver seguimientos pendientes."})

    actor = sanitize_text(payload.get("actor") or "Coordinador de Operaciones Demo")
    note = sanitize_text(payload.get("note") or "")
    detail = "Seguimiento marcado como resuelto." + (f" Nota: {note}" if note else "")
    entry = history_entry("resolved", detail, actor=actor)
    notify = f"El seguimiento correctivo {followup_id} fue marcado como resuelto."
    return {"id": followup_id, "status": "resuelto", "history_entry": entry, "notify": notify}
