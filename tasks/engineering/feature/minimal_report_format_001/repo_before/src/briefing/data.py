"""Offline deterministic status fixture."""

ROWS = [
    {"service": "relay", "status": "degraded", "latency_ms": 90},
    {"service": "observer", "status": "ok", "latency_ms": 32},
]


def get_snapshot():
    return [dict(row) for row in ROWS]
