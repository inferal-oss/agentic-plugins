# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 02: Skill Runtime - File Creation & Script Execution

Hypotheses:
1. File creation works via --allowedTools WITHOUT --dangerously-skip-permissions
2. Script execution via Bash(uv run *) works
3. File creation FAILS when tools are NOT authorized (permission model is real)
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-runtime-test")
OUTPUT_DIR = Path("/tmp/gutcheck-runtime-output")


def setup_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)

    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "file-creator").mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-runtime-test",
        "version": "0.0.1",
        "description": "Test fixture for runtime file creation experiment"
    }, indent=2))

    (PLUGIN_DIR / "skills" / "file-creator" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: file-creator
        description: Create a test file to verify skill file-creation permissions.
        allowed-tools:
          - Bash(mkdir *)
          - Bash(uv run *)
          - Write
          - Read
        ---

        # File Creator Test Skill

        When invoked, create a file at the path specified in the arguments.
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)


def test_01_file_creation_with_allowedtools_no_skip_permissions():
    """File creation works via --allowedTools WITHOUT --dangerously-skip-permissions."""
    target_file = OUTPUT_DIR / "test-allowed-tools.txt"

    prompt = (
        f"Use the Write tool to create {target_file} "
        f"with content 'gutcheck-allowed-tools-success'. "
        f"The directory already exists. Output only the path."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Write",
            "--add-dir", str(OUTPUT_DIR),
        ],
        capture_output=True, text=True, timeout=120
    )
    print("STDOUT:", result.stdout[:500])
    print("STDERR:", result.stderr[:500])

    assert target_file.exists(), (
        f"File not created. stdout: {result.stdout[:300]}, stderr: {result.stderr[:300]}"
    )
    assert "gutcheck-allowed-tools-success" in target_file.read_text()


def test_02_uv_run_script_execution():
    """Bash(uv run *) can execute a Python script that creates output."""
    script_dir = OUTPUT_DIR / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)

    script_file = script_dir / "experiment.py"
    script_file.write_text(textwrap.dedent("""\
        from pathlib import Path
        out = Path(__file__).parent.parent / "uv-run-result.txt"
        out.write_text("gutcheck-uv-run-success")
        print(f"wrote {out}")
    """))

    result_file = OUTPUT_DIR / "uv-run-result.txt"

    prompt = (
        f"Run this command exactly: uv run {script_file} "
        f"Output only what the script prints."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Bash(uv run *)",
        ],
        capture_output=True, text=True, timeout=120
    )
    print("STDOUT:", result.stdout[:500])
    print("STDERR:", result.stderr[:500])

    assert result_file.exists(), (
        f"Script output file not created. "
        f"stdout: {result.stdout[:300]}, stderr: {result.stderr[:300]}"
    )
    assert "gutcheck-uv-run-success" in result_file.read_text()


def test_03_file_creation_fails_without_authorization():
    """With empty --allowedTools, Write is blocked. Permission model is real."""
    target_file = OUTPUT_DIR / "test-unauthorized.txt"
    if target_file.exists():
        target_file.unlink()

    prompt = (
        f"Create {target_file} with content 'should-not-exist'. "
        f"Use the Write tool. Output only the path."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "",
        ],
        capture_output=True, text=True, timeout=60
    )

    assert not target_file.exists(), \
        "File was created WITHOUT authorization - permission model is broken!"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
