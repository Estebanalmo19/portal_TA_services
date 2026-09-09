import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.appearance import ROLE_SLUGS, SHIFT_SLUGS
from mock_data.people import eligible_population
from mock_data.reference import SITES
from solutions.services import appearance as appearance_service
from solutions.services.common import ValidationError


class AppearanceEthicalConstraintsTests(SimpleTestCase):
    """Section 8.7 forbids computing Approved/Requires review from criteria.
    These tests assert that guarantee at the service layer, not just in the
    UI copy."""

    def _employee(self):
        return eligible_population("appearance")[0]

    def test_result_is_whatever_the_human_reviewer_chose_regardless_of_criteria(self):
        employee = self._employee()
        create = appearance_service.create_review(
            {"employee_id": employee["id"], "site": SITES[0]["slug"], "role": ROLE_SLUGS[0], "shift": SHIFT_SLUGS[0]}
        )
        review_id = create["record"]["id"]
        appearance_service.start_review({"id": review_id, "current_status": "pending"})

        # All criteria unchecked (worst possible checklist) but the human
        # reviewer still explicitly picks "approved" — the service must
        # honor that choice, not override it with a computed rejection.
        result = appearance_service.complete_review(
            {
                "id": review_id,
                "current_status": "in_review",
                "presentation_notes": "Todo en orden a criterio del revisor.",
                "resultado": "approved",
                "criteria": [],
            }
        )
        self.assertEqual(result["result"], "approved")

    def test_requires_review_needs_a_followup_responsible_and_date(self):
        with self.assertRaises(ValidationError):
            appearance_service.complete_review(
                {
                    "id": "APR-0001",
                    "current_status": "in_review",
                    "presentation_notes": "Observación de prueba.",
                    "resultado": "requires_review",
                    "criteria": [],
                    "follow_up": {},
                }
            )

    def test_tattoo_notes_are_plain_optional_text_not_a_criterion(self):
        employee = self._employee()
        create = appearance_service.create_review(
            {"employee_id": employee["id"], "site": SITES[0]["slug"], "role": ROLE_SLUGS[0], "shift": SHIFT_SLUGS[0]}
        )
        review_id = create["record"]["id"]
        appearance_service.start_review({"id": review_id, "current_status": "pending"})
        result = appearance_service.complete_review(
            {
                "id": review_id,
                "current_status": "in_review",
                "presentation_notes": "Presentación adecuada.",
                "tattoo_notes": "Caso ficticio: cobertura según guía de sede.",
                "resultado": "approved",
                "criteria": [],
            }
        )
        self.assertEqual(result["result"], "approved")
        self.assertIn("cobertura", result["tattoo_notes"])


class AppearanceTransitionTests(SimpleTestCase):
    def test_cannot_complete_a_review_that_never_started(self):
        with self.assertRaises(ValidationError):
            appearance_service.complete_review(
                {
                    "id": "APR-0001",
                    "current_status": "pending",
                    "presentation_notes": "x",
                    "resultado": "approved",
                    "criteria": [],
                }
            )


class AppearanceEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_create_review_end_to_end(self):
        employee = eligible_population("appearance")[1]
        payload = {
            "employee_id": employee["id"],
            "site": SITES[0]["slug"],
            "role": ROLE_SLUGS[0],
            "shift": SHIFT_SLUGS[0],
            "existing_ids": [],
        }
        response = self.client.post(
            reverse("appearance:api_create"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["record"]["status"], "pending")
