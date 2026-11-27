"""Synthetic receipt store, not a real external service."""

import json
from pathlib import Path

FILE = Path("state/receipts.json")


def load_receipts():
    return json.loads(FILE.read_text(encoding="utf-8"))


def replay_stage(step):
    """Simulate an expensive duplicate stage, and record its unwanted replay."""
    data = load_receipts()
    data["replay_count"] += 1
    data["receipts"].append({
        "step": step, "status": "done",
        "receipt_id": f"duplicate-{data['replay_count']}"
    })
    FILE.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
