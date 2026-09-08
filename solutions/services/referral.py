"""Referral Portal domain logic. Pure functions: Django never stores a
referral between requests — every operation receives (and returns) the
slice of state it needs; see ``core.state`` and
``docs/implementation-notes.md``."""

from mock_data.people import employees_by_id
from mock_data.reference import COUNTRY_SLUGS
from mock_data.referral import (
    JOB_OPENING_BY_ID,
    RELATIONS,
    STATUS_LABELS,
    STATUS_SLUGS,
    TRANSITIONS,
)

from .common import TransitionGraph, ValidationError, Validator, history_entry, next_id, now_iso, sanitize_text

RELATION_SLUGS = [r["slug"] for r in RELATIONS]
GRAPH = TransitionGraph(TRANSITIONS, terminal={"hired", "rejected"})


def create_referral(payload: dict) -> dict:
    v = Validator()
    candidate_name = v.text(payload, "candidate_name", label="Nombre del candidato", max_length=120, min_length=3)
    v.id_ref(payload, "vacancy_id", set(JOB_OPENING_BY_ID), label="Vacante")
    v.choice(payload, "country", COUNTRY_SLUGS, label="País")
    referrer_id = payload.get("referrer_id")
    if referrer_id not in employees_by_id():
        v.errors["referrer_id"] = "Referente: selecciona un colaborador válido."
    candidate_email = v.text(payload, "candidate_email", label="Correo del candidato", max_length=160, required=False, default="")
    v.choice(payload, "relation", RELATION_SLUGS, label="Relación con el candidato")
    cv_filename = v.text(payload, "cv_filename", label="CV", max_length=120, required=False, default="cv_demo.pdf")
    v.raise_if_errors()

    if candidate_email and "@" not in candidate_email:
        raise ValidationError({"candidate_email": "Correo del candidato: formato inválido."})

    existing_ids = payload.get("existing_ids") or []
    new_id = next_id("REF", existing_ids)
    referrer = employees_by_id()[referrer_id]
    vacancy = JOB_OPENING_BY_ID[v.cleaned["vacancy_id"]]

    record = {
        "id": new_id,
        "candidate_name": candidate_name,
        "vacancy_id": vacancy["id"],
        "vacancy_title": vacancy["title"],
        "country": v.cleaned["country"],
        "referrer_id": referrer_id,
        "referrer_name": referrer["name"],
        "referrer_email": referrer["email"],
        "relation": v.cleaned["relation"],
        "candidate_email": sanitize_text(candidate_email) or f"candidato.demo.{new_id.lower()}@example.com",
        "cv_filename": sanitize_text(cv_filename) or "cv_demo.pdf",
        "status": "submitted",
        "notes": [],
        "history": [history_entry("created", "Referido registrado.", actor=referrer["name"])],
        "created_at": now_iso(),
    }
    return {"record": record}


def transition_referral(payload: dict) -> dict:
    current_status = payload.get("current_status")
    target_status = payload.get("target_status")
    record_id = payload.get("id")
    if not record_id:
        raise ValidationError({"id": "Falta el identificador del referido."})
    GRAPH.validate(current_status, target_status)

    entry = history_entry(
        "status_change",
        f"Cambio de etapa de «{STATUS_LABELS.get(current_status, current_status)}» a «{STATUS_LABELS.get(target_status, target_status)}».",
        actor=sanitize_text(payload.get("actor") or "Reclutador Demo"),
    )
    notify = (
        f"Tu referido {record_id} avanzó a «{STATUS_LABELS.get(target_status, target_status)}»."
    )
    return {"id": record_id, "status": target_status, "history_entry": entry, "notify": notify}


def add_note(payload: dict) -> dict:
    v = Validator()
    record_id = payload.get("id")
    if not record_id:
        raise ValidationError({"id": "Falta el identificador del referido."})
    note_text = v.text(payload, "note", label="Nota", max_length=1000, min_length=2)
    v.raise_if_errors()
    entry = history_entry("comment", note_text, actor=sanitize_text(payload.get("actor") or "Reclutador Demo"))
    return {"id": record_id, "note": entry}


def allowed_next_statuses(current_status: str) -> list[str]:
    return sorted(GRAPH.allowed_next(current_status))
