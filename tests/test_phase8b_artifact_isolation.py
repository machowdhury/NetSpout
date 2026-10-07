import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.artifact_isolation import (
    ARTIFACT_ROOT_ENV,
    artifact_dir,
    artifact_root,
    snapshot_changes,
    snapshot_files,
)
from scripts.run_isolated_tests import run_guarded


class TestPhase8BArtifactIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_configured_current_run_root_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: directory}):
                destination = artifact_dir("gate13d", "evidence")
            self.assertEqual(
                destination,
                Path(directory).resolve() / "evidence" / "gate13d",
            )
            self.assertTrue(destination.is_dir())

    def test_default_root_is_temporary_and_not_accepted_evidence(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ARTIFACT_ROOT_ENV, None)
            destination = artifact_root()
        self.assertTrue(str(destination).startswith(tempfile.gettempdir()))
        self.assertNotIn("docs/acceptance", destination.as_posix())
        self.assertNotIn("docs/implementation/images", destination.as_posix())

    def test_configured_root_cannot_target_accepted_evidence(self):
        accepted = self.root / "docs" / "acceptance" / "evidence" / "new-run"
        with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(accepted)}):
            with self.assertRaisesRegex(ValueError, "must not target"):
                artifact_root()

    def test_snapshot_detects_added_modified_and_deleted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            modified = root / "modified.json"
            deleted = root / "deleted.png"
            modified.write_text("accepted", encoding="utf-8")
            deleted.write_bytes(b"accepted")
            before = snapshot_files((root,))
            modified.write_text("rewritten", encoding="utf-8")
            deleted.unlink()
            (root / "added.json").write_text("new", encoding="utf-8")
            changes = snapshot_changes(before, snapshot_files((root,)))
        self.assertEqual(changes[str(modified.resolve())], "MODIFIED")
        self.assertEqual(changes[str(deleted.resolve())], "DELETED")
        self.assertEqual(changes[str((root / "added.json").resolve())], "ADDED")

    def test_guarded_run_preserves_accepted_artifacts_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory) / "current-run"
            exit_code, manifest = run_guarded(
                [sys.executable, "-c", "print('isolated')"],
                repo_root=self.root,
                current_run_root=run_root,
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(manifest["mutations"], {})
            self.assertEqual(
                manifest["classification"],
                "CURRENT_RUN_EVIDENCE",
            )
            self.assertTrue(
                (run_root / "artifact-isolation-manifest.json").is_file()
            )

    def test_guarded_run_fails_when_a_protected_fixture_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            accepted = repo / "docs" / "acceptance" / "fixture.json"
            accepted.parent.mkdir(parents=True)
            accepted.write_text('{"state":"accepted"}\n', encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            run_root = Path(directory) / "current-run"
            command = [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path;"
                    "Path('docs/acceptance/fixture.json').write_text"
                    "('{\"state\":\"rewritten\"}\\n')"
                ),
            ]
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                exit_code, manifest = run_guarded(
                    command,
                    repo_root=repo,
                    current_run_root=run_root,
                )
            self.assertEqual(exit_code, 86)
            self.assertEqual(
                manifest["mutations"][str(accepted.resolve())],
                "MODIFIED",
            )

    def test_live_python_suites_use_isolated_evidence_directories(self):
        for relative in (
            "tests/test_gate13d_gnmi_splunk_e2e.py",
            "tests/test_gate13e_customer_acceptance.py",
        ):
            text = (self.root / relative).read_text(encoding="utf-8")
            self.assertIn("artifact_dir(", text)
            self.assertNotIn(
                'os.path.join(REPO_ROOT, "docs", "acceptance", "evidence"',
                text,
            )

    def test_playwright_suites_do_not_target_historical_screenshots(self):
        for path in (self.root / "frontend" / "tests").glob("*.ts"):
            if path.name == "artifact-paths.ts":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("docs/implementation/images", text, path.name)
            self.assertNotIn("../docs/implementation/images", text, path.name)


if __name__ == "__main__":
    unittest.main()
