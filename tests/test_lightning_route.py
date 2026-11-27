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
    "print(json.dumps({'profile':m['PROFILE'],'routes':m['ROUTES']}))"
)


class FixedModelRoutes(unittest.TestCase):
    def run_profile(self, profile):
        env = os.environ.copy()
        env.pop("PILOT_API_KEY", None)
        env.pop("NVIDIA_API_KEY", None)
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

    def test_unlisted_profile_fails_closed(self):
        completed = self.run_profile("nvidia/other-paid")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported fixed model profile", completed.stderr)


if __name__ == "__main__":
    unittest.main()
