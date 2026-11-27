# Investigate and optimise an incremental reconciliation regression

The `stream_merge.reconcile(existing, incoming)` operation merges a snapshot
with ordered updates. Existing record order is stable; each update replaces
the **first matching ID** without moving it, or appends a new ID. Later updates
to that ID win. Existing duplicates, empty IDs, input generators and the
identity and types of returned record objects are part of the contract. The
input list must not be mutated.

The supplied implementation preserves the visible results but has regressed
under larger update batches. Identify and remove its algorithmic bottleneck.
Provide a reproducible explanation of why the complexity improves. Grading
uses deterministic record-ID access and equality probes instead of timing
races, as well as exact functional tests.

Use only the standard library. Edit implementation files under `src/` only;
do not edit any tests, task/scoring contracts, dependencies or configuration.
Do not short-circuit work or hardcode expected outputs. No caching service,
database or infrastructure is necessary.
