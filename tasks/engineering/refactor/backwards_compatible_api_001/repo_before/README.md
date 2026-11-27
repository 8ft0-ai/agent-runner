# Activity consumers

Public interfaces are `ledger.api.list_activity(events, account_id)` and
`ledger.csv_export.export_activity_csv(events, account_id)`.

Input events are mappings containing account_id, reference, occurred_at
(ISO8601 string), amount_cents and optionally memo. Filter by exact account.
Normalise reference with `str(...).strip()`, amount with `int(...)`, and
memo with `str(...)` (default empty). Sort by (occurred_at, reference),
keeping input order for ties. Never modify inputs.

CSV header: reference,occurred_at,amount_cents,memo and a terminal newline.
The two public functions must retain their original signatures and outputs.
