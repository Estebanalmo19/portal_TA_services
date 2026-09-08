"""Placeholder view used only until a solution's real views module lands.
Every `urls_<slug>.py` importing this should be replaced wholesale once
that solution is implemented — see docs/implementation-notes.md."""

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def stub_home(request, name):
    return render(request, "solutions/_stub.html", {"solution_name": name})
