import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.people import employees
from mock_data.referral import JOB_OPENINGS
from solutions.services import referral as referral_service
from solutions.services.common import ValidationError


class ReferralServiceTests(SimpleTestCase):
    def _valid_payload(self):
        return {
            "candidate_name": "Ana Prueba (candidato demo)",
            "vacancy_id": JOB_OPENINGS[0]["id"],
            "country": "co",
            "referrer_id": employees()[0]["id"],
            "relation": "amigo",
            "candidate_email": "candidato.demo.test@example.com",
            "existing_ids": ["REF-0001", "REF-0002"],
        }

    def test_create_referral_generates_next_id_and_submitted_status(self):
        result = referral_service.create_referral(self._valid_payload())
        record = result["record"]
        self.assertEqual(record["id"], "REF-0003")
        self.assertEqual(record["status"], "submitted")
        self.assertEqual(len(record["history"]), 1)

    def test_create_referral_rejects_missing_required_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            referral_service.create_referral({})
        self.assertIn("candidate_name", ctx.exception.errors)
        self.assertIn("referrer_id", ctx.exception.errors)

    def test_create_referral_rejects_invalid_email(self):
        payload = self._valid_payload()
        payload["candidate_email"] = "not-an-email"
        with self.assertRaises(ValidationError):
            referral_service.create_referral(payload)

    def test_valid_transition_submitted_to_under_review(self):
        result = referral_service.transition_referral(
            {"id": "REF-0001", "current_status": "submitted", "target_status": "under_review"}
        )
        self.assertEqual(result["status"], "under_review")

    def test_invalid_transition_rejected(self):
        with self.assertRaises(ValidationError):
            referral_service.transition_referral(
                {"id": "REF-0001", "current_status": "submitted", "target_status": "hired"}
            )

    def test_terminal_statuses_have_no_outgoing_transitions(self):
        self.assertEqual(referral_service.allowed_next_statuses("hired"), [])
        self.assertEqual(referral_service.allowed_next_statuses("rejected"), [])

    def test_add_note_requires_text(self):
        with self.assertRaises(ValidationError):
            referral_service.add_note({"id": "REF-0001", "note": ""})

    def test_add_note_success(self):
        result = referral_service.add_note({"id": "REF-0001", "note": "Nota de prueba."})
        self.assertEqual(result["note"]["type"], "comment")


class ReferralEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def _post(self, name, payload):
        return self.client.post(
            reverse(f"referral:{name}"), data=json.dumps(payload), content_type="application/json"
        )

    def test_create_referral_end_to_end(self):
        payload = {
            "candidate_name": "Carlos Prueba (candidato demo)",
            "vacancy_id": JOB_OPENINGS[0]["id"],
            "country": "co",
            "referrer_id": employees()[1]["id"],
            "relation": "amigo",
            "existing_ids": [],
        }
        response = self._post("api_create", payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["record"]["id"], "REF-0001")

    def test_transition_endpoint_rejects_invalid_move(self):
        response = self._post(
            "api_transition", {"id": "REF-0001", "current_status": "hired", "target_status": "submitted"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
