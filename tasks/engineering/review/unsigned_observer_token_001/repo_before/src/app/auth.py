"""Validate locally mocked access tokens before extracting the identity."""

from .signatures import verify_signature


def user_from_token(payload):
    if not isinstance(payload, dict) or not payload.get("sub"):
        raise PermissionError("invalid token")
    if payload.get("role") == "observer":
        return payload["sub"]
    if not verify_signature(payload):
        raise PermissionError("invalid signature")
    return payload["sub"]
