import io
import json
import unittest

from scripts.run_diagnostics import collect_events


class RunDiagnosticsTests(unittest.TestCase):
    def test_retains_error_retry_and_last_successful_tool(self):
        events = [
            {"type": "tool_use", "timestamp": 1000,
             "part": {"tool": "read", "state": {"status": "completed"}}},
            {"type": "tool_use", "timestamp": 1100,
             "part": {"tool": "edit", "state": {"status": "error"}}},
            {"type": "retry", "timestamp": 1200, "attempt": 2, "nextRetryAt": 3200,
             "error": {"type": "provider.rate-limit", "status": 429, "retryAfterMs": 2000}},
            {"type": "error", "timestamp": 3300,
             "error": {"type": "provider.transport", "message": "Request timed out"}},
        ]
        record = {}
        tools, trace = collect_events(map(json.dumps, events), record)
        self.assertEqual(tools, {"read"})
        self.assertEqual(trace[-1], {"tool": "edit", "completed": False})
        diagnostics = record["agent_diagnostics"]
        self.assertEqual(diagnostics["retry_count"], 1)
        self.assertEqual(diagnostics["last_retry"]["http_status"], 429)
        self.assertEqual(diagnostics["last_retry"]["retry_after_ms"], 2000)
        self.assertEqual(diagnostics["last_retry"]["attempt"], 2)
        self.assertEqual(diagnostics["last_error"]["type"], "provider.transport")
        self.assertEqual(diagnostics["last_error"]["timestamp_ms"], 3300)
        self.assertEqual(diagnostics["last_successful_tool"], {"tool": "read", "timestamp_ms": 1000})
        self.assertEqual(record["provider_error"], "timeout")

    def test_retry_does_not_mark_recovered_run_as_terminal_error(self):
        record = {}
        collect_events([json.dumps({"type": "retry", "error": {"status": 429}})], record)
        self.assertEqual(record["agent_diagnostics"]["retry_count"], 1)
        self.assertIsNone(record["agent_diagnostics"]["last_error"])
        self.assertNotIn("provider_error", record)

    def test_untrusted_values_and_non_event_lines_stay_out_of_evidence(self):
        sentinel = "private-credential-or-prompt"
        events = [
            {"type": "error", "error": {"type": sentinel, "message": sentinel,
                                       "status": sentinel, "response": {"body": sentinel}}},
            {"type": "tool_use", "part": {"tool": "glob", "state": {"status": "completed", "input": sentinel}}},
            {"type": "step_finish", "part": {"type": "step-finish", "tokens": {"input": 13, sentinel: 42}}},
            {"type": "tool_use", "part": {"tool": ["unexpected"]}},
            None,
        ]
        record = {}
        stream = io.StringIO(sentinel + "\n" + "\n".join(map(json.dumps, events)))
        _, trace = collect_events(stream, record)
        self.assertNotIn(sentinel, json.dumps([record, trace]))
        self.assertEqual(record["provider_error"], "unclassified")
        self.assertEqual(record["usage_by_step"], [{"input": 13}])
