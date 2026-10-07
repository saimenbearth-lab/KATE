# KATE operations

## Configuration

Supabase project: `bshxiuzdqlqezqsrybtn` (KATE, eu-central-1).
Frontend: https://kate-kenya-trip-planner.netlify.app
Source: https://github.com/saimenbearth-lab/KATE

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are read only by the Edge Function. `VIATOR_API_KEY` is read only on the server. The existing production supplier credential was verified by a successful live product search; its value was never inspected or committed.

Use an existing `KATE_ADMIN_SECRET`, or store a SHA-256 verifier of a securely generated password as the private `business_memory` value under key `control_admin_secret_sha256`. Do not expose the verifier to browser table roles. The environment secret takes precedence over a verifier. Never include plaintext credentials in source, logs or a public issue. Verify authenticated `/api/control` before treating any supplied password as usable.

## Deployment sequence

1. Run Node tests and the full Python/static-build checks in a complete repository checkout.
2. Apply any new reviewed database migrations. Both `20261006224939_kate_catalogue_clickouts.sql` and `20261006224940_kate_scheduled_metrics.sql` have already been applied to production; do not manually rerun their cron scheduling steps.
3. Deploy `index.js`, `handler.js`, `validation.js` and `viator.js` together as `kate-api`. Keep `verify_jwt = false` because public planning/search routes are intentional; sensitive routes perform custom admin authentication.
4. Publish the Git commit to Netlify's production branch after checks pass. Confirm `/build.json` reports that exact commit and the supplier preview release.
5. Fetch `/api/health` fresh and confirm storage and supplier configuration. Check a real preview search. Check that unauthenticated control access remains closed. Test authenticated control privately.

The Netlify deployment does not deploy Supabase code. Database migrations are not an automatic side effect of either deployment.

## Scheduled work

`kate-hourly-metrics` runs `public.kate_collect_metrics()` at minute 10 of every hour in UTC. Inspect pg_cron run history for execution failures. The latest summary is private `business_memory.scheduled_metrics_latest`, and `agent_runs` records execution. This job aggregates the last 24 hours of events and lifetime evidence-backed financial records; it does not call Viator or a model.

## Verified evidence and remaining checks

During the takeover, the public Netlify proxy and Supabase health endpoint returned HTTP 200. Supabase Edge version 3 returned a successful live Viator search with real product IDs, prices, durations and ratings. The supplier credential was configured; admin access was not configured in that health response. The two new migrations were applied, and the hourly cron job was inspected as active. A first metrics routine run was verified. Twenty-seven Node cases passed after duration filtering and private-verifier support were added.

The managed local execution environment lacks the original binary hero image and blocks localhost sockets. Consequently, a full Python suite and complete static build must be verified in GitHub Actions or a complete checkout. An attempted transactional SQL click-out regression did not finish through the connector; database click-out rejection/redirect behavior is covered by handler unit tests but still needs an end-to-end production check.

An attempted private admin-verifier write through the SQL connector did not return a result. Do not assume it committed. Verify `admin_configured` after deploying verifier support and check authenticated control privately. A generated password file is outside the repository and must not be described as working before this check.

No end-to-end booking or affiliate payout has been verified. All revenue claims require a real supplier report. Four development subagents were used; persistent CEO/Scout/Product/Growth/Builder/Money services are not provisioned by this change.
