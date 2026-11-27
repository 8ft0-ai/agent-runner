# Refactor the activity API without changing consumer behaviour

A compact ledger exposes two long-lived public entry points:
`ledger.api.list_activity(events, account_id)` (list of dictionaries) and
`ledger.csv_export.export_activity_csv(events, account_id)` (CSV text).
Both currently implement the same activity filtering, field normalisation and
sort rules. Consumers depend on the exact signatures, output field types,
stable ordering for equal sort keys, exact account matching, CSV escaping and
the empty-result header.

Extract **one canonical activity-selection function** named
`ledger.activity.select_entries(events, account_id)`. Both public modules
must delegate their shared work to that function, while keeping CSV formatting
inside the CSV module and preserving the original public API. The extraction
must actually eliminate the repeated filtering/normalisation logic; cosmetic
renaming or adding a function that callers do not use is insufficient.

Use only the standard library. Do not change tests, contracts, dependency
files or add infrastructure. Explain how the structural change and backwards
compatibility were verified.
