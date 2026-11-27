"""Offline reproduction of the captured CI job-selection mismatch."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ci_probe import select_checks

expected = ("client-unit",)
actual = select_checks(["src/api_client/transport.py"])
print("expected checks:", expected)
print("observed checks:", actual)
if actual != expected:
    raise SystemExit("FAIL: CI selected a check owned by an untouched package")
print("PASS: required checks match the changed package")
