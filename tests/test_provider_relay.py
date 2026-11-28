"""Credential-free relay and budget regressions; never makes upstream calls."""
import io
import json
import os
import runpy
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "hosted-screen.py"
module = SimpleNamespace(**runpy.run_path(str(SCRIPT)))


class FakeResponse:
    def __init__(self, code, retry_after=None):
        self.status = code
        self.retry_after = retry_after

    def getheader(self, name, default=None):
        return (self.retry_after if name == "Retry-After"
                else "application/json" if name == "Content-Type" else default)

    def read(self, _size):
        return b'{"model":"minimaxai/minimax-m3.1-flash"}'

    def readline(self):
        return b""


class RelayTests(TestCase):
    def handler(self, statuses):
        body = json.dumps({"model": "minimaxai/minimax-m3.1-flash"}).encode()
        server = SimpleNamespace(
            host="integrate.api.nvidia.com", endpoint="/v1/chat/completions",
            key="test-key", model="minimaxai/minimax-m3.1-flash",
            statuses=[], request_limit=16, local_budget_rejections=0,
            budget_exhausted=threading.Event(), transient_retries=0,
            retry_wait_seconds=[], transport_error_types=[],
            observe=mock.Mock(),
        )
        handler = object.__new__(module.ProviderRequest)
        handler.path = "/v1/chat/completions"
        handler.server = server
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.send_error = mock.Mock()

        queue = list(statuses)
        class Connection:
            def __init__(self, *args, **kwargs):
                pass
            def request(self, *args, **kwargs):
                pass
            def getresponse(self):
                return queue.pop(0)
            def close(self):
                pass
        return handler, Connection, queue

    def test_429_retries_and_each_upstream_attempt_consumes_budget(self):
        handler, connection, queue = self.handler([
            FakeResponse(429, "0"), FakeResponse(503, "0"), FakeResponse(200)])
        with mock.patch.object(module.http.client, "HTTPSConnection", connection):
            with mock.patch.object(module.time, "sleep"):
                handler.do_POST()
        self.assertEqual(handler.server.statuses, [429, 503, 200])
        self.assertEqual(handler.server.transient_retries, 2)
        self.assertEqual(handler.server.retry_wait_seconds, [0.0, 0.0])
        self.assertEqual(handler.server.local_budget_rejections, 0)
        self.assertFalse(handler.server.budget_exhausted.is_set())
        self.assertEqual(len(queue), 0)
        handler.send_response.assert_called_once_with(200)

    def test_large_retry_after_is_respected_without_long_wait(self):
        handler, connection, queue = self.handler([FakeResponse(429, "120")])
        with mock.patch.object(module.http.client, "HTTPSConnection", connection):
            with mock.patch.object(module.time, "sleep") as sleep:
                handler.do_POST()
        sleep.assert_not_called()
        self.assertEqual(handler.server.statuses, [429])
        self.assertEqual(handler.server.transient_retries, 0)
        handler.send_response.assert_called_once_with(429)

    def test_http_date_retry_after_and_invalid_header(self):
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=3))
        delay = module.transient_retry_delay(503, future, 0)
        self.assertIsNotNone(delay)
        self.assertGreaterEqual(delay, 0)
        self.assertLessEqual(delay, 3.5)
        self.assertIsNone(module.transient_retry_delay(429, "not-a-date", 0))
        self.assertIsNone(module.transient_retry_delay(429, "120", 0))
        self.assertIsNone(module.transient_retry_delay(400, None, 0))

    def test_no_retry_when_last_slot_is_used(self):
        handler, connection, queue = self.handler([FakeResponse(429, "0")])
        handler.server.statuses = [200] * 15
        with mock.patch.object(module.http.client, "HTTPSConnection", connection):
            handler.do_POST()
        self.assertEqual(len(handler.server.statuses), 16)
        self.assertEqual(handler.server.transient_retries, 0)
        handler.send_response.assert_called_once_with(429)

    def test_reject_after_ceiling_sets_exhaustion_event_without_provider_hit(self):
        handler, connection, queue = self.handler([])
        handler.server.statuses = [200] * 16
        with mock.patch.object(module.http.client, "HTTPSConnection", connection):
            handler.do_POST()
        self.assertEqual(len(handler.server.statuses), 16)
        self.assertTrue(handler.server.budget_exhausted.is_set())
        self.assertEqual(handler.server.local_budget_rejections, 1)
        handler.send_error.assert_called_once_with(429)

    def test_scored_limits_are_circuit_breakers_not_sixteen_step_budgets(self):
        with mock.patch.dict(os.environ, {
            "SCREEN_PHASE": "score", "PILOT_MODEL_PROFILE": "ultra",
        }):
            scope = runpy.run_path(str(SCRIPT))
        self.assertEqual(scope["REQUEST_LIMIT"], 128)
        self.assertEqual(scope["AGENT_STEP_LIMIT"], 128)
        self.assertEqual(scope["EXECUTION_POLICY"], "circuit_breakers_v1")
        env, _command = scope["configure"](
            "opencode", "nvidia/nemotron-3-ultra-550b-a55b",
            Path("."), "test prompt", Path("."))
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["agent"]["build"]["steps"], 128)

    def test_historical_diagnostics_remain_outside_new_cohort(self):
        with mock.patch.dict(os.environ, {
            "SCREEN_PHASE": "diagnostic", "PILOT_MODEL_PROFILE": "ultra",
        }):
            scope = runpy.run_path(str(SCRIPT))
        self.assertEqual(scope["REQUEST_LIMIT"], 18)
        self.assertEqual(scope["AGENT_STEP_LIMIT"], 16)

    def test_circuit_breaker_stops_at_128_not_on_the_sixteenth_request(self):
        handler, connection, queue = self.handler([FakeResponse(200)])
        handler.server.request_limit = 128
        handler.server.statuses = [200] * 127
        with mock.patch.object(module.http.client, "HTTPSConnection", connection):
            handler.do_POST()
        self.assertEqual(len(handler.server.statuses), 128)
        self.assertFalse(handler.server.budget_exhausted.is_set())
        handler.do_POST()
        self.assertEqual(handler.server.local_budget_rejections, 1)
        self.assertTrue(handler.server.budget_exhausted.is_set())
        self.assertEqual(len(handler.server.statuses), 128)
        handler.send_error.assert_called_once_with(429)

    def test_process_group_stops_after_budget_event(self):
        event = threading.Event()
        ready = threading.Timer(0.1, event.set)
        ready.start()
        try:
            exit_code, _, reason = module.run_with_budget(
                [sys.executable, "-c", "import time;time.sleep(10)"],
                os.environ.copy(), event, 4)
        finally:
            ready.join()
        self.assertEqual(exit_code, 125)
        self.assertEqual(reason, "request_budget_exhausted")

    def test_timeout_remains_bounded(self):
        exit_code, _, reason = module.run_with_budget(
            [sys.executable, "-c", "import time;time.sleep(10)"],
            os.environ.copy(), threading.Event(), 0.2)
        self.assertEqual(exit_code, 124)
        self.assertEqual(reason, "agent_timeout")


if __name__ == "__main__":
    import unittest
    unittest.main()
