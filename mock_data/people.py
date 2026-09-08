"""Synthetic employee directory used to compute adoption/eligibility KPIs.

This is not an HR system: it is a small, deterministic population of
fictional collaborators ("Colaborador Demo 014", `@example.com`) tagged by
area and country, used only so the dashboard's "adoption" KPI has a real,
documented denominator (eligible population) instead of a made-up constant.
"""

from functools import lru_cache

from .clock import new_rng
from .reference import AREA_SLUGS, COUNTRY_SLUGS, SOLUTION_BY_SLUG

EMPLOYEE_COUNT = 240

# Rough headcount weighting per area, applied when distributing the
# synthetic population (Operations is the largest, front-line-heavy area).
AREA_WEIGHTS = {
    "ta": 0.14,
    "hr": 0.12,
    "security": 0.16,
    "data-analytics": 0.10,
    "operations": 0.48,
}


@lru_cache(maxsize=1)
def employees() -> list[dict]:
    rng = new_rng("people.employees")
    areas = rng.choices(AREA_SLUGS, weights=[AREA_WEIGHTS[a] for a in AREA_SLUGS], k=EMPLOYEE_COUNT)
    countries = rng.choices(COUNTRY_SLUGS, k=EMPLOYEE_COUNT)
    people = []
    for i in range(1, EMPLOYEE_COUNT + 1):
        seq = f"{i:03d}"
        people.append(
            {
                "id": f"EMP-{seq}",
                "name": f"Colaborador Demo {seq}",
                "area": areas[i - 1],
                "country": countries[i - 1],
                "email": f"colaborador.demo.{seq}@example.com",
            }
        )
    return people


@lru_cache(maxsize=1)
def employees_by_id() -> dict:
    return {e["id"]: e for e in employees()}


@lru_cache(maxsize=None)
def eligible_population(solution_slug: str) -> list[dict]:
    """Employees counted in the 'eligible population' denominator for a
    solution's adoption KPI, per the ``eligible_areas`` documented in
    ``mock_data.reference.SOLUTIONS``."""
    solution = SOLUTION_BY_SLUG[solution_slug]
    eligible_areas = set(solution["eligible_areas"])
    return [e for e in employees() if e["area"] in eligible_areas]


def eligible_population_count(solution_slug: str) -> int:
    return len(eligible_population(solution_slug))


def pick_employee(rng, solution_slug: str | None = None, area: str | None = None) -> dict:
    pool = employees()
    if solution_slug:
        pool = eligible_population(solution_slug)
    if area:
        pool = [e for e in pool if e["area"] == area]
    return rng.choice(pool)
