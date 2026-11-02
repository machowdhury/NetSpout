#!/usr/bin/env python3
"""Run a test command without permitting accepted-artifact mutation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

try:
    from scripts.artifact_isolation import (
        ARTIFACT_ROOT_ENV,
        protected_roots,
        snapshot_changes,
        snapshot_files,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/run_isolated_tests.py
    from artifact_isolation import (  # type: ignore[no-redef]
        ARTIFACT_ROOT_ENV,
        protected_roots,
        snapshot_changes,
        snapshot_files,
    )


def run_guarded(
    command: Sequence[str],
    *,
    repo_root: Path,
    current_run_root: Path | None = None,
) -> tuple[int, dict]:
    root = repo_root.resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = (
        current_run_root.resolve()
        if current_run_root
        else Path(
            tempfile.mkdtemp(prefix=f"netspout-current-run-{run_id}-")
        ).resolve()
    )
    output_root = run_root / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    studio_root = output_root / "runtime" / "scenario-studio"
    studio_root.mkdir(parents=True, exist_ok=True)

    protected = protected_roots(root)
    before = snapshot_files(protected)
    status_before = _git_status(root, protected)
    env = {
        **os.environ,
        ARTIFACT_ROOT_ENV: str(output_root),
        "NETSPOUT_TEST_RUN_ID": run_id,
        "NETSPOUT_STUDIO_DIR": str(studio_root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    completed = subprocess.run(list(command), cwd=root, env=env, check=False)
    after = snapshot_files(protected)
    status_after = _git_status(root, protected)
    mutations = snapshot_changes(before, after)

    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "classification": "CURRENT_RUN_EVIDENCE",
        "command": list(command),
        "artifact_root": str(output_root),
        "studio_root": str(studio_root),
        "protected_roots": [str(path) for path in protected],
        "protected_file_count_before": len(before),
        "protected_file_count_after": len(after),
        "git_status_before": status_before,
        "git_status_after": status_after,
        "mutations": mutations,
        "test_exit_code": completed.returncode,
    }
    (run_root / "artifact-isolation-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    if mutations or status_after != status_before:
        print(
            "ERROR: test command mutated accepted historical evidence.",
            file=sys.stderr,
        )
        for path, change in mutations.items():
            print(f"  {change}: {path}", file=sys.stderr)
        print(f"Current-run artifacts: {run_root}", file=sys.stderr)
        return 86, manifest
    print(f"Current-run artifacts: {run_root}")
    return completed.returncode, manifest


def _git_status(repo_root: Path, roots: Sequence[Path]) -> list[str]:
    relative = [str(path.relative_to(repo_root)) for path in roots]
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", *relative],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.splitlines()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Fresh current-run directory; defaults to an OS temporary directory.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    repo_root = Path(__file__).resolve().parents[1]
    exit_code, _ = run_guarded(
        command,
        repo_root=repo_root,
        current_run_root=args.artifact_root,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
