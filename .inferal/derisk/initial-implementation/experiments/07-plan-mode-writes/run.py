# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 07: Writing During REAL Plan Mode

Uses --permission-mode plan (system-level enforcement), NOT --system-prompt
simulation. This is the actual plan mode mechanism in Claude Code.

Tests whether skills, subagents, or forked contexts can write files when
the session is in real plan mode.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-planmode-test")
OUTPUT_DIR = Path("/tmp/gutcheck-planmode-output")
WORK_DIR = Path("/tmp/gutcheck-planmode-workdir")


def setup_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)
    OUTPUT_DIR.mkdir(parents=True)

    WORK_DIR.mkdir(parents=True)
    env = {**dict(__import__("os").environ),
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init"], cwd=WORK_DIR, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=WORK_DIR, capture_output=True, env=env)

    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-planmode-test",
        "version": "0.0.1",
        "description": "Test write during real plan mode"
    }, indent=2))

    # Normal skill
    (PLUGIN_DIR / "skills" / "write-normal").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "write-normal" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: write-normal
        description: Write a verification token to a file path.
        allowed-tools:
          - Write
          - Bash(mkdir *)
        ---

        # Write Normal

        Write "planmode-normal-7k2x" to the file path from $ARGUMENTS.
    """))

    # Forked skill
    (PLUGIN_DIR / "skills" / "write-forked").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "write-forked" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: write-forked
        description: Write a verification token to a file path. Runs in forked context.
        context: fork
        allowed-tools:
          - Write
          - Bash(mkdir *)
        ---

        # Write Forked

        Write "planmode-forked-9m4p" to the file path from $ARGUMENTS.
    """))

    # Subagent skill
    (PLUGIN_DIR / "skills" / "write-subagent").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "write-subagent" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: write-subagent
        description: Dispatch a subagent to write a verification token.
        allowed-tools:
          - Agent
          - Write
          - Bash(mkdir *)
        ---

        # Write Subagent

        Use the Agent tool to launch a subagent. The subagent prompt:
        "Write 'planmode-subagent-3f8q' to {path} using the Write tool. Just create the file."

        Replace {path} with $ARGUMENTS.
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def _run_claude(prompt, allowed_tools, timeout=120, permission_mode="plan"):
    """Run claude -p with real --permission-mode plan."""
    return subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", allowed_tools,
            "--add-dir", str(OUTPUT_DIR),
            "--permission-mode", permission_mode,
            "--disable-slash-commands",
        ],
        capture_output=True, text=True, timeout=timeout,
        cwd=WORK_DIR
    )


def test_01_plan_mode_blocks_direct_writes():
    """Real --permission-mode plan blocks direct Write calls."""
    target = OUTPUT_DIR / "direct.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Write 'should-not-exist' to {target} using Write tool.",
        "Write,Bash(mkdir *)"
    )
    print("Direct stdout:", result.stdout[:500])
    assert not target.exists(), "Direct write succeeded in plan mode!"


def test_02_skill_during_plan_mode():
    """Skill invocation via Skill tool during real plan mode."""
    target = OUTPUT_DIR / "skill-normal.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Use the Skill tool to invoke 'write-normal' with argument '{target}'.",
        "Skill,Write,Bash(mkdir *)"
    )
    print("Normal skill stdout:", result.stdout[:500])
    exists = target.exists()
    content = target.read_text() if exists else ""
    print(f"File exists: {exists}, has token: {'planmode-normal-7k2x' in content}")


def test_03_forked_skill_during_plan_mode():
    """Skill with context:fork during real plan mode."""
    target = OUTPUT_DIR / "skill-forked.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Use the Skill tool to invoke 'write-forked' with argument '{target}'.",
        "Skill,Write,Bash(mkdir *)"
    )
    print("Forked skill stdout:", result.stdout[:500])
    exists = target.exists()
    content = target.read_text() if exists else ""
    print(f"File exists: {exists}, has token: {'planmode-forked-9m4p' in content}")


def test_04_subagent_during_plan_mode():
    """Subagent dispatched from skill during real plan mode."""
    target = OUTPUT_DIR / "subagent.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Use the Skill tool to invoke 'write-subagent' with argument '{target}'.",
        "Skill,Agent,Write,Bash(mkdir *)",
        timeout=180
    )
    print("Subagent stdout:", result.stdout[:500])
    exists = target.exists()
    content = target.read_text() if exists else ""
    print(f"File exists: {exists}, has token: {'planmode-subagent-3f8q' in content}")


def test_05_control_same_setup_without_plan_mode():
    """Same setup but --permission-mode default. Proves the test works when not in plan mode."""
    target = OUTPUT_DIR / "control.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Write 'control-success' to {target} using Write tool.",
        "Write,Bash(mkdir *)",
        permission_mode="default"
    )
    print("Control stdout:", result.stdout[:500])
    assert target.exists(), (
        f"Control test failed - Write doesn't work even outside plan mode!\n"
        f"stdout: {result.stdout[:300]}"
    )
    assert "control-success" in target.read_text()


def test_06_summary():
    """Report which approaches work under real plan mode."""
    results = {}
    for name, filename, magic in [
        ("direct_write", "direct.txt", "should-not-exist"),
        ("normal_skill", "skill-normal.txt", "planmode-normal-7k2x"),
        ("forked_skill", "skill-forked.txt", "planmode-forked-9m4p"),
        ("subagent", "subagent.txt", "planmode-subagent-3f8q"),
        ("control_no_plan", "control.txt", "control-success"),
    ]:
        path = OUTPUT_DIR / filename
        if path.exists() and magic in path.read_text():
            results[name] = "WRITES"
        else:
            results[name] = "BLOCKED"

    print("\n=== Real Plan Mode Results ===")
    for approach, status in results.items():
        print(f"  {approach}: {status}")

    # Control must work
    assert results.get("control_no_plan") == "WRITES", \
        "Control failed - test infrastructure broken"

    # Direct write must be blocked
    assert results.get("direct_write") == "BLOCKED", \
        "Direct write not blocked - plan mode not enforced!"

    # Report what works for /derisk
    plan_mode_approaches = {k: v for k, v in results.items()
                           if k not in ("control_no_plan", "direct_write")}
    working = [k for k, v in plan_mode_approaches.items() if v == "WRITES"]
    blocked = [k for k, v in plan_mode_approaches.items() if v == "BLOCKED"]

    print(f"\nWorking in plan mode: {working or 'NONE'}")
    print(f"Blocked in plan mode: {blocked}")

    if not working:
        print("\n=> /derisk must run BEFORE plan mode or plan mode needs .gutcheck/ exception")


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
