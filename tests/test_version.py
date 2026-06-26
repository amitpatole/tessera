"""Version drift-guard: the packaging metadata and the import-time string must agree."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tessera


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["version"] == tessera.__version__


def test_version_is_semver_ish() -> None:
    parts = tessera.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
