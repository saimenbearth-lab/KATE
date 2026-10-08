"""Synthetic offline cases only: these fixtures are never imported into KATE."""
import csv
from io import StringIO
import unittest

from scripts.validate_affiliate_report import FIELDS, validate_report


def report(*changes):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for index, change in enumerate(changes):
        row = dict(record_type="commission", source="synthetic-test", external_event_id=f"test-{index}",
                   event_time="2026-10-08T12:00:00Z", product_id="", amount="0.10", currency="USD",
                   evidence_note="Synthetic validator fixture; not real finance evidence.")
        row.update(change)
        writer.writerow(row)
    return validate_report(StringIO(output.getvalue()))


class AffiliateReportTests(unittest.TestCase):
    def test_decimal_sums_and_separate_commission_payout(self):
        result = report({}, {"amount": "0.20"}, {"record_type": "payout", "amount": "0.30"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["amounts"], [
            {"record_type": "commission", "currency": "USD", "amount": "0.30"},
            {"record_type": "payout", "currency": "USD", "amount": "0.30"}])
        self.assertEqual(result["writes"], 0)

    def test_booking_does_not_use_customer_transaction_price_as_revenue(self):
        self.assertFalse(report({"record_type": "booking", "amount": "1950.00"})["valid"])
        self.assertTrue(report({"record_type": "booking", "amount": "", "currency": "", "product_id": "test-product"})["valid"])

    def test_duplicate_identity_in_revenue_reports_conflict_without_echoing_id(self):
        result = report({"external_event_id": "private-test-id"},
                        {"external_event_id": "private-test-id", "record_type": "payout"})
        self.assertFalse(result["valid"])
        self.assertEqual(result["duplicates"], [{"row": 3, "first_row": 2, "route": "revenue", "conflicting_values": True}])
        self.assertNotIn("private-test-id", str(result))
        self.assertTrue(report({"external_event_id": "same-id"},
                               {"external_event_id": "same-id", "record_type": "booking", "amount": "", "currency": ""})["valid"])

    def test_actual_database_money_limit_and_no_rounding(self):
        self.assertTrue(report({"amount": "9999999999.99"})["valid"])
        for amount in ("10000000000.00", "0.001", "-1", "NaN", "Infinity", "1e2", "1,20"):
            with self.subTest(amount=amount):
                self.assertFalse(report({"amount": amount})["valid"])

    def test_limits_use_backend_utf16_and_do_not_silently_truncate(self):
        self.assertTrue(report({"source": "x" * 80, "external_event_id": "y" * 200, "evidence_note": "z" * 2000})["valid"])
        for change in ({"source": "x" * 81}, {"external_event_id": "y" * 201},
                       {"evidence_note": "z" * 2001}, {"source": "\U0001f600" * 41}):
            self.assertFalse(report(change)["valid"])

    def test_timestamps_require_valid_calendar_and_explicit_timezone(self):
        self.assertTrue(report({"event_time": "2026-10-08T12:00:00+03:00"})["valid"])
        for value in ("2026-02-30T12:00:00Z", "2026-10-08", "2026-10-08T12:00:00", "tomorrow"):
            self.assertFalse(report({"event_time": value})["valid"])

    def test_supplier_csv_requires_explicit_mapping_and_empty_report_fails(self):
        result = validate_report(StringIO("Booking ID,Commission\nreal-looking,1.00\n"))
        self.assertEqual(result["errors"][0]["code"], "canonical_header_required")
        self.assertFalse(validate_report(StringIO(",".join(FIELDS) + "\n"))["valid"])

    def test_structural_rows_and_revenue_product_are_rejected(self):
        result = validate_report(StringIO(",".join(FIELDS) + "\nonly,three,columns\n"))
        self.assertEqual(result["errors"][0]["code"], "column_count")
        self.assertFalse(report({"product_id": "unexpected"})["valid"])

    def test_json_byte_limit_accounts_for_escaped_control_characters(self):
        result = report({"evidence_note": "evidence:" + "\x00" * 1900})
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"][0]["code"], "backend_json_body_over_8192_bytes")
