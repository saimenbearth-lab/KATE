#!/usr/bin/env python3
"""Export the existing KATE page templates and assets as a Netlify static site."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server  # noqa: E402


PRODUCTION_CONTROL_HTML = '''
<section class="control-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> INTERNAL OPERATIONS</p><h1>Control Center</h1><p>Only persistent records are shown. No projected conversions or revenue are generated.</p></section>
<section class="status-panel"><div class="status-panel-heading"><span class="status-lock">⌑</span><div><h2>Supabase-backed operations</h2><p>Analytics remain hidden until server-side admin authentication succeeds.</p></div></div><div class="status-rows"><div><span>Frontend</span><strong>Static Netlify build</strong></div><div><span>Persistent storage</span><strong class="status-ok">Supabase PostgreSQL</strong></div><div><span>Admin access</span><strong>Server-side only</strong></div><div><span>Supplier product previews</span><strong><a href="/mara">Check connection</a></strong></div></div><div class="status-footnote">The browser never receives the Supabase service-role key. Date-specific availability and bookings are not represented as verified.</div></section>
<form class="planner-form" data-control-login novalidate><div class="form-heading"><span class="step-badge">01</span><div><h2>Admin access</h2><p>Enter the server-configured KATE admin secret for this session.</p></div></div><label class="field"><span>Admin secret</span><input type="password" name="admin_secret" autocomplete="current-password" required maxlength="512" data-admin-secret></label><div class="form-alert" data-control-error role="alert" hidden></div><button class="button button-primary form-submit" type="submit">Open Control Center</button><p class="privacy-note">The secret is sent only to the Supabase Edge Function and is not saved in browser storage.</p></form>
<section class="metrics-wrap" data-control-dashboard aria-live="polite" hidden></section>
'''


PRODUCTION_OFFERS_HTML = '''
<section class="offers-section" data-offers data-nosnippet>
<p class="section-kicker">VIATOR PRODUCT PREVIEWS</p><h2>Explore Nairobi–Mara trips</h2>
<p class="offer-disclosure">Supplier from prices are a starting point. Final dates, total party price and availability are checked on Viator. Confirm the route, departure point and full itinerary before deciding.</p>
<div class="offer-controls"><label class="field"><span>Price currency</span><select data-offer-currency><option>USD</option><option>EUR</option><option>GBP</option><option>CHF</option></select></label><button class="button button-quiet" type="button" data-offers-load>Load product previews</button></div>
<p class="offer-status" data-offers-status role="status">Load supplier previews to see from prices. Date-specific availability has not been checked.</p><div class="offer-grid" data-offers-results></div>
<p class="offer-disclosure">Affiliate disclosure: KATE may earn a commission if you book through a Viator link.</p>
</section>
'''


def production_mara_html() -> str:
    body = server.MARA_HTML.replace(
        "KATE has no verified offers or date availability to show.",
        "Supplier product previews below can help you explore options; date-specific availability is checked on Viator.",
    ).replace(
        "No product ranking, price quote or booking hand-off is available in this preview.",
        "Compare complete trip details. Supplier from prices are not a quote for your dates or group.",
    ).replace("Why there are no prices here", "Treat from prices as a starting point").replace(
        "Prior public snapshots are discovery-only. Their <code>fromPrice</code> basis and date-specific availability are unconfirmed; cancellation data contain conflicts and some records have anomalies. They are not displayed as current or bookable offers.",
        "Supplier catalog previews may show a from price. That price does not confirm date-specific availability, inclusions or the total for your party. Check the details on Viator before booking.",
    ).replace(
        "Add your group size, budget target and comfort preference—without triggering a supplier search.",
        "Add your group size, budget target and comfort preference. Nairobi–Mara plans of 2–4 days can also load supplier product previews.",
    )
    return body.replace('<section class="mara-cta">', PRODUCTION_OFFERS_HTML + '<section class="mara-cta">')


def production_shell(title: str, body: str, current: str) -> bytes:
    html = server.shell(title, body, current).decode("utf-8")
    html = html.replace(
        '<div class="preview-ribbon"><span>PREVIEW BUILD</span><span>Not a production-ready sales page · No live inventory or booking</span></div>',
        '<div class="preview-ribbon"><span>PLANNING PREVIEW</span><span>Supplier previews · Confirm dates and total price on Viator</span></div>',
    )
    html = html.replace(
        "Your entries stay in this local preview database and are not shared with suppliers.",
        "Your planning outline and essential usage events are stored in KATE’s Supabase database. No contact details are requested.",
    )
    html = html.replace(
        "Live Viator inventory is not connected. No supplier link or date-specific offer is shown.",
        "Supplier product previews can be loaded on the Mara page. From prices are not date-specific quotes. KATE may earn a commission from Viator bookings.",
    ).replace(
        "These inputs shape a practical planning outline only. Nothing is sent to a supplier; no live inventory, price or availability check takes place.",
        "These inputs shape a practical planning outline. Nairobi–Mara trips of 2–4 days can also load supplier product previews. Your dates and total party price must be checked on Viator.",
    ).replace("Live inventory gap", "Supplier previews and your dates").replace(
        "Live Viator inventory is not connected. No current offers or date availability can be confirmed.",
        "Eligible Nairobi–Mara plans may show supplier from prices. They are not matched to your budget or comfort preference. Date-specific availability and the price for your party are checked on Viator.",
    ).replace(
        "Independent planning preview. No offer, price, availability, endorsement or booking result is verified here. Check dates, full terms and total price directly with a provider before booking.",
        "Independent planning guide. Supplier previews show from prices only. Check dates, full terms and total party price on Viator before booking. KATE may earn a commission through affiliate links.",
    ).replace(
        "KATE Kenya trip planning preview. No offers or date availability are verified.",
        "KATE Kenya trip planning guide with supplier product previews. Check date availability and total party price on Viator.",
    )
    if current in {"planner", "control"}:
        html = html.replace('</head>', '<meta name="robots" content="noindex"></head>')
    return html.encode("utf-8")


def build(destination: Path | str = ROOT / "dist") -> Path:
    output = Path(destination).resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "static").mkdir(parents=True, exist_ok=True)

    pages = {
        "index.html": ("Plan your Kenya trip with the details that matter", server.HOME_HTML, "home"),
        "planner/index.html": ("Kenya Trip Planner", server.PLANNER_HTML, "planner"),
        "mara/index.html": ("Nairobi to Maasai Mara: Road vs Fly-in (3 Days)", production_mara_html(), "mara"),
        "control/index.html": ("Control Center", PRODUCTION_CONTROL_HTML, "control"),
    }
    for relative, (title, body, current) in pages.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(production_shell(title, body, current))

    for asset in ("app.css", "app.js", "mara-hero.jpg"):
        shutil.copy2(ROOT / "static" / asset, output / "static" / asset)
    (output / "build.json").write_text(json.dumps({
        "commit": os.environ.get("COMMIT_REF") or os.environ.get("COMMIT"),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "release": "kate-supplier-preview-v1",
    }) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the KATE static Netlify frontend")
    parser.add_argument("--output", default=str(ROOT / "dist"), help="Output directory (default: dist)")
    args = parser.parse_args()
    output = build(args.output)
    print(f"Built 4 KATE pages and 3 static assets into {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
