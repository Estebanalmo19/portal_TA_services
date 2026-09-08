"""Security Database Hub domain logic. Pure functions: Django never stores an
incident between requests — every operation receives (and returns) the slice
of state it needs; see ``core.state`` and ``docs/implementation-notes.md``.

``GRAPH`` mirrors ``mock_data.security.TRANSITIONS`` — see that module's
docstring for why ``resolved``/``closed`` are not modeled as dead-end
(``terminal``) nodes here: both allow reopening back to ``in_progress``.
"""

import csv
import io

from mock_data.people import eligible_population
from mock_data.reference import SITE_BY_SLUG
from mock_data.security import (
    CATEGORY_LABELS,
    CATEGORY_SLUGS,
    SEVERITY_LABELS,
    SEVERITY_SLUGS,
    STATUS_LABELS,
    TRANSITIONS,
)

from .common import TransitionGraph, ValidationError, Validator, csv_cell, history_entry, next_id, now_iso, sanitize_text

SITE_SLUGS = list(SITE_BY_SLUG.keys())
GRAPH = TransitionGraph(TRANSITIONS, terminal=set())


def _security_staff_by_id() -> dict:
    return {e["id"]: e for e in eligible_population("security")}


def create_incident(payload: dict) -> dict:
    v = Validator()
    title = v.text(payload, "title", label="Título", max_length=140, min_length=3)
    description = v.text(payload, "description", label="Descripción", max_length=1000, min_length=5)
    v.choice(payload, "site", SITE_SLUGS, label="Sede")
    floor = v.text(payload, "floor", label="Piso", max_length=40, min_length=1)
    v.choice(payload, "category", CATEGORY_SLUGS, label="Categoría")
    v.choice(payload, "severity", SEVERITY_SLUGS, label="Severidad")
    v.raise_if_errors()

    assignee_id = payload.get("assignee_id") or None
    assignee_name = None
    status = "new"
    if assignee_id:
        staff_by_id = _security_staff_by_id()
        if assignee_id not in staff_by_id:
            raise ValidationError({"assignee_id": "Responsable: selecciona un colaborador de Security válido."})
        assignee_name = staff_by_id[assignee_id]["name"]
        status = "assigned"

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("INC", existing_ids)
    actor = sanitize_text(payload.get("actor") or "Analista de Seguridad Demo")

    history = [history_entry("created", "Incidente registrado.", actor=actor)]
    if assignee_name:
        history.append(history_entry("assigned", f"Incidente asignado a {assignee_name}.", actor=actor))

    record = {
        "id": new_id,
        "title": sanitize_text(title),
        "description": sanitize_text(description),
        "site": v.cleaned["site"],
        "floor": sanitize_text(floor),
        "category": v.cleaned["category"],
        "severity": v.cleaned["severity"],
        "status": status,
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "created_at": now_iso(),
        "last_sync": now_iso(),
        "history": history,
    }
    return {"record": record}


def assign_incident(payload: dict) -> dict:
    incident_id = payload.get("id")
    if not incident_id:
        raise ValidationError({"id": "Falta el identificador del incidente."})
    current_status = payload.get("current_status")
    assignee_id = payload.get("assignee_id")

    staff_by_id = _security_staff_by_id()
    if assignee_id not in staff_by_id:
        raise ValidationError({"assignee_id": "Responsable: selecciona un colaborador de Security válido."})
    assignee = staff_by_id[assignee_id]

    new_status = current_status
    if current_status == "new":
        GRAPH.validate("new", "assigned")
        new_status = "assigned"

    entry = history_entry(
        "assigned",
        f"Incidente asignado a {assignee['name']}.",
        actor=sanitize_text(payload.get("actor") or "Coordinador de Seguridad Demo"),
    )
    return {
        "id": incident_id,
        "assignee_id": assignee["id"],
        "assignee_name": assignee["name"],
        "status": new_status,
        "history_entry": entry,
    }


def transition_incident(payload: dict) -> dict:
    incident_id = payload.get("id")
    if not incident_id:
        raise ValidationError({"id": "Falta el identificador del incidente."})
    current_status = payload.get("current_status")
    target_status = payload.get("target_status")
    GRAPH.validate(current_status, target_status)

    entry = history_entry(
        "status_change",
        f"Cambio de estado de «{STATUS_LABELS.get(current_status, current_status)}» a «{STATUS_LABELS.get(target_status, target_status)}».",
        actor=sanitize_text(payload.get("actor") or "Analista de Seguridad Demo"),
    )
    notify = f"El incidente {incident_id} cambió a «{STATUS_LABELS.get(target_status, target_status)}»."
    return {"id": incident_id, "status": target_status, "history_entry": entry, "notify": notify}


def allowed_next_statuses(current_status: str) -> list[str]:
    return sorted(GRAPH.allowed_next(current_status))


_EXPORT_FIELDS = [
    ("id", "ID"),
    ("title", "Título"),
    ("site", "Sede"),
    ("floor", "Piso"),
    ("category", "Categoría"),
    ("severity", "Severidad"),
    ("status", "Estado"),
    ("assignee_name", "Responsable"),
    ("created_at", "Creado"),
    ("last_sync", "Última sincronización"),
]


def export_incidents_csv(rows: list) -> str:
    """Build a CSV export of the incident rows the browser currently has in
    view (already filtered/sorted client-side — there is no server-side
    store to query, see module docstring). Every cell goes through
    ``csv_cell`` to neutralize spreadsheet-formula injection, and category/
    severity/status slugs are translated to their Spanish labels."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([csv_cell(label) for _, label in _EXPORT_FIELDS])
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = []
        for field, _ in _EXPORT_FIELDS:
            value = row.get(field, "")
            if field == "category":
                value = CATEGORY_LABELS.get(value, value)
            elif field == "severity":
                value = SEVERITY_LABELS.get(value, value)
            elif field == "status":
                value = STATUS_LABELS.get(value, value)
            values.append(csv_cell(sanitize_text(value) if isinstance(value, str) else value))
        writer.writerow(values)
    return buf.getvalue()
