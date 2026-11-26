"""Extract publishable diagnostics from OpenCode 2.4 JSON events."""
import json

ERROR_TYPES = frozenset({
    "unknown", "permission.rejected", "tool.execution", "provider.timeout",
    "provider.transport", "provider.rate-limit", "provider.auth", "provider.quota",
    "provider.internal", "provider.invalid-output", "provider.invalid-request",
    "provider.unsupported-operation", "provider.unknown", "provider.no-route",
    "provider.content-filter", "provider.free-limit", "provider.budget-limit",
    "provider.model-budget-limit", "provider.go-limit", "provider.chatgpt-limit",
    "provider.chatgpt-workspace-limit",
})
TOOLS = frozenset({"read", "edit", "write", "apply_patch", "glob", "grep"})
TOKEN_FIELDS = ("total", "input", "output", "reasoning", "cacheRead", "cacheWrite")


def object_or_empty(value):
    return value if isinstance(value, dict) else {}


def integer(value, maximum=2**53 - 1, minimum=0):
    return value if type(value) is int and minimum <= value <= maximum else None


def error_summary(event):
    error = object_or_empty(event.get("error"))
    error_type = error.get("type")
    if not isinstance(error_type, str) or error_type not in ERROR_TYPES:
        error_type = "unknown"
    status = integer(error.get("status"), minimum=100, maximum=599)
    message = error.get("message")
    message = message.lower() if isinstance(message, str) else ""
    if status == 429 or error_type == "provider.rate-limit" or "rate limit" in message:
        category = "rate_limit"
    elif status in (401, 403) or error_type == "provider.auth":
        category = "authentication"
    elif status in (408, 504) or error_type == "provider.timeout" or "timeout" in message or "timed out" in message:
        category = "timeout"
    elif error_type != "unknown":
        category = error_type
    else:
        category = "unclassified"
    return {
        "type": error_type,
        "category": category,
        "http_status": status,
        "retry_after_ms": integer(error.get("retryAfterMs")),
        "timestamp_ms": integer(event.get("timestamp")),
    }


def collect_events(lines, record):
    """Keep fixed labels and numeric metadata. Never publish event payloads."""
    tools = set()
    trace = []
    usage = []
    diagnostics = {
        "retry_count": 0,
        "last_retry": None,
        "error_count": 0,
        "last_error": None,
        "last_successful_tool": None,
    }
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        event = object_or_empty(event)
        part = object_or_empty(event.get("part"))
        event_type = event.get("type")
        if event_type == "tool_use":
            tool = part.get("tool")
            if isinstance(tool, str) and tool in TOOLS:
                completed = object_or_empty(part.get("state")).get("status") == "completed"
                trace.append({"tool": tool, "completed": completed})
                if completed:
                    tools.add(tool)
                    diagnostics["last_successful_tool"] = {
                        "tool": tool, "timestamp_ms": integer(event.get("timestamp")),
                    }
        elif event_type == "retry":
            diagnostics["retry_count"] += 1
            diagnostics["last_retry"] = {
                **error_summary(event),
                "attempt": integer(event.get("attempt")),
                "next_retry_at_ms": integer(event.get("nextRetryAt")),
            }
        elif event_type == "error":
            diagnostics["error_count"] += 1
            diagnostics["last_error"] = error_summary(event)
        if part.get("type") == "step-finish":
            tokens = object_or_empty(part.get("tokens"))
            usage.append({field: tokens[field] for field in TOKEN_FIELDS
                          if integer(tokens.get(field)) is not None})

    record["agent_diagnostics"] = diagnostics
    record["usage_by_step"] = usage or None
    if diagnostics["last_error"] is not None:
        record["provider_error"] = diagnostics["last_error"]["category"]
    return tools, trace
