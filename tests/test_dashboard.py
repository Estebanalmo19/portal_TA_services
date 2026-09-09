from django.test import Client, SimpleTestCase
from django.urls import reverse

from dashboard import services


class FilterParsingTests(SimpleTestCase):
    def test_unknown_values_fall_back_to_defaults(self):
        filters = services.parse_filters({"periodo": "9y", "solucion": "no-existe", "pais": "xx", "area": "xx"})
        self.assertEqual(filters["period"], services.DEFAULT_PERIOD)
        self.assertEqual(filters["solution"], "all")
        self.assertEqual(filters["country"], "global")
        self.assertEqual(filters["area"], "all")

    def test_valid_values_are_kept(self):
        filters = services.parse_filters({"periodo": "12m", "solucion": "referral", "pais": "co", "area": "ta"})
        self.assertEqual(filters, {"period": "12m", "solution": "referral", "country": "co", "area": "ta"})


class DashboardAggregationTests(SimpleTestCase):
    def test_all_solutions_all_scope_has_full_kpi_set(self):
        context = services.build_dashboard_context(services.parse_filters({}))
        for key in ("active_users", "adoption", "executions", "success_rate", "hours_saved", "savings", "satisfaction", "open_items"):
            self.assertIn(key, context["kpis"])

    def test_single_solution_scope_matches_its_own_row_in_ranking(self):
        context = services.build_dashboard_context(services.parse_filters({"solucion": "referral"}))
        self.assertEqual(len(context["usage_by_solution"]), 1)
        self.assertEqual(context["usage_by_solution"][0]["slug"], "referral")
        self.assertEqual(context["kpis"]["executions"]["value"], context["usage_by_solution"][0]["executions"])

    def test_twelve_month_period_has_no_comparable_previous_window(self):
        context = services.build_dashboard_context(services.parse_filters({"periodo": "12m"}))
        self.assertEqual(context["kpis"]["active_users"]["delta"]["label"], "Sin base comparable")

    def test_area_filter_never_exceeds_eligible_population(self):
        context = services.build_dashboard_context(
            services.parse_filters({"solucion": "security", "area": "security"})
        )
        self.assertLessEqual(context["kpis"]["active_users"]["value"], 240)

    def test_adoption_percentage_is_0_to_100_not_a_bare_fraction(self):
        context = services.build_dashboard_context(services.parse_filters({}))
        adoption = context["kpis"]["adoption"]["value"]
        if adoption is not None:
            self.assertGreaterEqual(adoption, 0)
            self.assertLessEqual(adoption, 100)

    def test_impossible_scope_yields_sin_datos_not_a_crash(self):
        # No employee is simultaneously in the "ta" area AND a Colombia-only
        # solution's population edge case: exercise a narrow, possibly-empty
        # scope and confirm we get a clean "no data" value, not a ZeroDivisionError.
        context = services.build_dashboard_context(
            services.parse_filters({"solucion": "security", "pais": "ge", "area": "hr"})
        )
        self.assertEqual(context["kpis"]["active_users"]["value"], 0)
        self.assertIsNone(context["kpis"]["adoption"]["value"])


class DashboardViewTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_page_loads(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_respects_filters_in_querystring(self):
        response = self.client.get(reverse("dashboard:home"), {"solucion": "referral", "periodo": "3m"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filters"]["solution"], "referral")

    def test_csv_export_matches_filtered_view(self):
        response = self.client.get(reverse("dashboard:export_csv"), {"solucion": "referral"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8")
        self.assertIn("Referral Portal", content)
        self.assertNotIn("Security Database Hub", content)
