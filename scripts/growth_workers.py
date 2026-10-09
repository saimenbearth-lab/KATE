#!/usr/bin/env python3
"""Bounded, deterministic public-site workers. No LLM, outreach or paid API.

Reports prove only the checks performed, never a customer, booking or payout.
IndexNow state records accepted notifications, not confirmed indexing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SITE_URL = "https://kate-kenya-trip-planner.netlify.app"
ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE_BYTES = 2_000_000
MAX_URLS = 30
TIMEOUT_SECONDS = 12


def request(url: str, *, payload=None):
    headers = {"User-Agent": "KATE-Public-Checks/1.0", "Accept": "application/json,text/html,application/xml"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    req = Request(url, data=body, headers=headers)
    try:
        response = urlopen(req, timeout=TIMEOUT_SECONDS)
    except HTTPError as error:
        response = error
    with response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Public response exceeds worker size limit")
        # Do not treat a redirect to an unrelated host as an owned-site success.
        if urlsplit(response.geturl()).netloc != urlsplit(url).netloc:
            raise ValueError("Unexpected cross-host response")
        return response.status, data


def live_build(expected_commit: str | None, *, wait_attempts=1):
    if not 1 <= wait_attempts <= 3:
        raise ValueError("At most three deployment checks are permitted")
    if expected_commit and not re.fullmatch(r"[a-f0-9]{40}", expected_commit):
        raise ValueError("Expected commit must be a full Git commit SHA")
    latest = None
    for attempt in range(wait_attempts):
        status, body = request(SITE_URL + "/build.json")
        if status != 200:
            raise ValueError("Build metadata is unavailable")
        latest = json.loads(body)
        if latest.get("release") != "kate-supplier-preview-v1":
            raise ValueError("Unexpected production release")
        if not expected_commit or latest.get("commit") == expected_commit:
            return latest
        if attempt + 1 < wait_attempts:
            time.sleep(20)
    raise ValueError("Production commit does not match the requested deployment")


def health_monitor(expected_commit=None, *, wait_attempts=1):
    build = live_build(expected_commit, wait_attempts=wait_attempts)
    public_paths = ("/", "/mara/", "/guides/", "/de/", "/de/mara/")
    for path in public_paths:
        status, body = request(SITE_URL + path)
        if status != 200 or b"<html" not in body.lower():
            raise ValueError("Public page is unhealthy: " + path)
    status, body = request(SITE_URL + "/api/health")
    health = json.loads(body)
    if status != 200 or health.get("release") != build.get("release") or not all(health.get(flag) is True for flag in ("ok", "viator_configured", "admin_configured")):
        raise ValueError("Public API configuration/health check failed")
    control_status, _ = request(SITE_URL + "/api/control")
    if control_status != 401:
        raise ValueError("Unauthenticated control endpoint is not protected")
    return {"production_commit": build.get("commit"), "api_release": health.get("release"), "page_statuses": f"{len(public_paths)} public pages returned 200", "api_healthy": True, "unauthenticated_control_status": control_status, "browser_events_or_clicks_created": False}


def sitemap_urls(data: bytes):
    urls = [node.text for node in ET.fromstring(data).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    if not urls or len(urls) > MAX_URLS or len(set(urls)) != len(urls):
        raise ValueError("Sitemap must contain 1–30 distinct owned URLs")
    for url in urls:
        if not isinstance(url, str):
            raise ValueError("Empty sitemap URL")
        parsed = urlsplit(url)
        decoded_path = unquote(parsed.path, errors="strict")
        segments = [segment for segment in decoded_path.split("/") if segment]
        # Only canonical public routes belong in the sitemap. Decode once to
        # catch escaped private names, and reject traversal or nested escapes.
        if "%" in decoded_path or "\\" in decoded_path or any(segment in {".", ".."} for segment in segments):
            raise ValueError("Sitemap contains a noncanonical path")
        if segments and segments[0] == "de":
            segments = segments[1:]
        public_path = "/" + "/".join(segments)
        if parsed.scheme != "https" or parsed.netloc != urlsplit(SITE_URL).netloc or parsed.query or parsed.fragment or public_path.startswith(("/api", "/control", "/planner")):
            raise ValueError("Sitemap contains a private or unowned URL")
    return urls


def search_discovery(expected_commit=None, *, submit=False, state_file=None, wait_attempts=1):
    if submit and not expected_commit:
        raise ValueError("Submission requires an exact expected production commit")
    build = live_build(expected_commit, wait_attempts=wait_attempts)
    key = (ROOT / "indexnow-key.txt").read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{32}", key):
        raise ValueError("Invalid local ownership verification key")
    key_url = SITE_URL + "/" + key + ".txt"
    status, body = request(key_url)
    if status != 200 or body.decode().strip() != key:
        raise ValueError("Live ownership file does not match the repository")
    status, body = request(SITE_URL + "/sitemap.xml")
    if status != 200:
        raise ValueError("Live sitemap is unavailable")
    urls = sitemap_urls(body)
    status, robots = request(SITE_URL + "/robots.txt")
    if status != 200 or ("Sitemap: " + SITE_URL + "/sitemap.xml").encode() not in robots or b"Disallow: /\n" in robots:
        raise ValueError("Production robots rules do not expose this sitemap")
    previous = {}
    if state_file and Path(state_file).is_file():
        saved = json.loads(Path(state_file).read_text())
        if saved.get("site") == SITE_URL:
            previous = saved.get("notified_fingerprints", {})
    fingerprints = {}
    for url in urls:
        status, body = request(url)
        if status != 200 or b"noindex" in body.lower():
            raise ValueError("Sitemap page cannot be indexed: " + url)
        fingerprints[url] = hashlib.sha256(body).hexdigest()
    changed = [url for url in urls if previous.get(url) != fingerprints[url]]
    result = {"production_commit": build.get("commit"), "owned_urls_checked": len(urls), "changed_since_last_accepted_notification": changed, "submitted": False, "indexing_verified": False}
    if submit and changed:
        if not state_file:
            raise ValueError("Submission requires a persisted state file to prevent repeated notifications")
        # Content hashes can race a deployment; verify its exact version again.
        live_build(expected_commit)
        status, _ = request("https://api.indexnow.org/indexnow", payload={"host": urlsplit(SITE_URL).netloc, "key": key, "keyLocation": key_url, "urlList": changed})
        if status not in (200, 202):
            raise ValueError("IndexNow refused the notification with HTTP " + str(status))
        path = Path(state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"site": SITE_URL, "notified_fingerprints": fingerprints, "accepted_at": datetime.now(timezone.utc).isoformat(), "commit": expected_commit, "http_status": status}, indent=2) + "\n")
        result.update({"submitted": True, "notification_http_status": status, "notification_receipt_only": True})
    return result


def evidence_auditor(evidence_file=None):
    result = {"worker_type": "deterministic_automation", "customer_activity_verified": False, "bookings_verified": False, "revenue_verified": False, "supplier_financial_reports_read": False, "snapshot_checked": False}
    if not evidence_file:
        result["limitation"] = "No financial snapshot supplied; automation is not sales evidence."
        return result
    path = Path(evidence_file)
    if not path.is_file():
        raise ValueError("Requested evidence snapshot is missing")
    evidence = json.loads(path.read_text())
    counts = [evidence.get(field, 0) for field in ("affiliate_clicks", "known_test_clicks", "recorded_conversions")]
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise ValueError("Evidence counts must be nonnegative integers")
    clicks, tests, conversions = counts
    if tests > clicks:
        raise ValueError("Known test clicks exceed all recorded clicks")
    revenues = evidence.get("recorded_revenue", [])
    if not isinstance(revenues, list):
        raise ValueError("Recorded revenue must be a source-evidence list")
    if evidence.get("customer_revenue_claimed") and (not revenues or not conversions):
        raise ValueError("Customer revenue is claimed without conversion and revenue evidence")
    if evidence.get("advertising_budget_eur", 0) != 0 or evidence.get("paid_campaign_started") or evidence.get("new_paid_services_started"):
        raise ValueError("Snapshot contradicts the zero-budget launch policy")
    result.update({"snapshot_checked": True, "snapshot_verified_at": evidence.get("verified_at"), "snapshot_is_historical_not_a_live_finance_query": True, "financial_claim_consistency_checked": True, "recorded_clicks": clicks, "known_test_clicks": tests, "remaining_clicks_are_not_proven_customers": clicks - tests, "recorded_conversions": conversions, "supplier_reports_automatically_synced": bool(evidence.get("supplier_reports_automatically_synced")), "limitation": "Snapshot consistency does not independently verify supplier bookings or payments."})
    return result


def resource_auditor(path, expected_commit=None, *, wait_attempts=1):
    if not path or not path.startswith("/resources/") or ".." in path or "?" in path or "#" in path:
        raise ValueError("An owned /resources/ path is required")
    if expected_commit:
        live_build(expected_commit, wait_attempts=wait_attempts)
    status, body = request(SITE_URL + path)
    if status != 200 or b"<html" not in body.lower() or b"/mara/#safari-options" not in body:
        raise ValueError("Owned resource or its booking-options link is unavailable")
    return {"resource_url": SITE_URL + path, "http_status": status, "booking_options_link_present": True, "outbound_messages_sent": 0, "limitation": "Reachability is not evidence that someone distributed or used this resource."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", choices=("health-monitor", "search-discovery", "evidence-auditor", "resource-auditor"))
    parser.add_argument("--expected-commit")
    parser.add_argument("--wait-attempts", type=int, default=1, choices=(1, 2, 3))
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--state-file")
    parser.add_argument("--evidence-file")
    parser.add_argument("--resource-path")
    parser.add_argument("--output", default="growth-report.json")
    args = parser.parse_args()
    report = {"worker": args.worker, "checked_at": datetime.now(timezone.utc).isoformat(), "paid_services_used": False, "llm_used": False}
    try:
        if args.worker == "health-monitor":
            details = health_monitor(args.expected_commit, wait_attempts=args.wait_attempts)
        elif args.worker == "search-discovery":
            details = search_discovery(args.expected_commit, submit=args.submit, state_file=args.state_file, wait_attempts=args.wait_attempts)
        elif args.worker == "evidence-auditor":
            details = evidence_auditor(args.evidence_file)
        else:
            details = resource_auditor(args.resource_path, args.expected_commit, wait_attempts=args.wait_attempts)
        report.update({"ok": True, "details": details})
    except Exception as error:
        # Errors contain no private token or response payload.
        report.update({"ok": False, "error": str(error)})
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
