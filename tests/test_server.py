from __future__ import annotations

import json
import base64
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import server


class KatePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="kate-test-")
        cls.db_path = Path(cls.tmp.name) / "kate.sqlite3"
        cls.patches = [
            patch.object(server, "DB_PATH", cls.db_path),
            patch.object(server, "DATA_DIR", Path(cls.tmp.name)),
            patch.object(server, "SNAPSHOT_PATH", None),
            patch.object(server, "SETTINGS", {"admin_secret": None, "admin_configured": False}),
        ]
        for item in cls.patches:
            item.start()
        server.init_db()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.KateHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        for item in reversed(cls.patches):
            item.stop()
        cls.tmp.cleanup()

    def request(self, path, payload=None, method=None, extra_headers=None):
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        headers.update(extra_headers or {})
        req = Request(self.base + path, data=data, method=method, headers=headers)
        try:
            response = urlopen(req, timeout=4)
            return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def setUp(self):
        with server.open_db() as db:
            for table in ("events", "planner_sessions", "travel_intents", "affiliate_clicks", "products", "conversions", "revenue"):
                db.execute(f"DELETE FROM {table}")

    def test_home_and_security_headers_and_health(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"PREVIEW BUILD", body)
        self.assertIn("nosniff", headers.get("X-Content-Type-Options"))
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy"))
        self.assertEqual(self.request("/healthz")[0], 200)

    def test_planner_persists_completion_events_and_input_without_supplier_claims(self):
        payload = {"origin": "Nairobi", "focus": "maasai_mara", "days": 3, "travelers": 2,
                   "budget": 1200, "currency": "CHF", "interests": ["wildlife", "photography"],
                   "comfort": "balanced", "target_date": "", "flexibility": "not_sure"}
        self.assertEqual(self.request("/planner")[0], 200)
        status, _, body = self.request("/api/plan", payload)
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(len(result["itinerary"]), 3)
        self.assertFalse(result["availability_checked"])
        self.assertFalse(result["price_checked"])
        self.assertIn("No live inventory", result["message"])
        with server.open_db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM planner_sessions").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM travel_intents").fetchone()[0], 1)
            rows = dict(db.execute("SELECT event_type,COUNT(*) FROM events GROUP BY event_type").fetchall())
        self.assertEqual(rows.get("planner_started"), 1)
        self.assertEqual(rows.get("planner_completed"), 1)
        self.assertGreaterEqual(rows.get("page_view", 0), 1)

    def test_invalid_plan_records_start_but_never_completion(self):
        status, _, body = self.request("/api/plan", {"origin": "", "days": 3, "travelers": 2})
        self.assertEqual(status, 400)
        self.assertIn(b"starting point", body)
        with server.open_db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM planner_sessions").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE event_type='planner_completed'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE event_type='planner_started'").fetchone()[0], 1)

    def test_control_is_not_exposed_without_admin_secret(self):
        status, _, body = self.request("/control")
        self.assertEqual(status, 200)
        self.assertIn(b"Access is not configured", body)
        self.assertNotIn(b"Recorded activity", body)
        status, _, body = self.request("/api/control")
        self.assertEqual(status, 403)
        self.assertIn(b"analytics remain hidden", body)

    def test_configured_control_requires_basic_auth(self):
        original = server.SETTINGS
        server.SETTINGS = {"admin_secret": "unit-test-admin-secret-value-12345", "admin_configured": True}
        try:
            self.assertEqual(self.request("/api/control")[0], 401)
            credential = base64.b64encode(b"admin:unit-test-admin-secret-value-12345").decode("ascii")
            status, _, body = self.request("/api/control", extra_headers={"Authorization": f"Basic {credential}"})
            self.assertEqual(status, 200)
            self.assertIn(b'"events"', body)
            self.assertNotIn(b"unit-test-admin-secret-value", body)
        finally:
            server.SETTINGS = original

    def test_unapproved_product_view_and_affiliate_click_are_blocked(self):
        for path in ("/api/product-view", "/api/affiliate-click"):
            status, _, body = self.request(path, {"product_id": "not-configured"})
            self.assertEqual(status, 409)
            self.assertTrue(json.loads(body).get("error"))
        with server.open_db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE event_type='affiliate_click'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM affiliate_clicks").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM conversions").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM revenue").fetchone()[0], 0)

    def test_optional_snapshot_import_keeps_filter_partitions_separate(self):
        with server.open_db() as db:
            db.execute("INSERT INTO products(product_id,comparison_id,search_partition,product_name,availability_state,affiliate_state,snapshot_context) VALUES(?,?,?,?,?,?,?)",
                       ("road-test", "cmp", "road", "internal only", "unverified", "not_configured", "{}"))
            db.execute("INSERT INTO products(product_id,comparison_id,search_partition,product_name,availability_state,affiliate_state,snapshot_context) VALUES(?,?,?,?,?,?,?)",
                       ("fly-test", "cmp", "fly", "internal only", "unverified", "not_configured", "{}"))
            groups = dict(db.execute("SELECT search_partition,COUNT(*) FROM products GROUP BY search_partition").fetchall())
        self.assertEqual(groups, {"fly": 1, "road": 1})


if __name__ == "__main__":
    unittest.main()
