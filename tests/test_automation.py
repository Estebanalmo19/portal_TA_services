import json

from django.test import Client, SimpleTestCase
from django.urls import reverse

from mock_data.automation import AUTOMATION_IDS
from solutions.services import automation as automation_service
from solutions.services.common import ValidationError


class HealthFormulaTests(SimpleTestCase):
    def test_all_success_is_good(self):
        self.assertEqual(automation_service.recompute_health(["success"] * 5), "good")

    def test_mostly_failed_is_critical(self):
        self.assertEqual(automation_service.recompute_health(["failed"] * 4 + ["success"]), "critical")

    def test_empty_history_does_not_crash(self):
        # Never divide by zero on a brand-new automation with no runs yet.
        self.assertIn(automation_service.recompute_health([]), ("good", "warning", "critical"))


class RetryExecutionTests(SimpleTestCase):
    def test_retry_always_succeeds_deterministically(self):
        result = automation_service.retry_execution(
            {
                "automation_id": AUTOMATION_IDS[0],
                "execution_id": "RUN-0099",
                "records_processed": 10,
                "existing_ids": ["RUN-0001"],
                "recent_statuses": ["failed", "failed"],
            }
        )
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["execution"]["retry_of"], "RUN-0099")
        self.assertEqual(result["execution"]["id"], "RUN-0002")

    def test_retry_recomputes_health_from_recent_statuses_plus_new_success(self):
        result = automation_service.retry_execution(
            {
                "automation_id": AUTOMATION_IDS[0],
                "execution_id": "RUN-0001",
                "recent_statuses": ["success", "success", "success", "success"],
                "existing_ids": [],
            }
        )
        self.assertEqual(result["health"], "good")

    def test_retry_rejects_unknown_automation(self):
        with self.assertRaises(ValidationError):
            automation_service.retry_execution({"automation_id": "AUTO-9999", "execution_id": "RUN-0001"})


class PauseResumeTests(SimpleTestCase):
    def test_pause_sets_flag_true(self):
        result = automation_service.set_paused({"automation_id": AUTOMATION_IDS[0], "paused": True})
        self.assertTrue(result["paused"])

    def test_resume_sets_flag_false(self):
        result = automation_service.set_paused({"automation_id": AUTOMATION_IDS[0], "paused": False})
        self.assertFalse(result["paused"])


class AutomationEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_retry_endpoint_preserves_original_failure_semantics(self):
        payload = {
            "automation_id": AUTOMATION_IDS[1],
            "execution_id": "RUN-0005",
            "recent_statuses": ["failed"],
            "existing_ids": ["RUN-0001", "RUN-0002"],
        }
        response = self.client.post(
            reverse("automation:api_retry"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["result"]["execution"]["retry_of"], "RUN-0005")
        self.assertNotEqual(data["result"]["execution"]["id"], "RUN-0005")
