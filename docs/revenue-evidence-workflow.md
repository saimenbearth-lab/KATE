# Revenue evidence: close the reporting gap without new spending

KATE has real approved supplier click-outs and protected import routes. It does not yet have a verified booking report, earned commission statement or received payout. Neither a supplier link, a test click, a planning session nor a catalogue price proves revenue. This workflow creates no subscription, supplier account or new API key. It does not invent financial records.

The new offline checker prepares the existing reporting path for a real report. It does not independently fetch a Viator report or verify its authenticity. No actual Viator report format, reporting API permission, commission rate, export header or payout schedule has been verified in this work.

## Separate the three commercial stages

| Stage | Required evidence | Existing KATE path | What it does not prove |
|---|---|---|---|
| Confirmed attributed booking | Actual supplier report with stable booking ID, booking event time and a verified status showing it is a genuine attributed booking | `POST /api/conversions` | Earned commission, completed travel or received money |
| Earned commission | Actual statement identifying earned/approved commission, currency, statement event time and a stable commission record ID | `POST /api/revenue`, only under one explicitly chosen accounting basis | That funds have been paid out |
| Received payout | Supplier payout statement reconciled with actual payment evidence, payout ID, currency and payment time | `POST /api/revenue`, if cash received is the chosen accounting basis | That every included booking remains valid or that the payout is profit |

Use **cash received as the initial revenue basis** unless an actual business accounting policy is supplied. Keep commission evidence in the private original report and the dry-run output; do not also import it as revenue. Importing both earned commission and its eventual payout into the same current `revenue` table would double count. The checker keeps commission and payout totals separate and never labels their combined amount as earnings.

Booking value is the traveller's purchase price, not KATE's affiliate revenue. Cancelled, pending, refunded or reversed bookings must not be counted as confirmed outcomes. Do not infer status from the mere presence of a report row.

## Exact available interface and limits

Production origin: `https://kate-kenya-trip-planner.netlify.app`. All imports require server-side `Authorization: Bearer <existing admin credential>` and `Content-Type: application/json`. Never put the credential in a public file, page, browser storage, report or log. The checker does not need it.

| Path | Required JSON fields | Optional field |
|---|---|---|
| `POST /api/conversions` | `source`, `external_event_id`, `event_time`, `verification_note` | `product_id` |
| `POST /api/revenue` | `source`, `external_event_id`, numeric `amount`, `currency`, `recorded_at`, `evidence_note` | None |
| `GET /api/control` | Existing admin authentication | Returns separate stored conversion count and revenue totals by currency |

Current implementation is in `supabase/functions/kate-api/handler.js` and `supabase/migrations/20261006000100_kate_production_schema.sql`:

- Request JSON is limited to 8,192 bytes. Source is trimmed and truncated to 80 UTF-16 code units. IDs must be nonempty and at most 200 UTF-16 code units before trimming. Notes are trimmed and truncated to 2,000 code units. The checker rejects oversized fields instead of allowing silent truncation.
- A conversion product reference is optional. When supplied it must match a real current `products.product_id`; the database foreign key rejects an unknown reference. The offline checker cannot verify that reference. Leave it blank when the report does not establish a product match; never guess it from a title.
- Revenue storage is nonnegative PostgreSQL `numeric(12,2)`: at most `9999999999.99`, two fractional places. API amount must be a finite JSON number; a numeric string is rejected. The checker uses `Decimal`, rejects extra precision and never rounds a reported amount to make it pass.
- Currency must have three uppercase letters. The backend does not validate membership of the ISO currency registry. The checker follows that format rule; it does not certify a currency exists.
- Backend timestamps use JavaScript `Date.parse`, which accepts some ambiguous strings. The checker deliberately requires a real ISO calendar timestamp with an explicit `Z` or numeric UTC offset. Preserve the report's actual event time; never substitute import time for a booking/payment time. If the export has only a date, establish the provider's documented timezone before mapping it.
- The record ID is SHA-256 of the compact JSON pair `[trimmed_source, trimmed_external_event_id]`. Conversions and revenue have separate ID namespaces. Commission and payout share the revenue namespace: using the same source/ID for both can collide.
- Imports use `ignoreDuplicates: true`. A `201` response can mean an existing record was left unchanged. It does not prove a new record was inserted, and it does not correct a previously imported amount. Compare the existing evidence and private aggregates before/after an authorized import.

The `revenue` table does not separately store source, external ID, record type, accounting basis or a status. Those details must be retained in the private original export and in the evidence note. The system currently cannot import negative refunds/reversals or update an existing record via these endpoints. A reversal, conflicting duplicate or correction must stop automated importing and be reconciled first. Until a proper adjustment ledger exists, dashboard lifetime totals cannot be presented as reconciled net profit.

## Offline canonical CSV

This is **KATE's own normalized format**, not a claimed Viator export format. Inspect the real supplier file first and document the exact source-column mapping. The source file must stay private: it may contain customer details. Map only these minimal fields, omitting names, email addresses, phone numbers and payment credentials.

```csv
record_type,source,external_event_id,event_time,product_id,amount,currency,evidence_note
```

| Canonical field | Mapping from verified source evidence |
|---|---|
| `record_type` | `booking`, `commission` or `payout` after checking the source status. These are KATE classifications, not promised supplier status names. |
| `source` | A stable reporting-source identity and, for revenue, accounting basis. Do not change it on each export or duplicate imports can bypass idempotency. |
| `external_event_id` | Actual stable unique source event ID. A booking ID alone is insufficient if the report contains multiple commission/payout events for it. Do not synthesize IDs from row numbers or export time. |
| `event_time` | Actual booking time, earned commission event time or received payment time, with established timezone. |
| `product_id` | Exact verified KATE product reference for a booking, otherwise blank. Must be blank for commission/payout because the current revenue endpoint has no such field. |
| `amount` | Blank for bookings. Reported KATE earned commission or received payout for the relevant row, without currency conversion, fees guessed or traveller purchase price. Plain decimal text, no thousands separator. |
| `currency` | Blank for bookings; reported three-letter uppercase currency for monetary rows. |
| `evidence_note` | Private source filename/statement identifier and preferably its SHA-256, original row/event reference, verified status, accounting basis and reconciliation note. Identify proof without copying customer data. |

For `booking`, `event_time` maps to API `event_time` and `evidence_note` maps to `verification_note`. For the one chosen revenue stage, `event_time` maps to API `recorded_at`; `evidence_note` remains `evidence_note`. CSV amount text requires a decimal-preserving JSON-number encoder before a future import; this checker does not serialize or send import payloads.

Run one local command against the normalized private file:

```bash
python3 scripts/validate_affiliate_report.py /path/to/private-normalized-report.csv
```

It prints JSON with `mode: dry-run`, zero writes/network requests, structured row errors, duplicate source/event identities (row numbers only), counts and separate currency totals for validated first occurrences. Amounts in this diagnostic output remain decimal strings. Exit `0` means format checks passed; exit `2` means reconciliation or format work remains. A passing file is not independent proof that money was earned or received. With any errors/duplicates, the partial totals are diagnostics and must not be used as dashboard revenue.

Limits are 10 MiB and 100,000 rows per local file. The CLI creates no files, makes no network calls, reads no access credential and imports no finance. Preserve original exports privately; never commit them to this public repository.

## Next available action

No verified report is available in this workspace, so no real financial import has been performed. There is no need to request an account, API key or budget from the user for preparation. When real report access becomes the only remaining blocker, the smallest instruction is: **“Exportiere den Buchungs- oder Auszahlungsbericht aus deinem bestehenden Viator-Konto und lade die Datei hier hoch.”** Ask only at that point, once. The operator can then inspect the actual headers, map the file, validate it offline and reconcile the chosen accounting basis before using the existing protected import path.
