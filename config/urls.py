from django.urls import include, path

from core.views import error_404_view, error_500_view

urlpatterns = [
    path("", include("core.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("soluciones/", include("solutions.urls")),
]

handler404 = error_404_view
handler500 = error_500_view
