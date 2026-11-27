"""Run a selected synthetic fixture on a GitHub-hosted Linux runner."""
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from run_diagnostics import collect_events

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = os.environ.get("PILOT_TASK") or "feature.minimal_report_format_001"
TASKS = {
    "feature.minimal_report_format_001": "feature/minimal_report_format_001",
    "root_cause.relay_request_correlation_001": "root_cause/relay_request_correlation_001",
    "root_cause.incremental_catalog_refresh_001": "root_cause/incremental_catalog_refresh_001",
}
TASK = ROOT / "tasks/engineering" / TASKS[TASK_ID]
PROVIDER = os.environ.get("PILOT_PROVIDER", "NVIDIA")
ENDPOINT, MODEL = {
    "NVIDIA": ("https://integrate.api.nvidia.com/v1", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
    "OpenRouter": ("https://openrouter.ai/api/v1", "nvidia/nemotron-3.5-super-vl:free"),
}[PROVIDER]
TEMP = Path(os.environ["RUNNER_TEMP"])
WORK = TEMP / "fixture"
EVIDENCE = TEMP / "evidence"
GIT = TEMP / "baseline.git"


def git(*args):
    return subprocess.check_output(["git", "--git-dir", GIT, "--work-tree", WORK, *args], cwd=WORK)


def main(record):
    key = os.environ.pop("PILOT_API_KEY")
    if not key:
        raise ValueError("missing provider secret")
    shutil.copytree(TASK / "repo_before", WORK)
    shutil.copytree(TASK / "visible_tests", WORK / "visible_tests")
    subprocess.run(["git", "init", "--bare", GIT], check=True)
    git("add", "-f", ".")
    git("-c", "user.name=pilot", "-c", "user.email=pilot@localhost", "commit", "-qm", "fixture")
    config = {
        "model": "pilot/" + MODEL, "small_model": "pilot/" + MODEL,
        "agent": {"build": {"steps": 16}},
        "enabled_providers": ["pilot"], "share": "disabled",
        "permission": {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow",
                       "edit": "allow", "external_directory": "deny"},
        "provider": {"pilot": {"npm": "@ai-sdk/openai-compatible", "name": PROVIDER,
                               "options": {"baseURL": ENDPOINT,
                                           "apiKey": "{env:PILOT_API_KEY}"},
                               "models": {MODEL: {"name": "Nemotron"}}}},
    }
    cli = TEMP / "cli/opencode"
    env = {**os.environ, "PILOT_API_KEY": key, "OPENCODE_CONFIG_CONTENT": json.dumps(config)}
    cmd = ["docker", "run", "--rm", "--name", "nemotron-pilot", "--user",
           f"{os.getuid()}:{os.getgid()}", "--cap-drop=ALL", "--security-opt=no-new-privileges",
           "--pids-limit=160", "--memory=4g", "--read-only", "--tmpfs", "/tmp:exec",
           "-e", "HOME=/tmp", "-e", "OPENCODE_CONFIG_CONTENT", "-e", "PILOT_API_KEY",
           "-v", f"{cli}:/usr/local/bin/opencode:ro", "-v", f"{WORK}:/task", "-w", "/task",
           "ubuntu:24.04", "opencode", "run", "--standalone", "--format", "json", "--model", "pilot/" + MODEL,
           (TASK / "instruction.md").read_text() + "\nIndependent tests run after your edits."]
    record["failure_category"] = "runner_or_provider"
    record["phase"] = "agent"
    agent_start = time.monotonic()
    raw_events = TEMP / "raw-events"
    with raw_events.open("wb") as log:
        try:
            status = subprocess.run(cmd, env=env, stdout=log, stderr=log, timeout=600).returncode
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", "nemotron-pilot"], capture_output=True, timeout=20)
            record["failure_category"] = "runner_timeout"
            status = 124
    record["agent_exit"] = status
    record["agent_duration_seconds"] = round(time.monotonic() - agent_start, 2)
    with raw_events.open(errors="replace") as events:
        tools, trace = collect_events(events, record)
    raw_events.unlink()
    (EVIDENCE / "trace.json").write_text(json.dumps(trace, indent=2))
    record["phase"] = "patch"
    git("add", "-f", ".")
    changed = git("diff", "--cached", "--name-only", "-z", "HEAD").split(b"\0")[:-1]
    patch = git("diff", "--cached", "--no-ext-diff", "--binary", "HEAD")
    if len(patch) > 262144 or key.encode() in patch or base64.b64encode(key.encode()) in patch or any(prefix in patch for prefix in (b"nvapi-", b"sk-or-")):
        raise ValueError("patch withheld")
    if not all(p.startswith(b"src/") for p in changed) or any(p.is_symlink() for p in WORK.rglob("*")):
        record["failure_category"] = "scope"
        return False
    (EVIDENCE / "result.patch").write_bytes(patch)
    checker = ROOT / "scripts/visible.py"
    record["phase"] = "public_checks"
    checks = {}
    record["check_exit_codes"] = checks
    for group, test_command in [
        ("text" if TASK_ID.startswith("feature.") else "unit", ["-m", "unittest", "discover", "-s", "tests"]),
        ("visible", ["/check.py"]),
    ]:
        result = subprocess.run(["docker", "run", "--rm", "--network=none", "--read-only",
                                 "--cap-drop=ALL", "--pids-limit=64", "--memory=512m",
                                 "--tmpfs", "/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
                                 "-e", "PYTHONPATH=/task/src", "-v", f"{WORK}:/task:ro", "-v", f"{checker}:/check.py:ro",
                                 "-w", "/task",
                                 "python:3.11-slim", "python", *test_command], capture_output=True, timeout=90)
        checks[group] = result.returncode
    record["phase"] = "complete"
    ok = (status == 0 and "provider_error" not in record and bool(changed)
          and "read" in tools and bool({"edit", "write", "apply_patch"}.intersection(tools))
          and not any(checks.values()))
    if tools and not ok and status == 0 and "provider_error" not in record:
        record["failure_category"] = "agent"
    return ok


if __name__ == "__main__":
    start = time.time()
    result = {"source_revision": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
              "task": TASK_ID, "agent": "OpenCode 2.4.2",
              "requested_model": MODEL, "provider": PROVIDER, "reported_model": None,
              "human_interventions": 0, "actual_cost": None, "started_unix": start,
              "failure_category": "harness", "phase": "setup", "passed": False}
    try:
        result["passed"] = main(result)
        if result["passed"]:
            result["failure_category"] = None
    finally:
        result["duration_seconds"] = round(time.time() - start, 2)
        (EVIDENCE / "run.json").write_text(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
