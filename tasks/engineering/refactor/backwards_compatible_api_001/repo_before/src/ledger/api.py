"""Public in-process activity API. Keep its signature and return schema."""


def list_activity(events, account_id):
    """Select activity records in stable chronological order."""
    selected = []
    for event in events:
        if event["account_id"] != account_id:
            continue
        selected.append({
            "reference": str(event["reference"]).strip(),
            "occurred_at": event["occurred_at"],
            "amount_cents": int(event["amount_cents"]),
            "memo": str(event.get("memo", "")),
        })
    selected.sort(key=lambda row: (row["occurred_at"], row["reference"]))
    return selected
