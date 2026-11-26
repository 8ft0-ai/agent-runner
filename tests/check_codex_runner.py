"""Exercise the pinned Codex binary and real sandbox on Ubuntu without provider calls."""
import importlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("hosted-codex")
MODEL = "openai/gpt-oss-120b"
SENTINEL = "offline-provider-credential"
NONCE = "local-fixture-content\n"


class ResponsesHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == "/v1/responses"
        assert self.headers["Authorization"] == "Bearer " + SENTINEL
        assert request["model"] == MODEL and request["stream"] is True

        outputs = [item["output"] for item in request["input"]
                   if item["type"] == "function_call_output"]
        if not outputs:
            # The shell must be unable to inherit or read the inference credential,
            # and it must be unable to reach the mock inferencer over loopback.
            port = self.server.server_port
            credential_path = "/proc/[0-9]*/environ"
            command = (
                'test -z "${PILOT_API_KEY:-}" && '
                f'! grep -asq {SENTINEL} {credential_path} && '
                f'! curl -s --max-time 1 http://127.0.0.1:{port}/ && cat input.txt'
            )
            output = tool_call(1, command)
        elif len(outputs) == 1:
            assert NONCE.strip() in outputs[0], "Read, credential isolation or network isolation failed"
            output = tool_call(2, "cp input.txt output.txt")
        else:
            output = {"type": "message", "id": "msg_1", "role": "assistant",
                      "content": [{"type": "output_text", "text": "Done"}]}

        response = {"id": f"resp_{len(outputs)}"}
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for kind, data in [
            ("response.created", {"response": response}),
            ("response.output_item.done", {"item": output}),
            ("response.completed", {"response": {
                **response, "output": [output],
                "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
            }}),
        ]:
            self.wfile.write(f"event: {kind}\ndata: {json.dumps(dict(type=kind, **data))}\n\n".encode())

    def log_message(self, *args):
        pass


def tool_call(index, command):
    return {"type": "function_call", "id": f"fc_{index}", "call_id": f"call_{index}",
            "name": "exec_command", "arguments": json.dumps({"cmd": command})}


def main():
    cli = Path(os.environ["RUNNER_TEMP"]) / "codex" / runner.CLI_NAME
    with ThreadingHTTPServer(("127.0.0.1", 0), ResponsesHandler) as api, TemporaryDirectory() as temp:
        thread = Thread(target=api.serve_forever, daemon=True)
        thread.start()
        work = Path(temp)
        (work / "input.txt").write_text(NONCE)
        record = {}
        try:
            tools, _ = runner.run_codex(cli, work, f"http://127.0.0.1:{api.server_port}/v1",
                                        MODEL, SENTINEL, runner.PROBE_PROMPT, 30, record)
        finally:
            api.shutdown()
            thread.join()
        assert record["agent_exit"] == 0, record
        assert (work / "output.txt").read_text() == NONCE
        assert "edit" in tools and record["usage_by_step"]


if __name__ == "__main__":
    main()
