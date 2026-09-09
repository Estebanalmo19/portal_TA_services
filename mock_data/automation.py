"""Automation Health Center mock dataset.

Ficticious operational data for six internal automations (recruiter
assignment, HiBob<->Heinsohn sync, candidate processing, mailbox tracker,
security reporting and Restricted Companies screening). See
``docs/implementation-notes.md`` for the shared state-contract writeup and
this module's docstrings below for the design decisions specific to this
solution (health formula, retry rule).

**Explicit scope restriction (per the original task brief, section 8.5):**
this module never changes hiring decisions and never references Referral
Portal data (``mock_data.referral``/``solutions.services.referral`` are not
imported here, directly or indirectly), and it never performs a real
integration call — HiBob, Heinsohn, the mail provider and the "restricted
companies" list are all simulated names used purely as flavor text for
``dependencies``/error messages. Nothing in this module opens a network
socket; every "run" is a hand-seeded or server-generated record.

Every timestamp is computed relative to ``mock_data.clock.reference_datetime``
(the frozen demo "now") so the seed data is stable across requests/sessions,
exactly like every other solution's showcase data.
"""

from datetime import timedelta

from .clock import iso, reference_datetime
from .people import eligible_population_count
from .timeseries import MonthlyProfile, generate_monthly_series

HEALTH_LABELS = {
    "good": "Buena",
    "warning": "Atención",
    "critical": "Crítica",
}
HEALTH_SLUGS = list(HEALTH_LABELS.keys())

EXECUTION_STATUS_LABELS = {
    "success": "Éxito",
    "failed": "Fallido",
}
EXECUTION_STATUS_SLUGS = list(EXECUTION_STATUS_LABELS.keys())

# Sanitized, generic failure reasons — never a real stack trace or any data
# that could identify a real person/system. Assigned to failed seed
# executions by cycling through this list by index (deterministic, not
# random), and reused verbatim by the frontend.
ERROR_MESSAGES = [
    "Tiempo de espera agotado al conectar con el proveedor simulado.",
    "El proveedor simulado devolvió un error temporal (5xx).",
    "No se pudo autenticar con el servicio simulado (token de acceso expirado).",
    "Límite de solicitudes alcanzado en el servicio simulado.",
]

# ---------------------------------------------------------------------------
# Automation catalog.
#
# Design decision: rather than randomly generating the six automations (the
# task brief names them literally), each is a small hand-authored profile
# (id, name, description, dependencies, run cadence, typical duration,
# estimated weekly hours saved) plus a hand-authored, deterministic sequence
# of seed executions (`outcomes`: a list of ("success"|"failed",
# records_processed) tuples, oldest first). Hand-authoring the 16 seed
# executions (instead of a seeded RNG) keeps the demo narrative legible and
# guarantees the intended spread of health states (good/warning/critical)
# and at least one failed run per automation that needs a "retry" demo,
# without needing a hidden random seed to reproduce it.
# ---------------------------------------------------------------------------
_AUTOMATION_DEFS = [
    {
        "id": "AUTO-0001",
        "name": "Asignación de Recruiters",
        "description": "Asigna automáticamente un recruiter disponible a cada vacante nueva según carga de trabajo.",
        "dependencies": ["HiBob API (simulada)", "Calendario de disponibilidad (simulado)"],
        "frequency_label": "Cada 2 horas",
        "interval_hours": 2,
        "typical_duration_seconds": 45,
        "hours_saved_per_week": 6.5,
        "paused": False,
        "outcomes": [("success", 12), ("success", 15), ("success", 14)],
    },
    {
        "id": "AUTO-0002",
        "name": "Sincronización HiBob–Heinsohn",
        "description": "Sincroniza cambios de nómina y estructura organizacional entre HiBob y Heinsohn.",
        "dependencies": ["HiBob API (simulada)", "Heinsohn ERP (simulado)"],
        "frequency_label": "Diaria",
        "interval_hours": 24,
        "typical_duration_seconds": 240,
        "hours_saved_per_week": 10.0,
        "paused": False,
        "outcomes": [("failed", 150), ("success", 148), ("failed", 152)],
    },
    {
        "id": "AUTO-0003",
        "name": "Procesamiento de Candidatos",
        "description": "Normaliza y clasifica hojas de vida entrantes antes de pasarlas al equipo de reclutamiento.",
        "dependencies": ["ATS interno (simulado)", "Bandeja de correo (simulada)"],
        "frequency_label": "Cada hora",
        "interval_hours": 1,
        "typical_duration_seconds": 90,
        "hours_saved_per_week": 14.0,
        "paused": False,
        "outcomes": [("success", 22), ("success", 27)],
    },
    {
        "id": "AUTO-0004",
        "name": "Mailbox Tracker",
        "description": "Rastrea y clasifica correos entrantes de la bandeja compartida de operaciones.",
        "dependencies": ["Bandeja de correo (simulada)", "Reglas de clasificación (simuladas)"],
        "frequency_label": "Cada 30 minutos",
        "interval_hours": 0.5,
        "typical_duration_seconds": 30,
        "hours_saved_per_week": 4.5,
        "paused": True,
        "outcomes": [("success", 38), ("failed", 41), ("success", 39)],
    },
    {
        "id": "AUTO-0005",
        "name": "Security Reporting",
        "description": "Genera y distribuye el reporte semanal de indicadores de Security Database Hub.",
        "dependencies": ["Security Database Hub (simulado)", "Generador de reportes (simulado)"],
        "frequency_label": "Semanal",
        "interval_hours": 168,
        "typical_duration_seconds": 600,
        "hours_saved_per_week": 8.0,
        "paused": False,
        "outcomes": [("success", 1), ("success", 1)],
    },
    {
        "id": "AUTO-0006",
        "name": "Restricted Companies Screening",
        "description": "Verifica nuevas contrapartes contra la lista de compañías restringidas.",
        "dependencies": ["Lista de compañías restringidas (simulada)", "ATS interno (simulado)"],
        "frequency_label": "Diaria",
        "interval_hours": 24,
        "typical_duration_seconds": 120,
        "hours_saved_per_week": 5.5,
        "paused": False,
        "outcomes": [("success", 298), ("success", 305), ("failed", 300)],
    },
]
AUTOMATION_IDS = [a["id"] for a in _AUTOMATION_DEFS]

# ---------------------------------------------------------------------------
# Health formula (also mirrored, read-only, by the retry endpoint in
# solutions.services.automation.recompute_health so Python stays the single
# source of truth): looks at up to the last 5 executions of an automation
# (oldest ones drop off) and buckets the success ratio into
# good (>=0.8) / warning (>=0.5) / critical (<0.5). This mirrors the
# resolved/closed-ratio heuristic already used by Security Database Hub's
# ``catalog_summary`` (see mock_data.security), applied per-automation
# instead of portfolio-wide.
# ---------------------------------------------------------------------------
def _health_from_statuses(statuses: list[str]) -> str:
    recent = [s for s in statuses if s in EXECUTION_STATUS_SLUGS][-5:]
    if not recent:
        return "warning"
    ratio = recent.count("success") / len(recent)
    if ratio >= 0.8:
        return "good"
    if ratio >= 0.5:
        return "warning"
    return "critical"


def _build_executions_and_automations():
    reference = reference_datetime()
    automations = []
    executions = []
    error_cycle_index = 0

    for definition in _AUTOMATION_DEFS:
        interval = timedelta(hours=definition["interval_hours"])
        outcomes = definition["outcomes"]
        run_count = len(outcomes)
        # Newest run happened half an interval ago; next run is therefore
        # half an interval from now — always in the future relative to the
        # frozen "now", regardless of cadence. Older runs step back one full
        # interval at a time from there.
        last_run_at = reference - (interval / 2)
        next_run_at = last_run_at + interval

        automation_executions = []
        for idx, (status, records_processed) in enumerate(outcomes):
            steps_before_last = run_count - 1 - idx
            started_at = last_run_at - (interval * steps_before_last)
            if status == "failed":
                duration_seconds = max(5, int(definition["typical_duration_seconds"] * 0.4))
                error = ERROR_MESSAGES[error_cycle_index % len(ERROR_MESSAGES)]
                error_cycle_index += 1
            else:
                duration_seconds = definition["typical_duration_seconds"]
                error = None
            run_id = f"RUN-{len(executions) + len(automation_executions) + 1:04d}"
            automation_executions.append(
                {
                    "id": run_id,
                    "automation_id": definition["id"],
                    "started_at": iso(started_at),
                    "duration_seconds": duration_seconds,
                    "status": status,
                    "records_processed": records_processed,
                    "error": error,
                    "retry_of": None,
                }
            )
        executions.extend(automation_executions)

        statuses = [e["status"] for e in automation_executions]
        successes = statuses.count("success")
        history = [
            {
                "type": "created",
                "detail": "Automatización registrada en Automation Health Center.",
                "actor": "Sistema de automatización",
                "at": iso(reference - (interval * run_count)),
            }
        ]
        if definition["paused"]:
            history.append(
                {
                    "type": "paused",
                    "detail": "Automatización pausada manualmente (simulado, no interrumpe ninguna integración real).",
                    "actor": "Operador Demo",
                    "at": iso(last_run_at + (interval / 4)),
                }
            )

        automations.append(
            {
                "id": definition["id"],
                "name": definition["name"],
                "description": definition["description"],
                "dependencies": list(definition["dependencies"]),
                "frequency_label": definition["frequency_label"],
                "typical_duration_seconds": definition["typical_duration_seconds"],
                "hours_saved_per_week": definition["hours_saved_per_week"],
                "paused": definition["paused"],
                "health": _health_from_statuses(statuses),
                "last_run_at": iso(last_run_at),
                "next_run_at": iso(next_run_at),
                "success_rate": round(successes / run_count, 2) if run_count else None,
                "records_processed_last_run": automation_executions[-1]["records_processed"],
                "records_processed_total": sum(e["records_processed"] for e in automation_executions),
                "history": history,
            }
        )

    return automations, executions


def showcase_automations() -> list[dict]:
    automations, _ = _build_executions_and_automations()
    return automations


def showcase_executions() -> list[dict]:
    _, executions = _build_executions_and_automations()
    return executions


def monthly_series() -> list[dict]:
    profile = MonthlyProfile(
        base_active_ratio=0.5,
        executions_per_active=3.0,
        success_rate=0.85,  # fraction of monthly automation runs ending in success (demo assumption)
        manual_minutes=25,
        assisted_minutes=3,
        satisfaction_response_rate=0.3,
        satisfaction_mean=4.2,
    )
    return generate_monthly_series("automation.monthly", "automation", profile)


def initial_state() -> dict:
    automations, executions = _build_executions_and_automations()
    return {
        "automations": automations,
        "executions": executions,
        "health_statuses": [{"slug": s, "label": HEALTH_LABELS[s]} for s in HEALTH_SLUGS],
        "execution_statuses": [{"slug": s, "label": EXECUTION_STATUS_LABELS[s]} for s in EXECUTION_STATUS_SLUGS],
        "monthly_series": monthly_series(),
        "last_sync": iso(reference_datetime() - timedelta(minutes=12)),
    }


def catalog_summary() -> dict:
    automations, executions = _build_executions_and_automations()

    # This solution has no direct human "operators" the way a ticketing
    # queue does — automations run unattended. As a reasonable stand-in for
    # "active users" we use the eligible population for this solution
    # (mock_data.reference.SOLUTIONS["automation"]["eligible_areas"] =
    # ta/data-analytics/operations, i.e. the areas that consume or maintain
    # these automations' output), same denominator concept the dashboard
    # already uses for adoption elsewhere. See mock_data.people for the
    # shared helper.
    active_users = eligible_population_count("automation")

    last_activity = max((e["started_at"] for e in executions), default=None)
    open_items = sum(1 for a in automations if a["health"] != "good" or a["paused"])

    if any(a["health"] == "critical" for a in automations):
        health = "critical"
    elif any(a["health"] == "warning" for a in automations):
        health = "warning"
    else:
        health = "good"

    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
