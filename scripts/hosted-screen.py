"""Run one unattended agent against the same generated read/edit/test fixture."""
import hashlib
import base64
import difflib
import http.client
import json
import os
import re
import runpy
import secrets
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "root_cause.relay_request_correlation_001"
TASKS = {
    "root_cause.relay_request_correlation_001": "root_cause/relay_request_correlation_001",
    "feature.minimal_report_format_001": "feature/minimal_report_format_001",
    "review.unsigned_observer_token_001": "review/unsigned_observer_token_001",
    "recovery.stale_handover_001": "recovery/stale_handover_001",
    "root_cause.incremental_catalog_refresh_001": "root_cause/incremental_catalog_refresh_001",
    "diagnostics.ci_failure_investigation_001": "diagnostics/ci_failure_investigation_001",
    "refactor.backwards_compatible_api_001": "refactor/backwards_compatible_api_001",
    "security.auth_boundary_repair_001": "security/auth_boundary_repair_001",
    "performance.incremental_regression_001": "performance/incremental_regression_001",
}
FIXTURE_REVISION = "c7f87d835c0d7110118bd0e31655e6a223f2d735"
FIXTURE_REVISIONS = {
    "root_cause.incremental_catalog_refresh_001": "ef7ba31d3f0117bdba3375d4be29afb11f5b98b2",
    "diagnostics.ci_failure_investigation_001": "405aa5d0d2552834980a01f147a8ef792994ee26",
    "refactor.backwards_compatible_api_001": "405aa5d0d2552834980a01f147a8ef792994ee26",
    "security.auth_boundary_repair_001": "405aa5d0d2552834980a01f147a8ef792994ee26",
    "performance.incremental_regression_001": "405aa5d0d2552834980a01f147a8ef792994ee26",
}
# Fixed free-prototype profiles. Never accept a model ID supplied by an agent.
MODEL_PROFILES = {
    "super": {
        "NVIDIA": ("integrate.api.nvidia.com", "/v1/chat/completions",
                   "nvidia/nemotron-3.5-super-vl-120b-a12b"),
        "OpenRouter": ("openrouter.ai", "/api/v1/chat/completions",
                       "nvidia/nemotron-3.5-super-vl:free"),
    },
    "lightning": {
        "NVIDIA": ("integrate.api.nvidia.com", "/v1/chat/completions",
                   "nvidia/nemotron-3.5-lightning-30b-a3b"),
    },
}
PROFILE = os.environ.get("PILOT_MODEL_PROFILE", "super")
if PROFILE not in MODEL_PROFILES:
    raise ValueError("unsupported fixed model profile")
ROUTES = MODEL_PROFILES[PROFILE]
VERSIONS = {
    "qwen": "0.28.6", "goose": "1.61.1", "pi": "1.6.1", "aider": "0.86.2",
    "cline": "3.0.76", "continue": "1.5.47", "claude": "2.1.332",
    "opencode": "2.4.2", "codex": "0.172.0", "copilot": "1.0.116", "mini": "2.4.6",
}
PROMPT = (
    "Read input.txt for a generated identifier. Edit only answer.txt, replacing its "
    "placeholder with the exact identifier on one line. Then run probe-check in the "
    "working directory and finish after it succeeds. Do not edit the input or test."
)
CHECK = """#!/usr/bin/python3
from pathlib import Path
import hashlib

identifier = Path("input.txt").read_bytes()
if Path("answer.txt").read_bytes() != identifier:
    raise SystemExit("answer does not match input")
marker = "SCREEN_TEST_PASS " + hashlib.sha256(identifier).hexdigest()
Path("/test-evidence/result").write_text(marker)
print(marker)
"""
BASE_URL = "http://127.0.0.1:8017"
SAFE_MODEL = re.compile(r"[a-zA-Z0-9._:/-]{1,160}")


class ProviderRelay(socketserver.UnixStreamServer):
    """Expose only the selected Chat Completions route via a mounted socket."""

    def __init__(self, path, provider, key):
        self.host, self.endpoint, self.model = ROUTES[provider]
        self.key = key
        self.statuses = []
        self.models = set()
        self.usage = []
        super().__init__(str(path), ProviderRequest)

    def observe(self, body):
        try:
            event = json.loads(body)
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        model = event.get("model")
        if isinstance(model, str) and SAFE_MODEL.fullmatch(model):
            self.models.add(model)
        usage = event.get("usage")
        if isinstance(usage, dict):
            counts = {field: usage[field] for field in ("prompt_tokens", "completion_tokens", "total_tokens")
                      if type(usage.get(field)) is int and 0 <= usage[field] < 10**9}
            if counts:
                self.usage.append(counts)


class ProviderRequest(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        if len(self.server.statuses) >= 16:
            self.send_error(429)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                raise ValueError
            body = json.loads(self.rfile.read(length))
            if (not isinstance(body, dict) or body.get("model") != self.server.model
                    or {"models", "route", "provider"}.intersection(body)):
                raise ValueError
        except ValueError:
            self.send_error(400)
            return

        connection = http.client.HTTPSConnection(self.server.host, timeout=35)
        self.server.statuses.append(None)
        try:
            connection.request("POST", self.server.endpoint, json.dumps(body), {
                "Content-Type": "application/json", "Authorization": "Bearer " + self.server.key,
            })
            response = connection.getresponse()
            self.server.statuses[-1] = response.status
            content_type = response.getheader("Content-Type", "")
            self.send_response(response.status)
            self.send_header("Content-Type", content_type)
            retry_after = response.getheader("Retry-After")
            if retry_after and retry_after.isdecimal():
                self.send_header("Retry-After", retry_after)
            self.end_headers()
            if "text/event-stream" in content_type:
                for line in iter(response.readline, b""):
                    if line.startswith(b"data:"):
                        self.server.observe(line[5:])
                    self.wfile.write(line)
                    self.wfile.flush()
            else:
                payload = response.read(2 * 1024 * 1024)
                self.server.observe(payload)
                self.wfile.write(payload)
        except OSError:
            # The recorded null status identifies a connection-level failure.
            self.close_connection = True
        finally:
            connection.close()


def configure(agent, model, settings, prompt, task):
    env = {"PATH": "/cli/bin:/usr/bin:/bin", "HOME": "/tmp/home",
           "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1",
           "OPENAI_API_KEY": "local-relay", "OPENAI_BASE_URL": BASE_URL + "/v1",
           "BENCHMARK_AGENT": agent, "BENCHMARK_MODEL": model}
    if agent == "qwen":
        env["QWEN_CODE_DISABLE_TELEMETRY"] = "1"
        command = ["qwen", "--auth-type", "openai", "--model", model,
                   "--approval-mode", "yolo", "--output-format", "stream-json", "-p", prompt]
    elif agent == "goose":
        env.update(OPENAI_HOST=BASE_URL, OPENAI_BASE_PATH="v1/chat/completions",
                   GOOSE_PROVIDER="openai", GOOSE_MODEL=model, GOOSE_MODE="auto", GOOSE_MAX_TURNS="16",
                   GOOSE_DISABLE_KEYRING="1", GOOSE_TELEMETRY_ENABLED="false")
        command = ["goose", "run", "--no-session", "--with-builtin", "developer",
                   "--output-format", "stream-json", "--text", prompt]
    elif agent == "pi":
        env.update(PI_CODING_AGENT_DIR="/tmp/home/pi", PI_TELEMETRY="0")
        (settings / "pi").mkdir()
        (settings / "pi/models.json").write_text(json.dumps({"providers": {"screen": {
            "baseUrl": BASE_URL + "/v1", "api": "openai-completions", "apiKey": "OPENAI_API_KEY",
            "models": [{"id": model, "input": ["text"], "reasoning": False}],
        }}}))
        command = ["pi", "--provider", "screen", "--model", model, "--no-session",
                   "--mode", "json", "--tools", "read,bash,edit,write", "--no-extensions", "-p", prompt]
    elif agent == "cline":
        command = ["cline", "--json", "--provider", "openai", "--model", model, prompt]
    elif agent == "continue":
        config = {
            "name": "Hosted benchmark", "version": "1.0.0", "schema": "v1",
            "models": [{"name": "Nemotron", "provider": "openai", "model": model,
                        "apiBase": BASE_URL + "/v1", "apiKey": "local-relay",
                        "capabilities": ["tool_use"]}],
        }
        (settings / "continue.yaml").write_text(json.dumps(config))
        command = ["cn", "--config", "/settings/continue.yaml", "--auto", "--format", "json", "-p", prompt]
    elif agent == "claude":
        env.update(
            ANTHROPIC_MODEL=model, ANTHROPIC_DEFAULT_HAIKU_MODEL=model,
            ANTHROPIC_DEFAULT_SONNET_MODEL=model, ANTHROPIC_DEFAULT_OPUS_MODEL=model,
            CLAUDE_CODE_SUBAGENT_MODEL=model, CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
            CLAUDE_CODE_MAX_OUTPUT_TOKENS="8192",
        )
        command = ["claude", "--bare", "--model", model, "--permission-mode", "bypassPermissions",
                   "--strict-mcp-config", "--tools", "Read,Write,Edit,Glob,Grep,Bash",
                   "--verbose", "--output-format", "stream-json", "-p", prompt]
    elif agent == "copilot":
        env.update(
            COPILOT_OFFLINE="true", COPILOT_PROVIDER_TYPE="openai",
            COPILOT_PROVIDER_BASE_URL=BASE_URL + "/v1", COPILOT_PROVIDER_API_KEY="local-relay",
            COPILOT_PROVIDER_WIRE_API="completions", COPILOT_MODEL=model,
        )
        command = ["copilot", "--no-auto-update", "--disable-builtin-mcps",
                   "--disable-mcp-server", "computer-use", "--no-ask-user",
                   "--allow-all-tools", "--output-format", "json", "-p", prompt]
    elif agent == "mini":
        env.update(MSWEA_CONFIGURED="1", MSWEA_SILENT_STARTUP="1",
                   MSWEA_COST_TRACKING="ignore_errors", LITELLM_LOCAL_MODEL_COST_MAP="True")
        config = {"agent": {"step_limit": 16},
                  "model": {"model_kwargs": {"api_base": BASE_URL + "/v1", "num_retries": 0}}}
        (settings / "mini.yaml").write_text(json.dumps(config))
        command = ["/cli/mini/bin/python", "-m", "minisweagent.run.mini", "-m", "openai/" + model,
                   "-c", "mini.yaml", "-c", "/settings/mini.yaml", "-y", "--exit-immediately",
                   "-o", "/tmp/mini-trajectory.json", "-t", prompt]
    elif agent == "opencode":
        env.update(
            OPENCODE_DISABLE_MODELS_FETCH="true", OPENCODE_DISABLE_AUTOUPDATE="true",
            OPENCODE_CONFIG_CONTENT=json.dumps({
                "model": "pilot/" + model, "small_model": "pilot/" + model,
                "agent": {"build": {"steps": 16}}, "enabled_providers": ["pilot"],
                "share": "disabled",
                "permission": {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow",
                               "edit": "allow", "bash": "allow", "external_directory": "deny"},
                "provider": {"pilot": {"npm": "@ai-sdk/openai-compatible", "name": "Benchmark",
                                      "options": {"baseURL": BASE_URL + "/v1", "apiKey": "local-relay"},
                                      "models": {model: {"name": "Nemotron"}}}},
            }),
        )
        command = ["opencode", "run", "--standalone", "--format", "json", "--model", "pilot/" + model, prompt]
    elif agent == "codex":
        # The outer namespace already restricts files, credentials and network.
        env["CODEX_HOME"] = "/tmp/home/.codex"
        command = ["codex", "-a", "never", "exec", "--json", "--ephemeral",
                   "--skip-git-repo-check", "--sandbox", "danger-full-access",
                   "--disable", "multi_agent", "--model", model, prompt]
    else:
        env["OPENAI_API_BASE"] = BASE_URL + "/v1"
        command = ["/cli/aider/bin/python", "-m", "aider", "--model", "openai/" + model,
                   "--no-git", "--no-auto-lint", "--no-check-update", "--no-show-model-warnings",
                   "--analytics-disable", "--yes-always", "--edit-format", "whole",
                   "--input-history-file", "/tmp/input-history",
                   "--chat-history-file", "/tmp/chat-history",
                   "--auto-test", "--test-cmd", "probe-check", "--message", prompt]
        if task:
            starter = task / "repo_before"
            for path in sorted(starter.rglob("*")):
                if path.is_file():
                    relative = str(path.relative_to(starter))
                    if relative.startswith("src/"):
                        command.append(relative)
                    else:
                        command.extend(["--read", relative])
            for path in sorted((task / "visible_tests").glob("test_*.py")):
                command.extend(["--read", "visible_tests/" + path.name])
        else:
            command.extend(["--read", "input.txt", "answer.txt"])
    return env, command


def sandbox(work, cli, settings, *mounts):
    return [
        "bwrap", "--die-with-parent", "--unshare-all",
        "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
        "--ro-bind", "/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-certificates.crt",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--dir", "/tmp/home",
        "--ro-bind", str(cli), "/cli", "--ro-bind", str(settings), "/settings",
        "--bind", str(work), "/task", *mounts, "--chdir", "/task",
    ]


def run_fixture(root, cli, agent, provider, key, evidence, record):
    work = root / "task"
    work.mkdir()
    settings = root / "settings"
    settings.mkdir()
    baseline = b"pending\n"
    identifier = (secrets.token_hex(12) + "\n").encode()
    (work / "input.txt").write_bytes(identifier)
    (work / "answer.txt").write_bytes(baseline)
    (settings / "probe-check").write_text(CHECK)
    (settings / "probe-check").chmod(0o755)
    proof = root / "test-evidence"
    proof.mkdir()
    env, output = run_agent(root, work, settings, cli, agent, provider, key, record, PROMPT, None,
                            "--bind", str(proof), "/test-evidence")
    marker = b"SCREEN_TEST_PASS " + hashlib.sha256(identifier).hexdigest().encode()
    receipt = proof / "result"
    record["agent_test_trace"] = (receipt.is_file() and not receipt.is_symlink()
                                  and receipt.stat().st_size == len(marker)
                                  and receipt.read_bytes() == marker) or marker in output
    answer = work / "answer.txt"
    source = work / "input.txt"
    in_scope = (sorted(p.name for p in work.iterdir()) == ["answer.txt", "input.txt"]
                and all(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1
                        and p.stat().st_size < 1024 for p in (source, answer))
                and source.read_bytes() == identifier)
    record["in_scope"] = in_scope
    record["patch_correct"] = in_scope and answer.read_bytes() == identifier
    if record["patch_correct"]:
        replay = subprocess.run(sandbox(work, cli, settings, "--bind", str(proof), "/test-evidence")
                                + ["/settings/probe-check"], env=env, capture_output=True, timeout=10)
        record["independent_test_exit"] = replay.returncode
        (evidence / "result.patch").write_text("".join(difflib.unified_diff(
            baseline.decode().splitlines(keepends=True),
            identifier.decode().splitlines(keepends=True), "a/answer.txt", "b/answer.txt")))
    return (record["clean_exit"] and record["patch_correct"] and record["agent_test_trace"]
            and record.get("independent_test_exit") == 0)


def run_agent(root, work, settings, cli, agent, provider, key, record, prompt, task, *mounts):
    env, command = configure(agent, ROUTES[provider][2], settings, prompt, task)
    shutil.copyfile(ROOT / "scripts/screen-launch.sh", settings / "launch.sh")
    if agent in {"claude", "codex"}:
        shutil.copyfile(ROOT / "scripts/screen-protocol-bridge.py", settings / "start-bridge.py")
    env["PATH"] = "/settings:" + env["PATH"]
    if task:
        env["PYTHONPATH"] = "/task/src"
    socket = root / "upstream"
    with ProviderRelay(socket, provider, key) as relay:
        thread = threading.Thread(target=relay.serve_forever, daemon=True)
        thread.start()
        start = time.monotonic()
        try:
            args = sandbox(work, cli, settings, "--ro-bind", str(socket), "/upstream", *mounts)
            args.extend(["/bin/sh", "/settings/launch.sh", *command])
            try:
                result = subprocess.run(args, env=env, stdin=subprocess.DEVNULL,
                                        capture_output=True, timeout=600 if task else 90)
                exit_code, output = result.returncode, result.stdout + result.stderr
            except subprocess.TimeoutExpired as error:
                exit_code, output = 124, (error.stdout or b"") + (error.stderr or b"")
            record["agent_exit"] = exit_code
            record["agent_duration_seconds"] = round(time.monotonic() - start, 2)
        finally:
            relay.shutdown()
            thread.join()
        record["provider_statuses"] = relay.statuses
        record["upstream_requests"] = len(relay.statuses)
        record["reported_models"] = sorted(relay.models)
        record["usage_by_request"] = relay.usage or None

    record["agent_error"] = next((label for label, pattern in {
        "unknown_option": rb"unknown (argument|option)|unexpected argument",
        "model_configuration": rb"no models available|model not found|unknown model",
        "sandbox_setup": rb"bwrap:|socat.*E ",
        "cli_missing": rb"not found|No such file or directory",
    }.items() if not record["upstream_requests"] and re.search(pattern, output, re.I)), None)
    record["clean_exit"] = (exit_code == 0 and bool(record["provider_statuses"])
                            and record["provider_statuses"][-1] == 200)
    return env, output


def run_score(root, cli, agent, provider, key, evidence, record):
    started = time.monotonic()
    work = root / "task"
    settings = root / "settings"
    task = ROOT / "tasks/engineering" / TASKS[record["task"]]
    shutil.copytree(task / "repo_before", work)
    shutil.copytree(task / "visible_tests", work / "visible_tests")
    settings.mkdir()
    shutil.copyfile(ROOT / "scripts/visible.py", settings / "visible.py")
    check = settings / "probe-check"
    check.write_text(
        '#!/bin/sh\nset -e\npython3 -m unittest discover -s tests\n'
        'python3 /settings/visible.py\n'
    )
    check.chmod(0o755)

    baseline = root / "baseline.git"
    subprocess.run(["git", "init", "-q", "--bare", str(baseline)], check=True)

    def git(*args):
        return subprocess.check_output(
            ["git", "--git-dir", baseline, "--work-tree", work, *args],
            cwd=work, stderr=subprocess.DEVNULL,
        )

    git("add", "-f", ".")
    git("-c", "user.name=pilot", "-c", "user.email=pilot@localhost", "commit", "-qm", "fixture")
    prompt = (task / "instruction.md").read_text()
    run_agent(root, work, settings, cli, agent, provider, key, record, prompt, task)

    # Keep Python compilation artefacts out of candidate patches. The agent has no Git index.
    git("clean", "-f", "-x", "--", ":(glob)**/__pycache__/*.pyc")
    entries = list(work.rglob("*"))
    if any(p.is_symlink() or ".git" in p.relative_to(work).parts or
           (not p.is_dir() and (not p.is_file() or p.stat().st_nlink != 1 or
                                p.stat().st_size > 262144)) for p in entries):
        record["patch_withheld"] = "unsafe_workspace_entry"
        return False
    git("add", "-f", ".")
    changed = git("diff", "--cached", "--name-only", "-z", "HEAD").split(b"\0")[:-1]
    record["candidate"] = bool(changed)
    record["registry_only"] = changed == [b"src/relay/registry.py"]
    if any(not path.startswith(b"src/") for path in changed):
        record["patch_withheld"] = "non_source_changes"
        return False
    patch = git("diff", "--cached", "--no-ext-diff", "--text", "HEAD")
    try:
        patch.decode("utf-8")
    except UnicodeDecodeError:
        record["patch_withheld"] = "non_utf8_patch"
        return False
    if b"\0" in patch or len(patch) > 262144 or any(marker in patch for marker in (
        key.encode(), base64.b64encode(key.encode()), b"nvapi-", b"sk-or-", b"github_pat_",
    )):
        record["patch_withheld"] = "output_validation"
        return False
    if changed:
        (evidence / "result.patch").write_bytes(patch)
    public_checks = runpy.run_path(str(ROOT / "scripts/hosted-codex.py"))["public_checks"]
    checks_ok = public_checks(work, record)
    record["task_and_public_checks_seconds"] = round(time.monotonic() - started, 2)
    return record["clean_exit"] and bool(changed) and checks_ok


def main():
    temp = Path(os.environ["RUNNER_TEMP"])
    evidence = temp / "evidence"
    evidence.mkdir(exist_ok=True)
    agent, provider = os.environ["SCREEN_AGENT"], os.environ["PILOT_PROVIDER"]
    score = os.environ.get("SCREEN_PHASE") == "score"
    key = os.environ.pop("PILOT_API_KEY", "")
    selected_route = ROUTES.get(provider)
    record = {
        "agent": agent, "version": VERSIONS[agent], "provider": provider,
        "model_profile": PROFILE,
        "endpoint": "https://" + "".join(selected_route[:2]) if selected_route else None,
        "requested_model": selected_route[2] if selected_route else None,
        "adapter": "fixed-route Chat Completions relay",
        "run_id": os.environ["GITHUB_RUN_ID"], "source_revision": os.environ["GITHUB_SHA"],
        "retries": None, "actual_cost": None, "passed": False,
        "human_interventions": 0, "tool_calls": None,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "mode": "score" if score else "probe",
    }
    if agent in {"claude", "codex"}:
        record["adapter"] = ("SkillEvaluator Messages-to-Chat-Completions + fixed relay" if agent == "claude"
                             else "SkillEvaluator Responses-to-Chat-Completions + fixed relay")
    try:
        if selected_route is None:
            raise ValueError("unsupported model/provider combination")
        if not key:
            raise ValueError("missing selected credential")
        if score:
            if provider != "NVIDIA":
                raise ValueError("scored comparison uses NVIDIA")
            task_id = os.environ.get("SCREEN_TASK") or TASK_ID
            if task_id not in TASKS:
                raise ValueError("unknown scored fixture")
            record.update(task=task_id, fixture_revision=FIXTURE_REVISIONS.get(task_id, FIXTURE_REVISION))
        run = run_score if score else run_fixture
        with tempfile.TemporaryDirectory(prefix="screen-", dir=temp) as directory:
            record["passed"] = run(Path(directory), temp / "cli", agent, provider,
                                   key, evidence, record)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record["harness_error"] = type(error).__name__
    finally:
        (evidence / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
