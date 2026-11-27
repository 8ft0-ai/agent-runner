"""Public CSV export API. Keep CSV formatting and output contracts here."""
import csv
from io import StringIO


def export_activity_csv(events, account_id):
    """Export matching activity using the stable public CSV schema."""
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
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("reference", "occurred_at", "amount_cents", "memo"))
    for record in selected:
        writer.writerow((
            record["reference"], record["occurred_at"],
            record["amount_cents"], record["memo"],
        ))
    return output.getvalue()
