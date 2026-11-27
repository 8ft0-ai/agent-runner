"""Synthetic immutable snapshot record."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    record_id: str
    quantity: int
    source: str
