"""Offline route-admission regression: no credentials or provider requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hosted-screen.py"
INSPECT = (
    "import json,runpy; m=runpy.run_path(" + repr(str(SCRIPT)) + "); "
    "print(json.dumps({'profile':m['PROFILE'],'routes':m['ROUTES'],'limit':m['REQUEST_LIMIT']}))"
)


class FixedModelRoutes(unittest.TestCase):
    def run_profile(self, profile, phase=None):
        env = os.environ.copy()
        env.pop("PILOT_API_KEY", None)
        env.pop("NVIDIA_API_KEY", None)
        env["SCREEN_PHASE"] = phase or "probe"
        if profile is None:
            env.pop("PILOT_MODEL_PROFILE", None)
        else:
            env["PILOT_MODEL_PROFILE"] = profile
        return subprocess.run([sys.executable, "-c", INSPECT],
                              env=env, capture_output=True, text=True)

    def test_original_default_unchanged(self):
        completed = self.run_profile(None)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["profile"], "super")
        self.assertEqual(result["routes"]["NVIDIA"][2],
                         "nvidia/nemotron-3.5-super-vl-120b-a12b")
        self.assertEqual(result["routes"]["OpenRouter"][2],
                         "nvidia/nemotron-3.5-super-vl:free")

    def test_lightning_nvidia_only_exact_id(self):
        completed = self.run_profile("lightning")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(set(result["routes"]), {"NVIDIA"})
        self.assertEqual(result["routes"]["NVIDIA"],
                         ["integrate.api.nvidia.com", "/v1/chat/completions",
                          "nvidia/nemotron-3.5-lightning-30b-a3b"])

    def test_issue104_nvidia_routes_are_fixed(self):
        expected = {
            "minimax": "minimaxai/minimax-m3.1-flash",
            "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
            "bolt": "nvidia/nemotron-3.5-bolt-e4b",
        }
        for profile, model in expected.items():
            with self.subTest(profile=profile):
                completed = self.run_profile(profile)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(set(result["routes"]), {"NVIDIA"})
                self.assertEqual(result["routes"]["NVIDIA"],
                                 ["integrate.api.nvidia.com", "/v1/chat/completions", model])

    def test_scored_request_circuit_breaker_applies_to_all_profiles(self):
        for profile in ("super", "minimax", "ultra", "lightning", "bolt"):
            with self.subTest(profile=profile):
                result = self.run_profile(profile, "score")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["limit"], 128)

    def test_diagnostic_budget_only_extends_two_models(self):
        for profile in ("super", "minimax", "ultra", "lightning", "bolt"):
            with self.subTest(profile=profile):
                result = self.run_profile(profile, "diagnostic")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["limit"],
                                 18 if profile in ("ultra", "lightning") else 16)

    def test_unlisted_profile_fails_closed(self):
        completed = self.run_profile("nvidia/other-paid")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported fixed model profile", completed.stderr)


if __name__ == "__main__":
    unittest.main()
