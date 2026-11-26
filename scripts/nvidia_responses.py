"""Run the pinned SkillEvaluator bridge with the documented experimental alias."""
import importlib.util
import secrets
import sys
from contextlib import contextmanager
from threading import Thread

MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
ALIAS = "private/nvidia/nemotron-3.5-super-120b-a12b"
BASE_URL = "https://integrate.api.nvidia.com/v1"
TOKEN_LIMIT = 8192


@contextmanager
def nvidia_bridge(temp, key, record):
    path = temp / "codex/nvidia_build_bridge.py"
    spec = importlib.util.spec_from_file_location("pinned_nvidia_bridge", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    request_build = module._request_build
    responses = []
    record["nvidia_upstream"] = responses
    record["transport"] = "SkillEvaluator Responses-to-NVIDIA Build Chat Completions"
    record["max_upstream_requests"] = 6 if record["mode"] == "probe" else 16

    def record_model(config, payload):
        if payload.get("model") != MODEL or not 0 < payload.get("max_tokens", 0) <= TOKEN_LIMIT:
            raise module._BackendError("request_disallowed")
        entry = {}
        responses.append(entry)
        try:
            response = request_build(config, payload)
        except module._BackendError as error:
            status = getattr(error.__cause__, "code", None)
            if type(status) is int and 100 <= status <= 599:
                entry["http_status"] = status
            raise
        actual = response.get("model")
        if actual not in (MODEL, ALIAS):
            entry["model_match"] = "unexpected"
            raise module._BackendError("response_model_mismatch")
        entry["model"] = actual
        seen = {item["model"] for item in responses if "model" in item}
        record["reported_model"] = actual if len(seen) == 1 else None
        record["experimental_alias_applied"] = ALIAS in seen
        record["served_checkpoint_verified"] = False
        return {**response, "model": MODEL}

    module._request_build = record_model
    token = secrets.token_urlsafe(32)
    config = module.BridgeConfig(
        api_key=key, build_base_url=BASE_URL, host="127.0.0.1", port=0,
        log_path=temp / "nvidia-bridge.log", readiness_token=secrets.token_urlsafe(32),
        client_token=token, allowed_model=MODEL, max_requests=record["max_upstream_requests"],
        max_output_tokens=TOKEN_LIMIT,
    )
    server = module._create_bridge_server(config)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", token
    finally:
        server.shutdown()
        server.close_active_requests()
        server.server_close()
        worker.join(timeout=5)
