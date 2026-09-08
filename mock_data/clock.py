"""Demo clock and reproducible RNG.

The whole demo dataset is generated relative to one frozen "reference date"
(``settings.DEMO_REFERENCE_DATE``) and one integer seed
(``settings.DEMO_SEED``). Freezing "now" means dashboard trends, "vencido"
(overdue) flags and relative timestamps ("hace 3 dias") are stable across
requests and across a whole demo session, instead of drifting with the
server's real clock and quietly invalidating the 6-months-vs-6-months
comparison.
"""

import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def reference_date() -> date:
    return datetime.strptime(settings.DEMO_REFERENCE_DATE, "%Y-%m-%d").date()


@lru_cache(maxsize=1)
def reference_datetime() -> datetime:
    d = reference_date()
    return datetime(d.year, d.month, d.day, 9, 0, 0, tzinfo=timezone.utc)


def seed() -> int:
    return settings.DEMO_SEED


def new_rng(namespace: str) -> random.Random:
    """A seeded RNG scoped to ``namespace`` so unrelated generators don't
    accidentally share/consume the same random stream and shift each other's
    output when one of them changes."""
    return random.Random(f"{seed()}::{namespace}")


def months_back(n: int) -> date:
    """First day of the month that is ``n`` months before the reference
    month (``n=0`` -> reference month)."""
    ref = reference_date()
    month_index = ref.month - 1 - n
    year = ref.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def last_n_months(n: int) -> list[str]:
    """Month keys ``YYYY-MM`` for the last ``n`` months, oldest first,
    ending on the reference month."""
    return [month_key(months_back(i)) for i in range(n - 1, -1, -1)]


def days_ago(n: int) -> datetime:
    return reference_datetime() - timedelta(days=n)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
