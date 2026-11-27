# Repair the incremental catalog refresh

After an import job, the inventory display sometimes shows older quantities or
keeps a source that has disappeared. An operator suspects timestamps arriving
out of order. Another report says a malformed import appears to change earlier
entries even though the refresh raised an error.

Trace the implementation and repair the smallest responsible component. Preserve
the public API, parser behaviour and deterministic output ordering. Each input to
`Catalog.refresh` is the complete snapshot, and its source name and payload are
authoritative. Timestamps are advisory: another import may reuse a timestamp or
supply an older one. Existing incremental reuse still matters: a successful
refresh should avoid parsing payloads that are unchanged for their source name,
even when only its timestamp changes.

A refresh must publish all of the new snapshot or leave the last successful
snapshot and its reusable parsed data intact. Removing a source, including an
empty snapshot, must remove its contribution. Results are sorted by SKU, combine
quantities across sources, and may be modified by callers without changing the
catalog's state. A malformed source must still raise the existing parse error.

Change only production code under `src/`. Use the standard library. Run the
relevant tests and briefly state the cause and checks you ran.
