from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from . import services


@ensure_csrf_cookie
def dashboard_home(request):
    filters = services.parse_filters(request.GET)
    context = services.build_dashboard_context(filters)
    return render(request, "dashboard/dashboard.html", context)


def export_csv(request):
    filters = services.parse_filters(request.GET)
    content = services.export_csv_rows(filters)
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="dashboard_arrise.csv"'
    return response
