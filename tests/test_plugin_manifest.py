"""Structural validation for Cursor plugin manifests and install-plugin.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CURSOR_PLUGIN_MANIFEST = REPO_ROOT / ".cursor-plugin" / "plugin.json"
LEGACY_MANIFEST_PATH = REPO_ROOT / "cursor-plugin.json"
INSTALL_PLUGIN_SH_PATH = REPO_ROOT / "scripts" / "install-plugin.sh"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# .cursor-plugin/plugin.json (official Cursor plugin manifest)
# ---------------------------------------------------------------------------


def test_cursor_plugin_manifest_exists() -> None:
    assert CURSOR_PLUGIN_MANIFEST.exists(), ".cursor-plugin/plugin.json not found"


def test_cursor_plugin_manifest_is_valid_json() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    assert isinstance(data, dict)


def test_cursor_plugin_manifest_required_fields() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    for field in ("name", "displayName", "version", "description"):
        assert field in data, f".cursor-plugin/plugin.json missing field: {field}"


def test_cursor_plugin_manifest_name() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    assert data["name"] == "omnicursor"


def test_cursor_plugin_manifest_component_paths() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    for key in ("rules", "agents", "skills", "hooks"):
        assert key in data, f"plugin.json missing component path: {key}"
        path = REPO_ROOT / data[key]
        assert path.exists(), f"component '{key}' path {path} does not exist"


def test_cursor_plugin_manifest_hooks_is_hooks_json() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    assert data["hooks"].endswith("hooks.json")


def test_cursor_plugin_manifest_version_format() -> None:
    data = _load_json(CURSOR_PLUGIN_MANIFEST)
    parts = data["version"].split(".")
    assert len(parts) == 3, "version must be semver (X.Y.Z)"
    for part in parts:
        assert part.isdigit(), f"version part '{part}' is not an integer"


# ---------------------------------------------------------------------------
# cursor-plugin.json (companion manifest for tooling)
# ---------------------------------------------------------------------------


def test_legacy_manifest_exists() -> None:
    assert LEGACY_MANIFEST_PATH.exists(), "cursor-plugin.json not found at repo root"


def test_legacy_manifest_is_valid_json() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    assert isinstance(data, dict)


def test_legacy_manifest_required_fields() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    for field in ("name", "displayName", "version", "description", "execution", "surfaces", "install"):
        assert field in data, f"cursor-plugin.json missing required field: {field}"


def test_legacy_manifest_points_at_official_manifest() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    assert data["manifest"] == ".cursor-plugin/plugin.json"


def test_legacy_manifest_name() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    assert data["name"] == "omnicursor"


def test_legacy_manifest_execution_is_cursor_native() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    assert data["execution"] == "cursor_native"


def test_legacy_manifest_surfaces_keys() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    surfaces = data["surfaces"]
    for key in ("rules", "hooks", "agents", "skills"):
        assert key in surfaces, f"surfaces missing key: {key}"


def test_legacy_manifest_surfaces_point_to_cursor_dirs() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    surfaces = data["surfaces"]
    assert surfaces["rules"].startswith(".cursor/")
    assert surfaces["agents"].startswith(".cursor/")
    assert surfaces["skills"].startswith(".cursor/")


def test_legacy_manifest_surfaces_dirs_exist() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    surfaces = data["surfaces"]
    for key in ("rules", "agents", "skills"):
        path = REPO_ROOT / surfaces[key]
        assert path.exists(), f"surface '{key}' path {path} does not exist"


def test_legacy_manifest_install_points_to_install_plugin_sh() -> None:
    data = _load_json(LEGACY_MANIFEST_PATH)
    assert data["install"] == "scripts/install-plugin.sh"


def test_legacy_and_official_manifest_versions_match() -> None:
    legacy = _load_json(LEGACY_MANIFEST_PATH)
    official = _load_json(CURSOR_PLUGIN_MANIFEST)
    assert legacy["version"] == official["version"]


# ---------------------------------------------------------------------------
# scripts/install-plugin.sh
# ---------------------------------------------------------------------------


def test_install_plugin_sh_exists() -> None:
    assert INSTALL_PLUGIN_SH_PATH.exists(), "scripts/install-plugin.sh not found"


def test_install_plugin_sh_is_executable() -> None:
    assert os.access(INSTALL_PLUGIN_SH_PATH, os.X_OK), "scripts/install-plugin.sh is not executable"


def test_install_plugin_sh_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(INSTALL_PLUGIN_SH_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"install-plugin.sh has syntax errors:\n{result.stderr}"


def test_install_plugin_sh_has_shebang() -> None:
    first_line = INSTALL_PLUGIN_SH_PATH.read_text().splitlines()[0]
    assert first_line.startswith("#!"), "install-plugin.sh missing shebang line"


def test_install_plugin_sh_targets_cursor_plugins_local() -> None:
    content = INSTALL_PLUGIN_SH_PATH.read_text()
    assert "plugins/local" in content
    assert "omnicursor" in content

