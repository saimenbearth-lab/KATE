# KATE — static frontend and Supabase backend

KATE preserves the existing Home, Kenya Trip Planner, Nairobi–Maasai Mara comparison and Control Center. The deployed architecture is a generated static frontend plus Supabase PostgreSQL and Edge Functions; the existing Python/SQLite server remains for local preview and regression compatibility only. Do not run `server.py` as the production server.

## Local use and checks

Run the compatibility preview:

```bash
python3 server.py --host 0.0.0.0 --port 8787
```

Build the Netlify-publishable static site:

```bash
python3 scripts/build_static.py
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_edge_validation.mjs
```

`dist/` is generated and ignored by Git. The build exports the existing page templates and copies the existing CSS, JavaScript and illustrative Mara image. It does not bundle Python, SQLite, database credentials or supplier keys into the published assets.

## Pages and API

- `/` — Home and clear no-booking/no-verified-inventory disclosure.
- `/planner` — validated planning outline, sent to the Supabase Edge Function and persisted as a planner session, intent and events.
- `/mara` — existing neutral road-vs-fly-in decision guide. No unverified products, prices, ratings or booking links are shown.
- `/control` — aggregate activity screen gated by a server-side `KATE_ADMIN_SECRET`; the browser field is not written to local/session storage.

Netlify serves `dist` and rewrites `/api/*` to the Supabase `kate-api` Edge Function. The function uses the server-side `SUPABASE_SERVICE_ROLE_KEY`; that key and all other server credentials must never be put in static assets. Public input handlers have bounded JSON request bodies and validated fields. Sensitive control, revenue and conversion routes require the server-side admin secret. Only verified products with confirmed date availability, an approved affiliate state and an HTTPS URL can create a tracked affiliate click.

## Database and data policy

The Git-tracked migrations under `supabase/migrations/` translate all 14 existing SQLite entities to PostgreSQL with timestamps, keys, constraints, indexes and RLS. Browser roles receive no table or protected-RPC privileges; RLS has no permissive client policies by design. Planner completion is stored atomically in PostgreSQL; Control Center aggregates are read from the database, not from local SQLite. Three user-authorized source-returned click-outs are stored as discovery-only records; no conversions or revenue are synthesized.

Both schema/data migrations were applied to project `bshxiuzdqlqezqsrybtn` (KATE, `eu-central-1`). All 14 tables have RLS enabled, client roles have no table privileges, and the production `kate-api` Edge Function is deployed. A live Planner POST wrote a session, intent and completion event, which were read back from PostgreSQL; temporary probe rows were removed. The existing postgres-owned `ensure_rls` trigger remains active, while browser roles no longer have EXECUTE on its SECURITY DEFINER function.

## Viator and production deployment status

The three source-returned IDs (`427094P4`, `107758P7`, `260078P150`) and exact click-out URLs supplied by KATE HQ are stored with the approved PID/tracking parameters and source provenance. Their record state is `discovery_needs_data`; `from_price`/currency are null, `availability_state` is `unverified`, and date availability, price basis, cancellation, commission, booking and revenue remain unverified. The approved PID/click-out state does not claim commission. The public product and affiliate endpoints return 409 for these records, and the Mara page does not present them as offers.

`VIATOR_API_KEY` has not been requested, entered, logged or committed; no supplier API request or inventory sync is implemented. Do not infer live availability, a confirmed price basis, cancellations, commission, a booking or revenue from these links. The server reads `KATE_ADMIN_SECRET` only from Supabase Edge Function Secrets. The user will set it manually under **Supabase → KATE → Edge Functions → Secrets**; until then, Control Center access remains closed with HTTP 503. No Supabase account email/password was requested or stored.

`netlify.toml` defines the static build and security headers. The production migration remains on `production-migration`; no Netlify site has yet been deployed. Do not describe a local build as a live production deployment.
