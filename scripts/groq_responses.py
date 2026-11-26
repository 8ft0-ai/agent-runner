"""Keep Groq on native Responses while requesting sequential tool calls."""
import hmac
import http.client
import json
import secrets
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

MODEL = "openai/gpt-oss-120b"
FIELDS = ("parallel_tool_calls", "reasoning.encrypted_content", "prompt_cache_key",
          "client_metadata", "reasoning.summary", "function_call_output")


@contextmanager
def sequential_groq(key, evidence):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth.encode(), f"Bearer {token}".encode()):
                self.send_error(403)
                return
            if self.path != "/v1/responses":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4_194_304:
                    raise ValueError
                request = json.loads(self.rfile.read(size))
                if not isinstance(request, dict) or request.get("model") != MODEL:
                    raise ValueError
            except ValueError:
                self.send_error(400)
                return
            request["parallel_tool_calls"] = False
            entry = {}
            evidence.append(entry)
            connection = http.client.HTTPSConnection("api.groq.com", timeout=38)
            try:
                connection.request("POST", "/openai/v1/responses", json.dumps(request), {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                })
                result = connection.getresponse()
                entry["http_status"] = result.status
                if result.status >= 400:
                    body = result.read(16_384)
                    entry["mentioned_fields"] = [field for field in FIELDS if field.encode() in body]
                    retry_after = result.getheader("Retry-After", "")
                    if retry_after.isascii() and retry_after.isdecimal() and len(retry_after) <= 6:
                        entry["retry_after_seconds"] = int(retry_after)
                    self.send_response(result.status)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":{"message":"Groq rejected the request"}}')
                    return
                self.send_response(result.status)
                self.send_header("Content-Type", result.getheader("Content-Type", "application/json"))
                self.end_headers()
                while chunk := result.read1(65536):
                    self.wfile.write(chunk)
            except (OSError, http.client.HTTPException) as error:
                entry["transport_error"] = type(error).__name__
                if "http_status" not in entry:
                    self.send_error(502)
            finally:
                connection.close()

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", token
        finally:
            server.shutdown()
            worker.join()
