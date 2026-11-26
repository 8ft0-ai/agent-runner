"""Check that the runner retains a source patch after a failed session."""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("hosted-codex")


class CodexScoreTests(unittest.TestCase):
    def test_timeout_retains_patch_against_starter_and_visible_tests(self):
        def timed_out_agent(cli, work, endpoint, model, key, prompt, seconds, record):
            self.assertTrue((work / "visible_tests/test_visible_correlation.py").is_file())
            registry = work / "src/relay/registry.py"
            with registry.open("a") as source:
                source.write("\n# synthetic candidate\n")
            record["agent_exit"] = 124
            return set(), []

        with tempfile.TemporaryDirectory() as location:
            temp = Path(location)
            evidence = temp / "evidence"
            evidence.mkdir()
            record = {"provider": "OpenRouter", "mode": "score"}
            with (patch.object(runner, "run_codex", side_effect=timed_out_agent),
                  patch.object(runner, "public_checks", return_value=True) as checks):
                self.assertFalse(runner.execute(temp, evidence, "mock-key", record))
            checks.assert_called_once()
            self.assertTrue(record["registry_only"])
            self.assertTrue(record["candidate"])
            self.assertFalse(record["clean_exit"])
            result = (evidence / "result.patch").read_text()
            self.assertIn("+# synthetic candidate", result)
            self.assertNotIn("visible_tests", result)
