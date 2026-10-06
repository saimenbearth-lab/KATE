#!/usr/bin/env python3
"""KATE MVP — standard-library-only local preview service."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = Path(os.environ.get("KATE_DATA_DIR", ROOT / "data")).expanduser().resolve()
DB_PATH = DATA_DIR / "kate.sqlite3"
DEFAULT_SNAPSHOT = Path("/home/ubuntu/upload/1ce3ec0af4690b41cf96f073_d2a884cb61bccce2a44bddd0_kenya_viator_product_records_20261005.json")
SNAPSHOT_PATH: Path | None = Path(os.environ.get("KATE_PRODUCT_SNAPSHOT", str(DEFAULT_SNAPSHOT)))
CONFIG_PATH = Path(os.environ.get("KATE_CONFIG_FILE", str(Path.home() / ".config/kate-mvp/server.env"))).expanduser()
APP_VERSION = "kate-mvp-2026-10-06"
MAX_BODY = 8192


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def open_db() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(DATA_DIR, 0o700)
    db = sqlite3.connect(DB_PATH, timeout=8)
    try:
        os.chmod(DB_PATH, 0o600)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        with db:
            yield db
    finally:
        db.close()


def read_private_config(path: Path = CONFIG_PATH) -> dict[str, str]:
    """Read an allow-listed plain env file only if it is a regular, private file."""
    if not path.exists() or path.is_symlink() or not path.is_file():
        return {}
    try:
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            return {}
        parsed: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if key == "KATE_ADMIN_SECRET" and value:
                parsed[key] = value
        return parsed
    except (OSError, UnicodeError):
        return {}


def load_settings() -> dict[str, object]:
    private = read_private_config()
    admin = os.environ.get("KATE_ADMIN_SECRET") or private.get("KATE_ADMIN_SECRET")
    return {
        "admin_secret": admin if admin else None,
        "admin_configured": bool(admin),
    }


SETTINGS = load_settings()


def init_db() -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS destinations (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS travel_intents (
      id TEXT PRIMARY KEY, intent_type TEXT NOT NULL, destination_id TEXT,
      stage TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(destination_id) REFERENCES destinations(id)
    );
    CREATE TABLE IF NOT EXISTS products (
      product_id TEXT PRIMARY KEY, comparison_id TEXT, search_partition TEXT NOT NULL,
      provider TEXT, product_name TEXT NOT NULL, destination_text TEXT,
      category TEXT, from_price REAL, currency TEXT, price_basis_confirmed INTEGER NOT NULL DEFAULT 0,
      date_availability_confirmed INTEGER NOT NULL DEFAULT 0, availability_state TEXT NOT NULL,
      affiliate_url TEXT, affiliate_state TEXT NOT NULL, cancellation_note TEXT,
      confidence_note TEXT, snapshot_context TEXT NOT NULL, source_last_checked TEXT
    );
    CREATE TABLE IF NOT EXISTS opportunities (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, stage TEXT NOT NULL,
      evidence_note TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS pages (
      path TEXT PRIMARY KEY, page_name TEXT NOT NULL, intent TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS planner_sessions (
      id TEXT PRIMARY KEY, origin TEXT NOT NULL, focus TEXT NOT NULL, days INTEGER NOT NULL,
      travelers INTEGER NOT NULL, budget_amount REAL, budget_currency TEXT NOT NULL,
      interests_json TEXT NOT NULL, comfort TEXT NOT NULL, target_date TEXT,
      date_flexibility TEXT, created_at TEXT NOT NULL, completed_at TEXT NOT NULL,
      output_summary TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, source TEXT NOT NULL,
      page TEXT NOT NULL, intent TEXT, product_id TEXT, position TEXT, occurred_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS events_type_time_idx ON events(event_type, occurred_at);
    CREATE TABLE IF NOT EXISTS affiliate_clicks (
      id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL,
      destination_url TEXT NOT NULL, clicked_at TEXT NOT NULL,
      FOREIGN KEY(product_id) REFERENCES products(product_id)
    );
    CREATE TABLE IF NOT EXISTS conversions (
      id TEXT PRIMARY KEY, product_id TEXT, event_time TEXT NOT NULL,
      source TEXT NOT NULL, verification_note TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS revenue (
      id TEXT PRIMARY KEY, amount REAL NOT NULL, currency TEXT NOT NULL,
      recorded_at TEXT NOT NULL, evidence_note TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS experiments (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
      hypothesis TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS agent_runs (
      id TEXT PRIMARY KEY, task TEXT NOT NULL, status TEXT NOT NULL,
      started_at TEXT NOT NULL, finished_at TEXT, outcome_note TEXT
    );
    CREATE TABLE IF NOT EXISTS business_memory (
      key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS incidents (
      id TEXT PRIMARY KEY, summary TEXT NOT NULL, severity TEXT NOT NULL,
      status TEXT NOT NULL, opened_at TEXT NOT NULL, resolved_at TEXT
    );
    """
    with open_db() as db:
        db.executescript(schema)
        now = utc_now()
        db.executemany(
            "INSERT OR IGNORE INTO destinations(id,name,country,created_at) VALUES(?,?,?,?)",
            [("nairobi", "Nairobi", "Kenya", now), ("maasai-mara", "Maasai Mara", "Kenya", now)],
        )
        db.executemany(
            "INSERT OR IGNORE INTO pages(path,page_name,intent,created_at) VALUES(?,?,?,?)",
            [
                ("/", "Home", "kenya_trip_planning", now),
                ("/planner", "Kenya Trip Planner", "trip_planning", now),
                ("/mara", "Nairobi–Maasai Mara · 3 days", "mara_3d_decision", now),
                ("/control", "Control Center", "internal_operations", now),
            ],
        )
        db.execute(
            "INSERT OR IGNORE INTO opportunities(id,title,stage,evidence_note,created_at) VALUES(?,?,?,?,?)",
            ("KEN-20261005-01", "3-day Nairobi–Maasai Mara decision intent", "discovery_only",
             "Intent and source limitations were supplied in the task; no conversion or revenue evidence.", now),
        )
        memories = [
            ("product_data_policy", "Discovery-only snapshots; do not claim bookability, date availability, eligibility, promotion approval, or confirmed price basis.", now),
            ("affiliate_policy", "No approved affiliate URL or commission terms are present; do not emit affiliate_click without a verified approved URL.", now),
            ("preview_status", "Temporary preview only; not a production-ready sales page.", now),
            ("live_inventory_gap", "Live supplier inventory is not connected in this MVP; no external integration or supplier credential entry is available.", now),
        ]
        db.executemany("INSERT OR IGNORE INTO business_memory(key,value,updated_at) VALUES(?,?,?)", memories)
        _import_snapshot(db)


def _import_snapshot(db: sqlite3.Connection) -> None:
    path = SNAPSHOT_PATH
    if path is None or not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        comparison_id = str(payload.get("comparison_id", ""))[:80]
        context = payload.get("search_context", {})
        if not comparison_id or not isinstance(payload.get("records"), list):
            return
        for item in payload["records"]:
            product_id = str(item.get("product_id", ""))[:80]
            if not product_id:
                continue
            evidence = str(item.get("field_evidence", ""))
            partition = "road" if "S-Road" in evidence and "S-Fly" not in evidence else (
                "fly" if "S-Fly" in evidence and "S-Road" not in evidence else "unresolved"
            )
            source_context = {
                "source": payload.get("source"),
                "search_context": context,
                "partition_evidence": evidence,
                "record_status": item.get("status"),
                "search_date_is_not_trip_date": True,
            }
            price = item.get("price_from")
            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError):
                price = None
            db.execute(
                """INSERT OR IGNORE INTO products(
                  product_id,comparison_id,search_partition,provider,product_name,destination_text,
                  category,from_price,currency,price_basis_confirmed,date_availability_confirmed,
                  availability_state,affiliate_url,affiliate_state,cancellation_note,confidence_note,
                  snapshot_context,source_last_checked
                ) VALUES(?,?,?,?,?,?,?,?,?,0,0,'unverified',NULL,'not_configured',?,?,?,?)""",
                (product_id, comparison_id, partition, item.get("provider"), str(item.get("product_name", ""))[:300],
                 item.get("destination"), item.get("category"), price, item.get("currency"),
                 item.get("cancellation"), item.get("confidence"), json.dumps(source_context, ensure_ascii=False),
                 item.get("last_checked")),
            )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, sqlite3.Error):
        # A malformed optional snapshot must never prevent the service from starting.
        return


def record_event(db: sqlite3.Connection, event_type: str, source: str, page: str,
                 intent: str | None = None, product_id: str | None = None,
                 position: str | None = None) -> None:
    db.execute(
        "INSERT INTO events(event_type,source,page,intent,product_id,position,occurred_at) VALUES(?,?,?,?,?,?,?)",
        (event_type, source[:80], page[:160], intent, product_id, position, utc_now()),
    )


def h(value: object) -> str:
    text = str(value)
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def shell(title: str, body: str, current: str = "") -> bytes:
    body = body.replace("Live Viator inventory and a secure API-key configuration are not available", "Live Viator inventory is not connected")
    body = body.replace("Live Viator inventory and secure API-key configuration are not available", "Live Viator inventory is not connected")
    nav_items = [("/", "Home", "home"), ("/planner", "Trip Planner", "planner"),
                 ("/mara", "3-day Mara", "mara"), ("/control", "Control Center", "control")]
    links = "".join(
        f'<a href="{path}"{" aria-current=page" if key == current else ""}>{label}</a>'
        for path, label, key in nav_items
    )
    doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f7f5ef"><meta name="description" content="KATE Kenya trip planning preview. No offers or date availability are verified.">
<title>{h(title)} · KATE</title><link rel="stylesheet" href="/static/app.css"><script defer src="/static/app.js"></script></head>
<body><div class="preview-ribbon"><span>PREVIEW BUILD</span><span>Not a production-ready sales page · No live inventory or booking</span></div>
<header class="site-header"><a class="brand" href="/" aria-label="KATE home"><span class="brand-mark">K</span><span>KATE</span></a><nav aria-label="Main navigation">{links}</nav></header>
<main>{body}</main><footer class="site-footer"><div class="footer-brand">KATE <span>· Kenya trip planning</span></div><p>Independent planning preview. No offer, price, availability, endorsement or booking result is verified here. Check dates, full terms and total price directly with a provider before booking.</p><div class="footer-links"><a href="/planner">Plan a trip</a><a href="/mara">Road vs fly-in</a><a href="/control">Control Center</a></div></footer>
</body></html>'''
    return doc.encode("utf-8")


HOME_HTML = '''
<section class="home-hero">
  <div class="hero-copy"><p class="eyebrow"><span class="eyebrow-dot"></span> KENYA TRIP PLANNING · PREVIEW</p>
    <h1>Plan your Kenya trip with the details that matter.</h1>
    <p class="hero-lede">Start with your travel preferences. For one focused decision, compare road and fly-in planning for a 3-day Nairobi–Maasai Mara trip.</p>
    <div class="hero-actions"><a class="button button-primary" href="/planner">Start your Kenya trip plan <span aria-hidden="true">↗</span></a><a class="button button-quiet" href="/mara">Compare road vs fly-in</a></div>
    <div class="hero-trust"><span class="trust-icon">i</span><span>Offers, prices and date availability are <strong>not verified</strong>.</span></div>
  </div>
  <figure class="hero-image"><img src="/static/mara-hero.jpg" alt="Illustrative savannah landscape created for this preview; not evidence of an itinerary or availability."><figcaption>Illustrative image · not an inventory signal</figcaption><div class="image-stamp"><span>01</span><span>ONE DECISION<br>AT A TIME</span></div></figure>
</section>
<section class="home-under"><div class="section-kicker">A useful first step</div><div class="home-under-grid"><div><h2>Clarity before the commitment.</h2><p>KATE helps frame what to check next—not what to book. Set your trip inputs, then compare the details that matter for your dates.</p></div><a class="decision-card" href="/mara"><div class="decision-meta"><span>FOCUSED COMPARISON</span><span>3 DAYS</span></div><h3>Nairobi → Maasai Mara</h3><p>Road or fly-in? Compare the verification checklist, not an unconfirmed headline price.</p><span class="card-arrow" aria-hidden="true">↗</span></a></div></section>
<section class="disclosure-strip"><span class="disclosure-symbol">↗</span><p><strong>Preview, not a booking service.</strong> Live Viator inventory and a secure API-key configuration are not available. No supplier link or date-specific offer is shown.</p></section>
'''

PLANNER_HTML = '''
<section class="page-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> KENYA · TRIP PLANNER</p><h1>Plan the trip around <em>your</em> priorities.</h1><p>These inputs shape a practical planning outline only. Nothing is sent to a supplier; no live inventory, price or availability check takes place.</p></section>
<section class="planner-layout"><form class="planner-form" data-planner-form novalidate>
  <div class="form-heading"><span class="step-badge">01</span><div><h2>Trip basics</h2><p>Set the frame. Add only what you already know.</p></div></div>
  <div class="form-grid"><label class="field"><span>Starting point</span><input name="origin" type="text" maxlength="80" value="Nairobi" required autocomplete="off"><small>Use the city or place you plan to start from.</small></label>
  <label class="field"><span>Main focus</span><select name="focus"><option value="maasai_mara">Maasai Mara</option><option value="undecided">Still deciding</option></select><small>The comparison page covers Nairobi–Mara only.</small></label>
  <label class="field"><span>Trip length <b>days</b></span><input name="days" type="number" min="1" max="21" value="3" required><small>Planning window; not a supplier itinerary.</small></label>
  <label class="field"><span>Travelers</span><input name="travelers" type="number" min="1" max="20" value="2" required><small>Total party size only—no names needed.</small></label>
  <label class="field field-wide"><span>Budget per person <b>optional</b></span><div class="budget-input"><input name="budget" type="number" min="0" max="10000000" step="0.01" placeholder="Add a planning target"><select name="currency" aria-label="Budget currency"><option>CHF</option><option>EUR</option><option>USD</option><option>GBP</option></select></div><small>A planning input only. It is not matched against offers or used as a price quote.</small></label>
  <label class="field"><span>Travel date <b>optional</b></span><input name="target_date" type="date"><small>Not checked for availability.</small></label>
  <label class="field"><span>Date flexibility</span><select name="flexibility"><option value="not_sure">Not sure</option><option value="fixed">Dates are fixed</option><option value="flexible">Dates are flexible</option></select><small>Planning context only.</small></label></div>
  <fieldset class="field-set"><legend>What matters most?</legend><p>Select any that apply.</p><div class="check-grid"><label><input type="checkbox" name="interests" value="wildlife"><span>Wildlife</span></label><label><input type="checkbox" name="interests" value="culture"><span>Culture</span></label><label><input type="checkbox" name="interests" value="photography"><span>Photography</span></label><label><input type="checkbox" name="interests" value="slow_pace"><span>Unhurried pace</span></label></div></fieldset>
  <label class="field comfort-field"><span>Comfort preference</span><select name="comfort"><option value="balanced">Balanced</option><option value="simple">Keep it simple</option><option value="more_comfort">More comfort</option></select><small>A preference to carry into provider questions, not an offer filter.</small></label>
  <div class="form-alert" data-form-error role="alert" hidden></div><button class="button button-primary form-submit" type="submit">Build my planning outline <span aria-hidden="true">↗</span></button><p class="privacy-note">No contact details requested. Your entries stay in this local preview database and are not shared with suppliers.</p>
</form><aside class="planner-aside"><div class="aside-topline"><span class="aside-icon">✳</span><span>WHAT HAPPENS NEXT</span></div><h2>A plan to verify, not a promise.</h2><ol class="next-steps"><li><b>01</b><span>Turn your inputs into a day-by-day planning outline.</span></li><li><b>02</b><span>Call out what to confirm for your group and preferences.</span></li><li><b>03</b><span>Use the Mara comparison to frame road vs fly-in.</span></li></ol><div class="aside-warning"><strong>Live inventory gap</strong><p>Live Viator inventory and secure API-key configuration are not available. No current offers or date availability can be confirmed.</p></div></aside></section>
<section class="output-wrap" data-plan-output hidden aria-live="polite"></section>
'''

MARA_HTML = '''
<section class="page-intro mara-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> 3-DAY TRIP · STARTING IN NAIROBI</p><h1>Nairobi to the Maasai Mara:<br><em>road vs fly-in.</em></h1><p class="answer-lede">There is no verified winner here. Compare the complete trip details for your dates before choosing. KATE has no verified offers or date availability to show.</p><div class="intro-tags"><span>3 days</span><span>Nairobi origin</span><span>Decision guide</span></div></section>
<section class="compare-section"><div class="section-heading"><div><p class="section-kicker">COMPARE THE DETAILS, NOT A HEADLINE PRICE</p><h2>Two ways to frame the same trip.</h2></div><p class="section-note">No product ranking, price quote or booking hand-off is available in this preview.</p></div>
<div class="compare-grid"><article class="compare-card road-card"><div class="compare-top"><span class="mode-icon">↗</span><span class="mode-label">OPTION 01</span><span class="mode-line"></span></div><h3>Road</h3><p class="compare-summary">Ask for a complete overland plan from Nairobi, with each transfer and inclusion spelled out.</p><h4>Confirm with the provider</h4><ul><li>Exact departure and return arrangements</li><li>Vehicle and transfer details</li><li>What is included—and any additional fees</li><li>Total price, currency and traveler basis</li><li>Date-specific availability and cancellation terms</li></ul><div class="neutral-offer"><span class="status-dot"></span><div><strong>No verified road offer yet</strong><p>Provider, itinerary, inclusions, total price, date validity, availability and booking URL require verification.</p></div></div></article>
<article class="compare-card fly-card"><div class="compare-top"><span class="mode-icon">✳</span><span class="mode-label">OPTION 02</span><span class="mode-line"></span></div><h3>Fly-in</h3><p class="compare-summary">Ask for the full flight-and-transfer chain, not just the flight segment.</p><h4>Confirm with the provider</h4><ul><li>Flight operator, schedule and baggage rules</li><li>Airstrip and ground-transfer arrangements</li><li>What is included—and any additional fees</li><li>Total price, currency and traveler basis</li><li>Date-specific availability and cancellation terms</li></ul><div class="neutral-offer"><span class="status-dot"></span><div><strong>No verified fly-in offer yet</strong><p>Provider, itinerary, inclusions, total price, date validity, availability and booking URL require verification.</p></div></div></article></div></section>
<section class="decision-note"><div class="note-mark">i</div><div><h2>Why there are no prices here</h2><p>Prior public snapshots are discovery-only. Their <code>fromPrice</code> basis and date-specific availability are unconfirmed; cancellation data contain conflicts and some records have anomalies. They are not displayed as current or bookable offers.</p><p><strong>Before deciding:</strong> confirm dates, total party price, currency, inclusions, fees, timings and cancellation terms directly with the provider.</p></div></section>
<section class="mara-cta"><div><p class="section-kicker">NEXT STEP</p><h2>Frame it around your trip.</h2><p>Add your group size, budget target and comfort preference—without triggering a supplier search.</p></div><a class="button button-light" href="/planner">Open the trip planner <span aria-hidden="true">↗</span></a></section>
'''


def control_html() -> str:
    admin_set = bool(SETTINGS["admin_configured"])
    if not admin_set:
        return '''<section class="control-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> INTERNAL OPERATIONS · PREVIEW</p><h1>Control Center</h1><p>Configuration status is shown below. Analytics and operational records are hidden until an admin secret is configured.</p></section>
<section class="status-panel"><div class="status-panel-heading"><span class="status-lock">⌑</span><div><h2>Access is not configured</h2><p>No admin secret is set; no sensitive records or analytics are shown.</p></div></div><div class="status-rows"><div><span>Preview service</span><strong>Local Python + SQLite</strong></div><div><span>Admin secret</span><strong class="status-missing">Not configured</strong></div><div><span>Live inventory connection</span><strong class="status-missing">Not connected</strong></div><div><span>Snapshot records</span><strong>Discovery-only · not shown as offers</strong></div></div><div class="status-footnote">Supplier inventory is not connected. No supplier credential entry or external API request is available in this preview.</div></section>
<section class="locked-empty"><span class="empty-orbit">—</span><div><h2>Analytics are locked</h2><p>No aggregate data is exposed on this unprotected view. Once an admin secret is configured, the dashboard can show real SQLite aggregates; empty metrics will read “No data yet”.</p></div></section>'''
    return '''<section class="control-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> INTERNAL OPERATIONS · PREVIEW</p><h1>Control Center</h1><p>Only recorded SQLite values are shown. No projected conversions or revenue are generated.</p></section><section class="status-panel compact-status"><div class="status-rows"><div><span>Preview service</span><strong>Local Python + SQLite</strong></div><div><span>Admin access</span><strong class="status-ok">Configured</strong></div><div><span>Live inventory connection</span><strong class="status-missing">Not connected</strong></div></div></section><section class="metrics-wrap" data-control-dashboard aria-live="polite"><p>Loading stored aggregates…</p></section>'''


class KateHandler(BaseHTTPRequestHandler):
    server_version = "KATEPreview/1.0"
    sys_version = ""

    def log_message(self, fmt: str, *args: object) -> None:
        # Keep logs free of IPs, query strings, headers, form inputs and credentials.
        try:
            route = urlsplit(self.path).path[:120]
            sys.stderr.write(f"KATE request {self.command} {route}\n")
        except Exception:
            pass

    def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8",
              extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj: dict[str, object]) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _is_admin(self) -> bool:
        secret = SETTINGS.get("admin_secret")
        if not isinstance(secret, str) or not secret:
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (ValueError, UnicodeError):
            return False
        return username == "admin" and hmac.compare_digest(password, secret)

    def _require_admin(self) -> bool:
        if self._is_admin():
            return True
        self._send(401, b'{"error":"Authentication required"}', "application/json; charset=utf-8",
                   {"WWW-Authenticate": 'Basic realm="KATE Control Center", charset="UTF-8"'})
        return False

    def _source(self) -> str:
        referrer = self.headers.get("Referer", "")
        if not referrer:
            return "direct"
        try:
            ref = urlsplit(referrer)
            host = self.headers.get("Host", "")
            return "internal" if ref.netloc and ref.netloc.lower() == host.lower() else "external"
        except ValueError:
            return "unknown"

    def do_HEAD(self) -> None:
        self._dispatch_get(head=True)

    def do_GET(self) -> None:
        self._dispatch_get(head=False)

    def _dispatch_get(self, head: bool = False) -> None:
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._json(200, {"ok": True, "preview": True, "version": APP_VERSION})
            return
        if path.startswith("/static/"):
            rel = path.removeprefix("/static/")
            target = (STATIC_DIR / rel).resolve()
            if not target.is_relative_to(STATIC_DIR.resolve()) or not target.is_file():
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            try:
                body = target.read_bytes()
            except OSError:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
                content_type += "; charset=utf-8"
            self._send(200, body, content_type)
            return
        if path == "/api/control":
            if not SETTINGS["admin_configured"]:
                self._json(403, {"error": "Admin secret is not configured; analytics remain hidden."})
                return
            if not self._require_admin():
                return
            self._control_data()
            return
        routes = {
            "/": ("home", "Plan your Kenya trip with the details that matter", HOME_HTML),
            "/planner": ("planner", "Kenya Trip Planner", PLANNER_HTML),
            "/mara": ("mara", "Nairobi to Maasai Mara: Road vs Fly-in (3 Days)", MARA_HTML),
            "/control": ("control", "Control Center", control_html()),
        }
        if path not in routes:
            self._send(404, b"<h1>Not found</h1>")
            return
        key, title, content = routes[path]
        if path == "/control" and SETTINGS["admin_configured"] and not self._is_admin():
            self._send(401, b"Control Center authentication required", "text/plain; charset=utf-8",
                       {"WWW-Authenticate": 'Basic realm="KATE Control Center", charset="UTF-8"'})
            return
        try:
            with open_db() as db:
                record_event(db, "page_view", self._source(), path,
                             "mara_3d_decision" if path == "/mara" else ("internal_operations" if path == "/control" else "trip_planning"))
        except sqlite3.Error:
            self._send(503, b"Preview storage unavailable", "text/plain; charset=utf-8")
            return
        self._send(200, shell(title, content, key))

    def _body_json(self) -> dict[str, object] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY or "application/json" not in self.headers.get("Content-Type", "").lower():
            return None
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _build_itinerary(data: dict[str, object]) -> list[dict[str, str]]:
        days = int(data["days"])
        origin = str(data["origin"])
        focus = str(data["focus"])
        interests = [str(x).replace("_", " ") for x in data["interests"]]
        focus_text = "the Maasai Mara" if focus == "maasai_mara" else "your selected Kenya focus"
        interest_text = ", ".join(interests) if interests else "your chosen priorities"
        itinerary: list[dict[str, str]] = []
        for day in range(1, days + 1):
            if days == 1:
                title = "One-day planning window"
                detail = f"From {origin}, check whether travel, your selected focus ({focus_text}) and the return plan fit the same day. Confirm the exact schedule, inclusions and fees directly; no route or availability has been checked."
            elif day == 1:
                title = "Arrival and onward arrangements"
                detail = f"From {origin}, confirm the departure or pickup details, onward transport, first-day inclusions and the provider's exact itinerary for {focus_text}."
            elif day == days:
                title = "Return and final checks"
                detail = "Confirm the return arrangements, hand-off point, schedule, total party price, extra fees and cancellation terms with the provider."
            else:
                title = f"Day {day} · Your main priorities"
                detail = f"Leave room for {interest_text}. Confirm the exact activity schedule, transfers and what is included; this outline does not imply that any service is available."
            itinerary.append({"day": f"DAY {day:02d}", "title": title, "detail": detail})
        return itinerary

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/plan":
            self._post_plan()
            return
        if path == "/api/product-view":
            self._post_product_view()
            return
        if path == "/api/affiliate-click":
            self._post_affiliate_click()
            return
        self._json(404, {"error": "Not found"})

    def _post_plan(self) -> None:
        data = self._body_json()
        if data is None:
            self._json(400, {"error": "Send a small JSON form payload."})
            return
        with open_db() as db:
            record_event(db, "planner_started", "planner_form", "/planner", "kenya_trip_planning", position="form_submit")
            try:
                origin = str(data.get("origin", "")).strip()
                if not origin or len(origin) > 80:
                    raise ValueError("Add a starting point (80 characters maximum).")
                days = int(data.get("days", 0))
                travelers = int(data.get("travelers", 0))
                if not 1 <= days <= 21:
                    raise ValueError("Trip length must be between 1 and 21 days.")
                if not 1 <= travelers <= 20:
                    raise ValueError("Travelers must be between 1 and 20.")
                focus = str(data.get("focus", "maasai_mara"))
                if focus not in {"maasai_mara", "undecided"}:
                    raise ValueError("Choose a listed trip focus.")
                raw_budget = data.get("budget")
                budget = None if raw_budget in (None, "") else float(raw_budget)
                if budget is not None and (budget < 0 or budget > 10_000_000):
                    raise ValueError("Enter a non-negative planning budget.")
                currency = str(data.get("currency", "CHF"))
                if currency not in {"CHF", "EUR", "USD", "GBP"}:
                    raise ValueError("Choose a listed currency.")
                raw_interests = data.get("interests", [])
                allowed_interests = {"wildlife", "culture", "photography", "slow_pace"}
                if not isinstance(raw_interests, list) or any(not isinstance(x, str) for x in raw_interests):
                    raise ValueError("Choose valid interests.")
                interests = sorted(set(raw_interests) & allowed_interests)
                comfort = str(data.get("comfort", "balanced"))
                if comfort not in {"simple", "balanced", "more_comfort"}:
                    raise ValueError("Choose a listed comfort preference.")
                target_date = str(data.get("target_date", "")).strip()[:10] or None
                if target_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date):
                    raise ValueError("Use a valid date or leave it blank.")
                flexibility = str(data.get("flexibility", "not_sure"))
                if flexibility not in {"fixed", "flexible", "not_sure"}:
                    raise ValueError("Choose a listed date preference.")
            except (ValueError, TypeError, OverflowError) as exc:
                self._json(400, {"error": str(exc) or "Check the trip inputs and try again."})
                return
            itinerary = self._build_itinerary({"origin": origin, "days": days, "focus": focus, "interests": interests})
            session_id = str(uuid.uuid4())
            intent_type = "mara_3d_decision" if focus == "maasai_mara" and days == 3 and origin.lower() == "nairobi" else "kenya_trip_planning"
            now = utc_now()
            summary = "Illustrative planning outline; live availability and prices not checked."
            destination_id = "maasai-mara" if focus == "maasai_mara" else None
            db.execute(
                """INSERT INTO planner_sessions(id,origin,focus,days,travelers,budget_amount,budget_currency,
                   interests_json,comfort,target_date,date_flexibility,created_at,completed_at,output_summary)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (session_id, origin, focus, days, travelers, budget, currency, json.dumps(interests), comfort,
                 target_date, flexibility, now, now, summary),
            )
            db.execute(
                "INSERT INTO travel_intents(id,intent_type,destination_id,stage,created_at) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), intent_type, destination_id, "planner_completed", now),
            )
            record_event(db, "planner_completed", "planner_form", "/planner", intent_type, position="itinerary_output")
        self._json(200, {
            "session_id": session_id,
            "itinerary": itinerary,
            "planning_inputs": {
                "origin": origin, "focus": "Maasai Mara" if focus == "maasai_mara" else "Still deciding",
                "days": days, "travelers": travelers,
                "budget": None if budget is None else {"amount": budget, "currency": currency},
                "interests": interests, "comfort": comfort,
                "target_date": target_date, "date_flexibility": flexibility,
            },
            "availability_checked": False,
            "price_checked": False,
            "message": "Planning outline only. No live inventory, supplier availability or price was checked.",
        })

    def _post_product_view(self) -> None:
        data = self._body_json()
        product_id = str(data.get("product_id", ""))[:80] if data else ""
        with open_db() as db:
            row = db.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
            if not row or row["availability_state"] != "confirmed" or row["affiliate_state"] != "approved" or not row["affiliate_url"]:
                self._json(409, {"error": "No verified public product is available."})
                return
            record_event(db, "product_view", "product_card", "/mara", "mara_3d_decision", product_id, "offer_card")
        self._json(200, {"ok": True})

    def _post_affiliate_click(self) -> None:
        data = self._body_json()
        product_id = str(data.get("product_id", ""))[:80] if data else ""
        with open_db() as db:
            row = db.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
            if not row or row["availability_state"] != "confirmed" or row["affiliate_state"] != "approved" or not row["affiliate_url"]:
                self._json(409, {"error": "No approved affiliate URL and verified availability are configured."})
                return
            target = str(row["affiliate_url"])
            parsed = urlsplit(target)
            if parsed.scheme != "https" or not parsed.netloc:
                self._json(409, {"error": "The configured destination is not a valid HTTPS URL."})
                return
            now = utc_now()
            cursor = db.execute("INSERT INTO affiliate_clicks(product_id,destination_url,clicked_at) VALUES(?,?,?)", (product_id, target, now))
            record_event(db, "affiliate_click", "product_card", "/mara", "mara_3d_decision", product_id, str(cursor.lastrowid))
        self._send(303, b"", "text/plain; charset=utf-8", {"Location": target})

    def _control_data(self) -> None:
        with open_db() as db:
            events = {row["event_type"]: row["n"] for row in db.execute("SELECT event_type,COUNT(*) AS n FROM events GROUP BY event_type")}
            pages = {row["page"]: row["n"] for row in db.execute("SELECT page,COUNT(*) AS n FROM events WHERE event_type='page_view' GROUP BY page")}
            products = {row["search_partition"]: row["n"] for row in db.execute("SELECT search_partition,COUNT(*) AS n FROM products GROUP BY search_partition")}
            conversion_count = db.execute("SELECT COUNT(*) FROM conversions").fetchone()[0]
            revenue_row = db.execute("SELECT currency,ROUND(SUM(amount),2) AS total,COUNT(*) AS n FROM revenue GROUP BY currency ORDER BY currency").fetchall()
        self._json(200, {
            "events": events, "page_views": pages, "discovery_snapshot_by_filter": products,
            "conversions": conversion_count,
            "revenue": [{"currency": row["currency"], "amount": row["total"], "records": row["n"]} for row in revenue_row],
            "note": "Snapshot partitions remain separate. No bookings, conversions or revenue are inferred.",
        })

    def do_OPTIONS(self) -> None:
        self._send(405, b"Method not allowed", "text/plain; charset=utf-8", {"Allow": "GET, HEAD, POST"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local KATE preview service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8787")))
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error("port must be between 1 and 65535")
    init_db()
    server = ThreadingHTTPServer((args.host, args.port), KateHandler)
    server.daemon_threads = True
    sys.stderr.write(f"KATE preview listening on {args.host}:{args.port} ({APP_VERSION})\n")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
