"""Offline validation of KATE's canonical CSV; never imports or contacts a service."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys

FIELDS = ("record_type", "source", "external_event_id", "event_time", "product_id", "amount", "currency", "evidence_note")
KINDS = {"booking", "commission", "payout"}
MAX_AMOUNT = Decimal("9999999999.99")  # PostgreSQL numeric(12,2).
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000


def validate_report(stream):
    """Return a JSON-safe dry-run summary. Cell contents are not echoed on error."""
    result = {"mode": "dry-run", "writes": 0, "network_requests": 0,
              "valid": False, "rows": 0, "accepted_rows": 0,
              "errors": [], "duplicates": [], "counts": {}, "amounts": [],
              "note": "Format validation only; this does not verify a supplier report, booking, commission or payout."}
    errors = result["errors"]
    reader = csv.DictReader(stream)
    try:
        header = reader.fieldnames
    except csv.Error:
        errors.append({"row": 1, "field": "header", "code": "invalid_csv"})
        return result
    if header != list(FIELDS):
        errors.append({"row": 1, "field": "header", "code": "canonical_header_required", "expected": list(FIELDS)})
        return result
    seen = {}
    totals = {}
    try:
        for number, raw in enumerate(reader, start=2):
            result["rows"] += 1
            if result["rows"] > MAX_ROWS:
                errors.append({"row": number, "field": "file", "code": "too_many_rows"})
                break
            if None in raw or any(value is None for value in raw.values()):
                errors.append({"row": number, "field": "row", "code": "column_count"})
                continue
            row = {key: value.strip() for key, value in raw.items()}
            start_errors = len(errors)

            def reject(field, code):
                errors.append({"row": number, "field": field, "code": code})

            kind = row["record_type"]
            if kind not in KINDS:
                reject("record_type", "use_booking_commission_or_payout")
            for field, limit in (("source", 80), ("external_event_id", 200), ("evidence_note", 2000)):
                # JS limits are UTF-16 code units, not Python Unicode code points.
                text = raw[field] if field == "external_event_id" else row[field]
                if not row[field]:
                    reject(field, "required")
                elif len(text.encode("utf-16-le")) // 2 > limit:
                    reject(field, "too_long")
            if len(row["product_id"].encode("utf-16-le")) // 2 > 80:
                reject("product_id", "too_long")
            try:
                value = row["event_time"]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
                    raise ValueError
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.utcoffset() is None:
                    raise ValueError
            except ValueError:
                reject("event_time", "iso_timestamp_with_timezone_required")

            amount = None
            if kind == "booking":
                if row["amount"] or row["currency"]:
                    reject("amount", "booking_is_not_revenue_leave_amount_and_currency_empty")
            elif kind in {"commission", "payout"}:
                try:
                    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", row["amount"]):
                        raise InvalidOperation
                    amount = Decimal(row["amount"])
                    if not amount.is_finite() or not Decimal("0") <= amount <= MAX_AMOUNT:
                        raise InvalidOperation
                except InvalidOperation:
                    reject("amount", "nonnegative_numeric_12_2_required")
                if not re.fullmatch(r"[A-Z]{3}", row["currency"]):
                    reject("currency", "uppercase_three_letters_required")
                if row["product_id"]:
                    reject("product_id", "revenue_endpoint_has_no_product_field")
            if len(errors) != start_errors:
                continue

            payload = {"source": row["source"], "external_event_id": row["external_event_id"]}
            if kind == "booking":
                payload.update(event_time=row["event_time"], product_id=row["product_id"] or None,
                               verification_note=row["evidence_note"])
            else:
                payload.update(amount=str(amount), currency=row["currency"], recorded_at=row["event_time"],
                               evidence_note=row["evidence_note"])
            # Amount is represented as a string only while measuring size; actual API
            # imports require a JSON number. This validator creates no import payload.
            if len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()) > 8192:
                reject("row", "backend_json_body_over_8192_bytes")
                continue

            # The backend hashes this pair, independently in conversions and revenue.
            key = json.dumps([row["source"], row["external_event_id"]], ensure_ascii=False, separators=(",", ":"))
            record_id = hashlib.sha256(key.encode()).hexdigest()
            route = "conversions" if kind == "booking" else "revenue"
            identity = (route, record_id)
            if identity in seen:
                previous_number, previous_row = seen[identity]
                result["duplicates"].append({"row": number, "first_row": previous_number,
                                             "route": route, "conflicting_values": row != previous_row})
                continue
            seen[identity] = (number, row)
            result["accepted_rows"] += 1
            result["counts"][kind] = result["counts"].get(kind, 0) + 1
            if amount is not None:
                total_key = (kind, row["currency"])
                totals[total_key] = totals.get(total_key, Decimal("0")) + amount
    except csv.Error:
        errors.append({"row": reader.line_num, "field": "file", "code": "invalid_csv"})
    result["amounts"] = [{"record_type": kind, "currency": currency, "amount": format(amount, ".2f")}
                         for (kind, currency), amount in sorted(totals.items())]
    # Do not silently accept empty reports or deduplicate conflicting source evidence.
    if not result["rows"]:
        errors.append({"row": 2, "field": "file", "code": "empty_report"})
    result["valid"] = not errors and not result["duplicates"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="Local canonical CSV; original supplier columns must be mapped first")
    args = parser.parse_args(argv)
    try:
        if args.csv_file.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("file_too_large")
        with args.csv_file.open(encoding="utf-8-sig", newline="") as stream:
            result = validate_report(stream)
    except (OSError, UnicodeError, ValueError):
        result = {"mode": "dry-run", "writes": 0, "network_requests": 0, "valid": False,
                  "errors": [{"row": None, "field": "file", "code": "unreadable_or_oversized_file"}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
