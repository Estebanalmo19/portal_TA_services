from django.urls import path

from solutions.views import uniform as views

app_name = "uniform"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/crear/", views.api_create, name="api_create"),
    path("api/seguimiento/resolver/", views.api_resolve_followup, name="api_resolve_followup"),
]
