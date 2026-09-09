"""Appearance Check mock dataset.

Simulates a **manual** operational-readiness review a supervisor performs
on a fictional collaborator before that collaborator enters live
operation. This module is deliberately kept separate from Uniform
Compliance Check's own garment checklist (``mock_data.uniform``) — see
``docs/implementation-notes.md`` for the shared state-contract writeup.

Ethical/scope constraints for this module (see the task brief — restated
here because they drove several data-shape decisions below, not just UI
copy):

- No photo analysis, no face/identity recognition, no inference of race,
  gender, age or any other sensitive characteristic, and no attractiveness
  scoring of any kind. There is no image upload anywhere in this module:
  "evidence" (``evidence_filename``) is a plain free-text simulated
  filename field, exactly like ``cv_filename`` in ``mock_data.referral`` —
  never a real ``<input type="file">`` and never processed as an image.
- ``CRITERIA`` below only lists observable, operational-readiness facts a
  supervisor can literally tick off during a lobby/floor walk (badge
  visible, uniform per site guide, safety gear, punctuality, workstation
  readiness, shift paperwork, induction kit handed over). None of them are
  about physical appearance or attractiveness.
- ``RESULT_SLUGS`` (``approved`` / ``requires_review``) is a decision made
  **explicitly by the human reviewer** in the "complete review" step
  (``solutions.services.appearance.complete_review``). No function in this
  codebase derives it automatically from the criteria checkboxes — the
  criteria are supporting context for the reviewer's own judgement call,
  never inputs to a scoring/decision formula.
- ``tattoo_notes`` is a free-text, OPTIONAL field for the reviewer to
  record operational context only (e.g., a fictional site's uniform
  coverage policy for a given fictional case). It is intentionally never a
  checkbox, never a "has tattoos: yes/no" flag, and never feeds any
  pass/fail rule anywhere in this module.
- Every collaborator, site, and case here is fictional
  ("Colaborador Demo", ``@example.com``).
"""

from datetime import timedelta
from functools import lru_cache

from .clock import days_ago, iso, new_rng, reference_date, reference_datetime
from .people import eligible_population
from .reference import SITES
from .timeseries import MonthlyProfile, generate_monthly_series

SITE_SLUGS = [s["slug"] for s in SITES]

# ---------------------------------------------------------------------------
# Review status graph.
#
# Design decision: a short, linear happy path only —
# `pending -> in_review -> completed` — with no reopen edge. Unlike Security
# Database Hub's incidents (which can legitimately resurface) a completed
# Appearance Check is a point-in-time readiness snapshot for one shift entry;
# a later concern about the same collaborator is modeled as a brand-new
# review (new `pending` record), not a reopen of an old one. `completed` is
# therefore a true terminal node.
# ---------------------------------------------------------------------------
STATUS_LABELS = {
    "pending": "Pendiente",
    "in_review": "En revisión",
    "completed": "Completada",
}
STATUS_SLUGS = list(STATUS_LABELS.keys())
TERMINAL_STATUSES = {"completed"}

TRANSITIONS = {
    "pending": {"in_review"},
    "in_review": {"completed"},
    "completed": set(),
}

# Human-chosen review outcome (see module docstring: never computed).
RESULT_LABELS = {
    "approved": "Aprobado",
    "requires_review": "Requiere revisión",
}
RESULT_SLUGS = list(RESULT_LABELS.keys())

SHIFT_LABELS = {
    "manana": "Turno mañana (06:00–14:00)",
    "tarde": "Turno tarde (14:00–22:00)",
    "noche": "Turno noche (22:00–06:00)",
}
SHIFT_SLUGS = list(SHIFT_LABELS.keys())

# Small demo catalog of operational roles within Operations (there is no
# per-employee "role" field in `mock_data.people`, so — same as Security
# Database Hub added its own `FLOORS` catalog — this module adds its own
# small, documented role list rather than inventing a new employee
# generator).
ROLE_LABELS = {
    "agente_operaciones": "Agente de Operaciones",
    "supervisor_turno": "Supervisor de Turno",
    "coordinador_sede": "Coordinador de Sede",
    "soporte_piso": "Soporte Técnico de Piso",
}
ROLE_SLUGS = list(ROLE_LABELS.keys())

# ---------------------------------------------------------------------------
# Checklist criteria: demo, transparent, operational-readiness items only —
# supporting context for a human reviewer's decision, never inputs to an
# automatic pass/fail rule (see module docstring).
# ---------------------------------------------------------------------------
CRITERIA = [
    {"slug": "identificacion", "label": "Identificación / carné visible"},
    {"slug": "uniforme_sede", "label": "Uniforme y vestimenta conforme a la guía de la sede"},
    {"slug": "epp", "label": "Elementos de seguridad requeridos (EPP) completos"},
    {"slug": "puntualidad", "label": "Llegada puntual al turno"},
    {"slug": "estacion_lista", "label": "Estación de trabajo lista para operar"},
    {"slug": "checklist_apertura", "label": "Checklist de apertura de turno firmado"},
    {"slug": "kit_induccion", "label": "Kit de bienvenida/inducción entregado (si aplica)"},
]
CRITERIA_SLUGS = [c["slug"] for c in CRITERIA]
CRITERIA_LABEL_BY_SLUG = {c["slug"]: c["label"] for c in CRITERIA}

REVIEWER_ACTORS = ["Supervisor de Turno Demo", "Coordinador de Sede Demo", "Líder de Operaciones Demo"]

PRESENTATION_NOTE_BANK = [
    "Presentación general conforme a la guía operativa de la sede.",
    "Uniforme correcto; se recordó llevar siempre visible el carné durante el turno.",
    "Estación de trabajo lista antes del inicio del turno; sin observaciones adicionales.",
    "Llegada puntual; checklist de apertura firmado sin novedades.",
    "Se solicitó completar el kit de inducción pendiente antes del próximo turno.",
]

# Purely illustrative operational-context notes for the optional tattoo
# field (see module docstring: never a flag, never a pass/fail input).
# Most seed records leave this empty on purpose.
TATTOO_NOTE_BANK = [
    "Sin observaciones.",
    "Tatuaje visible en antebrazo; el caso ficticio de esta sede aplica manga larga según su guía de uniforme.",
    "Colaborador informa tatuaje reciente; sin impacto en la política de uniforme de la sede para este caso ficticio.",
]


def _future_date_str(days_from_reference: int) -> str:
    return (reference_date() + timedelta(days=days_from_reference)).isoformat()


@lru_cache(maxsize=1)
def showcase_records() -> list[dict]:
    rng = new_rng("appearance.showcase")
    staff = eligible_population("appearance")

    status_cycle = ["pending"] * 3 + ["in_review"] * 3 + ["completed"] * 10
    rng.shuffle(status_cycle)

    records = []
    for i, status in enumerate(status_cycle, start=1):
        record_id = f"APR-{i:04d}"
        employee = rng.choice(staff)
        site = rng.choice(SITE_SLUGS)
        role = rng.choice(ROLE_SLUGS)
        shift = rng.choice(SHIFT_SLUGS)
        actor = rng.choice(REVIEWER_ACTORS)
        age_days = rng.randint(0, 60)
        created_at = days_ago(age_days)

        history = [
            {
                "type": "created",
                "detail": "Revisión programada.",
                "actor": actor,
                "at": iso(created_at),
            }
        ]

        started_at = None
        completed_at = None
        result = None
        criteria_results = []
        presentation_notes = ""
        tattoo_notes = ""
        evidence_filename = None
        follow_up = None

        if status in ("in_review", "completed"):
            # A review is a short in-person checklist walk, not a multi-day
            # process — keep started/completed a few minutes apart rather
            # than a day-granularity `days_ago()` apart (that previously
            # made the "tiempo promedio de revisión" KPI show ~1 day).
            started_dt = created_at + timedelta(minutes=rng.randint(2, 20))
            started_at = iso(started_dt)
            history.append(
                {"type": "started", "detail": "Revisión iniciada.", "actor": actor, "at": started_at}
            )

        if status == "completed":
            completed_dt = started_dt + timedelta(minutes=rng.randint(5, 45))
            completed_at = iso(completed_dt)
            result = rng.choices(RESULT_SLUGS, weights=[0.7, 0.3])[0]
            pass_chance = 0.92 if result == "approved" else 0.6
            criteria_results = [
                {"slug": slug, "checked": rng.random() < pass_chance, "note": ""} for slug in CRITERIA_SLUGS
            ]
            presentation_notes = rng.choice(PRESENTATION_NOTE_BANK)
            tattoo_notes = rng.choice(TATTOO_NOTE_BANK) if rng.random() < 0.3 else ""
            evidence_filename = f"registro_ingreso_{record_id.lower()}.jpg"
            history.append(
                {
                    "type": "completed",
                    "detail": f"Revisión completada: resultado «{RESULT_LABELS[result]}».",
                    "actor": actor,
                    "at": completed_at,
                }
            )
            if result == "requires_review":
                responsible = rng.choice(staff)
                # Mostly upcoming due dates, with a minority already overdue
                # so the catalog card's health heuristic and the "Pendientes
                # de seguimiento" view have something to show in the demo.
                due_days = rng.randint(-6, -1) if rng.random() < 0.3 else rng.randint(1, 10)
                follow_up = {
                    "responsible_id": responsible["id"],
                    "responsible_name": responsible["name"],
                    "due_date": _future_date_str(due_days),
                }
                history.append(
                    {
                        "type": "follow_up",
                        "detail": f"Seguimiento asignado a {responsible['name']} (vence {follow_up['due_date']}).",
                        "actor": actor,
                        "at": completed_at,
                    }
                )

        records.append(
            {
                "id": record_id,
                "employee_id": employee["id"],
                "employee_name": employee["name"],
                "employee_email": employee["email"],
                "site": site,
                "role": role,
                "shift": shift,
                "status": status,
                "criteria_results": criteria_results,
                "presentation_notes": presentation_notes,
                "tattoo_notes": tattoo_notes,
                "evidence_filename": evidence_filename,
                "result": result,
                "follow_up": follow_up,
                "created_at": iso(created_at),
                "started_at": started_at,
                "completed_at": completed_at,
                "history": history,
            }
        )
    return records


@lru_cache(maxsize=1)
def monthly_series() -> list[dict]:
    profile = MonthlyProfile(
        base_active_ratio=0.3,
        executions_per_active=1.1,
        success_rate=0.7,  # fraction of monthly reviews completed as "approved" (demo assumption)
        manual_minutes=15,
        assisted_minutes=6,
        satisfaction_response_rate=0.3,
        satisfaction_mean=4.2,
    )
    return generate_monthly_series("appearance.monthly", "appearance", profile)


def initial_state() -> dict:
    return {
        "records": showcase_records(),
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "results": [{"slug": r, "label": RESULT_LABELS[r]} for r in RESULT_SLUGS],
        "shifts": [{"slug": s, "label": SHIFT_LABELS[s]} for s in SHIFT_SLUGS],
        "roles": [{"slug": r, "label": ROLE_LABELS[r]} for r in ROLE_SLUGS],
        "criteria": CRITERIA,
        "sites": SITES,
        "employees": eligible_population("appearance"),
        "monthly_series": monthly_series(),
        "last_sync": iso(reference_datetime() - timedelta(minutes=22)),
    }


def catalog_summary() -> dict:
    records = showcase_records()
    # "Active users" here mirrors HR Colombia Ticketing's choice of
    # `requester_id` as the adoption denominator's numerator: the people the
    # tool is actually about (the collaborators being reviewed), not the
    # small fixed pool of reviewer job titles in REVIEWER_ACTORS.
    active_users = len({r["employee_id"] for r in records})
    last_activity = max((r["history"][-1]["at"] for r in records if r["history"]), default=None)
    open_items = sum(1 for r in records if r["status"] not in TERMINAL_STATUSES)

    completed = [r for r in records if r["status"] == "completed"]
    requires_review = [r for r in completed if r["result"] == "requires_review"]
    requires_review_ratio = (len(requires_review) / len(completed)) if completed else 0.0

    today_str = reference_date().isoformat()
    overdue_follow_ups = sum(
        1 for r in requires_review if r.get("follow_up") and r["follow_up"]["due_date"] < today_str
    )

    if requires_review_ratio > 0.4 or overdue_follow_ups >= 2:
        health = "critical"
    elif requires_review_ratio > 0.2 or overdue_follow_ups >= 1:
        health = "warning"
    else:
        health = "good"

    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
