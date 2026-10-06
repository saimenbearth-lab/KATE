# KATE route and data-access map

## Existing user-facing routes

| Route | Existing implementation | Production implementation | Data access |
|---|---|---|---|
| `/` | `server.py` `HOME_HTML` | `dist/index.html` generated from the existing template | `POST /api/event` records a page view in `events` |
| `/planner` | `PLANNER_HTML`, `POST /api/plan` | `dist/planner/index.html`, vanilla JS calls the Netlify rewrite | `events`, atomic RPC `record_planner_completion`, `planner_sessions`, `travel_intents` |
| `/mara` | `MARA_HTML` | `dist/mara/index.html`; no invented offer/product cards | Page view only; product events/clicks require a real eligible `products` row |
| `/control` | `control_html()`, Basic-auth preview API | Static Control Center with an ephemeral password field | `GET /api/control` requires `KATE_ADMIN_SECRET`; reads only aggregate RPC `kate_control_summary` |
| `/healthz` | Python preview health route | Production health is `GET /api/health` through the function rewrite | No business data returned |

## Production API routing

Netlify serves only the static output directory `dist`. `/api/*` is a same-origin Netlify proxy to the Supabase Edge Function `kate-api`; browser code contains no database key. The public Edge Function entrypoint validates payload size and values. Only `page_view` can be emitted through the public event endpoint. Planner start events are recorded server-side before validation to retain the existing funnel behavior; successful sessions/intents/completion events are persisted atomically by the restricted `record_planner_completion` RPC.

Product view and affiliate-click endpoints query/act on server-side product records only. A click is tracked and redirected only when the product has confirmed date availability, an approved affiliate state, and an HTTPS URL. The present database is empty of products, so these endpoints return a safe “not verified” response. Conversion and revenue ingestion endpoints require the admin secret plus explicit evidence fields; no values are inferred.

## PostgreSQL objects and protections

The migration creates all 14 entities from the SQLite model: `destinations`, `travel_intents`, `products`, `opportunities`, `pages`, `planner_sessions`, `events`, `affiliate_clicks`, `conversions`, `revenue`, `experiments`, `agent_runs`, `business_memory`, and `incidents`. It adds foreign keys, check constraints, timestamps, query indexes and RLS on every table. `anon` and `authenticated` receive no table privileges or RPC execution; only the Edge Function's server-side `service_role` can access records. `service_role` and supplier credentials must never appear in static assets.

## Explicit current limits

The repository has no verified Viator API endpoint, affiliate link, or live product source. Therefore the current implementation does not call Viator and does not seed product rows. `VIATOR_API_KEY` has not been requested, set, stored, logged, or committed. The Supabase Edge Function secret-input path still needs direct verification before asking for that key. Netlify account/site state is read-only and no site has been created or deployed.
