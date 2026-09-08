from django.urls import path

from solutions.views import security as views

app_name = "security"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/crear/", views.api_create, name="api_create"),
    path("api/asignar/", views.api_assign, name="api_assign"),
    path("api/transicion/", views.api_transition, name="api_transition"),
    path("api/exportar/", views.api_export, name="api_export"),
]
