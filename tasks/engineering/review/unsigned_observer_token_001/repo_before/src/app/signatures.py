"""Only a deterministic placeholder signature check; not real cryptography."""


def verify_signature(payload):
    return payload.get("signature") == "valid-synthetic-signature"
