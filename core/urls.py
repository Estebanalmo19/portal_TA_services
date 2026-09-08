from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("catalogo/", views.catalog, name="catalog"),
    path("acerca/", views.about, name="about"),
    path("api/busqueda/", views.global_search, name="global_search"),
    path("api/agent-ta/preguntar/", views.agent_ta_ask, name="agent_ta_ask"),
]
