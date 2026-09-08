from functools import partial

from django.urls import path

from solutions.views._stub import stub_home

app_name = "uniform"

urlpatterns = [
    path("", partial(stub_home, name="Uniform Compliance Check"), name="home"),
]
