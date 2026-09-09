from django.urls import path

from solutions.views import automation as views

app_name = "automation"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/reintentar/", views.api_retry, name="api_retry"),
    path("api/pausar/", views.api_pause, name="api_pause"),
]
