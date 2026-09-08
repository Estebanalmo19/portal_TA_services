from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.people import employees
from mock_data.support import (
    AFFECTED_SOLUTION_SLUGS,
    AFFECTED_SOLUTIONS,
    IMPACT_LABELS,
    IMPACT_SLUGS,
    PRIORITY_LABELS,
    PRIORITY_SLUGS,
    SLA_HOURS_BY_PRIORITY,
    STATUS_LABELS,
    STATUS_SLUGS,
    TICKET_TYPE_LABELS,
    TICKET_TYPE_SLUGS,
)
from solutions.services import support as support_service


def _prefill_from_query(request) -> dict:
    """Reads the optional `sol`/`asunto`/`descripcion`/`origen` query params
    every "Reportar un problema" link (catalog, each solution, Agent TA)
    sends here — see docs/implementation-notes.md. Never auto-submits: the
    frontend only uses this to pre-fill the "Nuevo ticket" form, the user
    still reviews and sends it manually. An unknown/missing `sol` simply
    means nothing gets preselected."""
    sol = request.GET.get("sol") or ""
    return {
        "affected_solution": sol if sol in AFFECTED_SOLUTION_SLUGS else "",
        "subject": (request.GET.get("asunto") or "")[:160],
        "description": (request.GET.get("descripcion") or "")[:4000],
        "origin": (request.GET.get("origen") or "")[:120],
        "active": bool(sol or request.GET.get("asunto") or request.GET.get("descripcion")),
    }


@ensure_csrf_cookie
def home(request):
    context = {
        "ticket_types": [{"slug": s, "label": TICKET_TYPE_LABELS[s]} for s in TICKET_TYPE_SLUGS],
        "impacts": [{"slug": s, "label": IMPACT_LABELS[s]} for s in IMPACT_SLUGS],
        "priorities": [{"slug": s, "label": PRIORITY_LABELS[s]} for s in PRIORITY_SLUGS],
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "affected_solutions": AFFECTED_SOLUTIONS,
        "sla_hours_by_priority": SLA_HOURS_BY_PRIORITY,
        "employees": employees(),
        "prefill": _prefill_from_query(request),
    }
    return render(request, "solutions/support/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return support_service.create_ticket(payload)


@operation_endpoint
def api_assign(request, payload):
    return support_service.assign_ticket(payload)


@operation_endpoint
def api_transition(request, payload):
    return support_service.transition_ticket(payload)


@operation_endpoint
def api_add_note(request, payload):
    return support_service.add_comment(payload)


@operation_endpoint
def api_rate(request, payload):
    return support_service.rate_ticket(payload)
