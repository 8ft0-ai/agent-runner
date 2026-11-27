"""Finalise work from verified receipts, not from a stale handover."""

from .ledger import load_receipts


class IncompleteWork(ValueError):
    pass


def finish():
    """Return a locally verifiable, repeatable completion result."""
    return {"status": "pending", "completed_steps": [], "receipt_ids": [],
            "replayed": True}
