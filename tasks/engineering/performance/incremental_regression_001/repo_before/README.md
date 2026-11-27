# Incremental snapshot reconciliation (synthetic)

A stream processor reconciles an existing ordered snapshot with successive
incoming records. Each incoming record replaces the **first** matching ID in
place, or appends when its ID is new. Later updates win; duplicates already in
the snapshot must remain in their original positions. The result is a new
list of the same record objects, with deterministic order and no mutation of
the caller's input collection.

A customer workload with thousands of records and updates now performs too
much repeated searching. Diagnose the cause and remove the avoidable work
without changing the `reconcile(existing, incoming)` signature or semantics.

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
No external services, resources or dependencies are required.
