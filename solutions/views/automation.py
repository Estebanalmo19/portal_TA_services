from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.automation import EXECUTION_STATUS_LABELS, HEALTH_LABELS
from solutions.services import automation as automation_service


@ensure_csrf_cookie
def home(request):
    support_query = urlencode(
        {
            "sol": "automation",
            "asunto": "Problema en Automation Health Center",
            "descripcion": "Describe el problema encontrado en Automation Health Center (automatizaciones, ejecuciones o analítica).",
            "origen": "solucion",
        }
    )
    context = {
        "health_statuses": [{"slug": s, "label": HEALTH_LABELS[s]} for s in HEALTH_LABELS],
        "execution_statuses": [{"slug": s, "label": EXECUTION_STATUS_LABELS[s]} for s in EXECUTION_STATUS_LABELS],
        "support_link": f"/soluciones/support/?{support_query}",
    }
    return render(request, "solutions/automation/home.html", context)


@operation_endpoint
def api_retry(request, payload):
    return automation_service.retry_execution(payload)


@operation_endpoint
def api_pause(request, payload):
    return automation_service.set_paused(payload)
