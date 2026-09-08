"""HR Colombia Ticketing mock dataset.

Population choice (documented per docs/implementation-notes.md /
task instructions): requesters are drawn from ``mock_data.people.employees()``
filtered to ``country == "co"`` (this module models HR *Colombia*
ticketing, so the fictional requesters are Colombia-based collaborators).
Assignees (HR agents) are drawn from the same pool filtered further to
``area == "hr"`` — a small (8-person) fictional Colombia HR team, which is
enough variety for a 15-20 record demo without inventing a new people list.

SLA hours, the category -> extra-field mapping and every procedure implied
by the UI copy are a demonstration guide only ("Guía de demostración"), not
a real ARRISE HR policy — see the labels used in
``templates/solutions/hr/home.html``.
"""

from datetime import timedelta
from functools import lru_cache

from .clock import days_ago, iso, new_rng, reference_datetime
from .people import employees

STATUS_LABELS = {
    "new": "Nuevo",
    "assigned": "Asignado",
    "in_progress": "En progreso",
    "waiting_for_employee": "Esperando al colaborador",
    "resolved": "Resuelto",
    "closed": "Cerrado",
}
STATUS_SLUGS = list(STATUS_LABELS.keys())

# Tickets counted as "open" for SLA/overdue tracking and for the catalog
# card's `open_items` — a ticket stops accruing SLA risk once it is
# resolved or closed.
OPEN_STATUSES = {"new", "assigned", "in_progress", "waiting_for_employee"}
TERMINAL_STATUSES = {"closed"}

# Transition graph (Python-authoritative; the real enforcement lives in
# `solutions.services.hr.GRAPH`, this is just the documented shape):
#
#   new                   -> assigned, in_progress, closed
#   assigned              -> in_progress, waiting_for_employee, closed
#   in_progress           -> waiting_for_employee, resolved, closed
#   waiting_for_employee  -> in_progress, resolved, closed   (*)
#   resolved              -> in_progress (reopen), closed
#   closed                -> (terminal, no outgoing edges)
#
# (*) "in_progress" is the explicitly required valid return from
# "waiting_for_employee" (the employee replied, the agent resumes work).
TRANSITIONS = {
    "new": {"assigned", "in_progress", "closed"},
    "assigned": {"in_progress", "waiting_for_employee", "closed"},
    "in_progress": {"waiting_for_employee", "resolved", "closed"},
    "waiting_for_employee": {"in_progress", "resolved", "closed"},
    "resolved": {"in_progress", "closed"},
    "closed": set(),
}

PRIORITY_LABELS = {
    "urgente": "Urgente",
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}
PRIORITY_SLUGS = list(PRIORITY_LABELS.keys())

# Demo SLA in hours by priority, counted from `created_at`. Fictional,
# labelled "Guía de demostración" in the UI, not a real ARRISE SLA.
SLA_HOURS_BY_PRIORITY = {
    "urgente": 24,
    "alta": 48,
    "media": 96,
    "baja": 168,
}

CATEGORY_LABELS = {
    "certificacion_laboral": "Certificación laboral",
    "nomina": "Nómina",
    "vacaciones": "Vacaciones",
    "beneficios": "Beneficios",
    "actualizacion_datos": "Actualización de datos",
    "consulta_contractual": "Consulta contractual",
    "retiro": "Retiro",
    "solicitud_general": "Solicitud general",
}
CATEGORY_SLUGS = list(CATEGORY_LABELS.keys())

# Extra fields the "Nuevo ticket" form shows/hides depending on the chosen
# category (mirrored — not re-derived — in solutions/services/hr.py at
# validation time, and in static/js/solutions/hr.js at render time).
# Categories not listed here fall back to GENERIC_EXTRA_FIELD.
CATEGORY_EXTRA_FIELDS = {
    "certificacion_laboral": [
        {"name": "entidad_destino", "label": "¿Para qué entidad es la certificación?", "type": "text", "required": True},
    ],
    "vacaciones": [
        {"name": "fecha_inicio", "label": "Fecha de inicio", "type": "date", "required": True},
        {"name": "fecha_fin", "label": "Fecha de fin", "type": "date", "required": True},
    ],
    "actualizacion_datos": [
        {"name": "dato_a_actualizar", "label": "¿Qué dato necesitas actualizar?", "type": "text", "required": True},
    ],
    "retiro": [
        {"name": "fecha_ultimo_dia", "label": "Fecha del último día laboral", "type": "date", "required": True},
    ],
}
GENERIC_EXTRA_FIELD = {"name": "detalle_adicional", "label": "Detalle adicional", "type": "text", "required": False}


def extra_fields_for(category: str) -> list[dict]:
    return CATEGORY_EXTRA_FIELDS.get(category, [GENERIC_EXTRA_FIELD])


ENTITIES_DEMO = ["Bancolombia", "Banco de Bogotá", "Davivienda", "Fondo Nacional del Ahorro", "Cooperativa Financiera Demo"]
DATA_FIELDS_DEMO = ["Número de teléfono", "Dirección de residencia", "Cuenta bancaria de nómina", "Contacto de emergencia"]

SUBJECTS_BY_CATEGORY = {
    "certificacion_laboral": [
        "Certificación laboral para trámite bancario",
        "Certificación laboral con funciones",
        "Certificación laboral para visa",
    ],
    "nomina": [
        "Inconsistencia en el pago de nómina",
        "Duda sobre un descuento en la nómina",
        "Solicitud de desprendible de nómina anterior",
    ],
    "vacaciones": [
        "Solicitud de vacaciones",
        "Cambio de fechas de vacaciones aprobadas",
    ],
    "beneficios": [
        "Consulta sobre póliza de salud",
        "Solicitud de auxilio educativo",
        "Duda sobre beneficio de gimnasio",
    ],
    "actualizacion_datos": [
        "Actualización de datos de contacto",
        "Cambio de cuenta bancaria para nómina",
    ],
    "consulta_contractual": [
        "Consulta sobre tipo de contrato",
        "Duda sobre cláusula de exclusividad",
    ],
    "retiro": [
        "Solicitud de retiro voluntario",
        "Consulta sobre liquidación de retiro",
    ],
    "solicitud_general": [
        "Solicitud general de HR",
        "Consulta sobre procedimiento interno",
    ],
}

DESCRIPTION_BY_CATEGORY = {
    "certificacion_laboral": "El colaborador solicita una certificación laboral (Guía de demostración: HR responde en el SLA definido por prioridad).",
    "nomina": "El colaborador reporta una duda o inconsistencia relacionada con su nómina.",
    "vacaciones": "El colaborador solicita o ajusta un periodo de vacaciones.",
    "beneficios": "El colaborador consulta sobre un beneficio corporativo vigente.",
    "actualizacion_datos": "El colaborador solicita actualizar información personal en su registro.",
    "consulta_contractual": "El colaborador tiene una duda sobre las condiciones de su contrato.",
    "retiro": "El colaborador inicia o consulta sobre su proceso de retiro.",
    "solicitud_general": "Solicitud general dirigida a HR Colombia que no encaja en otra categoría.",
}

# Path of statuses walked (oldest -> newest) to reach each target status,
# used only to build plausible seed history/timestamps. "waiting_for_employee"
# -> "in_progress" appears inside the "resolved" path to showcase the
# required valid return from waiting.
PATH_TO_STATUS = {
    "new": ["new"],
    "assigned": ["new", "assigned"],
    "in_progress": ["new", "assigned", "in_progress"],
    "waiting_for_employee": ["new", "assigned", "in_progress", "waiting_for_employee"],
    "resolved": ["new", "assigned", "in_progress", "waiting_for_employee", "in_progress", "resolved"],
    "closed": ["new", "assigned", "in_progress", "resolved", "closed"],
}


def requesters() -> list[dict]:
    """Fictional requester pool: Colombia-based employees (see module
    docstring for the country-filter rationale)."""
    return [e for e in employees() if e["country"] == "co"]


def agents() -> list[dict]:
    """Fictional HR Colombia agent pool used as the assignee pool."""
    return [e for e in employees() if e["country"] == "co" and e["area"] == "hr"]


def _extra_payload(rng, category: str) -> dict:
    if category == "certificacion_laboral":
        return {"entidad_destino": rng.choice(ENTITIES_DEMO)}
    if category == "vacaciones":
        start = days_ago(rng.randint(-40, -5))  # future-ish relative to creation, kept simple as demo text
        return {
            "fecha_inicio": start.strftime("%Y-%m-%d"),
            "fecha_fin": (start + timedelta(days=rng.randint(5, 15))).strftime("%Y-%m-%d"),
        }
    if category == "actualizacion_datos":
        return {"dato_a_actualizar": rng.choice(DATA_FIELDS_DEMO)}
    if category == "retiro":
        return {"fecha_ultimo_dia": days_ago(rng.randint(-30, -1)).strftime("%Y-%m-%d")}
    return {"detalle_adicional": ""}


# How "old" (in SLA multiples) a seed ticket typically is by the time it
# reaches a given open status — later stages have naturally had more time
# to elapse. Combined with a random multiplier this produces a believable
# mix of on-time, due-soon and overdue open tickets instead of an
# unrealistic pile where every open ticket is either brand new or wildly
# overdue (see the "Guía de demostración" SLA table above).
STAGE_SLA_FACTOR = {"new": 0.4, "assigned": 0.7, "in_progress": 1.0, "waiting_for_employee": 1.3}


def _age_days_for(rng, status: str, sla_hours: int) -> int:
    if status in OPEN_STATUSES:
        sla_days = max(sla_hours / 24, 0.5)
        factor = STAGE_SLA_FACTOR.get(status, 1.0) * rng.uniform(0.4, 1.6)
        return max(1, round(sla_days * factor))
    # Resolved/closed tickets have already played out their full seed
    # history; use a broader spread so "tiempo de resolución" analytics has
    # some variety across the sample.
    return rng.randint(5, 45)


def _history_for(status: str, created_at, age_days: int, requester_name: str, agent_name: str | None) -> list[dict]:
    history = [
        {"type": "created", "detail": "Ticket creado.", "actor": requester_name, "at": iso(created_at)}
    ]
    steps = PATH_TO_STATUS[status][1:]
    n = max(len(steps), 1)
    for idx, step in enumerate(steps, start=1):
        offset_days = max(age_days - round(idx * age_days / (n + 1)), 0)
        at = iso(days_ago(offset_days))
        actor = agent_name or "Agente HR Demo"
        if step == "assigned":
            detail = f"Ticket asignado a {actor}."
            event_type = "assigned"
        elif step == "in_progress" and idx > 1 and steps[idx - 2] == "waiting_for_employee":
            detail = "El colaborador respondió: el ticket vuelve a «En progreso»."
            event_type = "status_change"
        else:
            detail = f"Cambio de estado a «{STATUS_LABELS[step]}»."
            event_type = "status_change"
        history.append({"type": event_type, "detail": detail, "actor": actor, "at": at})
    return history


@lru_cache(maxsize=1)
def showcase_records() -> list[dict]:
    rng = new_rng("hr.showcase")
    requester_pool = requesters()
    agent_pool = agents()

    status_cycle = (
        ["new"] * 3
        + ["assigned"] * 3
        + ["in_progress"] * 4
        + ["waiting_for_employee"] * 3
        + ["resolved"] * 3
        + ["closed"] * 2
    )
    rng.shuffle(status_cycle)

    records = []
    for i, status in enumerate(status_cycle, start=1):
        record_id = f"HR-{i:04d}"
        category = CATEGORY_SLUGS[(i - 1) % len(CATEGORY_SLUGS)]
        priority = rng.choices(PRIORITY_SLUGS, weights=[0.15, 0.3, 0.35, 0.2])[0]
        requester = rng.choice(requester_pool)
        sla_hours = SLA_HOURS_BY_PRIORITY[priority]
        age_days = _age_days_for(rng, status, sla_hours)
        created_at = days_ago(age_days)
        due_at = created_at + timedelta(hours=sla_hours)

        needs_agent = status != "new"
        agent = rng.choice(agent_pool) if needs_agent else None
        history = _history_for(status, created_at, age_days, requester["name"], agent["name"] if agent else None)

        resolved_at = None
        closed_at = None
        if status in ("resolved", "closed"):
            resolved_at = history[-1]["at"] if status == "resolved" else history[-2]["at"]
        if status == "closed":
            closed_at = history[-1]["at"]

        comments = []
        if rng.random() < 0.4:
            comments.append(
                {
                    "type": "comment",
                    "detail": rng.choice([
                        "Quedamos atentos a la respuesta del colaborador.",
                        "Se solicitó documentación adicional.",
                        "Se validó la información con el área de nómina.",
                    ]),
                    "actor": (agent or {"name": "Agente HR Demo"})["name"],
                    "at": history[min(2, len(history) - 1)]["at"],
                }
            )

        attachments = []
        if rng.random() < 0.5:
            attachments.append({"filename": f"adjunto_demo_{i:03d}.pdf", "size_kb": rng.randint(80, 900)})

        survey = None
        if status in ("resolved", "closed") and rng.random() < 0.7:
            survey = {"score": rng.choices([5, 4, 3, 2, 1], weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0], "comment": ""}

        records.append(
            {
                "id": record_id,
                "requester_id": requester["id"],
                "requester_name": requester["name"],
                "requester_email": requester["email"],
                "requester_area": requester["area"],
                "category": category,
                "subject": rng.choice(SUBJECTS_BY_CATEGORY[category]),
                "description": DESCRIPTION_BY_CATEGORY[category],
                "extra_fields": _extra_payload(rng, category),
                "priority": priority,
                "sla_hours": sla_hours,
                "assignee_id": agent["id"] if agent else None,
                "assignee_name": agent["name"] if agent else None,
                "status": status,
                "created_at": iso(created_at),
                "due_at": iso(due_at),
                "resolved_at": resolved_at,
                "closed_at": closed_at,
                "comments": comments,
                "attachments": attachments,
                "history": history + comments,
                "survey": survey,
            }
        )
    return records


def initial_state() -> dict:
    return {
        "records": showcase_records(),
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "priorities": [{"slug": p, "label": PRIORITY_LABELS[p], "sla_hours": SLA_HOURS_BY_PRIORITY[p]} for p in PRIORITY_SLUGS],
        "categories": [
            {"slug": c, "label": CATEGORY_LABELS[c], "extra_fields": extra_fields_for(c)} for c in CATEGORY_SLUGS
        ],
        "agents": agents(),
    }


def catalog_summary() -> dict:
    records = showcase_records()
    active_users = len({r["requester_id"] for r in records})
    last_activity = max((r["history"][-1]["at"] for r in records if r["history"]), default=None)
    open_records = [r for r in records if r["status"] in OPEN_STATUSES]
    open_items = len(open_records)
    now = reference_datetime()
    overdue = sum(1 for r in open_records if iso(now) > r["due_at"])
    if open_items == 0:
        health = "good"
    else:
        overdue_ratio = overdue / open_items
        if overdue_ratio >= 0.4:
            health = "critical"
        elif overdue_ratio >= 0.15:
            health = "warning"
        else:
            health = "good"
    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
