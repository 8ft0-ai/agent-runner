"""One bounded GitHub-hosted NVIDIA Build rate-limit observation (not a benchmark score).

Six fixed, small, sequential requests; no model text, prompts, secrets, or
arbitrary headers are written to disk or Actions logs.
"""
import http.client
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

HOST = "integrate.api.nvidia.com"
PATH = "/v1/chat/completions"
MODELS = (
    ("minimax", "minimaxai/minimax-m3.1-flash"),
    ("ultra", "nvidia/nemotron-3-ultra-550b-a55b"),
    ("lightning", "nvidia/nemotron-3.5-lightning-30b-a3b"),
)
HEADER_ALLOWLIST = {
    "retry-after", "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
    "x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
    "x-ratelimit-reset-requests", "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens", "x-ratelimit-reset-tokens",
}
SPACING_S = 30
REQUEST_TIMEOUT_S = 50
MAX_REQUESTS = 6


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def allowlisted_headers(response):
    result = {}
    for name, value in response.getheaders():
        name = name.lower().strip()
        if name in HEADER_ALLOWLIST and len(value) <= 100 and re.fullmatch(
                r"[0-9A-Za-z.,: +\\-_/]+", value):
            result[name] = value
    return result


def probe(label, model, key):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply OK."}],
        "max_tokens": 32, "stream": False,
    }).encode()
    record = {"profile": label, "requested_model": model, "at_utc": utc_now()}
    connection = http.client.HTTPSConnection(HOST, timeout=REQUEST_TIMEOUT_S)
    started = time.monotonic()
    try:
        connection.request("POST", PATH, payload, {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        })
        response = connection.getresponse()
        record["status"] = response.status
        record["rate_headers"] = allowlisted_headers(response)
        # Discard without retaining text, error messages, or response headers.
        response.read(65536)
    except (OSError, http.client.HTTPException) as error:
        record["error_type"] = type(error).__name__
    finally:
        record["elapsed_s"] = round(time.monotonic() - started, 2)
        connection.close()
    return record


def main():
    key = os.environ.pop("NVIDIA_API_KEY", "")
    if not key:
        raise SystemExit("NVIDIA key missing; no requests sent")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("GitHub Actions only")
    results = []
    last_start = None
    for i in range(MAX_REQUESTS):
        if last_start is not None:
            time.sleep(max(0.0, SPACING_S - (time.monotonic() - last_start)))
        label, model = MODELS[i % len(MODELS)]
        last_start = time.monotonic()
        result = probe(label, model, key)
        result["probe_index"] = i + 1
        results.append(result)
        print("Probe %d/6 %s: %s (%ss)" % (
            i + 1, label, result.get("status", result.get("error_type")),
            result["elapsed_s"]), flush=True)
    destination = Path(os.environ["RUNNER_TEMP"]) / "rate-diagnostic"
    destination.mkdir(exist_ok=True)
    (destination / "rate-observation.json").write_text(json.dumps({
        "purpose": "diagnostic_only_not_a_benchmark_result",
        "source_revision": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "fixed_interval_seconds": SPACING_S,
        "results": results,
    }, indent=2) + "\n")
    print("Sanitised rate observation recorded; no credentials or content saved.")


if __name__ == "__main__":
    main()
