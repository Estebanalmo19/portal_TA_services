"""Solutions Support domain logic. Pure functions: Django never stores a
ticket between requests — every operation receives (and returns) the slice
of state it needs; see ``core.state`` and ``docs/implementation-notes.md``.

Status graph (source of truth; the JS module only mirrors it to disable
buttons the server would reject anyway)::

    new                     -> assigned
    assigned                -> in_progress, waiting_for_requester, resolved
    in_progress             -> waiting_for_requester, resolved
    waiting_for_requester   -> in_progress, resolved
    resolved                -> closed (confirm resolution), in_progress (reopen)
    closed                  -> (terminal)

Assigning a ticket that is still ``new`` also advances it to ``assigned``
(handled by :func:`assign_ticket`); re-assigning a ticket already past
``new`` only changes the owner. "Confirmar resolución" and "reabrir" are
both plain transitions out of ``resolved`` (to ``closed``/``in_progress``
respectively) routed through :func:`transition_ticket`, which keeps the
full history either way — reopening never resets or drops prior entries.
"""

from mock_data.clock import reference_datetime
from mock_data.people import employees_by_id
from mock_data.support import (
    AFFECTED_SOLUTION_SLUGS,
    IMPACT_SLUGS,
    PRIORITY_SLUGS,
    SLA_HOURS_BY_PRIORITY,
    STATUS_LABELS,
    TICKET_TYPE_SLUGS,
    TRANSITIONS,
)

from .common import TransitionGraph, ValidationError, Validator, history_entry, next_id, now_iso, parse_iso, sanitize_text

GRAPH = TransitionGraph(TRANSITIONS, terminal={"closed"})

# Ticket types that tend to indicate something is actually broken (as
# opposed to a request/question/suggestion) — used only to break the tie
# between the two suggested-priority options for a given impact, see
# ``suggested_priority`` below.
_URGENCY_LEANING_TYPES = {"problema_tecnico", "datos_incorrectos"}

# Demo-only priority suggestion ("Guía de demostración"), per the brief:
# solo_yo -> baja/media, mi_equipo -> media/alta, bloquea_operacion ->
# alta/urgente. It is a pure function of (impact, ticket_type): the ticket
# type only nudges between the two options documented for that impact, it
# never invents a priority outside that pair. The user can always override
# the result in the form before submitting — this never blocks a create.
_PRIORITY_OPTIONS_BY_IMPACT = {
    "solo_yo": ("baja", "media"),
    "mi_equipo": ("media", "alta"),
    "bloquea_operacion": ("alta", "urgente"),
}


def suggested_priority(impact: str, ticket_type: str | None = None) -> str:
    calm, urgent = _PRIORITY_OPTIONS_BY_IMPACT.get(impact, ("media", "media"))
    return urgent if ticket_type in _URGENCY_LEANING_TYPES else calm


def sla_hours_for(priority: str) -> int:
    """Demo SLA in hours by priority ("Guía de demostración") — ficticio,
    documented here and in ``mock_data.support.SLA_HOURS_BY_PRIORITY``."""
    return SLA_HOURS_BY_PRIORITY.get(priority, 48)


def is_overdue(created_at: str, priority: str, status: str) -> bool:
    """A ticket is "vencido" (overdue) if it is still open (not resolved or
    closed) and more hours than its priority's demo SLA have elapsed since
    ``created_at``, measured against the frozen demo reference clock."""
    if status in ("resolved", "closed"):
        return False
    try:
        created = parse_iso(created_at)
    except (ValueError, TypeError):
        return False
    elapsed_hours = (reference_datetime().replace(tzinfo=None) - created).total_seconds() / 3600
    return elapsed_hours > sla_hours_for(priority)


def create_ticket(payload: dict) -> dict:
    v = Validator()
    v.choice(payload, "affected_solution", AFFECTED_SOLUTION_SLUGS, label="Solución afectada")
    v.choice(payload, "ticket_type", TICKET_TYPE_SLUGS, label="Tipo de ticket")
    subject = v.text(payload, "subject", label="Asunto", max_length=160, min_length=3)
    description = v.text(payload, "description", label="Descripción", max_length=4000, min_length=5)
    v.choice(payload, "impact", IMPACT_SLUGS, label="Impacto")
    v.choice(payload, "priority", PRIORITY_SLUGS, label="Prioridad", required=False, default=None)
    repro_steps = v.text(payload, "repro_steps", label="Pasos para reproducir", max_length=2000, required=False, default="")
    requester_id = payload.get("requester_id")
    if requester_id not in employees_by_id():
        v.errors["requester_id"] = "Solicitante: selecciona un colaborador válido."
    v.raise_if_errors()

    requester = employees_by_id()[requester_id]
    priority = v.cleaned["priority"] or suggested_priority(v.cleaned["impact"], v.cleaned["ticket_type"])
    attachments = payload.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []
    attachments = [sanitize_text(a)[:120] for a in attachments if str(a).strip()][:5]

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("SUP", existing_ids)

    record = {
        "id": new_id,
        "affected_solution": v.cleaned["affected_solution"],
        "ticket_type": v.cleaned["ticket_type"],
        "subject": sanitize_text(subject),
        "description": sanitize_text(description),
        "impact": v.cleaned["impact"],
        "priority": priority,
        "repro_steps": sanitize_text(repro_steps),
        "requester_id": requester_id,
        "requester_name": requester["name"],
        "assignee_id": None,
        "assignee_name": None,
        "attachments": attachments,
        "status": "new",
        "rating": None,
        "notes": [],
        "history": [history_entry("created", f"Ticket registrado: «{subject}».", actor=requester["name"])],
        "created_at": now_iso(),
    }
    return {"record": record}


def assign_ticket(payload: dict) -> dict:
    ticket_id = payload.get("id")
    if not ticket_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    v = Validator()
    assignee_id = payload.get("assignee_id")
    if assignee_id not in employees_by_id():
        v.errors["assignee_id"] = "Responsable: selecciona un colaborador válido."
    v.raise_if_errors()

    current_status = payload.get("current_status")
    assignee = employees_by_id()[assignee_id]
    new_status = "assigned" if current_status == "new" else current_status
    if new_status not in GRAPH.edges:
        raise ValidationError({"status": "Estado actual desconocido."})

    entry = history_entry(
        "assigned",
        f"Ticket asignado a {assignee['name']}.",
        actor=sanitize_text(payload.get("actor") or "Manager Demo"),
    )
    return {
        "id": ticket_id,
        "assignee_id": assignee_id,
        "assignee_name": assignee["name"],
        "status": new_status,
        "history_entry": entry,
    }


def transition_ticket(payload: dict) -> dict:
    ticket_id = payload.get("id")
    current_status = payload.get("current_status")
    target_status = payload.get("target_status")
    if not ticket_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    GRAPH.validate(current_status, target_status)

    if current_status == "resolved" and target_status == "closed":
        detail = "Resolución confirmada por el solicitante."
    elif current_status == "resolved" and target_status == "in_progress":
        detail = "Ticket reabierto: continúa en «En progreso», conservando su historial."
    else:
        detail = f"Cambio de estado de «{STATUS_LABELS.get(current_status, current_status)}» a «{STATUS_LABELS.get(target_status, target_status)}»."

    entry = history_entry("status_change", detail, actor=sanitize_text(payload.get("actor") or "Manager Demo"))
    notify = f"Tu ticket {ticket_id} cambió a «{STATUS_LABELS.get(target_status, target_status)}»."
    return {"id": ticket_id, "status": target_status, "history_entry": entry, "notify": notify}


def add_comment(payload: dict) -> dict:
    v = Validator()
    ticket_id = payload.get("id")
    if not ticket_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    note_text = v.text(payload, "note", label="Comentario", max_length=1000, min_length=2)
    v.raise_if_errors()
    entry = history_entry("comment", note_text, actor=sanitize_text(payload.get("actor") or "Colaborador Demo"))
    return {"id": ticket_id, "note": entry}


def rate_ticket(payload: dict) -> dict:
    ticket_id = payload.get("id")
    if not ticket_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    current_status = payload.get("current_status")
    if current_status not in ("resolved", "closed"):
        raise ValidationError({"status": "Solo se puede valorar un ticket resuelto o cerrado."})
    try:
        score = int(payload.get("score"))
    except (TypeError, ValueError):
        score = None
    if score is None or score < 1 or score > 5:
        raise ValidationError({"score": "Valoración: elige un puntaje entre 1 y 5."})
    comment = sanitize_text(payload.get("comment") or "")[:500]

    rating = {"score": score, "comment": comment, "at": now_iso()}
    entry = history_entry(
        "rated",
        f"Valoración del solicitante: {score}/5." + (f" «{comment}»" if comment else ""),
        actor=sanitize_text(payload.get("actor") or "Solicitante Demo"),
    )
    return {"id": ticket_id, "rating": rating, "history_entry": entry}


def allowed_next_statuses(current_status: str) -> list[str]:
    return sorted(GRAPH.allowed_next(current_status))
