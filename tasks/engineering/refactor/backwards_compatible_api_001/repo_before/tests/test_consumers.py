from ledger.api import list_activity
from ledger.csv_export import export_activity_csv


EVENTS = [
    {"account_id": "a", "reference": "  z ", "occurred_at": "2026-11-02", "amount_cents": "12", "memo": "first"},
    {"account_id": "b", "reference": "no", "occurred_at": "2026-11-01", "amount_cents": 100},
    {"account_id": "a", "reference": "a", "occurred_at": "2026-11-01", "amount_cents": 3},
]


def test_dictionary_contract():
    assert [row["reference"] for row in list_activity(EVENTS, "a")] == ["a", "z"]


def test_csv_contract():
    assert export_activity_csv(EVENTS, "a") == (
        "reference,occurred_at,amount_cents,memo\n"
        "a,2026-11-01,3,\n"
        "z,2026-11-02,12,first\n"
    )
