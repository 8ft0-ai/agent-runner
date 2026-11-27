"""Deterministic selection of required checks for repository-relative POSIX paths."""

DEFAULT_RULES = (
    ("src/api", ("api-contract", "api-unit")),
    ("src/api_client", ("client-unit",)),
    ("src/worker", ("worker-unit",)),
    ("docs", ("docs-lint",)),
)


def select_checks(changed_paths, rules=DEFAULT_RULES):
    """Return sorted unique check names for changes under configured directories."""
    selected = set()
    for path in changed_paths:
        for root, checks in rules:
            if path.startswith(root):
                selected.update(checks)
    return tuple(sorted(selected))
