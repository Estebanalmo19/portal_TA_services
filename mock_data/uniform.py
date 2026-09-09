"""Uniform Compliance Check mock dataset.

Fictitious uniform-inspection data for Operations staff: each inspection is a
fixed checklist (camisa, pantalon, calzado, identificacion, accesorios
permitidos, elementos del rol) evaluated per employee/site/shift, plus a
"followups" collection of simulated corrective-action records generated when
an inspection does not reach 100% conformance on its applicable items. See
``docs/implementation-notes.md`` for the shared state-contract writeup and
the design-decision notes below (role model, score formula, health
heuristic).

---------------------------------------------------------------------------
Design decision: "elementos del rol".

The task brief left the exact shape open ("puedes representar 'elementos del
rol' como 1-2 ítems adicionales específicos, o como un único ítem genérico").
This module keeps the checklist to exactly six fixed slots (so scoring/UI
stay simple and every inspection has the same shape) and instead makes the
*label* of the last slot role-specific: every eligible (operations) employee
is deterministically assigned one of four demo roles (see ``ROLES``), and
that role supplies a concrete, human-readable label for the
``elementos_rol`` checklist item (e.g. "Elementos del rol (chaleco
reflectivo)" for an Operario de producción). This gives the "1-2 items
específicos según el rol" flavor the brief asks for without turning the
checklist into a variable-length structure that every consumer (score calc,
table columns, CSV/analytics) would have to special-case.
---------------------------------------------------------------------------
Design decision: score formula.

Score = conformes / aplicables × 100, where "aplicables" excludes any item
marked ``no_aplica``. If there are zero applicable items the score is
``None`` ("Sin evaluación") — never a division by zero. This exact formula
is re-implemented (not imported — mock_data must not depend on
``solutions.services``, only the reverse) as a tiny pure function in
``solutions.services.uniform.compute_score`` (the authoritative, server-side
copy used at write time) and mirrored again as a comment-documented JS
function in ``static/js/solutions/uniform.js`` for the live client preview.
All three copies must agree; keep them in sync if the formula ever changes.
---------------------------------------------------------------------------
Design decision: corrective followups.

An inspection whose score is not ``None`` and is below 100 "requiere
seguimiento" (per the brief's explicitly-labeled demo rule — never presented
as an official ARRISE policy in the UI). For every such inspection this
module generates one linked "followup" record: a responsible party (a
Supervisor de piso colleague based in the same country as the inspection's
site when one exists in the eligible population, otherwise a generic
"Coordinador de Operaciones Demo" placeholder — see ``_pick_responsible``)
and a due date of +5 simulated business days from the inspection. This
mirrors Security Database Hub's "controls" collection: a second, smaller
top-level collection in the state alongside the main records.
---------------------------------------------------------------------------
"""

from datetime import datetime, timedelta
from functools import lru_cache

from .clock import days_ago, iso, new_rng, reference_datetime
from .people import eligible_population
from .reference import SITE_BY_SLUG, SITES
from .timeseries import MonthlyProfile, generate_monthly_series


@lru_cache(maxsize=1)
def monthly_series() -> list[dict]:
    """12-month activity series for the executive dashboard — separate from
    ``showcase_inspections()`` (the ~15-20 "current" inspections shown in
    this module's own table)."""
    profile = MonthlyProfile(
        base_active_ratio=0.30,
        executions_per_active=1.1,
        success_rate=0.6,  # fraction of inspections reaching 100% conformance
        manual_minutes=15,
        assisted_minutes=5,
        satisfaction_response_rate=0.0,  # no satisfaction survey for this module
        satisfaction_mean=0.0,
    )
    return generate_monthly_series("uniform.monthly", "uniform", profile)

SITE_SLUGS = [s["slug"] for s in SITES]

SHIFT_LABELS = {"manana": "Mañana", "tarde": "Tarde", "noche": "Noche"}
SHIFT_SLUGS = list(SHIFT_LABELS.keys())

# Fixed checklist shape — every inspection has exactly these six items, in
# this order. See module docstring for why "elementos_rol" stays a single
# slot with a role-specific label rather than a variable set of extra items.
CHECKLIST_ITEM_LABELS = {
    "camisa": "Camisa",
    "pantalon": "Pantalón",
    "calzado": "Calzado",
    "identificacion": "Identificación",
    "accesorios": "Accesorios permitidos",
    "elementos_rol": "Elementos del rol",
}
CHECKLIST_ITEM_SLUGS = list(CHECKLIST_ITEM_LABELS.keys())

ITEM_STATUS_LABELS = {
    "conforme": "Conforme",
    "faltante": "Faltante",
    "danado": "Dañado",
    "no_aplica": "No aplica",
}
ITEM_STATUS_SLUGS = list(ITEM_STATUS_LABELS.keys())

INSPECTION_STATUS_LABELS = {
    "conforme": "Conforme",
    "seguimiento": "Requiere seguimiento",
    "sin_evaluacion": "Sin evaluación",
}

FOLLOWUP_STATUS_LABELS = {"pendiente": "Pendiente", "resuelto": "Resuelto"}
FOLLOWUP_STATUS_SLUGS = list(FOLLOWUP_STATUS_LABELS.keys())

# Demo-only inspector pool: free-text actor names (like Security's
# ACTOR_POOL), not tied to a specific employee record — an inspection's
# "inspector" is who performed the check, not who is being checked.
INSPECTOR_POOL = [
    "Supervisor de Turno Demo",
    "Coordinador de Cumplimiento Demo",
    "Auditor de Uniformes Demo",
]

# Demo roles assigned to the eligible (operations) population — see module
# docstring. `role_item_label` is what the "elementos_rol" checklist slot is
# called for an employee with that role.
ROLES = [
    {
        "slug": "operario_produccion",
        "label": "Operario de producción",
        "role_item_label": "Elementos del rol (chaleco reflectivo)",
    },
    {
        "slug": "supervisor_piso",
        "label": "Supervisor de piso",
        "role_item_label": "Elementos del rol (radio de comunicación)",
    },
    {
        "slug": "agente_atencion",
        "label": "Agente de atención",
        "role_item_label": "Elementos del rol (diadema de atención)",
    },
    {
        "slug": "tecnico_mantenimiento",
        "label": "Técnico de mantenimiento",
        "role_item_label": "Elementos del rol (guantes de seguridad)",
    },
]
ROLE_BY_SLUG = {r["slug"]: r for r in ROLES}
ROLE_SLUGS = [r["slug"] for r in ROLES]
ROLE_WEIGHTS = [0.40, 0.15, 0.25, 0.20]
DEFAULT_ROLE_SLUG = ROLE_SLUGS[0]


def _compute_score(items: list[dict]) -> float | None:
    """Private mirror of ``solutions.services.uniform.compute_score`` used
    only to build the showcase dataset below (mock_data cannot import
    solutions.services — the dependency runs the other way). Same formula,
    same edge case: 0 applicable items -> None."""
    applicable = [it for it in items if it.get("status") != "no_aplica"]
    if not applicable:
        return None
    conformes = sum(1 for it in applicable if it.get("status") == "conforme")
    return round(conformes / len(applicable) * 100, 1)


def _status_for_score(score: float | None) -> str:
    if score is None:
        return "sin_evaluacion"
    if score == 100:
        return "conforme"
    return "seguimiento"


def _add_business_days(start, n: int):
    d = start
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            added += 1
    return d


@lru_cache(maxsize=1)
def employee_roles() -> dict:
    """Deterministic role assignment for every operations employee eligible
    for this solution. Weighted so "Operario de producción" (the largest
    front-line group) dominates, matching the AREA_WEIGHTS flavor already
    used in mock_data.people."""
    population = eligible_population("uniform")
    rng = new_rng("uniform.roles")
    assigned = rng.choices(ROLE_SLUGS, weights=ROLE_WEIGHTS, k=len(population))
    return {e["id"]: assigned[i] for i, e in enumerate(population)}


@lru_cache(maxsize=1)
def employees_with_roles() -> list[dict]:
    """Eligible population enriched with their demo role — used by the
    create-inspection form so the browser can show the correct
    "elementos_rol" label live without a round trip."""
    roles = employee_roles()
    out = []
    for e in eligible_population("uniform"):
        role_slug = roles.get(e["id"], DEFAULT_ROLE_SLUG)
        role = ROLE_BY_SLUG[role_slug]
        out.append(
            {
                **e,
                "role": role_slug,
                "role_label": role["label"],
                "role_item_label": role["role_item_label"],
            }
        )
    return out


def _build_items(rng, scenario: str, role: dict) -> list[dict]:
    items = []
    for slug in CHECKLIST_ITEM_SLUGS:
        label = role["role_item_label"] if slug == "elementos_rol" else CHECKLIST_ITEM_LABELS[slug]
        items.append({"slug": slug, "label": label, "status": "conforme"})

    if scenario == "sin_evaluacion":
        for item in items:
            item["status"] = "no_aplica"
        return items

    # Some inspections legitimately have no applicable "accesorios" for a
    # given role/shift (e.g. no accessory policy applies) — flavor variety,
    # still scores 100 when everything else is conforme.
    if rng.random() < 0.25:
        for item in items:
            if item["slug"] == "accesorios":
                item["status"] = "no_aplica"

    if scenario == "seguimiento":
        applicable_slugs = [it["slug"] for it in items if it["status"] != "no_aplica"]
        fail_count = rng.randint(1, min(3, len(applicable_slugs)))
        fail_slugs = rng.sample(applicable_slugs, fail_count)
        for item in items:
            if item["slug"] in fail_slugs:
                item["status"] = rng.choice(["faltante", "danado"])

    return items


def _observation_text(rng, scenario: str, failing_labels: list[str]) -> str:
    if scenario == "sin_evaluacion":
        return rng.choice(
            [
                "Colaborador en licencia médica; el uniforme no aplica para este turno.",
                "Colaborador en labores administrativas fuera de piso; checklist no aplicable hoy.",
            ]
        )
    if scenario == "conforme":
        return rng.choice(
            [
                "Uniforme completo y en buen estado.",
                "Sin observaciones; cumple con el checklist en su totalidad.",
            ]
        )
    return f"Se detectaron incumplimientos en: {', '.join(failing_labels)}."


def _pick_responsible(rng, site_slug: str, exclude_employee_id: str):
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
    if candidates:
        chosen = rng.choice(candidates)
        return chosen["id"], chosen["name"]
    return None, "Coordinador de Operaciones Demo"


@lru_cache(maxsize=1)
def showcase_inspections() -> list[dict]:
    rng = new_rng("uniform.showcase")
    population = eligible_population("uniform")
    roles = employee_roles()

    # >= 15 required; 20 gives comfortable variety across sites/shifts/status.
    scenario_cycle = ["conforme"] * 8 + ["seguimiento"] * 10 + ["sin_evaluacion"] * 2
    rng.shuffle(scenario_cycle)

    inspections = []
    for i, scenario in enumerate(scenario_cycle, start=1):
        insp_id = f"INSP-{i:04d}"
        employee = rng.choice(population)
        role_slug = roles.get(employee["id"], DEFAULT_ROLE_SLUG)
        role = ROLE_BY_SLUG[role_slug]
        site = rng.choice(SITE_SLUGS)
        shift = rng.choice(SHIFT_SLUGS)
        inspector = rng.choice(INSPECTOR_POOL)
        age_days = rng.randint(1, 90)
        created_at = days_ago(age_days)

        items = _build_items(rng, scenario, role)
        score = _compute_score(items)
        status = _status_for_score(score)
        failing_labels = [it["label"] for it in items if it["status"] in ("faltante", "danado")]

        history = [
            {
                "type": "created",
                "detail": "Inspección registrada.",
                "actor": inspector,
                "at": iso(created_at),
            }
        ]

        followup_id = None
        if status == "seguimiento":
            followup_id = f"FUP-{i:04d}"
            history.append(
                {
                    "type": "followup_generated",
                    "detail": f"Seguimiento correctivo {followup_id} generado (score {score}%).",
                    "actor": inspector,
                    "at": iso(created_at),
                }
            )

        inspections.append(
            {
                "id": insp_id,
                "employee_id": employee["id"],
                "employee_name": employee["name"],
                "role": role_slug,
                "role_label": role["label"],
                "site": site,
                "shift": shift,
                "inspector": inspector,
                "items": items,
                "score": score,
                "status": status,
                "observations": _observation_text(rng, scenario, failing_labels),
                "evidence_filename": f"foto_uniforme_demo_{i:03d}.jpg",
                "created_at": iso(created_at),
                "history": history,
                "followup_id": followup_id,
            }
        )
    return inspections


@lru_cache(maxsize=1)
def showcase_followups() -> list[dict]:
    rng = new_rng("uniform.followups")
    followups = []
    for inspection in showcase_inspections():
        if inspection["status"] != "seguimiento" or not inspection["followup_id"]:
            continue
        created_at = inspection["created_at"]
        created_dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=reference_datetime().tzinfo)
        due_dt = _add_business_days(created_dt, 5)

        responsible_id, responsible_name = _pick_responsible(rng, inspection["site"], inspection["employee_id"])
        issues = [
            {"slug": it["slug"], "label": it["label"], "status": it["status"]}
            for it in inspection["items"]
            if it["status"] in ("faltante", "danado")
        ]

        history = [
            {
                "type": "created",
                "detail": f"Seguimiento correctivo generado tras la inspección {inspection['id']}.",
                "actor": inspection["inspector"],
                "at": created_at,
            }
        ]
        status = "pendiente"
        if rng.random() < 0.4:
            status = "resuelto"
            resolved_dt = min(due_dt, reference_datetime())
            history.append(
                {
                    "type": "resolved",
                    "detail": "Seguimiento marcado como resuelto.",
                    "actor": responsible_name,
                    "at": iso(resolved_dt),
                }
            )

        followups.append(
            {
                "id": inspection["followup_id"],
                "inspection_id": inspection["id"],
                "employee_id": inspection["employee_id"],
                "employee_name": inspection["employee_name"],
                "site": inspection["site"],
                "issues": issues,
                "responsible_id": responsible_id,
                "responsible_name": responsible_name,
                "due_date": iso(due_dt),
                "status": status,
                "created_at": created_at,
                "history": history,
            }
        )
    return followups


def initial_state() -> dict:
    return {
        "inspections": showcase_inspections(),
        "followups": showcase_followups(),
        "sites": SITES,
        "shifts": [{"slug": s, "label": SHIFT_LABELS[s]} for s in SHIFT_SLUGS],
        "checklist_items": [{"slug": s, "label": CHECKLIST_ITEM_LABELS[s]} for s in CHECKLIST_ITEM_SLUGS],
        "item_statuses": [{"slug": s, "label": ITEM_STATUS_LABELS[s]} for s in ITEM_STATUS_SLUGS],
        "roles": ROLES,
        "inspectors": INSPECTOR_POOL,
        "last_sync": iso(reference_datetime() - timedelta(minutes=22)),
    }


def catalog_summary() -> dict:
    inspections = showcase_inspections()
    followups = showcase_followups()

    active_users = len({i["employee_id"] for i in inspections})
    activity_times = [i["history"][-1]["at"] for i in inspections if i["history"]]
    activity_times += [f["history"][-1]["at"] for f in followups if f["history"]]
    last_activity = max(activity_times, default=None)

    open_items = sum(1 for f in followups if f["status"] == "pendiente")

    evaluable = [i for i in inspections if i["score"] is not None]
    conformes = sum(1 for i in evaluable if i["score"] == 100)
    conformance_rate = (conformes / len(evaluable)) if evaluable else None

    now = reference_datetime()
    overdue_followups = 0
    for f in followups:
        if f["status"] != "pendiente":
            continue
        due = datetime.strptime(f["due_date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=now.tzinfo)
        if due < now:
            overdue_followups += 1

    if conformance_rate is None:
        health = "warning"
    elif overdue_followups >= 3 or conformance_rate < 0.5:
        health = "critical"
    elif overdue_followups >= 1 or conformance_rate < 0.75:
        health = "warning"
    else:
        health = "good"

    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
