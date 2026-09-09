from django.urls import path

from solutions.views import appearance as views

app_name = "appearance"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/crear/", views.api_create, name="api_create"),
    path("api/iniciar/", views.api_start, name="api_start"),
    path("api/completar/", views.api_complete, name="api_complete"),
]
