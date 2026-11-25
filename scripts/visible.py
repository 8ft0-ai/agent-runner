"""Run the public fixture's standalone test functions using the standard library."""
import runpy
import unittest
from pathlib import Path

suite = unittest.TestSuite()
for path in sorted(Path("visible_tests").glob("test_*.py")):
    for name, function in runpy.run_path(str(path)).items():
        if name.startswith("test_") and callable(function):
            suite.addTest(unittest.FunctionTestCase(function))

if not suite.countTestCases():
    raise SystemExit("No visible tests collected")
raise SystemExit(0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1)
