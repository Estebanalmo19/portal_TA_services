"""HR Colombia Ticketing domain logic. Pure functions: Django never stores a
ticket between requests — every operation receives (and returns) the slice
of state it needs; see ``core.state`` and ``docs/implementation-notes.md``.

Transition graph and SLA table are documented in ``mock_data/hr.py`` (single
source of truth); this module only wires that graph and those tables into
validated, mutation-producing operations.
"""

from datetime import timedelta

from django.utils import timezone

from mock_data.hr import (
    CATEGORY_SLUGS,
    PRIORITY_SLUGS,
    STATUS_LABELS,
    TRANSITIONS,
    agents,
    extra_fields_for,
    SLA_HOURS_BY_PRIORITY,
)
from mock_data.people import employees_by_id

from .common import TransitionGraph, ValidationError, Validator, history_entry, next_id, now_iso, sanitize_text

GRAPH = TransitionGraph(TRANSITIONS, terminal={"closed"})


def _agent_ids() -> set:
    return {a["id"] for a in agents()}


def _clean_extra_fields(v: Validator, category: str, raw_extra: dict) -> dict:
    raw_extra = raw_extra if isinstance(raw_extra, dict) else {}
    cleaned = {}
    for spec in extra_fields_for(category):
        name = spec["name"]
        raw_value = raw_extra.get(name, "")
        value = sanitize_text(str(raw_value or ""))[:200]
        if spec.get("required") and not value:
            v.errors[name] = f"{spec['label']}: este campo es obligatorio."
        cleaned[name] = value
    return cleaned


def create_ticket(payload: dict) -> dict:
    v = Validator()
    requester_id = payload.get("requester_id")
    if requester_id not in employees_by_id():
        v.errors["requester_id"] = "Solicitante: selecciona un colaborador válido."
    category = v.choice(payload, "category", CATEGORY_SLUGS, label="Categoría")
    subject = v.text(payload, "subject", label="Asunto", max_length=160, min_length=3)
    description = v.text(payload, "description", label="Descripción", max_length=2000, min_length=5)
    priority = v.choice(payload, "priority", PRIORITY_SLUGS, label="Prioridad")
    attachment_filename = v.text(
        payload, "attachment_filename", label="Adjunto", max_length=120, required=False, default=""
    )
    extra_fields = _clean_extra_fields(v, category, payload.get("extra_fields") or {}) if category else {}
    v.raise_if_errors()

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("HR", existing_ids)
    requester = employees_by_id()[requester_id]
    sla_hours = SLA_HOURS_BY_PRIORITY[priority]
    created_at = timezone.now()
    due_at = created_at + timedelta(hours=sla_hours)

    attachments = []
    if attachment_filename:
        attachments.append({"filename": sanitize_text(attachment_filename), "size_kb": 120})

    record = {
        "id": new_id,
        "requester_id": requester_id,
        "requester_name": requester["name"],
        "requester_email": requester["email"],
        "requester_area": requester["area"],
        "category": category,
        "subject": subject,
        "description": description,
        "extra_fields": extra_fields,
        "priority": priority,
        "sla_hours": sla_hours,
        "assignee_id": None,
        "assignee_name": None,
        "status": "new",
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "due_at": due_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resolved_at": None,
        "closed_at": None,
        "comments": [],
        "attachments": attachments,
        "history": [history_entry("created", "Ticket creado.", actor=requester["name"])],
        "survey": None,
    }
    return {"record": record}


def assign_ticket(payload: dict) -> dict:
    record_id = payload.get("id")
    if not record_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    current_status = payload.get("current_status")
    if current_status not in GRAPH.edges:
        raise ValidationError({"status": "Estado actual desconocido."})

    assignee_id = payload.get("assignee_id")
    if assignee_id not in _agent_ids():
        raise ValidationError({"assignee_id": "Responsable: selecciona un agente de HR válido."})
    assignee = employees_by_id()[assignee_id]

    # Assigning a fresh ticket also moves it out of "new"; reassigning a
    # ticket already in progress keeps its current status untouched.
    target_status = current_status
    if current_status == "new":
        target_status = "assigned"
        GRAPH.validate(current_status, target_status)

    entry = history_entry(
        "assigned",
        f"Ticket asignado a {assignee['name']}.",
        actor=sanitize_text(payload.get("actor") or "Agente HR Demo"),
    )
    return {
        "id": record_id,
        "assignee_id": assignee_id,
        "assignee_name": assignee["name"],
        "status": target_status,
        "history_entry": entry,
    }


def transition_ticket(payload: dict) -> dict:
    record_id = payload.get("id")
    if not record_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    current_status = payload.get("current_status")
    target_status = payload.get("target_status")
    GRAPH.validate(current_status, target_status)

    actor = sanitize_text(payload.get("actor") or "Agente HR Demo")
    entry = history_entry(
        "status_change",
        f"Cambio de estado de «{STATUS_LABELS.get(current_status, current_status)}» a «{STATUS_LABELS.get(target_status, target_status)}».",
        actor=actor,
    )

    result = {
        "id": record_id,
        "status": target_status,
        "history_entry": entry,
        "notify": f"El ticket {record_id} cambió a «{STATUS_LABELS.get(target_status, target_status)}».",
    }

    if target_status == "resolved":
        result["resolved_at"] = now_iso()
        result["closed_at"] = None
    elif target_status == "closed":
        result["closed_at"] = now_iso()
    elif current_status == "resolved" and target_status == "in_progress":
        # Reopen: the ticket is no longer considered resolved.
        result["resolved_at"] = None

    # Optional satisfaction survey, only meaningful the moment a ticket is
    # resolved. Sent by the browser as part of this same transition payload
    # (see docs note in static/js/solutions/hr.js) rather than a separate
    # endpoint, since it only ever applies to this one transition.
    survey_payload = payload.get("survey")
    if target_status == "resolved" and isinstance(survey_payload, dict) and survey_payload.get("score"):
        try:
            score = int(survey_payload.get("score"))
        except (TypeError, ValueError):
            raise ValidationError({"survey": "Encuesta: la calificación debe ser un número."})
        if score < 1 or score > 5:
            raise ValidationError({"survey": "Encuesta: la calificación debe estar entre 1 y 5."})
        comment = sanitize_text(str(survey_payload.get("comment") or ""))[:500]
        result["survey"] = {"score": score, "comment": comment}

    return result


def add_comment(payload: dict) -> dict:
    record_id = payload.get("id")
    if not record_id:
        raise ValidationError({"id": "Falta el identificador del ticket."})
    v = Validator()
    comment_text = v.text(payload, "comment", label="Comentario", max_length=1000, min_length=2)
    v.raise_if_errors()
    entry = history_entry("comment", comment_text, actor=sanitize_text(payload.get("actor") or "Agente HR Demo"))
    return {"id": record_id, "comment": entry}


def allowed_next_statuses(current_status: str) -> list[str]:
    return sorted(GRAPH.allowed_next(current_status))
