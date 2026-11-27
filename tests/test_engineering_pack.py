"""Offline integrity and no-op checks for the four accepted #78 tasks.

Only agent-visible fixtures are public; hidden checks stay in opencode-eval.
Canonical fixture revision: c7f87d835c0d7110118bd0e31655e6a223f2d735.
"""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GIT_BLOBS = {
    "tasks/engineering/feature/minimal_report_format_001/instruction.md": "89efdb804e9430524b94fd93e45331a7e8b5974d",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/README.md": "898c11207cd457218b4ecae385ce7b988196303f",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/config/status.toml": "ca72ed1cb27c15b88530800f3a88695015307117",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/docs/future-options.md": "3650711f27f2954f7c311ef81872387549f0804e",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/pyproject.toml": "e0ef44421574e1ed99f214208d9ee6308c4460a3",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/src/briefing/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/src/briefing/cli.py": "888771b2c07cecb2b95a3535ea2796fde50bd68b",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/src/briefing/data.py": "02b8d465a88d521f8b80c5ae2b46900e8c0371c9",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/src/briefing/formatting.py": "40677e0032c8af6c7497ce9ee3bd931023f2d3d5",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/tests/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/feature/minimal_report_format_001/repo_before/tests/test_text.py": "504324ce6eda26f0f202b9856d1eb384bdb3c590",
    "tasks/engineering/feature/minimal_report_format_001/visible_tests/test_json_format.py": "7aea3f4a53132060c4a9fd7eaeaab9c46076bf63",
    "tasks/engineering/recovery/stale_handover_001/instruction.md": "95ae3ff2112c3c44953b48672d5ef6b9db4637ff",
    "tasks/engineering/recovery/stale_handover_001/repo_before/HANDOVER.md": "f7e4b2a081f821aac25d2bd9a994e626e87dda6c",
    "tasks/engineering/recovery/stale_handover_001/repo_before/README.md": "26254b76c7a2ae16b0578f892efaaf9573192af5",
    "tasks/engineering/recovery/stale_handover_001/repo_before/logs/execution.log": "d3ea55b555620dbe2b9d266ba35fa4949490ab76",
    "tasks/engineering/recovery/stale_handover_001/repo_before/src/recovery/__init__.py": "38a22dc67a83be5c14ec9ca831436602909ac4b1",
    "tasks/engineering/recovery/stale_handover_001/repo_before/src/recovery/ledger.py": "d85c983bbd21d95c67fb4bf67f629d2501a6886d",
    "tasks/engineering/recovery/stale_handover_001/repo_before/src/recovery/summary.py": "812bd6f5033df7cda964ed8336c56ef102adf3cf",
    "tasks/engineering/recovery/stale_handover_001/repo_before/state/receipts.json": "e7ef9e3d2dbdb6e3ad6c1220b67fa07718c14877",
    "tasks/engineering/recovery/stale_handover_001/repo_before/tests/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/recovery/stale_handover_001/repo_before/tests/test_summary.py": "f04f40ee564bebf6c6beb7f0ec7bb93d7329972d",
    "tasks/engineering/recovery/stale_handover_001/visible_tests/test_resume.py": "39f4dd8df4d507120d6fb76d9030bef5aba995a1",
    "tasks/engineering/review/unsigned_observer_token_001/instruction.md": "0d3ad5f5fd35e6fb22ba326ad5cb96ba28e9da31",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/README.md": "1e43424aa121710a9f96c1825b42cd6cd331e138",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/review/PR-17.diff": "b33046cb8bfeff30ee0ecb9c4ac122b323320015",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/review/PR-17.md": "171e92054e2bd53f6eca5fac58a72cfcbbfea2a4",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/src/app/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/src/app/auth.py": "5fc88319c3b3f1cbfdf9f0bd019e8413a7649191",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/src/app/formatting.py": "ae46ec5079a4ec5876d583c27d44894c8938adff",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/src/app/signatures.py": "f4c94341479d9f3bd194a711d0e0ff3d4eba285a",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/tests/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/review/unsigned_observer_token_001/repo_before/tests/test_auth.py": "eff8c92608afa042c26c9dd35faef776f1cafa42",
    "tasks/engineering/review/unsigned_observer_token_001/visible_tests/test_review_contract.py": "cdee9437719daf058d4c9f82870d439146c4771a",
    "tasks/engineering/root_cause/relay_request_correlation_001/instruction.md": "2a6c46e1aab8a3fb0ea0b5804fa03ce245dcfc51",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/README.md": "f9c2e1087f828f2e9e64977c31cc439d19c07197",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/docs/protocol.md": "e7ed4cbeb7b1ffd814e62d735bfaae3a77bf6487",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/logs/relay.log": "b2b2b257a106a2aeb329bb12cf48c3b41adbcfcb",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/src/relay/__init__.py": "4d75425f40fd46d446563a9b78b483bb4162d7c6",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/src/relay/models.py": "93e0dc896ae04f96757554770019383261f77af7",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/src/relay/policy.py": "77de239254cc63ec154835037a59bd2a8d4d0dfe",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/src/relay/registry.py": "bcdf5f823cd3677a2e9a3fab0e9a5b683a18047f",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/src/relay/router.py": "dd6a766def7b0b30cb932b7f971fcb708dfd3ec3",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/tests/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "tasks/engineering/root_cause/relay_request_correlation_001/repo_before/tests/test_router.py": "a15af405603589b05c665d73038f668fa133f149",
    "tasks/engineering/root_cause/relay_request_correlation_001/visible_tests/test_visible_correlation.py": "984df3c409ed87ba73856492e58d880d5e1f1c6b"
}
TASKS = {
    "root_cause.relay_request_correlation_001": "root_cause/relay_request_correlation_001",
    "feature.minimal_report_format_001": "feature/minimal_report_format_001",
    "review.unsigned_observer_token_001": "review/unsigned_observer_token_001",
    "recovery.stale_handover_001": "recovery/stale_handover_001",
}

class EngineeringPackContract(unittest.TestCase):
    def test_exact_canonical_agent_visible_snapshot(self):
        for relative, expected in EXPECTED_GIT_BLOBS.items():
            with self.subTest(path=relative):
                data = (ROOT / relative).read_bytes()
                actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                self.assertEqual(actual, expected)

    def test_hidden_material_not_vendored(self):
        for task in TASKS.values():
            root = ROOT / "tasks/engineering" / task
            self.assertTrue((root / "instruction.md").is_file())
            self.assertTrue((root / "repo_before").is_dir())
            self.assertTrue((root / "visible_tests").is_dir())
            self.assertFalse((root / "hidden_tests").exists())
            self.assertFalse((root / "oracle.patch").exists())
            self.assertFalse((root / "task.yaml").exists())

    def test_existing_runner_offers_all_four(self):
        source = (ROOT / "scripts/hosted-screen.py").read_text()
        mapping = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                       if isinstance(node, ast.Assign) and any(
                           isinstance(t, ast.Name) and t.id == "TASKS" for t in node.targets))
        workflow = (ROOT / ".github/workflows/hosted-nemotron.yml").read_text()
        for ident, relative in TASKS.items():
            self.assertEqual(mapping[ident], relative)
            self.assertIn("          - " + ident + "\n", workflow)

    def test_pilot_workflow_task_choices_match_runner(self):
        """Every workflow task choice must resolve to an existing pilot fixture."""
        source = (ROOT / "scripts/hosted-nemotron.py").read_text()
        mapping = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                       if isinstance(node, ast.Assign) and any(
                           isinstance(t, ast.Name) and t.id == "TASKS" for t in node.targets))
        workflow = (ROOT / ".github/workflows/hosted-nemotron.yml").read_text()
        task_choices = {
            line.removeprefix("          - ").strip()
            for line in workflow.split("      screen_agent:", 1)[0].splitlines()
            if line.startswith("          - ")
        }
        self.assertTrue(task_choices)
        self.assertEqual(set(mapping), task_choices)
        for ident, relative in mapping.items():
            with self.subTest(task=ident):
                self.assertEqual(relative, ident.replace(".", "/", 1))
                self.assertTrue((ROOT / "tasks/engineering" / relative / "instruction.md").is_file())

    def test_all_four_noop_visible_checks_fail(self):
        for ident, relative in TASKS.items():
            with self.subTest(task=ident), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / "workspace"
                fixture = ROOT / "tasks/engineering" / relative
                shutil.copytree(fixture / "repo_before", work)
                shutil.copytree(fixture / "visible_tests", work / "visible_tests")
                env = dict(os.environ, PYTHONPATH=str(work / "src"), PYTHONDONTWRITEBYTECODE="1")
                result = subprocess.run([sys.executable, str(ROOT / "scripts/visible.py")],
                                        cwd=work, env=env, capture_output=True, timeout=15)
                self.assertNotEqual(result.returncode, 0, ident)

if __name__ == "__main__":
    unittest.main()
