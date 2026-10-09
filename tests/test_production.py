from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.build_static import build

ROOT = Path(__file__).resolve().parents[1]


class ProductionBuildTests(unittest.TestCase):
    def test_german_funnel_has_real_pages_download_and_private_planner_metadata(self):
        with tempfile.TemporaryDirectory(prefix="kate-german-test-") as temp:
            output = build(Path(temp) / "dist")
            for relative in ("index.html", "mara/index.html", "planner/index.html", "guides/index.html", "resources/safari-booking-checklist/index.html"):
                html = (output / "de" / relative).read_text()
                self.assertIn('<html lang="de">', html)
                self.assertIn('hreflang="en"', html)
                self.assertIn('hreflang="de"', html)
                self.assertIn('src="/static/i18n.js"', html)
                self.assertLess(html.index('/static/i18n.js'), html.index('/static/app.js'))
            self.assertIn('content="noindex,follow"', (output / "de/planner/index.html").read_text())
            self.assertFalse((output / "de/control/index.html").exists())
            self.assertIn('BUCHUNGSCHECKLISTE', (output / "de/resources/safari-booking-checklist.txt").read_text())
            self.assertIn('/de/mara/', (output / 'sitemap.xml').read_text())

    def test_cross_sell_uses_existing_supplier_handoff_and_no_public_admin_navigation(self):
        with tempfile.TemporaryDirectory(prefix="kate-extras-test-") as temp:
            output = build(Path(temp) / "dist")
            home = (output / 'index.html').read_text()
            mara = (output / 'mara/index.html').read_text()
            self.assertIn('/mara/#nairobi-extras', home)
            self.assertNotIn('href="/control"', home)
            self.assertIn('data-offer-category="nairobi"', mara)
            self.assertIn('These are separate bookings', mara)
            self.assertIn('data-offer-category="nairobi"', (output / 'de/mara/index.html').read_text())

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
            self.assertIn("SAFARI PLANNING", home)
            self.assertIn('href="/planner/"', home)
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
            admin_js = js.split("const dashboard =", 1)[1]
            self.assertNotIn("localStorage", admin_js)
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

    def test_supplied_viator_clickouts_stay_discovery_only_and_exact(self):
        sql = (ROOT / "supabase/migrations/20261006000200_kate_security_and_clickout_data.sql").read_text()
        urls = (
            "https://www.viator.com/tours/Nairobi/3-Days-2-Nights-Masai-Mara-Shared-Transport-Safari/d5280-427094P4?pid=P00323912&mcid=42383&medium=link&medium_version=selector",
            "https://www.viator.com/tours/Nairobi/3-Days-masai-mara-safari/d5280-107758P7?pid=P00323912&mcid=42383&medium=link&medium_version=selector",
            "https://www.viator.com/tours/Nairobi/3-Days-Masai-Mara-Flying-Safari-and-Hot-Air-Balloon-Ride-Package/d5280-260078P150?pid=P00323912&mcid=42383&medium=link&medium_version=selector",
        )
        for product_id, url in zip(("427094P4", "107758P7", "260078P150"), urls, strict=True):
            self.assertIn(product_id, sql)
            self.assertIn(url, sql)
        self.assertIn("'discovery_needs_data'", sql)
        self.assertIn("'unverified'", sql)
        self.assertIn("'not_verified'", sql)
        self.assertIn("'source_method', 'clickOffToPDP'", sql)
        self.assertIn("ON CONFLICT (product_id) DO NOTHING", sql)
        edge = (ROOT / "supabase/functions/kate-api/handler.js").read_text()
        self.assertIn('product.availability_state !== "confirmed"', edge)
        self.assertIn("!product.date_availability_confirmed", edge)

    def test_supabase_hardening_migration_revokes_public_definer_and_indexes_fk(self):
        sql = (ROOT / "supabase/migrations/20261006000200_kate_security_and_clickout_data.sql").read_text()
        self.assertIn("REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated", sql)
        self.assertIn("travel_intents_destination_id_idx", sql)
        self.assertIn("2026-10-06T03:48:53Z", sql)
        self.assertIn("source_last_checked", sql)


if __name__ == "__main__":
    unittest.main()
