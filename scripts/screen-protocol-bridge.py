"""Expose SkillEvaluator's pinned translations to the existing fixed-route relay."""
import http.client
import os
from pathlib import Path
import sys
import threading

sys.path.insert(0, "/cli")
import nvidia_build_bridge


def chat(_endpoint, body):
    # This namespace can reach only the trial's existing loopback relay.
    connection = http.client.HTTPConnection("127.0.0.1", 8017, timeout=50)
    try:
        connection.request("POST", "/v1/chat/completions", body,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise nvidia_build_bridge._BackendError("upstream_http_error", response.status)
        return response.read(1_000_001)
    finally:
        connection.close()


if __name__ == "__main__":
    bridge = nvidia_build_bridge.start_in_process_bridge(
        api_key="test-local-relay",
        build_base_url="http://127.0.0.1:8017/v1",
        log_path=Path("/tmp/bridge.log"),
        request_transport=chat,
        allowed_model=os.environ["BENCHMARK_MODEL"],
    )
    path = Path("/tmp/bridge.env")
    pending = path.with_suffix(".tmp")
    pending.write_text(
        f'BRIDGE_URL={bridge.origin}\nBRIDGE_TOKEN={bridge.client_token}\n'
    )
    pending.replace(path)
    threading.Event().wait()
