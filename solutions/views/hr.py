from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.hr import (
    CATEGORY_LABELS,
    CATEGORY_SLUGS,
    PRIORITY_LABELS,
    PRIORITY_SLUGS,
    SLA_HOURS_BY_PRIORITY,
    STATUS_LABELS,
    STATUS_SLUGS,
    agents,
    extra_fields_for,
    requesters,
)
from solutions.services import hr as hr_service


@ensure_csrf_cookie
def home(request):
    context = {
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "priorities": [
            {"slug": p, "label": PRIORITY_LABELS[p], "sla_hours": SLA_HOURS_BY_PRIORITY[p]} for p in PRIORITY_SLUGS
        ],
        "categories": [
            {"slug": c, "label": CATEGORY_LABELS[c], "extra_fields": extra_fields_for(c)} for c in CATEGORY_SLUGS
        ],
        "requesters": requesters(),
        "agents": agents(),
    }
    return render(request, "solutions/hr/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return hr_service.create_ticket(payload)


@operation_endpoint
def api_assign(request, payload):
    return hr_service.assign_ticket(payload)


@operation_endpoint
def api_transition(request, payload):
    return hr_service.transition_ticket(payload)


@operation_endpoint
def api_comment(request, payload):
    return hr_service.add_comment(payload)
