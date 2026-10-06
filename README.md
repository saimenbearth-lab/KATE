# KATE MVP — temporary preview

**Status: preview only. Not a production-ready sales page.** Built with Python's standard library, SQLite, HTML, CSS and vanilla JavaScript. No Cloudflare, cloud database, external account, third-party runtime, or supplier API is used.

## Run

```bash
python3 server.py --host 0.0.0.0 --port 8787
```

The service binds to `0.0.0.0` for the current computer's temporary preview host. SQLite data is persisted locally at `data/kate.sqlite3` and is excluded from version control. This is preview persistence only—not a durable production cloud database or production hosting.

Run automated API/security tests with:

```bash
python3 -m unittest discover -s tests -v
```

## Pages

- `/` — Home and transparent preview disclosure.
- `/planner` — Functional local trip outline using origin, focus, days, party size, budget/person, interests, comfort, and optional date/flexibility. Nothing is sent to a supplier; no live match or availability check occurs.
- `/mara` — Neutral 3-day Nairobi–Maasai Mara road vs fly-in decision guide. No products, prices, ratings, booking buttons or availability claims are presented.
- `/control` — Configuration-only state until an admin secret exists. When configured, the page requires HTTP Basic (`admin` + secret) and displays SQLite aggregates only. Empty metric values render exactly **“No data yet”**.

## Data and safety

The SQLite schema covers destinations, travel intents, products, opportunities, pages, planner sessions, events, affiliate clicks, conversions, revenue, experiments, agent runs, business memory, and incidents. The optional local Viator snapshot is imported once at database creation, tagged discovery-only and partitioned by its Road/Fly source-filter evidence; the partitions are never combined into one product list. Price basis and date availability stay unconfirmed, affiliate URLs are absent, and snapshot records are not displayed publicly. No conversions or revenue are synthesized.

Real page views and accepted/finished planner requests are stored with source, page, intent, optional product, position, and timestamp fields. No names, contact details, full referrer URLs, or client IPs are stored in analytics. No affiliate-click event can be created unless a verified product has an approved HTTPS affiliate URL and confirmed availability; the current dataset has no such URL. Live supplier inventory is not connected. This preview exposes no supplier credential input, makes no supplier API request, and does not claim that local SQLite is production-ready.

The example config is intentionally empty. A local admin-only helper is available for Control Center access; it does not accept supplier credentials. To configure the admin secret later, run this from the project directory in a private terminal:

```bash
python3 tools/configure_server_secret.py
```

The helper prompts without echoing, stores the admin secret outside the repository at `~/.config/kate-mvp/server.env` with owner-only permissions, enforces a minimum length, and never prints the value. It was **not run** for this preview; no admin secret was requested, stored or committed. Restart the service after future configuration. The service ignores a config file with group/world permissions.

Standard-library-only regression tests run against a temporary SQLite database, not the persistent preview data. HTTP security headers, bounded JSON input, basic input validation, no-data admin gating and the no-affiliate-click condition are covered.

## Commercial boundaries

The only supplied buying intent is a 3-day Nairobi–Maasai Mara road-vs-fly-in decision. Snapshot `fromPrice` values have no confirmed per-person basis or date-specific availability; cancellation records conflict and anomalies are documented. No affiliate URLs or commission terms were supplied. This MVP captures planning intent, but it does not make a booking, supplier hand-off, revenue, or conversion claim. Confirm offer data, booking terms, tracking, disclosure and actual product availability before any sales use.
