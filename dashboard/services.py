"""Executive dashboard aggregation.

Every KPI, chart series and CSV row is computed at request time from the
same sources every solution already exposes — nothing here is a fixed
number typed into a template:

- ``mock_data.<slug>.monthly_series()`` — 12 months of activity per
  solution (see ``mock_data/timeseries.py``), used for trend, usage/hours,
  success rate, users-by-area/country and the period-over-period deltas.
- ``core.bootstrap.catalog_summary(slug)`` — each solution's current
  "open items" count (independent of the 12-month trend).
- ``mock_data.<slug>.showcase_records()`` — the small "current" record set
  each solution's own page renders, used here only for a couple of
  solution-specific callouts (Support's overdue/backlog card, "recent
  activity" across modules) explicitly requested by the brief.

Filtering by area/country prorates each month's executions/hours/success
proportionally to the fraction of that month's active users who match the
filter (documented assumption — the synthetic monthly series only records
*which* employees were active, not a per-user breakdown of each metric).
"""

import logging
from importlib import import_module

from core.bootstrap import catalog_summary
from mock_data.clock import reference_datetime
from mock_data.people import eligible_population, employees_by_id
from mock_data.reference import (
    AREA_NAME_BY_SLUG,
    AREA_SLUGS,
    COUNTRY_NAME_BY_SLUG,
    COUNTRY_SLUGS,
    CURRENCY,
    DEMO_HOURLY_RATE,
    GLOBAL_LABEL,
    GLOBAL_SLUG,
    SOLUTION_BY_SLUG,
    SOLUTION_SLUGS,
)

logger = logging.getLogger(__name__)

PERIOD_MONTHS = {"3m": 3, "6m": 6, "12m": 12}
DEFAULT_PERIOD = "6m"
PERIOD_LABELS = {"3m": "Últimos 3 meses", "6m": "Últimos 6 meses", "12m": "Últimos 12 meses"}


def _load_module(slug: str):
    return import_module(f"mock_data.{slug.replace('-', '_')}")


def _monthly_series(slug: str) -> list[dict]:
    try:
        return _load_module(slug).monthly_series()
    except Exception:  # noqa: BLE001 - defensive, see core.bootstrap for rationale
        logger.exception("dashboard: sin monthly_series() para %s", slug)
        return []


def _showcase_records(slug: str) -> list[dict]:
    try:
        return _load_module(slug).showcase_records()
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------


def parse_filters(get_params) -> dict:
    period = get_params.get("periodo", DEFAULT_PERIOD)
    if period not in PERIOD_MONTHS:
        period = DEFAULT_PERIOD
    solution = get_params.get("solucion", "all")
    if solution not in SOLUTION_SLUGS:
        solution = "all"
    country = get_params.get("pais", GLOBAL_SLUG)
    if country not in COUNTRY_SLUGS:
        country = GLOBAL_SLUG
    area = get_params.get("area", "all")
    if area not in AREA_SLUGS:
        area = "all"
    return {"period": period, "solution": solution, "country": country, "area": area}


def _selected_solutions(filters: dict) -> list[str]:
    if filters["solution"] == "all":
        return list(SOLUTION_SLUGS)
    return [filters["solution"]]


# ---------------------------------------------------------------------
# Area/country filtering + prorating
# ---------------------------------------------------------------------


def _matches_scope(employee: dict, area: str, country: str) -> bool:
    if area != "all" and employee["area"] != area:
        return False
    if country != GLOBAL_SLUG and employee["country"] != country:
        return False
    return True


def _filter_ids(ids, area: str, country: str) -> list[str]:
    if area == "all" and country == GLOBAL_SLUG:
        return list(ids)
    emp_by_id = employees_by_id()
    return [eid for eid in ids if eid in emp_by_id and _matches_scope(emp_by_id[eid], area, country)]


def _prorate(entry: dict, area: str, country: str) -> dict:
    filtered_ids = _filter_ids(entry["active_user_ids"], area, country)
    total = len(entry["active_user_ids"])
    ratio = (len(filtered_ids) / total) if total else 0.0
    satisfaction = entry["satisfaction_scores"]
    sat_count = round(len(satisfaction) * ratio)
    return {
        "month": entry["month"],
        "active_user_ids": filtered_ids,
        "executions": round(entry["executions"] * ratio),
        "success": round(entry["success"] * ratio),
        "fail": round(entry["fail"] * ratio),
        "hours_saved": entry["hours_saved"] * ratio,
        "satisfaction_scores": satisfaction[:sat_count],
    }


# ---------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------


def _aggregate(selected_slugs, months_n: int, area: str, country: str, *, offset: int = 0) -> dict | None:
    """Aggregate ``months_n`` months across ``selected_slugs``, ``offset``
    months back from "now" (offset=0 -> the most recent window, offset=N ->
    the equivalent window N*months_n months earlier, used for the
    period-over-period comparison). Returns None if that window isn't
    covered by the available 12 months of history.
    """
    active_ids: set[str] = set()
    executions = success = fail = 0
    hours_saved = 0.0
    satisfaction: list[int] = []
    per_solution = {}

    for slug in selected_slugs:
        series = _monthly_series(slug)
        start = -(months_n * (offset + 1))
        end = -(months_n * offset) or None
        window = series[start:end] if len(series) >= months_n * (offset + 1) else None
        if window is None:
            per_solution[slug] = None
            continue

        sol_ids: set[str] = set()
        sol_exec = sol_success = sol_fail = 0
        sol_hours = 0.0
        sol_sat: list[int] = []
        for raw_entry in window:
            entry = _prorate(raw_entry, area, country)
            sol_ids.update(entry["active_user_ids"])
            sol_exec += entry["executions"]
            sol_success += entry["success"]
            sol_fail += entry["fail"]
            sol_hours += entry["hours_saved"]
            sol_sat.extend(entry["satisfaction_scores"])

        per_solution[slug] = {
            "active_users": len(sol_ids),
            "executions": sol_exec,
            "success": sol_success,
            "fail": sol_fail,
            "hours_saved": round(sol_hours, 1),
            "satisfaction_avg": (sum(sol_sat) / len(sol_sat)) if sol_sat else None,
        }
        active_ids |= sol_ids
        executions += sol_exec
        success += sol_success
        fail += sol_fail
        hours_saved += sol_hours
        satisfaction.extend(sol_sat)

    if all(v is None for v in per_solution.values()):
        return None

    return {
        "active_user_ids": active_ids,
        "active_users": len(active_ids),
        "executions": executions,
        "success": success,
        "fail": fail,
        "hours_saved": round(hours_saved, 1),
        "satisfaction_avg": (sum(satisfaction) / len(satisfaction)) if satisfaction else None,
        "per_solution": per_solution,
    }


def _eligible_count(selected_slugs, area: str, country: str) -> int:
    ids: set[str] = set()
    for slug in selected_slugs:
        for employee in eligible_population(slug):
            if _matches_scope(employee, area, country):
                ids.add(employee["id"])
    return len(ids)


def _delta(current, previous):
    if previous is None:
        return {"value": None, "direction": "flat", "label": "Sin base comparable"}
    if previous == 0:
        if current == 0:
            return {"value": None, "direction": "flat", "label": "Sin datos"}
        return {"value": None, "direction": "up", "label": "Nuevo"}
    change = (current - previous) / previous
    direction = "up" if change > 0.005 else ("down" if change < -0.005 else "flat")
    return {"value": round(change * 100, 1), "direction": direction, "label": f"{change * 100:+.1f}%"}


def _breakdown(ids, attr: str, name_by_slug: dict) -> list[dict]:
    emp_by_id = employees_by_id()
    counts: dict[str, int] = {}
    for eid in ids:
        employee = emp_by_id.get(eid)
        if not employee:
            continue
        key = employee[attr]
        counts[key] = counts.get(key, 0) + 1
    return [
        {"slug": slug, "name": name_by_slug.get(slug, slug), "count": count}
        for slug, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


# ---------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------


def build_dashboard_context(filters: dict) -> dict:
    selected = _selected_solutions(filters)
    area, country = filters["area"], filters["country"]
    months_n = PERIOD_MONTHS[filters["period"]]

    current = _aggregate(selected, months_n, area, country, offset=0)
    previous = _aggregate(selected, months_n, area, country, offset=1)

    current = current or {
        "active_user_ids": set(), "active_users": 0, "executions": 0, "success": 0,
        "fail": 0, "hours_saved": 0.0, "satisfaction_avg": None, "per_solution": {},
    }

    eligible = _eligible_count(selected, area, country)
    adoption = (current["active_users"] / eligible) if eligible else None
    prev_adoption = None
    if previous and eligible:
        prev_adoption = previous["active_users"] / eligible

    finished = current["success"] + current["fail"]
    success_rate = (current["success"] / finished) if finished else None
    prev_finished = (previous["success"] + previous["fail"]) if previous else 0
    prev_success_rate = (previous["success"] / prev_finished) if previous and prev_finished else None

    open_items_total = 0
    open_items_by_solution = []
    health_alerts = []
    for slug in selected:
        summary = catalog_summary(slug)
        open_items_total += summary["open_items"]
        open_items_by_solution.append(
            {"slug": slug, "name": SOLUTION_BY_SLUG[slug]["name"], "open_items": summary["open_items"], "health": summary["health"]}
        )
        if summary["health"] != "good":
            health_alerts.append(
                {
                    "slug": slug,
                    "name": SOLUTION_BY_SLUG[slug]["name"],
                    "health": summary["health"],
                    "open_items": summary["open_items"],
                    "url": f"/soluciones/{slug}/",
                }
            )

    savings_amount = round(current["hours_saved"] * DEMO_HOURLY_RATE, 2)

    kpis = {
        "active_users": {
            "value": current["active_users"],
            "delta": _delta(current["active_users"], previous["active_users"] if previous else None),
        },
        "adoption": {
            # Delta is computed on the raw 0-1 ratio (so a move from 40% to
            # 44% adoption reads as "+10%" relative change); the displayed
            # "value" is the human percentage (0-100) the template renders.
            "value": round(adoption * 100, 1) if adoption is not None else None,
            "delta": _delta(adoption, prev_adoption) if adoption is not None else {"value": None, "direction": "flat", "label": "Sin datos"},
        },
        "executions": {
            "value": current["executions"],
            "delta": _delta(current["executions"], previous["executions"] if previous else None),
        },
        "success_rate": {
            "value": round(success_rate * 100, 1) if success_rate is not None else None,
            "delta": _delta(success_rate, prev_success_rate) if success_rate is not None else {"value": None, "direction": "flat", "label": "Sin datos"},
        },
        "hours_saved": {
            "value": current["hours_saved"],
            "delta": _delta(current["hours_saved"], previous["hours_saved"] if previous else None),
        },
        "savings": {"value": savings_amount, "currency": CURRENCY},
        "satisfaction": {
            "value": current["satisfaction_avg"],
            "delta": (
                _delta(current["satisfaction_avg"], previous["satisfaction_avg"] if previous else None)
                if current["satisfaction_avg"] is not None
                else {"value": None, "direction": "flat", "label": "Sin respuestas"}
            ),
        },
        "open_items": {"value": open_items_total},
    }

    trend_months = []
    for i in range(months_n):
        month_entries = {}
        for slug in selected:
            series = _monthly_series(slug)
            if len(series) >= months_n - i:
                raw = series[-(months_n - i)]
                month_entries[slug] = _prorate(raw, area, country)
        if not month_entries:
            continue
        month_label = next(iter(month_entries.values()))["month"]
        trend_months.append(
            {
                "month": month_label,
                "executions": sum(e["executions"] for e in month_entries.values()),
                "success": sum(e["success"] for e in month_entries.values()),
                "fail": sum(e["fail"] for e in month_entries.values()),
                "hours_saved": round(sum(e["hours_saved"] for e in month_entries.values()), 1),
                "active_users": len({eid for e in month_entries.values() for eid in e["active_user_ids"]}),
            }
        )

    usage_by_solution = [
        {
            "slug": slug,
            "name": SOLUTION_BY_SLUG[slug]["name"],
            **(current["per_solution"].get(slug) or {"active_users": 0, "executions": 0, "success": 0, "fail": 0, "hours_saved": 0.0, "satisfaction_avg": None}),
        }
        for slug in selected
    ]
    ranking = sorted(usage_by_solution, key=lambda row: row["executions"], reverse=True)

    users_by_area = _breakdown(current["active_user_ids"], "area", AREA_NAME_BY_SLUG)
    users_by_country = _breakdown(current["active_user_ids"], "country", COUNTRY_NAME_BY_SLUG)

    recent_activity = _recent_activity(selected)
    support_overview = _support_overview()

    return {
        "filters": filters,
        "period_label": PERIOD_LABELS[filters["period"]],
        "areas": [{"slug": s, "name": AREA_NAME_BY_SLUG[s]} for s in AREA_SLUGS],
        "countries": [{"slug": c, "name": COUNTRY_NAME_BY_SLUG[c]} for c in COUNTRY_SLUGS],
        "global_slug": GLOBAL_SLUG,
        "global_label": GLOBAL_LABEL,
        "solutions": [{"slug": s, "name": SOLUTION_BY_SLUG[s]["name"]} for s in SOLUTION_SLUGS],
        "kpis": kpis,
        "trend_months": trend_months,
        "usage_by_solution": usage_by_solution,
        "ranking": ranking,
        "users_by_area": users_by_area,
        "users_by_country": users_by_country,
        "open_items_by_solution": open_items_by_solution,
        "health_alerts": health_alerts,
        "recent_activity": recent_activity,
        "support_overview": support_overview,
        "currency": CURRENCY,
        "hourly_rate": DEMO_HOURLY_RATE,
    }


def _recent_activity(selected_slugs, limit: int = 10) -> list[dict]:
    items = []
    for slug in selected_slugs:
        for record in _showcase_records(slug):
            history = record.get("history") or []
            if not history:
                continue
            last = history[-1]
            items.append(
                {
                    "solution": SOLUTION_BY_SLUG[slug]["name"],
                    "solution_slug": slug,
                    "record_id": record.get("id"),
                    "detail": last.get("detail", ""),
                    "actor": last.get("actor", ""),
                    "at": last.get("at"),
                }
            )
    items.sort(key=lambda i: i["at"] or "", reverse=True)
    return items[:limit]


def _support_overview() -> dict:
    try:
        support_mock = _load_module("support")
        support_service = import_module("solutions.services.support")
    except Exception:  # noqa: BLE001
        return {"available": False}

    records = support_mock.showcase_records()
    open_records = [r for r in records if r["status"] not in support_mock.TERMINAL_STATUSES]
    overdue = [r for r in open_records if support_service.is_overdue(r["created_at"], r["priority"], r["status"])]

    resolved = [r for r in records if r["status"] in ("resolved", "closed")]
    resolution_days = []
    for r in resolved:
        history = r.get("history") or []
        resolved_at = next((h["at"] for h in reversed(history) if h.get("type") == "status_change" and "resuelto" in h.get("detail", "").lower()), None)
        if resolved_at:
            try:
                from solutions.services.common import parse_iso

                delta_days = (parse_iso(resolved_at) - parse_iso(r["created_at"])).total_seconds() / 86400
                resolution_days.append(delta_days)
            except (ValueError, TypeError):
                continue

    avg_resolution_days = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else None

    return {
        "available": True,
        "open": len(open_records),
        "overdue": len(overdue),
        "avg_resolution_days": avg_resolution_days,
    }


def export_csv_rows(filters: dict) -> str:
    import csv
    import io

    from solutions.services.common import csv_cell

    context = build_dashboard_context(filters)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["solucion", "usuarios_activos", "ejecuciones", "exito", "fallo", "horas_ahorradas", "satisfaccion_promedio"])
    for row in context["usage_by_solution"]:
        writer.writerow(
            [
                csv_cell(row["name"]),
                csv_cell(row["active_users"]),
                csv_cell(row["executions"]),
                csv_cell(row["success"]),
                csv_cell(row["fail"]),
                csv_cell(row["hours_saved"]),
                csv_cell(round(row["satisfaction_avg"], 2) if row["satisfaction_avg"] is not None else ""),
            ]
        )
    writer.writerow([])
    writer.writerow(["mes", "ejecuciones", "exito", "fallo", "horas_ahorradas", "usuarios_activos"])
    for month in context["trend_months"]:
        writer.writerow(
            [
                csv_cell(month["month"]),
                csv_cell(month["executions"]),
                csv_cell(month["success"]),
                csv_cell(month["fail"]),
                csv_cell(month["hours_saved"]),
                csv_cell(month["active_users"]),
            ]
        )
    return buffer.getvalue()
