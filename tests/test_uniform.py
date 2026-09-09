import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.people import eligible_population
from mock_data.reference import SITES
from mock_data.uniform import CHECKLIST_ITEM_SLUGS, INSPECTOR_POOL, SHIFT_SLUGS
from solutions.services import uniform as uniform_service
from solutions.services.common import ValidationError


def _all_status(items, status):
    return {slug: status for slug in items}


class ScoreFormulaTests(SimpleTestCase):
    """Section 10 explicitly asks for: conformes, faltantes, dañados, mezcla
    de no_aplica, y todos no_aplica."""

    def test_all_conforme_scores_100(self):
        items = [{"status": "conforme"} for _ in range(3)]
        self.assertEqual(uniform_service.compute_score(items), 100.0)

    def test_all_faltante_scores_0(self):
        items = [{"status": "faltante"} for _ in range(3)]
        self.assertEqual(uniform_service.compute_score(items), 0.0)

    def test_mixed_statuses_excludes_no_aplica_from_denominator(self):
        items = [
            {"status": "conforme"},
            {"status": "danado"},
            {"status": "no_aplica"},
            {"status": "no_aplica"},
        ]
        # 1 conforme / 2 aplicables (2 items marked no_aplica excluded) = 50%
        self.assertEqual(uniform_service.compute_score(items), 50.0)

    def test_all_no_aplica_returns_none_never_divides_by_zero(self):
        items = [{"status": "no_aplica"} for _ in range(4)]
        self.assertIsNone(uniform_service.compute_score(items))

    def test_status_for_score_none_is_sin_evaluacion(self):
        self.assertEqual(uniform_service.status_for_score(None), "sin_evaluacion")

    def test_status_for_score_100_is_conforme(self):
        self.assertEqual(uniform_service.status_for_score(100.0), "conforme")

    def test_status_for_score_below_100_requires_seguimiento(self):
        self.assertEqual(uniform_service.status_for_score(75.0), "seguimiento")


class CreateInspectionTests(SimpleTestCase):
    def _valid_payload(self, item_status="conforme"):
        employee = eligible_population("uniform")[0]
        return {
            "employee_id": employee["id"],
            "site": SITES[0]["slug"],
            "shift": SHIFT_SLUGS[0],
            "inspector": INSPECTOR_POOL[0],
            "observations": "Inspección de prueba.",
            "evidence_filename": "foto_demo.jpg",
            "items": _all_status(CHECKLIST_ITEM_SLUGS, item_status),
            "existing_ids": [],
        }

    def test_full_conformance_creates_conforme_inspection(self):
        result = uniform_service.create_inspection(self._valid_payload("conforme"))
        record = result["inspection"]
        self.assertEqual(record["score"], 100.0)
        self.assertEqual(record["status"], "conforme")
        self.assertEqual(record["id"], "INSP-0001")

    def test_partial_conformance_requires_followup(self):
        payload = self._valid_payload("conforme")
        items = payload["items"]
        first_key = next(iter(items))
        items[first_key] = "faltante"
        result = uniform_service.create_inspection(payload)
        self.assertEqual(result["inspection"]["status"], "seguimiento")
        self.assertIn("followup", result)
        self.assertIsNotNone(result["followup"])
        self.assertIn("responsible_id", result["followup"])
        self.assertIn("due_date", result["followup"])

    def test_all_no_aplica_creates_sin_evaluacion_with_no_followup(self):
        result = uniform_service.create_inspection(self._valid_payload("no_aplica"))
        self.assertEqual(result["inspection"]["status"], "sin_evaluacion")
        self.assertIsNone(result["followup"])

    def test_missing_checklist_item_rejected(self):
        payload = self._valid_payload("conforme")
        del payload["items"][CHECKLIST_ITEM_SLUGS[0]]
        with self.assertRaises(ValidationError):
            uniform_service.create_inspection(payload)

    def test_unknown_employee_rejected(self):
        payload = self._valid_payload("conforme")
        payload["employee_id"] = "EMP-999999"
        with self.assertRaises(ValidationError):
            uniform_service.create_inspection(payload)


class UniformEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_create_inspection_end_to_end(self):
        employee = eligible_population("uniform")[1]
        payload = {
            "employee_id": employee["id"],
            "site": SITES[0]["slug"],
            "shift": SHIFT_SLUGS[0],
            "inspector": INSPECTOR_POOL[0],
            "observations": "",
            "evidence_filename": "foto_demo.jpg",
            "items": _all_status(CHECKLIST_ITEM_SLUGS, "conforme"),
            "existing_ids": [],
        }
        response = self.client.post(
            reverse("uniform:api_create"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["inspection"]["score"], 100.0)
