from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import json_error, operation_endpoint, parse_json_body, require_post
from mock_data.people import eligible_population
from mock_data.reference import SITES
from mock_data.security import (
    CATEGORY_LABELS,
    CATEGORY_SLUGS,
    CONTROL_STATUS_LABELS,
    CONTROL_STATUS_SLUGS,
    CONTROL_TYPE_LABELS,
    CONTROL_TYPE_SLUGS,
    FLOORS,
    SEVERITY_LABELS,
    SEVERITY_SLUGS,
    STATUS_LABELS,
    STATUS_SLUGS,
)
from solutions.services import security as security_service


@ensure_csrf_cookie
def home(request):
    support_query = urlencode(
        {
            "sol": "security",
            "asunto": "Problema en Security Database Hub",
            "descripcion": "Describe el problema encontrado en Security Database Hub (incidentes, controles por piso o analítica).",
            "origen": "solucion",
        }
    )
    context = {
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "categories": [{"slug": c, "label": CATEGORY_LABELS[c]} for c in CATEGORY_SLUGS],
        "severities": [{"slug": s, "label": SEVERITY_LABELS[s]} for s in SEVERITY_SLUGS],
        "control_types": [{"slug": c, "label": CONTROL_TYPE_LABELS[c]} for c in CONTROL_TYPE_SLUGS],
        "control_statuses": [{"slug": s, "label": CONTROL_STATUS_LABELS[s]} for s in CONTROL_STATUS_SLUGS],
        "sites": SITES,
        "floors": FLOORS,
        "assignees": eligible_population("security"),
        "support_link": f"/soluciones/support/?{support_query}",
    }
    return render(request, "solutions/security/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return security_service.create_incident(payload)


@operation_endpoint
def api_assign(request, payload):
    return security_service.assign_incident(payload)


@operation_endpoint
def api_transition(request, payload):
    return security_service.transition_incident(payload)


@require_post
def api_export(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return json_error(str(exc))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return json_error({"rows": "Se requiere una lista de incidentes para exportar."})
    if len(rows) > 500:
        return json_error({"rows": "Demasiadas filas para exportar (máximo 500)."})
    csv_text = security_service.export_incidents_csv(rows)
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="incidentes_seguridad.csv"'
    return response
