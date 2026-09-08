"""Executive dashboard aggregation.

TODO(dashboard-integration): this is a placeholder until every solution's
``mock_data.<slug>.MONTHLY_SERIES`` exists — see docs/implementation-notes.md
step 5. Filled in once all seven solutions are built (see step 4).
"""

from mock_data.reference import AREAS, COUNTRIES, GLOBAL_LABEL, GLOBAL_SLUG, SOLUTIONS


def parse_filters(get_params) -> dict:
    return {
        "period": get_params.get("periodo", "6m"),
        "solution": get_params.get("solucion", "all"),
        "country": get_params.get("pais", GLOBAL_SLUG),
        "area": get_params.get("area", "all"),
    }


def build_dashboard_context(filters: dict) -> dict:
    return {
        "filters": filters,
        "areas": AREAS,
        "countries": COUNTRIES,
        "global_slug": GLOBAL_SLUG,
        "global_label": GLOBAL_LABEL,
        "solutions": SOLUTIONS,
        "not_implemented": True,
    }


def export_csv_rows(filters: dict) -> str:
    return "solucion,mes,ejecuciones,exito,fallo\n"
