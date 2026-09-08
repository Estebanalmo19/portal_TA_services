"""Builds the single JSON snapshot embedded on every page
(`#arrise-initial-state`, see `templates/base.html`) that seeds a tab's
`sessionStorage` on first visit (see `static/js/state/bootstrap.js`).

Contract every solution's `mock_data.<slug>` module must satisfy:

    def initial_state() -> dict:
        '''JSON-serializable snapshot for this solution: at least the
        showcase records list(s) and any small reference data (statuses,
        categories) the frontend needs to render forms/filters without a
        second round trip. Must not include Python objects (dates -> ISO
        strings, sets -> lists).'''

    def catalog_summary() -> dict:
        '''{"active_users": int, "last_activity": iso-str|None,
            "health": "good"|"warning"|"critical", "open_items": int}
        used to render the catalog card and Solutions Support metrics
        without importing the full initial_state() payload.'''

This module is deliberately defensive about a solution module being
mid-implementation (missing function, import error): the demo should still
boot and show whichever solutions are ready rather than hard-crash, and the
gap is logged loudly so it is never silently mistaken for "done".
"""

import logging
from functools import lru_cache
from importlib import import_module

from django.utils import timezone

from core.agent_ta.faqs import SUGGESTED_QUESTIONS, WELCOME_MESSAGE
from mock_data import STATE_VERSION
from mock_data.reference import SOLUTION_SLUGS

logger = logging.getLogger(__name__)


def _load_solution_mock(slug: str):
    return import_module(f"mock_data.{slug.replace('-', '_')}")


def _solution_initial_state(slug: str) -> dict:
    try:
        module = _load_solution_mock(slug)
        return module.initial_state()
    except Exception:  # noqa: BLE001 - defensive boot, see module docstring
        logger.exception("No se pudo cargar mock_data para la solución %s", slug)
        return {"records": [], "not_implemented": True}


@lru_cache(maxsize=1)
def build_snapshot() -> dict:
    solutions_state = {slug: _solution_initial_state(slug) for slug in SOLUTION_SLUGS}
    return {
        "version": STATE_VERSION,
        "generated_at": timezone.now().isoformat(),
        "core": {
            "notifications": _initial_notifications(),
            "agent_ta": {
                "messages": [{"role": "assistant", "text": WELCOME_MESSAGE}],
                "suggested": SUGGESTED_QUESTIONS,
            },
        },
        "solutions": solutions_state,
    }


def _initial_notifications() -> list[dict]:
    from mock_data.clock import iso, reference_datetime

    now = reference_datetime()
    return [
        {
            "id": "notif-0001",
            "title": "Nuevo referido en revisión",
            "body": "Un referido de Talent Acquisition pasó a «En revisión».",
            "read": False,
            "at": iso(now),
            "link": "/soluciones/referral/",
        },
        {
            "id": "notif-0002",
            "title": "Ticket de soporte asignado",
            "body": "Se asignó un ticket abierto en Solutions Support.",
            "read": False,
            "at": iso(now),
            "link": "/soluciones/support/",
        },
        {
            "id": "notif-0003",
            "title": "Automatización con fallo",
            "body": "Una automatización requiere revisión en Automation Health Center.",
            "read": True,
            "at": iso(now),
            "link": "/soluciones/automation/",
        },
    ]


def catalog_summary(slug: str) -> dict:
    try:
        module = _load_solution_mock(slug)
        return module.catalog_summary()
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo calcular catalog_summary para %s", slug)
        return {"active_users": 0, "last_activity": None, "health": "warning", "open_items": 0}
