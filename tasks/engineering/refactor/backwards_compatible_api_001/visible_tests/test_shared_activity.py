from ledger.api import list_activity
from ledger.csv_export import export_activity_csv


def _with_shared_stub(module, callback, selected_rows):
    import ledger.activity as activity
    canonical = activity.select_entries
    aliases = [name for name, value in vars(module).items() if value is canonical]
    invoked = []
    marker = object()

    def stub(events, account):
        assert events is marker
        invoked.append(account)
        return selected_rows

    activity.select_entries = stub
    for name in aliases:
        setattr(module, name, stub)
    try:
        result = callback(marker, "chosen")
    finally:
        activity.select_entries = canonical
        for name in aliases:
            setattr(module, name, canonical)
    assert invoked == ["chosen"]
    return result


def test_public_api_delegates_to_one_canonical_selection_function():
    import ledger.activity as activity
    import ledger.api as api
    assert callable(activity.select_entries)
    sentinel = [{"reference": "shared", "occurred_at": "2026-01-01", "amount_cents": 1, "memo": ""}]
    assert _with_shared_stub(api, list_activity, sentinel) == sentinel


def test_csv_delegates_to_shared_selection_and_keeps_formatting_local():
    import ledger.activity as activity
    import ledger.csv_export as exporter
    assert callable(activity.select_entries)
    sentinel = [{"reference": "source", "occurred_at": "2026-01-01", "amount_cents": 7, "memo": "yes"}]
    assert _with_shared_stub(exporter, export_activity_csv, sentinel) == (
        "reference,occurred_at,amount_cents,memo\nsource,2026-01-01,7,yes\n"
    )
