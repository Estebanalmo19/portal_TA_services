"""Automation Health Center domain logic. Pure functions: Django never
stores an automation or execution between requests — every operation
receives (and returns) the slice of state it needs; see ``core.state`` and
``docs/implementation-notes.md``.

Scope restriction (mirrors ``mock_data.automation``'s module docstring):
nothing here touches Referral Portal data or performs a real integration
call. Both operations below (retry, pause/resume) are pure, deterministic
functions over the payload the browser already holds in
``ArrisePortal.state.solutions.automation``.
"""

from mock_data.automation import AUTOMATION_IDS, EXECUTION_STATUS_SLUGS

from .common import ValidationError, Validator, history_entry, next_id, now_iso, sanitize_text


def recompute_health(statuses: list[str]) -> str:
    """Same bucketing used to seed the demo data
    (``mock_data.automation._health_from_statuses``): looks at up to the
    last 5 known execution statuses (oldest ones drop off) and buckets the
    success ratio into good (>=0.8) / warning (>=0.5) / critical (<0.5).
    Kept as a small standalone copy (rather than importing the "private"
    seeding helper) because this is the one that runs on live,
    browser-supplied history after a retry — the seeding module's version
    only ever runs once, at import time, over hand-authored data."""
    recent = [s for s in statuses if s in EXECUTION_STATUS_SLUGS][-5:]
    if not recent:
        return "warning"
    ratio = recent.count("success") / len(recent)
    if ratio >= 0.8:
        return "good"
    if ratio >= 0.5:
        return "warning"
    return "critical"


def retry_execution(payload: dict) -> dict:
    """Simulate retrying a failed execution.

    Deterministic retry rule (documented per the task brief, which left the
    exact rule open): **every retry of a failed run is simulated as having
    resolved the transient problem, so it always succeeds.** This makes the
    outcome a pure function of "this is a retry" — reproducible and free of
    any unseeded ``random()`` call — rather than trying to model a second,
    independent failure probability for what is already a simulated,
    no-network-call action. The original failed execution is never touched:
    this always returns a brand-new execution record (a new ``RUN-xxxx``
    id), so the failure stays visible in history exactly as it happened.
    """
    v = Validator()
    automation_id = v.id_ref(payload, "automation_id", set(AUTOMATION_IDS), label="Automatización")
    execution_id = v.text(payload, "execution_id", label="Ejecución original", max_length=40, min_length=3)
    v.raise_if_errors()

    records_processed = payload.get("records_processed", 0)
    if not isinstance(records_processed, int) or isinstance(records_processed, bool) or records_processed < 0:
        raise ValidationError({"records_processed": "Registros procesados: valor inválido."})

    duration_seconds = payload.get("typical_duration_seconds", 30)
    if not isinstance(duration_seconds, (int, float)) or isinstance(duration_seconds, bool) or duration_seconds <= 0:
        duration_seconds = 30

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("RUN", existing_ids)

    recent_statuses_raw = payload.get("recent_statuses") or []
    recent_statuses = [s for s in recent_statuses_raw if s in EXECUTION_STATUS_SLUGS]

    actor = sanitize_text(payload.get("actor") or "Operador Demo")

    new_execution = {
        "id": new_id,
        "automation_id": automation_id,
        "started_at": now_iso(),
        "duration_seconds": int(duration_seconds),
        "status": "success",
        "records_processed": records_processed,
        "error": None,
        "retry_of": execution_id,
    }

    health = recompute_health(recent_statuses + ["success"])

    entry = history_entry(
        "retry",
        f"Reintento de {execution_id} generó {new_id} con resultado exitoso (simulado).",
        actor=actor,
    )
    notify = f"La automatización {automation_id} tuvo un reintento exitoso ({new_id})."
    return {"execution": new_execution, "health": health, "history_entry": entry, "notify": notify}


def set_paused(payload: dict) -> dict:
    """Pause/resume an automation. A simple boolean flip — no
    ``TransitionGraph`` needed (see task brief) — but still validated
    through ``Validator`` like every other write in this project."""
    v = Validator()
    automation_id = v.id_ref(payload, "automation_id", set(AUTOMATION_IDS), label="Automatización")
    paused = v.choice(payload, "paused", [True, False], label="Estado de pausa")
    v.raise_if_errors()

    actor = sanitize_text(payload.get("actor") or "Operador Demo")
    label = "pausada" if paused else "reactivada"
    entry = history_entry(
        "paused" if paused else "resumed",
        f"Automatización {label} manualmente (simulado, no interrumpe ninguna integración real).",
        actor=actor,
    )
    return {"automation_id": automation_id, "paused": paused, "history_entry": entry}
