from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.reference import SITES
from mock_data.uniform import (
    CHECKLIST_ITEM_LABELS,
    CHECKLIST_ITEM_SLUGS,
    INSPECTOR_POOL,
    ITEM_STATUS_LABELS,
    ITEM_STATUS_SLUGS,
    ROLES,
    SHIFT_LABELS,
    SHIFT_SLUGS,
    employees_with_roles,
)
from solutions.services import uniform as uniform_service


@ensure_csrf_cookie
def home(request):
    support_query = urlencode(
        {
            "sol": "uniform",
            "asunto": "Problema en Uniform Compliance Check",
            "descripcion": "Describe el problema encontrado en Uniform Compliance Check (inspecciones, seguimientos correctivos o analítica).",
            "origen": "solucion",
        }
    )
    context = {
        "sites": SITES,
        "shifts": [{"slug": s, "label": SHIFT_LABELS[s]} for s in SHIFT_SLUGS],
        "checklist_items": [{"slug": s, "label": CHECKLIST_ITEM_LABELS[s]} for s in CHECKLIST_ITEM_SLUGS],
        "item_statuses": [{"slug": s, "label": ITEM_STATUS_LABELS[s]} for s in ITEM_STATUS_SLUGS],
        "roles": ROLES,
        "inspectors": INSPECTOR_POOL,
        "employees": employees_with_roles(),
        "support_link": f"/soluciones/support/?{support_query}",
    }
    return render(request, "solutions/uniform/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return uniform_service.create_inspection(payload)


@operation_endpoint
def api_resolve_followup(request, payload):
    return uniform_service.resolve_followup(payload)
