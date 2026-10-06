#!/usr/bin/env python3
"""Export the existing KATE page templates and assets as a Netlify static site."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server  # noqa: E402


PRODUCTION_CONTROL_HTML = '''
<section class="control-intro"><p class="eyebrow"><span class="eyebrow-dot"></span> INTERNAL OPERATIONS</p><h1>Control Center</h1><p>Only persistent records are shown. No projected conversions or revenue are generated.</p></section>
<section class="status-panel"><div class="status-panel-heading"><span class="status-lock">⌑</span><div><h2>Supabase-backed operations</h2><p>Analytics remain hidden until server-side admin authentication succeeds.</p></div></div><div class="status-rows"><div><span>Frontend</span><strong>Static Netlify build</strong></div><div><span>Persistent storage</span><strong class="status-ok">Supabase PostgreSQL</strong></div><div><span>Admin access</span><strong>Server-side only</strong></div><div><span>Live inventory</span><strong class="status-missing">Not connected</strong></div></div><div class="status-footnote">The browser never receives the Supabase service-role key. Live inventory and bookings are not represented as verified.</div></section>
<form class="planner-form" data-control-login novalidate><div class="form-heading"><span class="step-badge">01</span><div><h2>Admin access</h2><p>Enter the server-configured KATE admin secret for this session.</p></div></div><label class="field"><span>Admin secret</span><input type="password" name="admin_secret" autocomplete="current-password" required maxlength="512" data-admin-secret></label><div class="form-alert" data-control-error role="alert" hidden></div><button class="button button-primary form-submit" type="submit">Open Control Center</button><p class="privacy-note">The secret is sent only to the Supabase Edge Function and is not saved in browser storage.</p></form>
<section class="metrics-wrap" data-control-dashboard aria-live="polite" hidden></section>
'''


def production_shell(title: str, body: str, current: str) -> bytes:
    html = server.shell(title, body, current).decode("utf-8")
    html = html.replace(
        '<div class="preview-ribbon"><span>PREVIEW BUILD</span><span>Not a production-ready sales page · No live inventory or booking</span></div>',
        '<div class="preview-ribbon"><span>PLANNING PREVIEW</span><span>Persistent planning · No verified live inventory or booking</span></div>',
    )
    html = html.replace(
        "Your entries stay in this local preview database and are not shared with suppliers.",
        "Your planning outline and essential usage events are stored in KATE’s Supabase database. No contact details are requested.",
    )
    return html.encode("utf-8")


def build(destination: Path | str = ROOT / "dist") -> Path:
    output = Path(destination).resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "static").mkdir(parents=True, exist_ok=True)

    pages = {
        "index.html": ("Plan your Kenya trip with the details that matter", server.HOME_HTML, "home"),
        "planner/index.html": ("Kenya Trip Planner", server.PLANNER_HTML, "planner"),
        "mara/index.html": ("Nairobi to Maasai Mara: Road vs Fly-in (3 Days)", server.MARA_HTML, "mara"),
        "control/index.html": ("Control Center", PRODUCTION_CONTROL_HTML, "control"),
    }
    for relative, (title, body, current) in pages.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(production_shell(title, body, current))

    for asset in ("app.css", "app.js", "mara-hero.jpg"):
        shutil.copy2(ROOT / "static" / asset, output / "static" / asset)
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
