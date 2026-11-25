import json

from briefing.cli import run


def test_json_option_is_recognised():
    payload = json.loads(run(["--format", "json"]))
    assert isinstance(payload, dict)


def test_json_services_have_exact_current_records():
    payload = json.loads(run(["--format", "json"]))
    assert payload["services"] == [
        {"service": "observer", "status": "ok", "latency_ms": 32},
        {"service": "relay", "status": "degraded", "latency_ms": 90},
    ]


def test_json_has_version_one_schema():
    payload = json.loads(run(["--format", "json"]))
    assert payload["schema_version"] == 1


def test_json_preserves_integer_latency():
    payload = json.loads(run(["--format", "json"]))
    assert all(type(record["latency_ms"]) is int for record in payload["services"])


def test_text_format_is_still_supported():
    assert run(["--format", "text"]) == run([])
