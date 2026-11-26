"""Run one Codex relay comparison or a small local-tool compatibility probe."""
import base64
import json
import os
import re
import shutil
import subprocess
import time
from contextlib import nullcontext
from pathlib import Path
from threading import Timer

from nvidia_responses import BASE_URL as NVIDIA_URL, MODEL as NVIDIA_MODEL, nvidia_bridge
from run_diagnostics import collect_events, integer, object_or_empty

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "root_cause.relay_request_correlation_001"
TASK = ROOT / "tasks/engineering/root_cause/relay_request_correlation_001"
FIXTURE_REVISION = "c7f87d835c0d7110118bd0e31655e6a223f2d735"
CLI_NAME = "codex-x86_64-unknown-linux-musl"
CLI_DIGEST = "ad83b94c093f0cdd8176a6bc8005a461bdf23a759863e157d40f562b8a9d664d"
PROVIDERS = {
    "NVIDIA": (NVIDIA_URL, NVIDIA_MODEL),
    "OpenRouter": ("https://openrouter.ai/api/v1", "nvidia/nemotron-3.5-super-vl:free"),
    "Groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
}
PROBE_PROMPT = (
    "Use local tools to read input.txt. Then use a local tool to create output.txt "
    "containing exactly the same line, including its newline. Then finish."
)
COMMAND = re.compile(r"\b(cat|rg|grep|find|ls|sed|head|tail|printf|tee|cp)\b")
HTTP_ERROR = re.compile(r"(?:status(?: code)?[ :=]+|HTTP(?:/\d(?:\.\d)?)?\s+)([45]\d\d)\b", re.I)
SECRET_PREFIXES = (b"nvapi-", b"sk-or-", b"gsk_", b"AIza", b"ghp_", b"gho_", b"github_pat_")


def codex_events(lines):
    """Translate Codex JSONL into the existing allowlisted diagnostics contract."""
    for line in lines:
        try:
            event = object_or_empty(json.loads(line))
        except ValueError:
            continue
        kind = event.get("type")
        timestamp = time.time_ns() // 1_000_000
        if kind == "item.completed":
            item = object_or_empty(event.get("item"))
            if item.get("type") == "file_change":
                tool = "edit"
                completed = item.get("status") == "completed"
            elif item.get("type") == "command_execution":
                command = item.get("command")
                if not isinstance(command, str):
                    continue
                match = COMMAND.search(command)
                if not match:
                    continue
                name = match.group(1)
                if name in {"printf", "tee", "cp"} or re.search(r"(?<![<>=])>(?!=)", command):
                    tool = "edit"
                elif name in {"rg", "grep"}:
                    tool = "grep"
                elif name in {"find", "ls"}:
                    tool = "glob"
                else:
                    tool = "read"
                completed = item.get("status") == "completed" and item.get("exit_code") == 0
            else:
                continue
            yield {"type": "tool_use", "timestamp": timestamp,
                   "part": {"tool": tool, "state": {"status": "completed" if completed else "failed"}}}
        elif kind == "turn.completed":
            usage = object_or_empty(event.get("usage"))
            fields = {"input": "input_tokens", "output": "output_tokens",
                      "cacheRead": "cached_input_tokens", "reasoning": "reasoning_output_tokens"}
            yield {"part": {"type": "step-finish", "tokens": {
                field: usage[key] for field, key in fields.items() if integer(usage.get(key)) is not None}}}
        elif kind in {"error", "turn.failed"}:
            message = event.get("message") or object_or_empty(event.get("error")).get("message")
            if not isinstance(message, str):
                continue
            status = HTTP_ERROR.search(message)
            retry = re.match(r"Reconnecting\.\.\. (\d+)/\d+", message)
            yield {"type": "retry" if retry else "error", "timestamp": timestamp,
                   "attempt": int(retry.group(1)) if retry else None,
                   "error": {"type": "unknown", "status": int(status.group(1)) if status else None,
                             "message": message}}


def run_codex(cli, work, endpoint, model, key, prompt, seconds, record, *, stderr=subprocess.DEVNULL):
    # The outer namespace exposes only the fixture, Ubuntu runtime and DNS/CA files.
    # Codex then sandboxes agent shell commands with network disabled.
    command = [
        "bwrap", "--die-with-parent", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
        "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/lib64", "/lib64", "--ro-bind", "/etc/ssl", "/etc/ssl",
        "--ro-bind-try", "/etc/resolv.conf", "/etc/resolv.conf",
        "--ro-bind-try", "/etc/nsswitch.conf", "/etc/nsswitch.conf",
        "--ro-bind-try", "/etc/hosts", "/etc/hosts", "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp", "--tmpfs", "/codex-home", "--ro-bind", str(cli), "/cli/codex", "--bind", str(work), "/task",
        "--chdir", "/task", "/cli/codex", "-a", "never", "exec", "--json",
        "--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--model", model, "--disable", "multi_agent",
        "--disable", "goals", "--disable", "image_generation", "--disable", "view_image",
    ]
    config = {
        "model_provider": "benchmark",
        "model_providers.benchmark.name": "Benchmark",
        "model_providers.benchmark.base_url": endpoint,
        "model_providers.benchmark.env_key": "PILOT_API_KEY",
        "model_providers.benchmark.wire_api": "responses",
        "model_providers.benchmark.request_max_retries": 0,
        "model_providers.benchmark.stream_max_retries": 0,
        "model_providers.benchmark.stream_idle_timeout_ms": 30_000,
        "sandbox_workspace_write.network_access": False,
        "shell_environment_policy.include_only": ["PATH", "HOME", "LANG", "PYTHONDONTWRITEBYTECODE"],
        "analytics.enabled": False,
        "feedback.enabled": False,
        "web_search": "disabled",
    }
    for name, value in config.items():
        command.extend(["-c", f"{name}={json.dumps(value)}"])
    command.append("-")
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "CODEX_HOME": "/codex-home",
           "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PILOT_API_KEY": key}
    start = time.monotonic()
    # Stream JSONL through the allowlist without saving raw event bodies.
    with subprocess.Popen(command, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=stderr, text=True, errors="replace") as proc:
        timer = Timer(seconds, proc.kill)
        timer.start()
        try:
            try:
                proc.stdin.write(prompt)
                proc.stdin.close()
            except BrokenPipeError:
                pass
            translated = (json.dumps(event) for event in codex_events(proc.stdout))
            tools, trace = collect_events(translated, record)
            status = proc.wait()
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    elapsed = time.monotonic() - start
    record["agent_exit"] = 124 if status < 0 and elapsed >= seconds else status
    record["agent_duration_seconds"] = round(elapsed, 2)
    return tools, trace


def public_checks(work, record):
    checks = {}
    record["check_exit_codes"] = checks
    for group, args in {
        "unit": ["-m", "unittest", "discover", "-s", "tests"],
        "visible": ["/check.py"],
    }.items():
        result = subprocess.run([
            "docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
            "--pids-limit=64", "--memory=512m", "--tmpfs", "/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "PYTHONPATH=/task/src", "-v", f"{work}:/task:ro",
            "-v", f"{ROOT / 'scripts/visible.py'}:/check.py:ro", "-w", "/task",
            "python:3.11-slim", "python", *args,
        ], capture_output=True, timeout=90)
        checks[group] = result.returncode
    return not any(checks.values())


def execute(temp, evidence, key, record):
    task_start = time.monotonic()
    work = temp / "fixture"
    endpoint, model = PROVIDERS[record["provider"]]
    cli = temp / "codex" / CLI_NAME
    probe = record["mode"] == "probe"
    if probe:
        work.mkdir()
        # A fresh unpredictable value proves the model actually read the local file.
        nonce = os.urandom(16).hex() + "\n"
        (work / "input.txt").write_text(nonce)
        prompt = PROBE_PROMPT
    else:
        shutil.copytree(TASK / "repo_before", work)
        # Include the public checks in the baseline before any agent edits.
        shutil.copytree(TASK / "visible_tests", work / "visible_tests")
        baseline = temp / "baseline.git"

        def git(*args):
            return subprocess.check_output(
                ["git", "--git-dir", baseline, "--work-tree", work, *args],
                cwd=work, stderr=subprocess.DEVNULL,
            )

        subprocess.run(["git", "init", "-q", "--bare", baseline], check=True)
        git("add", "-f", ".")
        git("-c", "user.name=pilot", "-c", "user.email=pilot@localhost", "commit", "-qm", "fixture")
        prompt = (TASK / "instruction.md").read_text() + "\nIndependent tests run after your edits."
    record["phase"] = "agent"
    route = nvidia_bridge(temp, key, record) if record["provider"] == "NVIDIA" else nullcontext((endpoint, key))
    with route as (base_url, agent_key):
        _, trace = run_codex(cli, work, base_url, model, agent_key, prompt, 90 if probe else 600, record)
    (evidence / "trace.json").write_text(json.dumps(trace, indent=2))
    clean = record["agent_exit"] == 0 and "provider_error" not in record
    record["clean_exit"] = clean
    if probe:
        output = work / "output.txt"
        record["local_tool_round_trip"] = (not output.is_symlink() and output.is_file()
                                            and output.stat().st_size == len(nonce)
                                            and output.read_text(errors="replace") == nonce)
        return clean and record["local_tool_round_trip"]

    record["phase"] = "patch"
    if any(path.is_symlink() or (not path.is_file() and not path.is_dir()) for path in work.rglob("*")):
        raise ValueError("unsafe workspace entry")
    if (work / ".git").exists():
        raise ValueError("nested repository")
    git("add", "-f", ".")
    changed = git("diff", "--cached", "--name-only", "-z", "HEAD").split(b"\0")[:-1]
    record["registry_only"] = changed == [b"src/relay/registry.py"]
    if any(not name.startswith(b"src/") for name in changed):
        record["candidate"] = False
        record["patch_withheld"] = "non_source_changes"
        return False
    patch = git("diff", "--cached", "--no-ext-diff", "--text", "HEAD")
    patch.decode("utf-8")
    if b"\0" in patch or len(patch) > 262144 or any(token in patch for token in (
        key.encode(), base64.b64encode(key.encode()), *SECRET_PREFIXES,
    )):
        raise ValueError("patch withheld")
    record["candidate"] = bool(changed)
    if changed:
        (evidence / "result.patch").write_bytes(patch)
    record["phase"] = "public_checks"
    checks_ok = public_checks(work, record)
    record["task_and_public_checks_seconds"] = round(time.monotonic() - task_start, 2)
    return clean and bool(changed) and checks_ok


if __name__ == "__main__":
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    evidence = temp / "evidence"
    evidence.mkdir(exist_ok=True)
    provider = os.environ["PILOT_PROVIDER"]
    mode = os.environ["PILOT_MODE"]
    start = time.monotonic()
    record = {
        "source_revision": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "fixture_revision": FIXTURE_REVISION,
        "task": TASK_ID, "mode": mode, "agent": "Codex CLI 0.172.0", "binary_sha256": CLI_DIGEST,
        "requested_model": PROVIDERS[provider][1], "provider": provider, "reported_model": None,
        "human_interventions": 0, "actual_cost": None, "phase": "setup", "passed": False,
    }
    try:
        key = os.environ.pop("PILOT_API_KEY", "")
        if not key or mode not in {"probe", "score"}:
            raise ValueError("missing selected credential or invalid mode")
        record["passed"] = execute(temp, evidence, key, record)
        record["phase"] = "complete"
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        record["harness_error"] = type(error).__name__
    finally:
        record["duration_seconds"] = round(time.monotonic() - start, 2)
        (evidence / "run.json").write_text(json.dumps(record, indent=2))
    raise SystemExit(0 if record["passed"] else 1)
