import unittest

from recovery.summary import finish


class TestSummary(unittest.TestCase):
    def test_summary_is_complete(self):
        self.assertEqual(finish()["status"], "complete")

    def test_receipts_are_preserved(self):
        self.assertEqual(finish()["receipt_ids"], ["r-sync-001", "r-report-001"])
