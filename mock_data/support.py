"""Solutions Support mock dataset.

Independent helpdesk for the other six solutions, Agent TA and the portal
itself. Assumptions used to generate the showcase tickets are documented
inline; see ``docs/implementation-notes.md`` for the shared state-contract
writeup and ``solutions/services/support.py`` for the SLA / suggested
priority rules (those are demo-only, clearly labelled "Guía de demostración"
in the UI).
"""

from functools import lru_cache

from .clock import days_ago, iso, new_rng
from .people import employees
from .reference import SOLUTION_BY_SLUG

TICKET_TYPE_LABELS = {
    "problema_tecnico": "Problema técnico",
    "solicitud_acceso": "Solicitud de acceso",
    "datos_incorrectos": "Datos incorrectos",
    "consulta": "Consulta",
    "mejora": "Mejora / sugerencia",
}
TICKET_TYPE_SLUGS = list(TICKET_TYPE_LABELS.keys())

IMPACT_LABELS = {
    "solo_yo": "Solo a mí",
    "mi_equipo": "A mi equipo",
    "bloquea_operacion": "Bloquea la operación",
}
IMPACT_SLUGS = list(IMPACT_LABELS.keys())

PRIORITY_LABELS = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "urgente": "Urgente",
}
PRIORITY_SLUGS = list(PRIORITY_LABELS.keys())

STATUS_LABELS = {
    "new": "Nuevo",
    "assigned": "Asignado",
    "in_progress": "En progreso",
    "waiting_for_requester": "Esperando al solicitante",
    "resolved": "Resuelto",
    "closed": "Cerrado",
}
STATUS_SLUGS = list(STATUS_LABELS.keys())
OPEN_STATUSES = {"new", "assigned", "in_progress", "waiting_for_requester"}
TERMINAL_STATUSES = {"closed"}

# Transition graph mirrored (for UX only) in static/js/solutions/support.js —
# Python here is the sole authority (see solutions/services/support.py).
TRANSITIONS = {
    "new": {"assigned"},
    "assigned": {"in_progress", "waiting_for_requester", "resolved"},
    "in_progress": {"waiting_for_requester", "resolved"},
    "waiting_for_requester": {"in_progress", "resolved"},
    "resolved": {"closed", "in_progress"},  # explicit reopen path, keeps history
    "closed": set(),
}

# "Affected solution" catalog offered in the ticket form: the 7 solutions in
# the portal catalog (Solutions Support included, for meta-tickets about
# support itself) plus Agent TA and the portal in general.
AFFECTED_SOLUTIONS = [{"slug": s["slug"], "name": s["name"]} for s in SOLUTION_BY_SLUG.values()] + [
    {"slug": "ta", "name": "Agent TA / Talent Acquisition"},
    {"slug": "portal", "name": "Portal general"},
]
AFFECTED_SOLUTION_SLUGS = [s["slug"] for s in AFFECTED_SOLUTIONS]
AFFECTED_SOLUTION_BY_SLUG = {s["slug"]: s for s in AFFECTED_SOLUTIONS}

# Demo-only SLA in hours by priority ("Guía de demostración"): documented in
# solutions/services/support.py::sla_hours_for / is_overdue.
SLA_HOURS_BY_PRIORITY = {"baja": 72, "media": 48, "alta": 24, "urgente": 8}

SAMPLE_SUBJECTS = [
    ("problema_tecnico", "No puedo cargar el listado de la herramienta"),
    ("problema_tecnico", "La página se queda cargando indefinidamente"),
    ("solicitud_acceso", "Necesito acceso al módulo para mi equipo"),
    ("solicitud_acceso", "Perdí el acceso tras el cambio de área"),
    ("datos_incorrectos", "El país de un colaborador aparece equivocado"),
    ("datos_incorrectos", "El indicador muestra un total que no cuadra"),
    ("consulta", "¿Cómo se calcula esta métrica?"),
    ("consulta", "Duda sobre el flujo de aprobación"),
    ("mejora", "Sugerencia: agregar un filtro por fecha"),
    ("mejora", "Sería útil exportar esta vista a CSV"),
    ("problema_tecnico", "Un botón no responde al hacer clic"),
    ("solicitud_acceso", "Alta de un nuevo colaborador en la herramienta"),
    ("datos_incorrectos", "Duplicado de un mismo registro"),
    ("consulta", "¿Dónde reviso el historial de cambios?"),
    ("mejora", "Agregar notificación cuando cambia el estado"),
    ("problema_tecnico", "El formulario no guarda los cambios"),
    ("datos_incorrectos", "Fecha de creación desfasada"),
    ("consulta", "¿Qué significa este estado del ticket?"),
]

REPRO_STEPS_TEMPLATE = (
    "1. Entrar a la herramienta afectada.\n"
    "2. Repetir la acción descrita en el asunto.\n"
    "3. Observar el resultado inesperado."
)


def _impact_for_index(i: int) -> str:
    # Rough demo distribution: mostly "mi_equipo", some "solo_yo", a few
    # "bloquea_operacion" so the priority mix looks realistic.
    if i % 7 == 0:
        return "bloquea_operacion"
    if i % 3 == 0:
        return "mi_equipo"
    return "solo_yo"


def _priority_for_impact(impact: str, rng) -> str:
    # Mirrors solutions.services.support.suggested_priority — kept as a
    # simple local seed here so showcase data doesn't need the services
    # module (mock_data must not import from solutions/*).
    if impact == "bloquea_operacion":
        return rng.choice(["alta", "urgente"])
    if impact == "mi_equipo":
        return rng.choice(["media", "alta"])
    return rng.choice(["baja", "media"])


@lru_cache(maxsize=1)
def showcase_records() -> list[dict]:
    rng = new_rng("support.showcase")
    staff = employees()
    support_agents = staff[:12]  # fictional support-desk pool

    status_cycle = (
        ["new"] * 3
        + ["assigned"] * 3
        + ["in_progress"] * 4
        + ["waiting_for_requester"] * 2
        + ["resolved"] * 3
        + ["closed"] * 3
    )
    rng.shuffle(status_cycle)

    records = []
    for i, status in enumerate(status_cycle, start=1):
        ticket_id = f"SUP-{i:04d}"
        ticket_type, subject = SAMPLE_SUBJECTS[(i - 1) % len(SAMPLE_SUBJECTS)]
        affected = rng.choice(AFFECTED_SOLUTION_SLUGS)
        requester = rng.choice(staff)
        impact = _impact_for_index(i)
        priority = _priority_for_impact(impact, rng)
        age_days = rng.randint(1, 120)
        created_at = days_ago(age_days)

        history = [
            {
                "type": "created",
                "detail": f"Ticket registrado: «{subject}».",
                "actor": requester["name"],
                "at": iso(created_at),
            }
        ]

        assignee = None
        order = ["new", "assigned", "in_progress", "waiting_for_requester", "resolved", status]
        seen = []
        step_offset = 0
        for step in order:
            if step in seen:
                continue
            seen.append(step)
            step_offset += 1
            if step == "new":
                continue
            at = iso(days_ago(max(age_days - step_offset * 4, 0)))
            if step == "assigned" and assignee is None:
                assignee = rng.choice(support_agents)
                history.append(
                    {
                        "type": "assigned",
                        "detail": f"Ticket asignado a {assignee['name']}.",
                        "actor": "Manager Demo",
                        "at": at,
                    }
                )
            else:
                history.append(
                    {
                        "type": "status_change",
                        "detail": f"Cambio de estado a «{STATUS_LABELS[step]}».",
                        "actor": assignee["name"] if assignee else "Manager Demo",
                        "at": at,
                    }
                )
            if step == status:
                break

        rating = None
        if status == "closed":
            rating = {
                "score": rng.choice([3, 4, 4, 5, 5]),
                "comment": "Se resolvió el problema reportado (demo).",
                "at": history[-1]["at"],
            }
            history.append(
                {
                    "type": "rated",
                    "detail": f"Valoración del solicitante: {rating['score']}/5.",
                    "actor": requester["name"],
                    "at": rating["at"],
                }
            )

        records.append(
            {
                "id": ticket_id,
                "affected_solution": affected,
                "ticket_type": ticket_type,
                "subject": subject,
                "description": f"{subject}. Detalle capturado durante el uso habitual de la herramienta (dato demo).",
                "impact": impact,
                "priority": priority,
                "repro_steps": REPRO_STEPS_TEMPLATE if ticket_type == "problema_tecnico" else "",
                "requester_id": requester["id"],
                "requester_name": requester["name"],
                "assignee_id": assignee["id"] if assignee else None,
                "assignee_name": assignee["name"] if assignee else None,
                "attachments": [f"adjunto_demo_{i:03d}.png"] if i % 4 == 0 else [],
                "status": status,
                "rating": rating,
                "notes": [],
                "history": history,
                "created_at": iso(created_at),
            }
        )
    return records


def initial_state() -> dict:
    return {
        "records": showcase_records(),
        "ticket_types": [{"slug": s, "label": TICKET_TYPE_LABELS[s]} for s in TICKET_TYPE_SLUGS],
        "impacts": [{"slug": s, "label": IMPACT_LABELS[s]} for s in IMPACT_SLUGS],
        "priorities": [{"slug": s, "label": PRIORITY_LABELS[s]} for s in PRIORITY_SLUGS],
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "affected_solutions": AFFECTED_SOLUTIONS,
        "sla_hours_by_priority": SLA_HOURS_BY_PRIORITY,
    }


def catalog_summary() -> dict:
    records = showcase_records()
    active_users = len({r["requester_id"] for r in records})
    last_activity = max((r["history"][-1]["at"] for r in records), default=None)
    open_items = sum(1 for r in records if r["status"] not in TERMINAL_STATUSES)
    resolved_or_closed = [r for r in records if r["status"] in ("resolved", "closed")]
    rated = [r for r in resolved_or_closed if r.get("rating")]
    avg_rating = (sum(r["rating"]["score"] for r in rated) / len(rated)) if rated else None
    if avg_rating is None:
        health = "warning"
    elif avg_rating >= 4:
        health = "good"
    elif avg_rating >= 3:
        health = "warning"
    else:
        health = "critical"
    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
