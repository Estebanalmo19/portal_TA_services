"""Appearance Check domain logic. Pure functions: Django never stores a
review between requests — every operation receives (and returns) the slice
of state it needs; see ``core.state`` and ``docs/implementation-notes.md``.

Ethical/scope note (see ``mock_data.appearance`` module docstring for the
full write-up, restated briefly here because it directly shapes the
functions below): the checklist criteria are supporting context only.
``complete_review`` never computes ``approved``/``requires_review`` from
``criteria`` — that field is read verbatim from ``payload["resultado"]``,
i.e. it is always an explicit choice made by the human reviewer in the
frontend form, validated the same way any other required choice field is
(``Validator.choice`` against ``RESULT_SLUGS``). No scoring/threshold logic
over the criteria exists anywhere in this module.
"""

import re

from mock_data.appearance import (
    CRITERIA_SLUGS,
    RESULT_LABELS,
    RESULT_SLUGS,
    ROLE_SLUGS,
    SHIFT_SLUGS,
    TRANSITIONS,
)
from mock_data.people import eligible_population
from mock_data.reference import SITE_BY_SLUG

from .common import TransitionGraph, ValidationError, Validator, history_entry, next_id, now_iso, sanitize_text

SITE_SLUGS = list(SITE_BY_SLUG.keys())
GRAPH = TransitionGraph(TRANSITIONS, terminal={"completed"})

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _appearance_staff_by_id() -> dict:
    return {e["id"]: e for e in eligible_population("appearance")}


def create_review(payload: dict) -> dict:
    v = Validator()
    employee_id = payload.get("employee_id")
    staff_by_id = _appearance_staff_by_id()
    if employee_id not in staff_by_id:
        v.errors["employee_id"] = "Colaborador: selecciona un colaborador ficticio válido."
    v.choice(payload, "site", SITE_SLUGS, label="Sede")
    v.choice(payload, "role", ROLE_SLUGS, label="Área/rol")
    v.choice(payload, "shift", SHIFT_SLUGS, label="Turno")
    v.raise_if_errors()

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("APR", existing_ids)
    employee = staff_by_id[employee_id]
    actor = sanitize_text(payload.get("actor") or "Supervisor de Turno Demo")

    record = {
        "id": new_id,
        "employee_id": employee["id"],
        "employee_name": employee["name"],
        "employee_email": employee["email"],
        "site": v.cleaned["site"],
        "role": v.cleaned["role"],
        "shift": v.cleaned["shift"],
        "status": "pending",
        "criteria_results": [],
        "presentation_notes": "",
        "tattoo_notes": "",
        "evidence_filename": None,
        "result": None,
        "follow_up": None,
        "created_at": now_iso(),
        "started_at": None,
        "completed_at": None,
        "history": [history_entry("created", "Revisión programada.", actor=actor)],
    }
    return {"record": record}


def start_review(payload: dict) -> dict:
    review_id = payload.get("id")
    if not review_id:
        raise ValidationError({"id": "Falta el identificador de la revisión."})
    current_status = payload.get("current_status")
    GRAPH.validate(current_status, "in_review")

    actor = sanitize_text(payload.get("actor") or "Supervisor de Turno Demo")
    started_at = now_iso()
    entry = history_entry("started", "Revisión iniciada.", actor=actor)
    return {"id": review_id, "status": "in_review", "started_at": started_at, "history_entry": entry}


def _clean_criteria(v: Validator, raw_criteria) -> list[dict]:
    raw_list = raw_criteria if isinstance(raw_criteria, list) else []
    by_slug = {}
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug")
        if slug not in CRITERIA_SLUGS:
            continue
        by_slug[slug] = {
            "slug": slug,
            "checked": bool(item.get("checked")),
            "note": sanitize_text(str(item.get("note") or ""))[:280],
        }
    cleaned = [by_slug.get(slug, {"slug": slug, "checked": False, "note": ""}) for slug in CRITERIA_SLUGS]
    return cleaned


def _clean_follow_up(v: Validator, resultado: str, raw_follow_up) -> dict | None:
    if resultado != "requires_review":
        return None
    raw_follow_up = raw_follow_up if isinstance(raw_follow_up, dict) else {}
    responsible_id = raw_follow_up.get("responsible_id")
    staff_by_id = _appearance_staff_by_id()
    if responsible_id not in staff_by_id:
        v.errors["responsible_id"] = "Responsable de seguimiento: selecciona un colaborador válido."
        return None
    due_date = str(raw_follow_up.get("due_date") or "").strip()
    if not _DATE_RE.match(due_date):
        v.errors["due_date"] = "Fecha de seguimiento: usa el formato AAAA-MM-DD."
        return None
    responsible = staff_by_id[responsible_id]
    return {"responsible_id": responsible["id"], "responsible_name": responsible["name"], "due_date": due_date}


def complete_review(payload: dict) -> dict:
    review_id = payload.get("id")
    if not review_id:
        raise ValidationError({"id": "Falta el identificador de la revisión."})
    current_status = payload.get("current_status")
    GRAPH.validate(current_status, "completed")

    v = Validator()
    presentation_notes = v.text(
        payload, "presentation_notes", label="Observaciones de presentación", max_length=1000, min_length=3
    )
    tattoo_notes = v.text(
        payload, "tattoo_notes", label="Observaciones sobre tatuajes", max_length=500, required=False, default=""
    )
    evidence_filename = v.text(
        payload, "evidence_filename", label="Evidencia", max_length=120, required=False, default="registro_ingreso_demo.jpg"
    )
    resultado = v.choice(payload, "resultado", RESULT_SLUGS, label="Resultado de la revisión")
    criteria_results = _clean_criteria(v, payload.get("criteria"))
    follow_up = _clean_follow_up(v, resultado, payload.get("follow_up")) if resultado else None
    v.raise_if_errors()

    actor = sanitize_text(payload.get("actor") or "Supervisor de Turno Demo")
    completed_at = now_iso()
    entry = history_entry(
        "completed",
        f"Revisión completada: resultado «{RESULT_LABELS[resultado]}».",
        actor=actor,
    )
    history_entries = [entry]
    if follow_up:
        history_entries.append(
            history_entry(
                "follow_up",
                f"Seguimiento asignado a {follow_up['responsible_name']} (vence {follow_up['due_date']}).",
                actor=actor,
            )
        )

    return {
        "id": review_id,
        "status": "completed",
        "completed_at": completed_at,
        "criteria_results": criteria_results,
        "presentation_notes": sanitize_text(presentation_notes),
        "tattoo_notes": sanitize_text(tattoo_notes) if tattoo_notes else "",
        "evidence_filename": sanitize_text(evidence_filename) or "registro_ingreso_demo.jpg",
        "result": resultado,
        "follow_up": follow_up,
        "history_entries": history_entries,
        "notify": f"La revisión {review_id} se completó como «{RESULT_LABELS[resultado]}».",
    }


def allowed_next_statuses(current_status: str) -> list[str]:
    return sorted(GRAPH.allowed_next(current_status))
