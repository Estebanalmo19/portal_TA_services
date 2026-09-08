"""Referral Portal mock dataset.

Adoption/health assumptions used here are documented inline; see
``docs/implementation-notes.md`` for the shared state-contract writeup.
"""

from functools import lru_cache

from .clock import days_ago, iso, new_rng
from .people import employees
from .reference import COUNTRY_SLUGS
from .timeseries import MonthlyProfile, generate_monthly_series

STATUS_LABELS = {
    "submitted": "Enviado",
    "under_review": "En revisión",
    "recruiter_assigned": "Reclutador asignado",
    "interview": "Entrevista",
    "hired": "Contratado",
    "rejected": "Rechazado",
}
STATUS_SLUGS = list(STATUS_LABELS.keys())
TERMINAL_STATUSES = {"hired", "rejected"}

TRANSITIONS = {
    "submitted": {"under_review", "rejected"},
    "under_review": {"recruiter_assigned", "rejected"},
    "recruiter_assigned": {"interview", "rejected"},
    "interview": {"hired", "rejected"},
    "hired": set(),
    "rejected": set(),
}

RELATIONS = [
    {"slug": "ex_colega", "label": "Ex colega"},
    {"slug": "amigo", "label": "Amigo/a"},
    {"slug": "familiar", "label": "Familiar"},
    {"slug": "conocido", "label": "Conocido/a"},
]

JOB_OPENINGS = [
    {"id": "VAC-101", "title": "Recruiter Senior TA", "country": "co"},
    {"id": "VAC-102", "title": "Analista de Datos Jr.", "country": "co"},
    {"id": "VAC-103", "title": "Especialista en Seguridad Física", "country": "bg"},
    {"id": "VAC-104", "title": "Coordinador de Operaciones", "country": "rs"},
    {"id": "VAC-105", "title": "HR Business Partner", "country": "co"},
    {"id": "VAC-106", "title": "Ingeniero de Automatizaciones", "country": "ge"},
    {"id": "VAC-107", "title": "Analista de Cumplimiento", "country": "bg"},
    {"id": "VAC-108", "title": "Supervisor de Piso", "country": "co"},
    {"id": "VAC-109", "title": "Especialista en Screening", "country": "rs"},
    {"id": "VAC-110", "title": "Reclutador Bilingüe", "country": "co"},
]
JOB_OPENING_BY_ID = {j["id"]: j for j in JOB_OPENINGS}

CANDIDATE_FIRST_NAMES = [
    "Sofia", "Mateo", "Valentina", "Samuel", "Isabella", "Nicolas", "Camila",
    "Sebastian", "Maria", "Andres", "Daniela", "Julian", "Laura", "David",
    "Manuela", "Carlos", "Paula", "Diego", "Sara", "Felipe",
]
CANDIDATE_LAST_NAMES = [
    "Restrepo", "Gomez", "Rodriguez", "Martinez", "Hernandez", "Lopez",
    "Diaz", "Moreno", "Castro", "Vargas", "Suarez", "Romero",
]


def _random_candidate(rng):
    first = rng.choice(CANDIDATE_FIRST_NAMES)
    last = rng.choice(CANDIDATE_LAST_NAMES)
    return f"{first} {last} (candidato demo)"


@lru_cache(maxsize=1)
def showcase_records() -> list[dict]:
    rng = new_rng("referral.showcase")
    staff = employees()
    records = []
    status_cycle = (
        ["submitted"] * 4
        + ["under_review"] * 4
        + ["recruiter_assigned"] * 3
        + ["interview"] * 3
        + ["hired"] * 3
        + ["rejected"] * 4
    )
    rng.shuffle(status_cycle)

    for i, status in enumerate(status_cycle, start=1):
        record_id = f"REF-{i:04d}"
        vacancy = rng.choice(JOB_OPENINGS)
        referrer = rng.choice(staff)
        age_days = rng.randint(1, 150)
        created_at = days_ago(age_days)

        history = [
            {
                "type": "created",
                "detail": "Referido registrado.",
                "actor": referrer["name"],
                "at": iso(created_at),
            }
        ]
        order = ["submitted", "under_review", "recruiter_assigned", "interview", status]
        seen = []
        for step in order:
            if step in seen:
                continue
            seen.append(step)
            if step == "submitted":
                continue
            history.append(
                {
                    "type": "status_change",
                    "detail": f"Cambio de etapa a «{STATUS_LABELS[step]}».",
                    "actor": "Reclutador Demo",
                    "at": iso(days_ago(max(age_days - seen.index(step) * 5, 0))),
                }
            )
            if step == status:
                break

        records.append(
            {
                "id": record_id,
                "candidate_name": _random_candidate(rng),
                "vacancy_id": vacancy["id"],
                "vacancy_title": vacancy["title"],
                "country": vacancy["country"],
                "referrer_id": referrer["id"],
                "referrer_name": referrer["name"],
                "referrer_email": referrer["email"],
                "relation": rng.choice(RELATIONS)["slug"],
                "candidate_email": f"candidato.demo.{i:03d}@example.com",
                "cv_filename": f"cv_demo_{i:03d}.pdf",
                "status": status,
                "notes": [],
                "history": history,
                "created_at": iso(created_at),
            }
        )
    return records


@lru_cache(maxsize=1)
def monthly_series() -> list[dict]:
    profile = MonthlyProfile(
        base_active_ratio=0.28,
        executions_per_active=1.3,
        success_rate=0.55,  # fraction of finished referrals that end Hired
        manual_minutes=40,
        assisted_minutes=12,
        satisfaction_response_rate=0.4,
        satisfaction_mean=4.1,
    )
    return generate_monthly_series("referral.monthly", "referral", profile)


def initial_state() -> dict:
    return {
        "records": showcase_records(),
        "job_openings": JOB_OPENINGS,
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "relations": RELATIONS,
        "countries": COUNTRY_SLUGS,
    }


def catalog_summary() -> dict:
    records = showcase_records()
    active_users = len({r["referrer_id"] for r in records})
    last_activity = max((r["history"][-1]["at"] for r in records), default=None)
    open_items = sum(1 for r in records if r["status"] not in TERMINAL_STATUSES)
    hired = sum(1 for r in records if r["status"] == "hired")
    rejected = sum(1 for r in records if r["status"] == "rejected")
    finished = hired + rejected
    success_rate = (hired / finished) if finished else None
    if success_rate is None:
        health = "warning"
    elif success_rate >= 0.4:
        health = "good"
    elif success_rate >= 0.2:
        health = "warning"
    else:
        health = "critical"
    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
