from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.build_static import build

ROOT = Path(__file__).resolve().parents[1]


class ProductionBuildTests(unittest.TestCase):
    def test_static_build_preserves_four_pages_and_assets(self):
        with tempfile.TemporaryDirectory(prefix="kate-static-test-") as temp:
            output = build(Path(temp) / "dist")
            expected = ("index.html", "planner/index.html", "mara/index.html", "control/index.html")
            for relative in expected:
                self.assertTrue((output / relative).is_file(), relative)
            for asset in ("app.css", "app.js", "mara-hero.jpg"):
                self.assertTrue((output / "static" / asset).is_file(), asset)
                self.assertEqual((output / "static" / asset).read_bytes(), (ROOT / "static" / asset).read_bytes())

    def test_pages_keep_existing_planner_mara_navigation_and_disclosures(self):
        with tempfile.TemporaryDirectory(prefix="kate-pages-test-") as temp:
            output = build(Path(temp) / "dist")
            home = (output / "index.html").read_text()
            planner = (output / "planner/index.html").read_text()
            mara = (output / "mara/index.html").read_text()
            self.assertIn("PLANNING PREVIEW", home)
            self.assertIn('href="/planner"', home)
            self.assertIn('data-planner-form', planner)
            self.assertIn('name="target_date"', planner)
            self.assertIn("Supabase database", planner)
            self.assertIn("date-specific availability", mara)
            self.assertIn("Road vs fly-in", mara)
            self.assertNotIn("PREVIEW BUILD", home)
            self.assertNotIn("local preview database", planner)

    def test_control_center_is_locked_and_uses_no_persisted_browser_secret(self):
        with tempfile.TemporaryDirectory(prefix="kate-control-test-") as temp:
            output = build(Path(temp) / "dist")
            control = (output / "control/index.html").read_text()
            js = (output / "static/app.js").read_text()
            self.assertIn('data-control-login', control)
            self.assertIn('data-control-dashboard', control)
            self.assertIn('type="password"', control)
            self.assertIn("Authorization", js)
            self.assertNotIn("localStorage", js)
            self.assertNotIn("sessionStorage", js)
            self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", js)
            self.assertNotIn("VIATOR_API_KEY", js)

    def test_deployment_config_points_only_to_static_netlify_and_kate_function(self):
        config = tomllib.loads((ROOT / "netlify.toml").read_text())
        self.assertEqual(config["build"]["publish"], "dist")
        self.assertIn("scripts/build_static.py", config["build"]["command"])
        redirect = config["redirects"][0]
        self.assertEqual(redirect["from"], "/api/*")
        self.assertIn("bshxiuzdqlqezqsrybtn.supabase.co/functions/v1/kate-api", redirect["to"])
        self.assertEqual(redirect["status"], 200)
        function_config = tomllib.loads((ROOT / "supabase/config.toml").read_text())
        self.assertEqual(function_config["project_id"], "bshxiuzdqlqezqsrybtn")
        self.assertFalse(function_config["functions"]["kate-api"]["verify_jwt"])

    def test_postgres_migration_covers_all_entities_with_closed_client_roles(self):
        sql = (ROOT / "supabase/migrations/20261006000100_kate_production_schema.sql").read_text()
        for table in (
            "destinations", "travel_intents", "products", "opportunities", "pages",
            "planner_sessions", "events", "affiliate_clicks", "conversions", "revenue",
            "experiments", "agent_runs", "business_memory", "incidents",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS public.{table}", sql)
            self.assertIn(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("FROM PUBLIC, anon, authenticated", sql)
        self.assertIn("TO service_role", sql)
        self.assertIn("record_planner_completion", sql)
        self.assertIn("record_affiliate_click", sql)
        self.assertIn("kate_control_summary", sql)
        self.assertIn("ON DELETE SET NULL", sql)


if __name__ == "__main__":
    unittest.main()
