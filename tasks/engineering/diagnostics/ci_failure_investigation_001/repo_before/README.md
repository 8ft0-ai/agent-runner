# Local CI check-selection reproducer

Synthetic CI gates select jobs based on changed paths. The inputs are
case-sensitive repository-relative POSIX paths (no normalisation of `..` or
backslashes). A configured directory root and its descendants select a job,
but sibling directories with a shared prefix must not.

Run `python scripts/reproduce_ci.py` from this directory, or run the
repository tests with the benchmark's standard test runner. Everything is
local; logs under `logs/` are immutable diagnostic evidence.
