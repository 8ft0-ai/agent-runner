"""Human-oriented local formatting."""


def render_text(rows):
    return "\n".join(
        f"{row['service']}: {row['status']} ({row['latency_ms']} ms)"
        for row in rows
    )
