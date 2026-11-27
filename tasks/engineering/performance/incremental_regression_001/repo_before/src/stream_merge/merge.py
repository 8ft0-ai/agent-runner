"""Incrementally reconcile a record snapshot and ordered updates."""
from .models import Record


def reconcile(existing: list[Record], incoming) -> list[Record]:
    """Preserve first-seen positions; updates replace the first matching ID."""
    result = list(existing)
    for update in incoming:
        for index, current in enumerate(result):
            if current.record_id == update.record_id:
                result[index] = update
                break
        else:
            result.append(update)
    return result
