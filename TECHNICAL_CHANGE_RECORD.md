# Technical Change Record

- **Change ID:** `KATE-MVP-20261006-01`
- **Status:** Preview live; core paths and persistence pass. Mobile viewport simulation and a live supplier integration remain blocked by unavailable native capabilities.

## Problem

Deliver a mobile-first KATE MVP with Home, a working Kenya Trip Planner, one 3-day Nairobi–Maasai Mara road-vs-fly-in decision page, and an internal Control Center. The supplied product snapshot is discovery-only; price basis, date-specific availability, affiliate URLs and commission are unverified or absent. The preview must not imply booking or revenue.

## Root cause

The available runtime supports a temporary HTTP preview and local Python/SQLite, but not durable production hosting or live supplier inventory. The native browser's `openTab` accepts only a URL and its screenshot tool captures a fixed viewport; there is no viewport/device-emulation setter. The native Secret CLI exposes read-only `search` only; it has no safe write/set/store operation for an arbitrary local server secret, and no matching saved supplier-secret reference was reported. A genuine API adapter cannot safely authenticate without a server-side secret injection mechanism; putting a credential in a browser field, chat, repository, or ordinary environment file is intentionally not used.

## Change

- Added a self-contained Python-standard-library server, responsive HTML/CSS/vanilla-JS pages, and local SQLite persistence in a new isolated directory.
- Added the four requested routes. The Planner validates inputs, persists sessions/intents/events, and returns an illustrative day-by-day outline without supplier calls. The Mara page compares verification questions and displays no products, ratings, prices or booking links. The Control Center shows configuration status only until an admin secret exists; its aggregate API is gated.
- Created schema for all requested core objects. The optional local snapshot imports as **8 discovery-only records**, partitioned separately as **1 Road** and **7 Fly-in** from source-filter evidence; no cross-filter product list is formed. No affiliate URL, booking, conversion or revenue is inferred.
- Removed the earlier supplier-credential entry helper. The remaining local helper accepts only the Control Center admin secret; it was not run. No supplier credential was requested, saved, committed or used.
- No Cloudflare Workers/Bindings/D1, Supabase, external service, account relink or other cloud infrastructure was added. Preview data remain local SQLite; this is not a production database.

## Files/components affected

- `server.py` — routes, validation, schema, event persistence, auth/no-data behavior
- `static/app.css`, `static/app.js` — responsive UI and planner interaction
- `static/mara-hero.jpg` — generated illustrative hero image
- `tools/configure_server_secret.py`, `.env.example`, `.gitignore` — admin-only local secret setup and repository hygiene
- `tests/test_server.py`, `README.md`
- `artifacts/homepage-preview.png` — the single captured homepage screenshot
- `data/kate.sqlite3` — local runtime database, excluded from version control

`/workspace/MusikWunsch` was not modified.

## Tests

**Passed after the credential-path cleanup:**

- Python compilation: `server.py`, helper and tests compile successfully.
- Automated regression suite: **7/7 passed**, covering Planner persistence, start/completion events, validation, admin authentication/no-data gating, security headers, filter separation, and the absence of affiliate clicks/conversions/revenue.
- Local HTTP: `/healthz`, `/`, `/planner`, `/mara`, `/control` returned **200**; `/api/control` returned the expected **403** while no admin secret is configured.
- Public HTTP: the same routes returned **200** through the temporary sandbox URL; public `/api/control` returned the expected **403**.
- Public browser Planner: submitted the Planner and found a generated **3-day planning outline**. The response explicitly stated that no live inventory, supplier availability or price was checked.
- Cloud/external dependency scan: no Cloudflare/Workers/Bindings/D1/Supabase implementation found in executable project code.
- Secret CLI inspection: its `secret` command offers only read-only search. A search for a supplier-related saved reference did not report a match; no value was displayed or used.

**Not verified / blocked:**

- A real handset-width render was **not** tested. The In-App Browser has no viewport setter; `openTab` takes only `url`, and screenshot capture is fixed to the current viewport. The existing `@media` mobile rules remain in place, but a mobile-specific rendering pass cannot be claimed. Removing those rules would defeat the mobile-first requirement.
- The browser automation could not directly toggle the custom hidden interest-checkbox input (`REF_NOT_INTERACTABLE`); the Planner itself submitted and generated an outline with default interests. This is an automation limitation, not a confirmed user-facing failure.
- No live Viator/API adapter, availability check, supplier hand-off, affiliate click, conversion or revenue path is active because there is no approved supplier credential path or verified affiliate data.

## Risk

The preview URL is temporary and publicly reachable while the service is running. Planner data and page events persist only on this computer in SQLite; the service does not send them to suppliers. The snapshot is stale discovery evidence, not live inventory. Do not use this as a production sales page or promise durability, availability, pricing, booking, commission, conversion or revenue.

## Rollback

Stop the running preview service to make the temporary URL unavailable. The project is isolated at `/workspace/kate-mvp`; no existing project was changed. Removing that directory or its SQLite database is a separate destructive operation and was not performed.

## Preview and screenshot

- **Public preview:** https://8787-izyamc71riadvxij41but-89b8b5c9.us2.manus.computer
- **Screenshot:** `/workspace/kate-mvp/artifacts/homepage-preview.png` (PNG, 1265×624)

The one screenshot was captured after the initial local/public route tests. The later cleanup changed credential-related status copy below the first viewport; no second screenshot was taken.

## Native secret-management blocker

No native server-side secret write/injection point is available for this local app. The available Secret CLI can search saved references but cannot add or store one; no matching supplier reference was reported. An external connector setup card would introduce external integration/setup outside this scope. Without secure runtime injection, a live adapter cannot safely attach the required server-only authentication header. Therefore no credential field, ordinary config file, or browser form is provided for supplier credentials, and live inventory remains intentionally disconnected.


## Production migration — 2026-10-06

- **Branch:** `production-migration`, based on the requested first commit `0e12469a01300d307721485e3d8787c4c5e1dee2`; history retained.
- **Audit:** the original routes are `/`, `/planner`, `/mara`, `/control`; frontend assets are vanilla JS/CSS plus the illustrative Mara image; `server.py` owns the preview HTTP routes, SQLite schema, Planner validation/itinerary, affiliate guards, admin Basic auth, and SQLite aggregates. The seven original HTTP/security tests passed before modification.
- **Migration:** `supabase/migrations/20261006000100_kate_production_schema.sql` adds all 14 original entities, constraints, FKs, indexes, production timestamps, RLS, and restricted server-side RPCs. Applied to Supabase project `bshxiuzdqlqezqsrybtn`; project and migration status were verified. All 14 tables report RLS enabled; table grants were present only for `service_role`; three protected RPCs deny `anon` and `authenticated` execute privileges.
- **Persistence check:** one temporary event row and one temporary Planner RPC completion were written, independently read back, then removed. No real conversion or revenue was added.
- **Source migration:** `scripts/build_static.py` exports the existing pages into `dist/`; `netlify.toml` declares the build, publish directory, API proxy, and security headers; `supabase/functions/kate-api/` contains validated Planner/tracking/admin backend source. Local Python/SQLite remains only for preview/test compatibility.
- **Tests at this stage:** 12 Python tests and 4 Node tests passed; static build and JS/Python syntax checks passed; credential-shaped token scan returned no matches.
- **Checkpoint at first branch push:** Supabase Edge Function deployment, Viator secret setup/API integration, Netlify site creation/deployment and merge to `main` were still gated. The current status is recorded below.


## Production validation update — 2026-10-06

- **Supabase Edge Function:** `kate-api` is deployed in the existing KATE project. Live `GET /health` returned 200; a real Planner `POST /plan` returned a three-day outline and a session ID. The session, travel intent and completion event were independently read from PostgreSQL. The temporary session, intent and test events were removed afterwards.
- **Security hardening:** the project already had a postgres-owned `ensure_rls` event trigger calling `public.rls_auto_enable()`. The Git-tracked follow-up migration revokes `EXECUTE` from `PUBLIC`, `anon` and `authenticated` while keeping the owner-controlled trigger enabled; verified `anon_exec=false`, `authenticated_exec=false`, `owner_exec=true`. The missing `travel_intents.destination_id` index is now present. No SECURITY DEFINER advisor WARN remains.
- **RLS policy posture:** all 14 KATE tables have RLS enabled and no permissive client policies; `anon`/`authenticated` have no table grants, so client access remains closed by default. The advisor's `RLS Enabled No Policy` INFO notices are intentional; see [Supabase remediation guidance](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy). Fresh-schema unused-index notices are informational; the missing foreign-key index finding is resolved.
- **HQ-provided click-outs:** `427094P4` (road), `107758P7` (fly) and `260078P150` (fly) are stored in the second migration with the exact supplied URLs and `pid=P00323912&mcid=42383&medium=link&medium_version=selector`. Provenance is `KATE HQ / Product`, method `clickOffToPDP`, `record_state=discovery_needs_data`, and the provided record timestamp is stored as `source_last_checked`. Price/currency are null; date availability is false/unverified. Approved PID/click-out state is not a commission claim. Live `/product-view` and `/affiliate-click` calls both rejected an unverified item with 409; the Mara page does not expose the URLs as booking CTAs.
- **Admin secret:** code reads `KATE_ADMIN_SECRET` only from Supabase Edge Function Secrets. The user will enter it manually under **Supabase → KATE → Edge Functions → Secrets**. Until then, unauthenticated `/control` returns 503 and reveals no analytics. No Supabase account email/password or secret value was requested, logged or committed.
- **Viator API:** no `VIATOR_API_KEY` is set or used; no availability, pricing, cancellation, commission, booking or revenue is inferred from the provided URLs. Live supplier API integration remains pending the user's secure secret entry and a verified API contract.
- **Remaining release work:** complete local build/tests and secret scan, then merge the reviewed migration branch to `main` and perform the authorized Netlify site/deploy step. The branch remains available as `production-migration`.
