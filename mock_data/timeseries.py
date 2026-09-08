"""Generic 12-month monthly activity generator used by every solution to
feed the executive dashboard (trend, usage/hours, success rate, users by
area/country).

Each solution module calls :func:`generate_monthly_series` once with a
profile tuned to that solution (how many people typically use it, roughly
how many minutes it takes manually vs. assisted, its baseline success
rate...). The result is a list of 12 monthly snapshots, oldest first, each
one naming exactly which synthetic employees were "active" that month so
the dashboard can filter by area/country/period without double counting a
person who used more than one solution in the same period (dedupe by
employee id at aggregation time, see ``dashboard.services``).

All Python-side "hours saved" / "success rate" assumptions here are demo
assumptions, not measured data — they are documented per-solution in each
generator call and surfaced to the user via dashboard tooltips.
"""

from dataclasses import dataclass

from .clock import last_n_months, new_rng
from .people import eligible_population


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class MonthlyProfile:
    base_active_ratio: float = 0.35
    volatility: float = 0.12
    growth_per_month: float = 0.01
    executions_per_active: float = 2.2
    success_rate: float = 0.9
    manual_minutes: float = 30.0
    assisted_minutes: float = 8.0
    satisfaction_response_rate: float = 0.55
    satisfaction_mean: float = 4.2


def generate_monthly_series(
    namespace: str,
    solution_slug: str,
    profile: MonthlyProfile,
    months: int = 12,
) -> list[dict]:
    rng = new_rng(namespace)
    eligible = eligible_population(solution_slug)
    month_keys = last_n_months(months)

    series = []
    ratio = profile.base_active_ratio
    for i, month in enumerate(month_keys):
        ratio = _clamp(
            ratio + rng.uniform(-profile.volatility, profile.volatility) + profile.growth_per_month,
            0.05,
            0.97,
        )
        active_count = max(1, round(len(eligible) * ratio)) if eligible else 0
        active_count = min(active_count, len(eligible))
        active = rng.sample(eligible, active_count) if active_count else []

        executions = max(active_count, round(active_count * profile.executions_per_active * rng.uniform(0.85, 1.15)))
        success = min(executions, max(0, round(executions * profile.success_rate * rng.uniform(0.92, 1.03))))
        fail = executions - success

        hours_manual = executions * profile.manual_minutes / 60
        hours_assisted = executions * profile.assisted_minutes / 60
        hours_saved = round(max(0.0, hours_manual - hours_assisted) * rng.uniform(0.9, 1.05), 1)

        satisfaction_count = round(executions * profile.satisfaction_response_rate)
        satisfaction_scores = [
            int(round(_clamp(rng.gauss(profile.satisfaction_mean, 0.55), 1, 5)))
            for _ in range(satisfaction_count)
        ]

        series.append(
            {
                "month": month,
                "active_user_ids": [e["id"] for e in active],
                "executions": executions,
                "success": success,
                "fail": fail,
                "hours_manual": round(hours_manual, 1),
                "hours_assisted": round(hours_assisted, 1),
                "hours_saved": hours_saved,
                "satisfaction_scores": satisfaction_scores,
            }
        )
    return series
