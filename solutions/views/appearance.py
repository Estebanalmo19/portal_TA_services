from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.clock import reference_date
from mock_data.appearance import (
    CRITERIA,
    RESULT_LABELS,
    RESULT_SLUGS,
    ROLE_LABELS,
    ROLE_SLUGS,
    SHIFT_LABELS,
    SHIFT_SLUGS,
    STATUS_LABELS,
    STATUS_SLUGS,
)
from mock_data.people import eligible_population
from mock_data.reference import SITES
from solutions.services import appearance as appearance_service


@ensure_csrf_cookie
def home(request):
    support_query = urlencode(
        {
            "sol": "appearance",
            "asunto": "Problema en Appearance Check",
            "descripcion": "Describe el problema encontrado en Appearance Check (búsqueda de colaborador, checklist o seguimiento).",
            "origen": "solucion",
        }
    )
    context = {
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "results": [{"slug": r, "label": RESULT_LABELS[r]} for r in RESULT_SLUGS],
        "shifts": [{"slug": s, "label": SHIFT_LABELS[s]} for s in SHIFT_SLUGS],
        "roles": [{"slug": r, "label": ROLE_LABELS[r]} for r in ROLE_SLUGS],
        "criteria": CRITERIA,
        "sites": SITES,
        "employees": eligible_population("appearance"),
        "today": reference_date().isoformat(),
        "support_link": f"/soluciones/support/?{support_query}",
    }
    return render(request, "solutions/appearance/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return appearance_service.create_review(payload)


@operation_endpoint
def api_start(request, payload):
    return appearance_service.start_review(payload)


@operation_endpoint
def api_complete(request, payload):
    return appearance_service.complete_review(payload)
