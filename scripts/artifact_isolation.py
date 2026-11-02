"""Isolation and mutation detection for test-generated artifacts.

Accepted evidence is immutable input to test execution. Current-run output is
written below NETSPOUT_TEST_ARTIFACT_ROOT, or a process-scoped temporary
directory when the variable is absent.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Iterable


ARTIFACT_ROOT_ENV = "NETSPOUT_TEST_ARTIFACT_ROOT"
PROTECTED_RELATIVE_ROOTS = (
    Path("catalog"),
    Path("backend/app/catalog_data"),
    Path("netspout/catalog"),
    Path("netspout/bin/catalog_data"),
    Path("netspout/bin/netspout_core/catalog_data"),
    Path("netspout/appserver/static/vendor_catalog.json"),
    Path("docs/acceptance"),
    Path("docs/implementation/images"),
)


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"Invalid artifact path component: {value!r}")
    return cleaned


def artifact_root() -> Path:
    configured = os.environ.get(ARTIFACT_ROOT_ENV)
    if configured:
        destination = Path(configured).expanduser().resolve()
        repository = Path(__file__).resolve().parents[1]
        if any(
            destination == protected
            or destination.is_relative_to(protected)
            for protected in protected_roots(repository)
        ):
            raise ValueError(
                f"{ARTIFACT_ROOT_ENV} must not target accepted evidence: "
                f"{destination}"
            )
        return destination
    return (
        Path(tempfile.gettempdir())
        / "netspout-test-artifacts"
        / "temporary"
        / f"process-{os.getpid()}"
    )


def artifact_dir(suite: str, category: str = "evidence") -> Path:
    destination = artifact_root() / _safe_component(category) / _safe_component(suite)
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def protected_roots(repo_root: Path) -> tuple[Path, ...]:
    root = repo_root.resolve()
    return tuple(root / relative for relative in PROTECTED_RELATIVE_ROOTS)


def snapshot_files(roots: Iterable[Path]) -> Dict[str, str]:
    """Return path-to-SHA256 state, including a marker for missing files."""
    snapshot: Dict[str, str] = {}
    for root in roots:
        resolved = root.resolve()
        if resolved.is_file():
            files = (resolved,)
        elif resolved.exists():
            files = (path for path in resolved.rglob("*") if path.is_file())
        else:
            snapshot[str(resolved)] = "MISSING"
            continue
        for path in files:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot[str(path.resolve())] = digest
    return dict(sorted(snapshot.items()))


def snapshot_changes(
    before: Dict[str, str], after: Dict[str, str]
) -> Dict[str, str]:
    changes: Dict[str, str] = {}
    for path in sorted(set(before) | set(after)):
        old = before.get(path, "MISSING")
        new = after.get(path, "MISSING")
        if old != new:
            if old == "MISSING":
                changes[path] = "ADDED"
            elif new == "MISSING":
                changes[path] = "DELETED"
            else:
                changes[path] = "MODIFIED"
    return changes
