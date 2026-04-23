"""Structural validation for cursor-plugin.json and install.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "cursor-plugin.json"
INSTALL_SH_PATH = REPO_ROOT / "install.sh"


# ---------------------------------------------------------------------------
# cursor-plugin.json
# ---------------------------------------------------------------------------


def test_manifest_exists() -> None:
    assert MANIFEST_PATH.exists(), "cursor-plugin.json not found at repo root"


def test_manifest_is_valid_json() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    assert isinstance(data, dict)


def test_manifest_required_fields() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    for field in ("name", "displayName", "version", "description", "execution", "surfaces", "install"):
        assert field in data, f"cursor-plugin.json missing required field: {field}"


def test_manifest_name() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    assert data["name"] == "omnicursor"


def test_manifest_execution_is_cursor_native() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    assert data["execution"] == "cursor_native"


def test_manifest_surfaces_keys() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    surfaces = data["surfaces"]
    for key in ("rules", "hooks", "agents", "skills"):
        assert key in surfaces, f"surfaces missing key: {key}"


def test_manifest_surfaces_point_to_cursor_dirs() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    surfaces = data["surfaces"]
    assert surfaces["rules"].startswith(".cursor/")
    assert surfaces["agents"].startswith(".cursor/")
    assert surfaces["skills"].startswith(".cursor/")


def test_manifest_surfaces_dirs_exist() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    surfaces = data["surfaces"]
    for key in ("rules", "agents", "skills"):
        path = REPO_ROOT / surfaces[key]
        assert path.exists(), f"surface '{key}' path {path} does not exist"


def test_manifest_install_points_to_install_sh() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    assert data["install"] == "install.sh"


def test_manifest_version_format() -> None:
    data = json.loads(MANIFEST_PATH.read_text())
    parts = data["version"].split(".")
    assert len(parts) == 3, "version must be semver (X.Y.Z)"
    for part in parts:
        assert part.isdigit(), f"version part '{part}' is not an integer"


# ---------------------------------------------------------------------------
# install.sh
# ---------------------------------------------------------------------------


def test_install_sh_exists() -> None:
    assert INSTALL_SH_PATH.exists(), "install.sh not found at repo root"


def test_install_sh_is_executable() -> None:
    assert os.access(INSTALL_SH_PATH, os.X_OK), "install.sh is not executable"


def test_install_sh_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(INSTALL_SH_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"install.sh has syntax errors:\n{result.stderr}"


def test_install_sh_has_shebang() -> None:
    first_line = INSTALL_SH_PATH.read_text().splitlines()[0]
    assert first_line.startswith("#!"), "install.sh missing shebang line"


def test_install_sh_copies_cursor_skills() -> None:
    content = INSTALL_SH_PATH.read_text()
    assert "skills" in content, "install.sh does not reference skills directory"
    assert ".cursor" in content, "install.sh does not reference .cursor directory"


def test_install_sh_copies_cursor_agents() -> None:
    content = INSTALL_SH_PATH.read_text()
    assert "agents" in content, "install.sh does not reference agents directory"


def test_install_sh_handles_hooks_json() -> None:
    content = INSTALL_SH_PATH.read_text()
    assert "hooks.json" in content, "install.sh does not handle hooks.json"
