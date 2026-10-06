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

The Git-tracked migration under `supabase/migrations/` translates all 14 existing SQLite entities to PostgreSQL with timestamps, keys, constraints, indexes and RLS. Browser roles receive no table or protected-RPC privileges. Planner completion is stored atomically in PostgreSQL; Control Center aggregates are read from the database, not from local SQLite. Only reference/configuration rows from the existing initializer are seeded. Product inventory, conversions and revenue are not synthesized.

The Supabase migration was applied to project `bshxiuzdqlqezqsrybtn` (KATE, `eu-central-1`). Its 14 tables and RLS settings were verified; an isolated persistence probe through the planner RPC was read back and removed. Edge Function source exists in this branch; no Supabase Edge Function has been deployed yet.

## Viator and production deployment status

The repository contains no verified Viator API endpoint, approved affiliate URL or currently usable supplier product data. No Viator request is made and no product is presented as bookable. `VIATOR_API_KEY` has not been requested, set, logged or committed. A secure Supabase Edge Function secret-entry path must be verified before asking the user to enter that key; exact supplier integration must follow the verified API contract rather than guessed endpoints.

`netlify.toml` defines the static build and security headers, but no Netlify site has been created or deployed. The production migration is confined to `production-migration`; it has not been merged into `main`. Do not describe a local build as a live production deployment.
