"""Run one unattended agent against the same generated read/edit/test fixture."""
import hashlib
import difflib
import http.client
import json
import os
import re
import secrets
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROUTES = {
    "NVIDIA": ("integrate.api.nvidia.com", "/v1/chat/completions",
               "nvidia/nemotron-3.5-super-vl-120b-a12b"),
    "OpenRouter": ("openrouter.ai", "/api/v1/chat/completions",
                   "nvidia/nemotron-3.5-super-vl:free"),
}
VERSIONS = {"qwen": "0.28.6", "goose": "1.61.1", "pi": "1.6.1", "aider": "0.86.2"}
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
print("SCREEN_TEST_PASS " + hashlib.sha256(identifier).hexdigest())
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


def configure(agent, model, settings):
    env = {"PATH": "/cli/bin:/usr/bin:/bin", "HOME": "/tmp/home",
           "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1",
           "OPENAI_API_KEY": "local-relay", "OPENAI_BASE_URL": BASE_URL + "/v1"}
    if agent == "qwen":
        env["QWEN_CODE_DISABLE_TELEMETRY"] = "1"
        command = ["qwen", "--auth-type", "openai", "--model", model,
                   "--approval-mode", "yolo", "--output-format", "stream-json", "-p", PROMPT]
    elif agent == "goose":
        env.update(OPENAI_HOST=BASE_URL, OPENAI_BASE_PATH="v1/chat/completions",
                   GOOSE_PROVIDER="openai", GOOSE_MODEL=model, GOOSE_MODE="auto", GOOSE_MAX_TURNS="16",
                   GOOSE_DISABLE_KEYRING="1", GOOSE_TELEMETRY_ENABLED="false")
        command = ["goose", "run", "--no-session", "--with-builtin", "developer",
                   "--output-format", "stream-json", "--text", PROMPT]
    elif agent == "pi":
        env.update(PI_CODING_AGENT_DIR="/tmp/home/pi", PI_TELEMETRY="0")
        (settings / "pi").mkdir()
        (settings / "pi/models.json").write_text(json.dumps({"providers": {"screen": {
            "baseUrl": BASE_URL + "/v1", "api": "openai-completions", "apiKey": "OPENAI_API_KEY",
            "models": [{"id": model, "input": ["text"], "reasoning": False}],
        }}}))
        command = ["pi", "--provider", "screen", "--model", model, "--no-session",
                   "--mode", "json", "--tools", "read,bash,edit,write", "--no-extensions", "-p", PROMPT]
    else:
        env["OPENAI_API_BASE"] = BASE_URL + "/v1"
        command = ["/cli/aider/bin/python", "-m", "aider", "--model", "openai/" + model,
                   "--no-git", "--no-auto-lint", "--no-check-update", "--no-show-model-warnings",
                   "--analytics-disable", "--yes-always", "--edit-format", "whole",
                   "--input-history-file", "/tmp/input-history",
                   "--chat-history-file", "/tmp/chat-history",
                   "--auto-test", "--test-cmd", "probe-check", "--read", "input.txt",
                   "--message", PROMPT, "answer.txt"]
    return env, command


def sandbox(work, cli, settings, *mounts):
    return [
        "bwrap", "--die-with-parent", "--unshare-all",
        "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
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
    env, command = configure(agent, ROUTES[provider][2], settings)
    env["PATH"] = "/settings:" + env["PATH"]
    socket = root / "upstream"
    with ProviderRelay(socket, provider, key) as relay:
        thread = threading.Thread(target=relay.serve_forever, daemon=True)
        thread.start()
        start = time.monotonic()
        try:
            args = sandbox(work, cli, settings, "--ro-bind", str(socket), "/upstream")
            args.extend(["/bin/sh", "-c",
                         'if [ -d /settings/pi ]; then cp -r /settings/pi "$HOME/pi"; fi; '
                         'socat TCP-LISTEN:8017,bind=127.0.0.1,reuseaddr,fork UNIX-CONNECT:/upstream & '
                         'exec "$@"', "screen", *command])
            try:
                result = subprocess.run(args, env=env, stdin=subprocess.DEVNULL,
                                        capture_output=True, timeout=90)
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

    marker = b"SCREEN_TEST_PASS " + hashlib.sha256(identifier).hexdigest().encode()
    record["agent_test_trace"] = marker in output
    record["agent_error"] = next((label for label, pattern in {
        "unknown_option": rb"unknown (argument|option)|unexpected argument",
        "model_configuration": rb"no models available|model not found|unknown model",
        "sandbox_setup": rb"bwrap:|socat.*E ",
        "cli_missing": rb"not found|No such file or directory",
    }.items() if not record["upstream_requests"] and re.search(pattern, output, re.I)), None)
    record["clean_exit"] = (exit_code == 0 and bool(record["provider_statuses"])
                            and record["provider_statuses"][-1] == 200)
    answer = work / "answer.txt"
    source = work / "input.txt"
    in_scope = (sorted(p.name for p in work.iterdir()) == ["answer.txt", "input.txt"]
                and all(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1
                        and p.stat().st_size < 1024 for p in (source, answer))
                and source.read_bytes() == identifier)
    record["in_scope"] = in_scope
    record["patch_correct"] = in_scope and answer.read_bytes() == identifier
    if record["patch_correct"]:
        # Replay the harness-owned test in a new network-isolated namespace.
        replay = subprocess.run(sandbox(work, cli, settings) + ["/settings/probe-check"],
                                env=env, capture_output=True, timeout=10)
        record["independent_test_exit"] = replay.returncode
        (evidence / "result.patch").write_text("".join(difflib.unified_diff(
            baseline.decode().splitlines(keepends=True),
            identifier.decode().splitlines(keepends=True), "a/answer.txt", "b/answer.txt")))
    return (record["clean_exit"] and record["patch_correct"] and record["agent_test_trace"]
            and record.get("independent_test_exit") == 0)


def main():
    temp = Path(os.environ["RUNNER_TEMP"])
    evidence = temp / "evidence"
    evidence.mkdir(exist_ok=True)
    agent, provider = os.environ["SCREEN_AGENT"], os.environ["PILOT_PROVIDER"]
    key = os.environ.pop("PILOT_API_KEY", "")
    record = {
        "agent": agent, "version": VERSIONS[agent], "provider": provider,
        "endpoint": "https://" + "".join(ROUTES[provider][:2]),
        "requested_model": ROUTES[provider][2], "adapter": "fixed-route Chat Completions relay",
        "run_id": os.environ["GITHUB_RUN_ID"], "source_revision": os.environ["GITHUB_SHA"],
        "retries": None, "actual_cost": None, "passed": False,
    }
    try:
        if not key:
            raise ValueError("missing selected credential")
        with tempfile.TemporaryDirectory(prefix="screen-", dir=temp) as directory:
            record["passed"] = run_fixture(Path(directory), temp / "cli", agent, provider,
                                           key, evidence, record)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record["harness_error"] = type(error).__name__
    finally:
        (evidence / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
