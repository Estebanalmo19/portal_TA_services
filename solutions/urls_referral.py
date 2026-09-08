from django.urls import path

from solutions.views import referral as views

app_name = "referral"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/crear/", views.api_create, name="api_create"),
    path("api/transicion/", views.api_transition, name="api_transition"),
    path("api/nota/", views.api_add_note, name="api_add_note"),
]
