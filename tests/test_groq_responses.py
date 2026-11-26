"""Verify the Groq relay preserves the tool transcript and streaming route."""
import json
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from groq_responses import MODEL, sequential_groq


class GroqResponsesTests(unittest.TestCase):
    def test_serializes_tool_calls_without_rewriting_continuation(self):
        payload = {"model": MODEL, "stream": True, "parallel_tool_calls": True,
                   "client_metadata": {"client": "codex"}, "prompt_cache_key": "cache",
                   "include": ["reasoning.encrypted_content"],
                   "reasoning": {"summary": "auto", "effort": "medium"},
                   "input": [{"type": "function_call_output", "call_id": "call_1", "output": "ok"}]}
        evidence = []
        with patch("groq_responses.http.client.HTTPSConnection") as upstream:
            connection = upstream.return_value
            response = connection.getresponse.return_value
            response.status = 200
            response.getheader.return_value = "text/event-stream"
            response.read1.side_effect = [b"data: done\n\n", b""]
            with sequential_groq("upstream-key", evidence) as (base, token):
                request = urllib.request.Request(base + "/responses", json.dumps(payload).encode(),
                                                 {"Authorization": "Bearer " + token})
                with urllib.request.urlopen(request, timeout=2) as result:
                    self.assertEqual(result.read(), b"data: done\n\n")
            upstream.assert_called_once_with("api.groq.com", timeout=38)
            method, path, raw, headers = connection.request.call_args.args
            self.assertEqual((method, path), ("POST", "/openai/v1/responses"))
            self.assertEqual(json.loads(raw), {
                "model": MODEL, "stream": True, "parallel_tool_calls": False,
                "reasoning": {"effort": "medium"}, "input": payload["input"],
            })
            self.assertEqual(headers["Authorization"], "Bearer upstream-key")
            self.assertEqual(evidence, [{"http_status": 200}])

    def test_retries_once_after_provider_rate_limit(self):
        payload = json.dumps({"model": MODEL, "input": "probe"}).encode()
        evidence = []
        with patch("groq_responses.http.client.HTTPSConnection") as upstream, patch("groq_responses.sleep") as wait:
            connection = upstream.return_value
            first = connection.getresponse.return_value
            first.status = 429
            first.read.return_value = b"rate limited"
            first.getheader.return_value = "22"
            with sequential_groq("upstream-key", evidence) as (base, token):
                request = urllib.request.Request(base + "/responses", payload, {"Authorization": "Bearer " + token})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request, timeout=2)
                self.assertEqual(error.exception.code, 429)
                error.exception.close()
            wait.assert_called_once_with(23)
            self.assertEqual(connection.request.call_count, 2)
            self.assertEqual(evidence[0]["retry_wait_seconds"], 23)
            self.assertEqual(evidence[1]["http_status"], 429)
