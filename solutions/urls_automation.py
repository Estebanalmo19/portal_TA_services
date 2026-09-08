from functools import partial

from django.urls import path

from solutions.views._stub import stub_home

app_name = "automation"

urlpatterns = [
    path("", partial(stub_home, name="Automation Health Center"), name="home"),
]
