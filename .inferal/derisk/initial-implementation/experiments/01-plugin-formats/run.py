# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 01: Plugin Format & Distribution

Hypotheses:
1. Claude Code plugin validates with `claude plugin validate`
2. Marketplace JSON validates with subdirectory plugin source
3. Full marketplace lifecycle works: add, install, verify, uninstall, remove
4. Installed plugin has skills files at expected location with correct content
5. Codex symlink makes the same physical file accessible at discovery path
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-test-plugin")
MARKETPLACE_DIR = Path("/tmp/gutcheck-test-marketplace")
CODEX_SKILL_DIR = Path.home() / ".agents" / "skills" / "gutcheck-test"
MARKETPLACE_NAME = "gutcheck-test-mkt"
PLUGIN_INSTALL_ID = f"gutcheck-test@{MARKETPLACE_NAME}"


def setup_module():
    """Create test plugin and marketplace directory structures."""
    for d in [PLUGIN_DIR, MARKETPLACE_DIR]:
        if d.exists():
            shutil.rmtree(d)
    if CODEX_SKILL_DIR.is_symlink():
        CODEX_SKILL_DIR.unlink()
    elif CODEX_SKILL_DIR.exists():
        shutil.rmtree(CODEX_SKILL_DIR)

    # --- Build the plugin ---
    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "derisk-test").mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-test",
        "version": "0.0.1",
        "description": "Test fixture for gutcheck plugin format experiment",
        "author": {"name": "test"},
        "license": "MIT"
    }, indent=2))

    # Skill with ALL permissions gutcheck will need
    (PLUGIN_DIR / "skills" / "derisk-test" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: derisk-test
        description: Test skill that creates experiment artifact files. Use when testing file creation permissions.
        allowed-tools:
          - Bash(mkdir *)
          - Bash(uv run *)
          - Write
          - Edit
          - Read
        ---

        # Derisk Test Skill

        When invoked, create a directory `.gutcheck/derisk/experiments/test/` and write a result file into it.

        1. Create the directory: `mkdir -p .gutcheck/derisk/experiments/test/`
        2. Write a file `result.md` with the experiment outcome
        3. Report what was created
    """))

    # --- Build the marketplace (plugin in subdirectory) ---
    (MARKETPLACE_DIR / ".claude-plugin").mkdir(parents=True)
    plugin_subdir = MARKETPLACE_DIR / "plugins" / "gutcheck-test"
    shutil.copytree(PLUGIN_DIR, plugin_subdir)

    (MARKETPLACE_DIR / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": MARKETPLACE_NAME,
        "owner": {
            "name": "inferal-oss",
            "email": "oss@inferal.com"
        },
        "plugins": [
            {
                "name": "gutcheck-test",
                "description": "Test fixture for gutcheck derisking",
                "source": "./plugins/gutcheck-test",
                "version": "0.0.1",
                "author": {"name": "inferal-oss"},
                "keywords": ["test"]
            }
        ]
    }, indent=2))


def teardown_module():
    """Clean up all test fixtures and any installed plugins."""
    subprocess.run(
        ["claude", "plugin", "uninstall", PLUGIN_INSTALL_ID, "--scope", "user"],
        capture_output=True, text=True
    )
    subprocess.run(
        ["claude", "plugin", "marketplace", "remove", MARKETPLACE_NAME],
        capture_output=True, text=True
    )
    for d in [PLUGIN_DIR, MARKETPLACE_DIR]:
        if d.exists():
            shutil.rmtree(d)
    if CODEX_SKILL_DIR.is_symlink():
        CODEX_SKILL_DIR.unlink()
    elif CODEX_SKILL_DIR.exists():
        shutil.rmtree(CODEX_SKILL_DIR)


def test_01_claude_plugin_validates():
    """claude plugin validate accepts our plugin structure."""
    result = subprocess.run(
        ["claude", "plugin", "validate", str(PLUGIN_DIR)],
        capture_output=True, text=True
    )
    print("STDOUT:", result.stdout)
    assert result.returncode == 0, f"Validation failed: {result.stdout}"


def test_02_marketplace_json_validates():
    """claude plugin validate accepts our marketplace structure."""
    result = subprocess.run(
        ["claude", "plugin", "validate", str(MARKETPLACE_DIR)],
        capture_output=True, text=True
    )
    print("STDOUT:", result.stdout)
    assert result.returncode == 0, \
        f"Marketplace validation failed: {result.stdout}"


def test_03_marketplace_install_uninstall_e2e():
    """Full lifecycle: add marketplace, install plugin, verify in list, uninstall, remove, verify gone."""
    # Add marketplace
    r = subprocess.run(
        ["claude", "plugin", "marketplace", "add", str(MARKETPLACE_DIR)],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"Failed to add marketplace: {r.stdout} {r.stderr}"

    # Install plugin
    r = subprocess.run(
        ["claude", "plugin", "install", PLUGIN_INSTALL_ID, "--scope", "user"],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"Failed to install: {r.stdout} {r.stderr}"

    # Verify present
    r = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True)
    plugins = json.loads(r.stdout)
    ids = [p["id"] for p in plugins]
    assert PLUGIN_INSTALL_ID in ids, f"Not in installed list: {ids}"

    # Uninstall
    r = subprocess.run(
        ["claude", "plugin", "uninstall", PLUGIN_INSTALL_ID, "--scope", "user"],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"Failed to uninstall: {r.stdout} {r.stderr}"

    # Remove marketplace
    r = subprocess.run(
        ["claude", "plugin", "marketplace", "remove", MARKETPLACE_NAME],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"Failed to remove marketplace: {r.stdout} {r.stderr}"

    # Verify gone
    r = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True)
    plugins = json.loads(r.stdout)
    ids = [p["id"] for p in plugins]
    assert PLUGIN_INSTALL_ID not in ids, f"Still present after uninstall: {ids}"


def test_04_installed_plugin_has_skills_on_disk():
    """After install, SKILL.md exists at install path with content intact
    (including allowed-tools with uv run)."""
    # Install
    subprocess.run(
        ["claude", "plugin", "marketplace", "add", str(MARKETPLACE_DIR)],
        capture_output=True, text=True
    )
    subprocess.run(
        ["claude", "plugin", "install", PLUGIN_INSTALL_ID, "--scope", "user"],
        capture_output=True, text=True
    )

    try:
        r = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True)
        plugins = json.loads(r.stdout)
        match = [p for p in plugins if p["id"] == PLUGIN_INSTALL_ID]
        assert match, "Plugin not in list after install"

        install_path = Path(match[0]["installPath"])
        skill_md = install_path / "skills" / "derisk-test" / "SKILL.md"
        assert skill_md.exists(), f"SKILL.md not at {skill_md}"

        content = skill_md.read_text()
        assert "Bash(uv run" in content, "allowed-tools Bash(uv run *) not in installed SKILL.md"
    finally:
        subprocess.run(
            ["claude", "plugin", "uninstall", PLUGIN_INSTALL_ID, "--scope", "user"],
            capture_output=True, text=True
        )
        subprocess.run(
            ["claude", "plugin", "marketplace", "remove", MARKETPLACE_NAME],
            capture_output=True, text=True
        )


def test_05_codex_symlink_resolves_to_same_file():
    """Symlink from Codex discovery path resolves to same physical file as Claude Code path."""
    skill_source = PLUGIN_DIR / "skills" / "derisk-test"
    CODEX_SKILL_DIR.parent.mkdir(parents=True, exist_ok=True)
    CODEX_SKILL_DIR.symlink_to(skill_source)

    claude_file = PLUGIN_DIR / "skills" / "derisk-test" / "SKILL.md"
    codex_file = CODEX_SKILL_DIR / "SKILL.md"

    assert claude_file.resolve() == codex_file.resolve(), \
        "Symlink doesn't resolve to the same physical file"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
