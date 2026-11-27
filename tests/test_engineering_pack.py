"""Offline integrity and no-op checks for the eight frozen #97 tasks.

Only agent-visible fixtures are public; hidden checks stay in opencode-eval.
Canonical four-task revision: c7f87d835c0d7110118bd0e31655e6a223f2d735.
Additional four accepted at: 405aa5d0d2552834980a01f147a8ef792994ee26.
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
    "tasks/engineering/diagnostics/ci_failure_investigation_001/instruction.md": "0bc83b379f99aa62e38d4989233f464dbe39db03",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/README.md": "e9927dcb24fe44b1557ff6e3a89b1c560442d4f6",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/config/ci-matrix.yml": "ed8448e9e9fcc8dc5031170bae2265a388162838",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/logs/ci-run.txt": "250d173f09f00c275b18685057c58cb7de52bc47",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/scripts/reproduce_ci.py": "9bddbde7484d5ac0be9945defe5d65775d37b02d",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/src/ci_probe/__init__.py": "15babdffafd3c3a2ee3dc5552c34a53924cb4e7b",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/src/ci_probe/targets.py": "4b6dc6c1fd3b5caf884636c8b56af2d2e6923bfe",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/repo_before/tests/test_selection.py": "7401f5083a4ea48d5cdd4919d980f4274a6e392a",
    "tasks/engineering/diagnostics/ci_failure_investigation_001/visible_tests/test_ci_gate.py": "dca5216f79c2288e9de2bc8ac0dbd6d725451977",
    "tasks/engineering/performance/incremental_regression_001/instruction.md": "af8f882d5b8f870e01c6289145ac02f25fccccd4",
    "tasks/engineering/performance/incremental_regression_001/repo_before/README.md": "7f5128d67dea0399e98a5e66058664b5b7cfdeec",
    "tasks/engineering/performance/incremental_regression_001/repo_before/src/stream_merge/__init__.py": "b7617de3763f09d458d90774902f712f874167e5",
    "tasks/engineering/performance/incremental_regression_001/repo_before/src/stream_merge/merge.py": "ec1330343c57ecd6aedbefb93bb27388ab4577c3",
    "tasks/engineering/performance/incremental_regression_001/repo_before/src/stream_merge/models.py": "5b297a9028fafa6a19893189fdc904444ec95e4e",
    "tasks/engineering/performance/incremental_regression_001/repo_before/tests/test_reconciliation.py": "ef42416acffd206b062099e80d2f62e303457580",
    "tasks/engineering/performance/incremental_regression_001/visible_tests/test_visible_efficiency.py": "4a72861ac9bbd39a12b334c1e48aa167eeff5eec",
    "tasks/engineering/refactor/backwards_compatible_api_001/instruction.md": "84b0497f7f0c70da7c01ba6c0575856554b12dd8",
    "tasks/engineering/refactor/backwards_compatible_api_001/repo_before/README.md": "4ce1332b790293a1d97e4dc020aeaccfd641f8fa",
    "tasks/engineering/refactor/backwards_compatible_api_001/repo_before/src/ledger/__init__.py": "b097a0b5d74d7e09922ffd0f2e37607c87ec66c3",
    "tasks/engineering/refactor/backwards_compatible_api_001/repo_before/src/ledger/api.py": "df98ae8c5302d2b14549c9633ae431ce6aaba529",
    "tasks/engineering/refactor/backwards_compatible_api_001/repo_before/src/ledger/csv_export.py": "7664a1b001dd202f48d78bc86dfb4721cadafbd9",
    "tasks/engineering/refactor/backwards_compatible_api_001/repo_before/tests/test_consumers.py": "bd1e710712cfd183107e01ebd69a93d617e80ccf",
    "tasks/engineering/refactor/backwards_compatible_api_001/visible_tests/test_shared_activity.py": "ed2644ac2bbe66c0481f01c2fe94264c5b0f5e4a",
    "tasks/engineering/security/auth_boundary_repair_001/instruction.md": "b13d567d1a09db5ec784b2febc93a17e141a787c",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/README.md": "46616da725777b9a8295edfd1a7f46aa3f16a148",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/src/workspace_docs/__init__.py": "649b966053f8dc18ae4d7ab3ecc5747973d118f8",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/src/workspace_docs/access.py": "1c42a7dcdfa2b5bc269c216f407baa5fc19d6e7c",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/src/workspace_docs/models.py": "fe3f2dd69d4ebce10bdd55ffd53d3322d9e2265b",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/src/workspace_docs/service.py": "3befd9bda53c147631360d212bd6b7fe5cadd5cd",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/src/workspace_docs/store.py": "d42f255f4b5d506004bfd9bb81f222cf65394553",
    "tasks/engineering/security/auth_boundary_repair_001/repo_before/tests/test_authorised.py": "efd5c01a22823612069afaa587bc8152576382ec",
    "tasks/engineering/security/auth_boundary_repair_001/visible_tests/test_security_boundary.py": "37f372c2925729d3208a54c07eb0a1cb8af5ea4a",

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
    "diagnostics.ci_failure_investigation_001": "diagnostics/ci_failure_investigation_001",
    "refactor.backwards_compatible_api_001": "refactor/backwards_compatible_api_001",
    "security.auth_boundary_repair_001": "security/auth_boundary_repair_001",
    "performance.incremental_regression_001": "performance/incremental_regression_001",
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

    def test_existing_runner_offers_all_eight(self):
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

    def test_frozen_benchmark_fixture_revision_mapping(self):
        source = (ROOT / "scripts/hosted-screen.py").read_text()
        parsed = ast.parse(source)
        names = {node.targets[0].id: ast.literal_eval(node.value) for node in parsed.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in {"FIXTURE_REVISION", "FIXTURE_REVISIONS"}}
        for ident in TASKS:
            self.assertEqual(names["FIXTURE_REVISIONS"].get(ident, names["FIXTURE_REVISION"]),
                             "405aa5d0d2552834980a01f147a8ef792994ee26" if ident in {'security.auth_boundary_repair_001', 'refactor.backwards_compatible_api_001', 'diagnostics.ci_failure_investigation_001', 'performance.incremental_regression_001'} else "c7f87d835c0d7110118bd0e31655e6a223f2d735")

    def test_all_eight_noop_visible_checks_fail(self):
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
