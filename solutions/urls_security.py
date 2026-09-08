from functools import partial

from django.urls import path

from solutions.views._stub import stub_home

app_name = "security"

urlpatterns = [
    path("", partial(stub_home, name="Security Database Hub"), name="home"),
]
