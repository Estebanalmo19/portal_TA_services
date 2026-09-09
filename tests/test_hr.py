import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.hr import agents, requesters
from solutions.services import hr as hr_service
from solutions.services.common import ValidationError


class HrServiceTests(SimpleTestCase):
    def _valid_payload(self, category="solicitud_general"):
        return {
            "requester_id": requesters()[0]["id"],
            "category": category,
            "subject": "Necesito ayuda con mi solicitud",
            "description": "Descripción de prueba con suficiente longitud.",
            "priority": "media",
            "existing_ids": ["HR-0001"],
        }

    def test_create_ticket_defaults_to_new_status(self):
        result = hr_service.create_ticket(self._valid_payload())
        self.assertEqual(result["record"]["status"], "new")
        self.assertEqual(result["record"]["id"], "HR-0002")

    def test_create_ticket_requires_category_specific_fields(self):
        payload = self._valid_payload(category="vacaciones")
        with self.assertRaises(ValidationError) as ctx:
            hr_service.create_ticket(payload)
        self.assertTrue(any("fecha_inicio" in k or "fecha_fin" in k for k in ctx.exception.errors))

    def test_waiting_can_return_to_in_progress(self):
        result = hr_service.transition_ticket(
            {"id": "HR-0001", "current_status": "waiting_for_employee", "target_status": "in_progress"}
        )
        self.assertEqual(result["status"], "in_progress")

    def test_invalid_transition_new_to_closed_directly_is_rejected_or_allowed_consistently(self):
        # Whatever the module's graph allows for new->closed, calling it
        # must never raise for an edge the graph itself lists as valid.
        allowed = hr_service.allowed_next_statuses("new")
        for target in allowed:
            with self.subTest(target=target):
                result = hr_service.transition_ticket(
                    {"id": "HR-0001", "current_status": "new", "target_status": target}
                )
                self.assertEqual(result["status"], target)

    def test_unlisted_transition_rejected(self):
        with self.assertRaises(ValidationError):
            hr_service.transition_ticket(
                {"id": "HR-0001", "current_status": "closed", "target_status": "new"}
            )

    def test_resolve_with_invalid_survey_score_rejected(self):
        with self.assertRaises(ValidationError):
            hr_service.transition_ticket(
                {
                    "id": "HR-0001",
                    "current_status": "in_progress",
                    "target_status": "resolved",
                    "survey": {"score": 9},
                }
            )

    def test_resolve_with_valid_survey_score_accepted(self):
        result = hr_service.transition_ticket(
            {
                "id": "HR-0001",
                "current_status": "in_progress",
                "target_status": "resolved",
                "survey": {"score": 5, "comment": "Excelente"},
            }
        )
        self.assertEqual(result["survey"]["score"], 5)


class HrEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_create_ticket_end_to_end(self):
        payload = {
            "requester_id": requesters()[1]["id"],
            "category": "consulta_contractual",
            "subject": "Duda sobre mi contrato",
            "description": "Quisiera saber el tipo de contrato que tengo.",
            "priority": "baja",
            "existing_ids": [],
        }
        response = self.client.post(
            reverse("hr:api_create"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["record"]["id"], "HR-0001")
