# KATE — Kenya trip planning and supplier previews

Production: https://kate-kenya-trip-planner.netlify.app

Free tools for travelers:

- [Choose 2-, 3- or 4-day Maasai Mara safari previews](https://kate-kenya-trip-planner.netlify.app/mara/#safari-options): guided priorities and indicative supplier prices.
- [Safari booking checklist and two-quote comparison worksheet](https://kate-kenya-trip-planner.netlify.app/resources/safari-booking-checklist/): printable, downloadable and shareable.
- [Maasai Mara planning guides](https://kate-kenya-trip-planner.netlify.app/guides/): questions to resolve before paying.

KATE may earn a commission through its Viator affiliate links. Confirm dates, selected options and total party prices on Viator.

KATE uses a generated static Netlify frontend and Supabase PostgreSQL/Edge Functions. The Python/SQLite server is retained for local previews and compatibility checks. Production does not run `server.py`.

## Build and verification

```bash
python3 server.py --host 0.0.0.0 --port 8787
python3 scripts/build_static.py
python3 -m unittest discover -s tests -v
node --test tests/*.mjs
```

The build preserves the four original pages, adds a guide hub, two guides and a free booking resource, includes guided supplier preview cards, and writes `dist/build.json` with the Netlify `COMMIT_REF` identifier (or `COMMIT` in CI). Generated output is ignored by Git. GitHub Actions runs the Python checks, Node checks and complete static build. The original hero image must be present in a full checkout.

## Public experience

`/planner` saves a validated planning outline through an atomic database RPC. Nairobi–Maasai Mara plans of 2–4 days can load supplier product previews. `/mara` retains the road-versus-fly-in guide and lets visitors select two-, three- or four-day supplier previews in USD, EUR, GBP or CHF. Previews are not matched to a party budget or comfort preference. From prices, supplier ratings and durations are shown only when the supplier supplies usable values.

The API uses Viator Basic Affiliate `products/search`, on demand, with a five-minute response cache and a shared refresh lease. It does not use `availability/check`, which is unavailable to Basic access. A travel-date search filter does not confirm availability, a group quote, cancellation terms, commission or a booking. Visitors confirm the full itinerary, dates and total price on Viator.

Click-outs use native POST forms and a tracked HTTP 303 handoff. The database allows only fresh, active catalogue records from the verified supplier source and HTTPS Viator URLs with KATE's approved PID `P00323912`. Stale records require a refresh. The original discovery records and their provenance remain preserved; their historical links alone do not qualify as current previews.

## Backend and access

Netlify rewrites `/api/*` to Supabase project `bshxiuzdqlqezqsrybtn`, function `kate-api`. Supplier and database credentials remain server-side. All 14 public tables have RLS enabled, with no browser table access or protected-RPC permissions. Public JSON bodies are bounded and validated.

`/control`, conversion ingestion and revenue ingestion require Bearer authentication. The preferred credential is the Edge secret `KATE_ADMIN_SECRET`; a private SHA-256 verifier in `business_memory.control_admin_secret_sha256` is supported when the environment secret is absent. Missing configuration fails closed. Passwords are not stored in browser storage or committed to Git. Account login credentials are not used.

Financial ingestion requires an external event ID and evidence. A stable source/event hash makes repeated imports idempotent. No conversions or revenue are inferred from searches or click-outs. See [the route map](docs/route-data-access-map.md) and [operations](docs/operations.md).

## Automation and deployment

The applied `kate-hourly-metrics` pg_cron job runs at minute 10 of every UTC hour. It stores real event counts for the preceding 24 hours and evidence-backed lifetime financial totals by currency. It records its run in `agent_runs`. This is a deterministic database routine; it does not run six persistent AI agents, poll suppliers or publish content autonomously.

The October 2026 changes were checked with four temporary collaborating agents during development. These development agents are not hosted services. Persistent CEO/Scout/Product/Growth/Builder/Money workers require a separate authenticated runner, model credentials, execution budgets and an operating policy.

Deployment has two independent parts: Git changes trigger the Netlify frontend build; Edge Function changes require a separate Supabase deployment. Verify both `/build.json` and `/api/health` after publishing. The health response reports configuration flags, never keys. Deployment and verification evidence is documented in [operations](docs/operations.md).


## Active free workers and evidence

[The public worker workflow](.github/workflows/growth-workers.yml) schedules four independent deterministic checks daily at 07:23 UTC and after successful main deployments: public health, changed-page search notification, historical evidence consistency and resource availability. Jobs create reports and never infer customers or revenue. IndexNow notifies changed owned pages only; receipt is separate from indexing or ranking. These workers use the existing public repository workflow infrastructure, without a model key or new paid service. The on-site guided assistant is a deterministic interface, not a hosted LLM salesperson.

[The canonical CSV checker](scripts/validate_affiliate_report.py) validates a deliberately documented intermediate format offline. It neither fetches supplier reports nor imports financial data. See [the evidence workflow](docs/revenue-evidence-workflow.md) and [historical snapshot](docs/evidence.json). The advertising budget is fixed at €0. Supplier reporting and customer traffic still require real evidence.
