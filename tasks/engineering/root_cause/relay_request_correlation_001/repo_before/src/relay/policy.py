"""The free-only policy is intentionally independent from request routing."""

ALLOWED_MODELS = frozenset({"free/nemotron", "free/lightning"})


def require_allowed(model: str) -> None:
    if model not in ALLOWED_MODELS:
        raise ValueError("model not allowed")
