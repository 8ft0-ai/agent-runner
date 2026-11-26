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
