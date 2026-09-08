from core.bootstrap import build_snapshot
from mock_data import STATE_VERSION
from mock_data.reference import AREAS, COUNTRIES, PROFILES, SOLUTIONS


def brand(request):
    """Values every template may need regardless of which view rendered it
    (sidebar, breadcrumbs, the demo-data badge, and the initial-state
    snapshot every page embeds for `static/js/state/bootstrap.js`)."""
    return {
        "DEMO_LABEL": "Demo · Datos ficticios",
        "BRAND_NAME": "ARRISE Solutions Portal",
        "NAV_SOLUTIONS": SOLUTIONS,
        "NAV_AREAS": AREAS,
        "NAV_COUNTRIES": COUNTRIES,
        "NAV_PROFILES": PROFILES,
        "STATE_VERSION": STATE_VERSION,
        "initial_state": build_snapshot(),
    }
