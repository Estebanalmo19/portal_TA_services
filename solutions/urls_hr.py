from functools import partial

from django.urls import path

from solutions.views._stub import stub_home

app_name = "hr"

urlpatterns = [
    path("", partial(stub_home, name="HR Colombia Ticketing"), name="home"),
]
