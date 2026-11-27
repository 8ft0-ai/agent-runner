# Offline token verifier PR fixture

PR-17 adds support for an observer role, while preserving a signature
requirement for every accepted token. The Python app and tests are local.

Run the existing tests:

    PYTHONPATH=src python3 -m unittest discover -s tests -v

Inspect review/PR-17.diff and actual working files to make a review decision.
