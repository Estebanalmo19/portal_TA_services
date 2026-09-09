import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.people import eligible_population
from mock_data.reference import SITES
from solutions.services import security as security_service
from solutions.services.common import ValidationError


class SecurityServiceTests(SimpleTestCase):
    def _valid_payload(self):
        return {
            "title": "Puerta forzada en bodega",
            "description": "Se detectó una puerta forzada durante la ronda nocturna.",
            "site": SITES[0]["slug"],
            "floor": "Piso 1",
            "category": "acceso",
            "severity": "alta",
            "existing_ids": ["INC-0001"],
        }

    def test_create_incident_without_assignee_is_new(self):
        result = security_service.create_incident(self._valid_payload())
        self.assertEqual(result["record"]["status"], "new")
        self.assertEqual(result["record"]["id"], "INC-0002")

    def test_create_incident_with_assignee_starts_assigned(self):
        payload = self._valid_payload()
        payload["assignee_id"] = eligible_population("security")[0]["id"]
        result = security_service.create_incident(payload)
        self.assertEqual(result["record"]["status"], "assigned")

    def test_create_incident_rejects_unknown_category(self):
        payload = self._valid_payload()
        payload["category"] = "no-existe"
        with self.assertRaises(ValidationError):
            security_service.create_incident(payload)

    def test_reopen_from_resolved_is_allowed(self):
        self.assertTrue(security_service.GRAPH.can_transition("resolved", "in_progress"))

    def test_invalid_transition_new_to_resolved_rejected(self):
        with self.assertRaises(ValidationError):
            security_service.transition_incident(
                {"id": "INC-0001", "current_status": "new", "target_status": "resolved"}
            )


class SecurityExportCsvTests(SimpleTestCase):
    def test_export_neutralizes_formula_like_title(self):
        rows = [
            {
                "id": "INC-0099",
                "title": "=cmd|' /C calc'!A0",
                "site": SITES[0]["slug"],
                "floor": "Piso 1",
                "category": "acceso",
                "severity": "alta",
                "status": "new",
                "assignee_name": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        csv_text = security_service.export_incidents_csv(rows)
        self.assertNotIn("\n=cmd", csv_text)
        self.assertIn("'=cmd", csv_text)


class SecurityEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_create_incident_end_to_end(self):
        payload = {
            "title": "Cámara fuera de línea",
            "description": "La cámara del sótano dejó de transmitir video.",
            "site": SITES[1]["slug"],
            "floor": "Sótano",
            "category": "camara",
            "severity": "media",
            "existing_ids": [],
        }
        response = self.client.post(
            reverse("security:api_create"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["record"]["id"], "INC-0001")
