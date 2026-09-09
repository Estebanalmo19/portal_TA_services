"""Synthetic historical usage for Agent TA, used only by the executive
dashboard's trend/adoption view.

Agent TA itself is a purely local, per-tab rule engine (see
``core/agent_ta/engine.py``): it has no server-side memory of past
conversations across sessions, so there is no real cross-session usage log
to summarize. This module generates a documented, deterministic *simulated*
monthly usage/satisfaction series (same generator every other solution
uses) so the dashboard has something concrete to chart for "uso/valoraciones
de Agent TA" per the brief — it is clearly not live telemetry.

The dashboard additionally shows *this tab's own* live Agent TA rating
counts (read straight from ``sessionStorage`` client-side) alongside this
mock trend, labelled separately, so the two are never conflated.
"""

from functools import lru_cache

from .people import employees
from .timeseries import MonthlyProfile, generate_monthly_series

# Agent TA is scoped to Talent Acquisition; approximate its "eligible
# population" as every employee in the TA area plus a slice of the rest of
# the company (anyone can theoretically ask about referrals).
_ELIGIBLE_SLUG = "referral"  # reuse Referral Portal's eligible population (all areas)


@lru_cache(maxsize=1)
def monthly_series() -> list[dict]:
    profile = MonthlyProfile(
        base_active_ratio=0.10,
        executions_per_active=3.0,  # messages per active user per month
        success_rate=0.8,  # fraction of messages answered with a known FAQ
        manual_minutes=6,
        assisted_minutes=1,
        satisfaction_response_rate=0.3,
        satisfaction_mean=4.0,
    )
    return generate_monthly_series("agent_ta.monthly", _ELIGIBLE_SLUG, profile)
