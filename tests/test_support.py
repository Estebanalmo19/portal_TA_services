import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.people import employees
from solutions.services import support as support_service
from solutions.services.common import ValidationError


class SupportServiceTests(SimpleTestCase):
    def _valid_payload(self, **overrides):
        payload = {
            "affected_solution": "referral",
            "ticket_type": "problema_tecnico",
            "subject": "No carga el formulario",
            "description": "Al enviar un referido la página se queda cargando.",
            "impact": "mi_equipo",
            "requester_id": employees()[0]["id"],
            "existing_ids": ["SUP-0001"],
        }
        payload.update(overrides)
        return payload

    def test_create_ticket_generates_next_id(self):
        result = support_service.create_ticket(self._valid_payload())
        self.assertEqual(result["record"]["id"], "SUP-0002")
        self.assertEqual(result["record"]["status"], "new")

    def test_suggested_priority_used_when_priority_omitted(self):
        result = support_service.create_ticket(self._valid_payload(impact="bloquea_operacion"))
        self.assertIn(result["record"]["priority"], ("alta", "urgente"))

    def test_explicit_priority_overrides_suggestion(self):
        result = support_service.create_ticket(self._valid_payload(priority="baja"))
        self.assertEqual(result["record"]["priority"], "baja")

    def test_resolved_can_reopen_to_in_progress_preserving_history_contract(self):
        result = support_service.transition_ticket(
            {"id": "SUP-0001", "current_status": "resolved", "target_status": "in_progress"}
        )
        self.assertEqual(result["status"], "in_progress")
        self.assertIn("history_entry", result)

    def test_closed_is_terminal(self):
        self.assertEqual(support_service.allowed_next_statuses("closed"), [])

    def test_is_overdue_false_when_resolved(self):
        self.assertFalse(support_service.is_overdue("2020-01-01T00:00:00Z", "urgente", "resolved"))

    def test_is_overdue_true_when_open_past_sla(self):
        self.assertTrue(support_service.is_overdue("2020-01-01T00:00:00Z", "urgente", "new"))

    def test_rate_ticket_requires_resolved_or_closed(self):
        with self.assertRaises(ValidationError):
            support_service.rate_ticket({"id": "SUP-0001", "current_status": "new", "score": 5})


class SupportPrefillTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_prefill_query_params_render_without_error(self):
        response = self.client.get(
            reverse("support:home"),
            {"sol": "referral", "asunto": "Problema de ejemplo", "descripcion": "Detalle", "origen": "test"},
        )
        self.assertEqual(response.status_code, 200)

    def test_prefill_with_unknown_solution_does_not_crash(self):
        response = self.client.get(reverse("support:home"), {"sol": "no-existe"})
        self.assertEqual(response.status_code, 200)


class SupportEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_create_ticket_end_to_end(self):
        payload = {
            "affected_solution": "ta",
            "ticket_type": "consulta",
            "subject": "Duda sobre Agent TA",
            "description": "No entiendo cómo funciona el asistente.",
            "impact": "solo_yo",
            "requester_id": employees()[2]["id"],
            "existing_ids": [],
        }
        response = self.client.post(
            reverse("support:api_create"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["record"]["id"], "SUP-0001")
