"""Builds the seven catalog cards shown on `/catalogo/` from static
reference metadata plus each solution's ``catalog_summary()`` (see
``core.bootstrap`` for that contract)."""

from core.bootstrap import catalog_summary
from mock_data.people import eligible_population_count
from mock_data.reference import SOLUTIONS

HEALTH_LABELS = {
    "good": "Buena",
    "warning": "Media",
    "critical": "Baja",
}

STATUS_BADGE_CLASS = {
    "Live": "badge-live",
    "Pilot": "badge-pilot",
    "Demo": "badge-demo",
}


def catalog_cards() -> list[dict]:
    cards = []
    for solution in SOLUTIONS:
        summary = catalog_summary(solution["slug"])
        eligible = eligible_population_count(solution["slug"])
        adoption = (summary["active_users"] / eligible) if eligible else None
        cards.append(
            {
                **solution,
                "status_badge_class": STATUS_BADGE_CLASS.get(solution["status"], "badge-neutral"),
                "active_users": summary["active_users"],
                "last_activity": summary["last_activity"],
                "health": summary["health"],
                "health_label": HEALTH_LABELS.get(summary["health"], "Sin datos"),
                "open_items": summary["open_items"],
                "adoption": adoption,
            }
        )
    return cards
