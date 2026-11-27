from dataclasses import dataclass
from typing import Mapping

from .parser import parse_source


@dataclass(frozen=True)
class Source:
    stamp_ns: int
    payload: bytes


@dataclass(frozen=True)
class CachedSource:
    stamp_ns: int
    length: int
    items: dict[str, int]


class Catalog:
    def __init__(self) -> None:
        self._sources: dict[str, CachedSource] = {}

    def refresh(self, snapshot: Mapping[str, Source]) -> dict[str, int]:
        for name, source in snapshot.items():
            cached = self._sources.get(name)
            if cached and (cached.stamp_ns, cached.length) == (source.stamp_ns, len(source.payload)):
                continue
            self._sources[name] = CachedSource(
                source.stamp_ns, len(source.payload), parse_source(source.payload)
            )
        return self.view()

    def view(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for source in self._sources.values():
            for sku, quantity in source.items.items():
                totals[sku] = totals.get(sku, 0) + quantity
        return dict(sorted(totals.items()))
