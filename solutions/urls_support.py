from django.urls import path

from solutions.views import support as views

app_name = "support"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/crear/", views.api_create, name="api_create"),
    path("api/asignar/", views.api_assign, name="api_assign"),
    path("api/transicion/", views.api_transition, name="api_transition"),
    path("api/nota/", views.api_add_note, name="api_add_note"),
    path("api/valorar/", views.api_rate, name="api_rate"),
]
