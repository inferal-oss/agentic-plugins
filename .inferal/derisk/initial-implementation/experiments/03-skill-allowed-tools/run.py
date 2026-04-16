# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 03: Skill Invocation & allowed-tools Behavior

Tests:
1. Skill invocation pipeline works: Skill tool → SKILL.md → instructions followed → file created
2. allowed-tools is about auto-approval, NOT overriding session restrictions
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-allowedtools-test")
OUTPUT_DIR = Path("/tmp/gutcheck-allowedtools-output")


def setup_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)
    OUTPUT_DIR.mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "write-test").mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-allowedtools-test",
        "version": "0.0.1",
        "description": "Test that skill invocation and allowed-tools work correctly"
    }, indent=2))

    (PLUGIN_DIR / "skills" / "write-test" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: write-test
        description: Test skill for verifying allowed-tools pre-authorization. Invoke when asked to test write permissions or create test files.
        allowed-tools:
          - Write
          - Bash(mkdir *)
        ---

        # Write Test Skill

        This skill pre-authorizes the Write tool (auto-approval, no prompts).

        When invoked, write "skill-invocation-success" to the file path from $ARGUMENTS.
        If no path given, tell the user to provide one.
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)


def test_01_skill_invocation_pipeline_works():
    """Full pipeline: Skill tool invokes skill → skill instructions followed → file created.
    Both Skill AND Write authorized via CLI to test the pipeline, not the permission model."""
    target = OUTPUT_DIR / "skill-pipeline.txt"
    if target.exists():
        target.unlink()

    prompt = (
        f"Use the Skill tool to invoke the 'write-test' skill with argument '{target}'. "
        f"The skill should write a file. Report what happened."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Skill,Write,Bash(mkdir *)",
        ],
        capture_output=True, text=True, timeout=120
    )
    print("Pipeline stdout:", result.stdout[:500])
    print("Pipeline stderr:", result.stderr[:500])

    assert target.exists(), (
        f"Skill invocation pipeline failed - file not created.\n"
        f"stdout: {result.stdout[:400]}\nstderr: {result.stderr[:200]}"
    )
    content = target.read_text()
    assert "skill-invocation-success" in content, \
        f"Skill instructions not followed. Content: {content}"


def test_02_allowed_tools_does_not_override_session_ceiling():
    """Skill's allowed-tools cannot override --allowedTools session restriction.
    With only Skill authorized (NOT Write), Write should fail even after skill invocation."""
    target = OUTPUT_DIR / "ceiling-test.txt"
    if target.exists():
        target.unlink()

    prompt = (
        f"Use the Skill tool to invoke 'write-test' with argument '{target}'. "
        f"Then try to use Write to create the file."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Skill",
        ],
        capture_output=True, text=True, timeout=120
    )
    print("Ceiling test stdout:", result.stdout[:500])

    assert not target.exists(), (
        "Write succeeded despite being excluded from --allowedTools. "
        "allowed-tools OVERRIDES session restrictions (security issue)."
    )


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
