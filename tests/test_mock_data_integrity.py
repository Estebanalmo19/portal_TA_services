"""Dataset integrity that every solution's mock_data module must satisfy,
plus the server-side half of "estado malformado" handling (core.state):
the client-side sessionStorage recovery path is JS-only and is covered by
manual/browser verification instead — see docs/verification.md.
"""

import copy
import json
import re
from datetime import datetime

from django.test import RequestFactory, SimpleTestCase

from core.state import PayloadTooComplex, parse_json_body
from mock_data.reference import SOLUTION_SLUGS
from mock_data import (
    appearance,
    automation,
    hr,
    referral,
    security,
    support,
    uniform,
)

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

MODULES = {
    "referral": referral,
    "security": security,
    "uniform": uniform,
    "hr": hr,
    "automation": automation,
    "support": support,
    "appearance": appearance,
}


def _all_ids(records, key="id"):
    return [r[key] for r in records if key in r]


def _walk_dates(value, found):
    if isinstance(value, str) and "T" in value and value.endswith("Z"):
        found.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            _walk_dates(v, found)
    elif isinstance(value, list):
        for v in value:
            _walk_dates(v, found)


class ModuleContractTests(SimpleTestCase):
    def test_every_solution_slug_has_a_mock_module(self):
        self.assertEqual(set(MODULES.keys()), set(SOLUTION_SLUGS))

    def test_every_module_exposes_initial_state_and_catalog_summary(self):
        for slug, module in MODULES.items():
            with self.subTest(slug=slug):
                state = module.initial_state()
                self.assertIsInstance(state, dict)
                summary = module.catalog_summary()
                self.assertIn("active_users", summary)
                self.assertIn("health", summary)
                self.assertIn(summary["health"], ("good", "warning", "critical"))

    def test_initial_state_is_json_serializable(self):
        for slug, module in MODULES.items():
            with self.subTest(slug=slug):
                json.dumps(module.initial_state())  # raises on any non-JSON value (e.g. datetime, set)

    def test_at_least_fifteen_showcase_records_per_module(self):
        record_getters = {
            "referral": lambda: referral.showcase_records(),
            "security": lambda: security.showcase_records(),
            "uniform": lambda: uniform.showcase_inspections(),
            "hr": lambda: hr.showcase_records(),
            "support": lambda: support.showcase_records(),
            "appearance": lambda: appearance.showcase_records(),
        }
        for slug, getter in record_getters.items():
            with self.subTest(slug=slug):
                self.assertGreaterEqual(len(getter()), 15, f"{slug} debe precargar al menos 15 registros")

    def test_automation_has_exactly_six_automations_and_enough_executions(self):
        state = automation.initial_state()
        self.assertEqual(len(state["automations"]), 6)
        self.assertGreaterEqual(len(state["executions"]), 15)


class IdIntegrityTests(SimpleTestCase):
    def test_referral_ids_unique_and_well_formed(self):
        ids = _all_ids(referral.showcase_records())
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.match(r"^REF-\d{4}$", i) for i in ids))

    def test_security_incident_ids_unique(self):
        ids = _all_ids(security.showcase_records())
        self.assertEqual(len(ids), len(set(ids)))

    def test_hr_ticket_ids_unique(self):
        ids = _all_ids(hr.showcase_records())
        self.assertEqual(len(ids), len(set(ids)))

    def test_support_ticket_ids_unique_and_sup_prefixed(self):
        ids = _all_ids(support.showcase_records())
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.match(r"^SUP-\d{4}$", i) for i in ids))


class DateIntegrityTests(SimpleTestCase):
    def test_all_embedded_timestamps_parse_as_valid_iso(self):
        for slug, module in MODULES.items():
            state = module.initial_state()
            found = []
            _walk_dates(state, found)
            self.assertTrue(found, f"{slug}: se esperaban timestamps ISO en el estado inicial")
            for value in found:
                with self.subTest(slug=slug, value=value):
                    self.assertRegex(value, ISO_RE)
                    datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")  # raises if not a real date


class NoSharedMutationTests(SimpleTestCase):
    """mock_data getters are ``lru_cache``d process-wide: a view that
    mutated the cached list in place would leak that mutation into every
    other request for the lifetime of the process. Every solution's
    ``create_*``/``transition_*`` must build new dicts, never mutate the
    cached seed data."""

    def test_creating_a_referral_does_not_mutate_the_cached_showcase_list(self):
        from mock_data.people import employees
        from solutions.services import referral as referral_service

        before = copy.deepcopy(referral.showcase_records())
        referral_service.create_referral(
            {
                "candidate_name": "Mutación Test (candidato demo)",
                "vacancy_id": referral.JOB_OPENINGS[0]["id"],
                "country": "co",
                "referrer_id": employees()[0]["id"],
                "relation": "amigo",
                "existing_ids": [r["id"] for r in before],
            }
        )
        after = referral.showcase_records()
        self.assertEqual(before, after, "create_referral no debe mutar mock_data.referral.showcase_records()")

    def test_transitioning_a_security_incident_does_not_mutate_cached_records(self):
        from solutions.services import security as security_service

        before = copy.deepcopy(security.showcase_records())
        security_service.transition_incident(
            {"id": before[0]["id"], "current_status": "new", "target_status": "assigned"}
        )
        after = security.showcase_records()
        self.assertEqual(before, after)


class StatePayloadGuardTests(SimpleTestCase):
    """Server-side half of "estado ausente, corrupto o de una versión
    anterior": the operation endpoints must bound-check the payload before
    trusting anything in it (see core/state.py, docs/implementation-notes.md)."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_oversized_body_rejected(self):
        request = self.factory.post(
            "/x/", data=b"a" * 10, content_type="application/json"
        )
        with self.assertRaises(ValueError):
            parse_json_body(request, max_bytes=5)

    def test_too_deep_payload_rejected(self):
        nested = {}
        cursor = nested
        for _ in range(20):
            cursor["next"] = {}
            cursor = cursor["next"]
        request = self.factory.post(
            "/x/", data=json.dumps(nested), content_type="application/json"
        )
        with self.assertRaises(PayloadTooComplex):
            parse_json_body(request, max_depth=5)

    def test_non_json_body_rejected(self):
        request = self.factory.post("/x/", data=b"not json at all", content_type="application/json")
        with self.assertRaises(ValueError):
            parse_json_body(request)

    def test_non_object_json_rejected(self):
        request = self.factory.post("/x/", data=b"[1, 2, 3]", content_type="application/json")
        with self.assertRaises(ValueError):
            parse_json_body(request)

    def test_empty_body_returns_empty_dict(self):
        request = self.factory.post("/x/", data=b"", content_type="application/json")
        self.assertEqual(parse_json_body(request), {})
