from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.state import operation_endpoint
from mock_data.people import employees
from mock_data.reference import COUNTRY_NAME_BY_SLUG, COUNTRY_SLUGS
from mock_data.referral import JOB_OPENINGS, RELATIONS, STATUS_LABELS, STATUS_SLUGS
from solutions.services import referral as referral_service


@ensure_csrf_cookie
def home(request):
    context = {
        "job_openings": JOB_OPENINGS,
        "relations": RELATIONS,
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "countries": [{"slug": c, "name": COUNTRY_NAME_BY_SLUG[c]} for c in COUNTRY_SLUGS],
        "employees": employees(),
    }
    return render(request, "solutions/referral/home.html", context)


@operation_endpoint
def api_create(request, payload):
    return referral_service.create_referral(payload)


@operation_endpoint
def api_transition(request, payload):
    return referral_service.transition_referral(payload)


@operation_endpoint
def api_add_note(request, payload):
    return referral_service.add_note(payload)
