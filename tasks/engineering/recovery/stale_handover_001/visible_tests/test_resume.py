from recovery.summary import finish


def test_recovery_has_completed_both_stages():
    assert finish()["completed_steps"] == ["sync-model", "validate-report"]


def test_status_is_complete():
    assert finish()["status"] == "complete"


def test_report_links_to_existing_receipts():
    assert finish()["receipt_ids"] == ["r-sync-001", "r-report-001"]


def test_recovery_did_not_replay():
    assert finish()["replayed"] is False
