# KATE route and data-access map

| Route | Behavior | Storage and access |
|---|---|---|
| `/` | Static trip planning introduction | Public page-view event |
| `/planner` | Planning outline; optional 2–4-day Nairobi–Mara supplier previews | Atomic `record_planner_completion`, sessions, intents and events |
| `/mara` | Road-versus-fly-in guide and on-demand three-day previews | Supplier search, private cache and product records |
| `/control` | Session-only password field and aggregate dashboard | Bearer-protected `kate_control_summary` |
| `/build.json` | Frontend release, build time and source commit | Public generated metadata; no secrets |
| `/api/health` | Backend release and configuration flags | Private verifier existence check; no verifier returned |
| `GET /api/offers` | Currency, 2–4-day duration and optional date filter | Viator Basic search; five-minute cache; refresh lease |
| `POST /api/event` | Known page views only | Bounded JSON; `events` |
| `POST /api/plan` | Validated planning input | Server-side start event and atomic completion RPC |
| `POST /api/product-view` | Eligible server-side product activity | Current supplier catalogue or previously confirmed product |
| `POST /api/affiliate-click` | Tracked 303 redirect to approved Viator URL | Native form or JSON; atomic `record_catalogue_click` |
| `POST /api/conversions` | Evidence-backed, idempotent import | Admin authentication, source and external event ID required |
| `POST /api/revenue` | Evidence-backed, idempotent import | Admin authentication, numeric amount and currency required |

Netlify serves `dist` and proxies `/api/*` to `kate-api`. Browser code contains no Supabase or supplier credential. Admin authentication uses the Edge environment secret or, when absent, a private stored SHA-256 verifier. An unconfigured service returns 503 and hides analytics; incorrect authentication returns 401.

All 14 tables (`destinations`, `travel_intents`, `products`, `opportunities`, `pages`, `planner_sessions`, `events`, `affiliate_clicks`, `conversions`, `revenue`, `experiments`, `agent_runs`, `business_memory`, `incidents`) have RLS enabled. Browser roles have no table privileges or protected-RPC execution. Only server-side `service_role` has the required privileges. New RPCs use SECURITY INVOKER.

The three historical discovery products retain their exact supplied URLs and provenance. New catalogue previews are sourced from authenticated Viator `products/search`. They explicitly retain `date_availability_confirmed = false` and `price_basis_confirmed = false`. Approved catalogue click-outs are a separate eligibility path; they do not claim confirmed date availability or a party quote. Click eligibility expires after 15 minutes without a supplier refresh.

The hourly SQL metrics routine reads actual stored records and writes a private summary plus an execution record. No booking, revenue, commission, supplier availability or persistent AI-agent run is fabricated.
