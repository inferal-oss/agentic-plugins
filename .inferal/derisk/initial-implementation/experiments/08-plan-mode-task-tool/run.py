# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 08: Agent Tool Bypasses Real Plan Mode

Uses --permission-mode plan (real system-level enforcement).
Tests whether Agent-dispatched subagents can write files during plan mode.

Key design: the magic string ONLY appears in the Agent prompt (the subagent's
instructions), never in the parent prompt or allowedTools. If the magic string
appears in the output file, the SUBAGENT wrote it, not the parent.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-planmode-agent")
OUTPUT_DIR = Path("/tmp/gutcheck-planmode-agent-output")
WORK_DIR = Path("/tmp/gutcheck-planmode-agent-workdir")

# Magic token ONLY in the Agent dispatch prompt, never in parent context
MAGIC = "zephyr-planmode-4q8r"


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
        "name": "gutcheck-planmode-agent",
        "version": "0.0.1",
        "description": "Test Agent tool during real plan mode"
    }, indent=2))

    # Create a test script the subagent should execute
    (OUTPUT_DIR / "experiment.py").write_text(textwrap.dedent(f"""\
        from pathlib import Path
        out = Path(__file__).parent / "script-result.txt"
        out.write_text("{MAGIC}-script")
        print(f"wrote {{out}}")
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def _run_claude(prompt, allowed_tools, timeout=120, permission_mode="plan"):
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


def test_01_control_writes_work_without_plan_mode():
    """Control: writes succeed with default permission mode."""
    target = OUTPUT_DIR / "control.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Write 'control-ok' to {target} using Write tool.",
        "Write", permission_mode="default"
    )
    assert target.exists(), f"Control failed: {result.stdout[:300]}"
    assert "control-ok" in target.read_text()


def test_02_plan_mode_blocks_direct_write():
    """Plan mode blocks direct Write from the parent model."""
    target = OUTPUT_DIR / "direct.txt"
    if target.exists():
        target.unlink()

    result = _run_claude(
        f"Write 'should-not-exist' to {target} using Write tool.",
        "Write"
    )
    print("Direct stdout:", result.stdout[:500])
    assert not target.exists(), "Direct write succeeded in plan mode!"


def test_03_agent_subagent_writes_during_plan_mode():
    """Agent tool subagent writes a file during real plan mode.
    The magic token ONLY appears in the subagent prompt (not the parent prompt).
    If it's in the output file, the subagent wrote it."""
    target = OUTPUT_DIR / "agent-write.txt"
    if target.exists():
        target.unlink()

    # Parent prompt does NOT contain the magic token.
    # It tells the model to dispatch a subagent with a specific prompt.
    # The magic token is embedded in the subagent's instructions.
    prompt = (
        f"Use the Agent tool to launch a subagent. "
        f"The subagent's prompt must be exactly: "
        f"\"Write '{MAGIC}' to {target} using the Write tool. Output only the path.\" "
        f"Report the subagent's result."
    )

    result = _run_claude(
        prompt,
        "Agent,Write,Bash(mkdir *)",
        timeout=180
    )
    print("Agent stdout:", result.stdout[:500])

    assert target.exists(), (
        f"Subagent failed to write file during plan mode.\n"
        f"stdout: {result.stdout[:400]}"
    )
    content = target.read_text()
    assert MAGIC in content, (
        f"Magic token not in file. Parent may have written directly.\n"
        f"Content: {content[:200]}"
    )


def test_04_agent_subagent_runs_script_during_plan_mode():
    """Agent tool subagent can execute uv run during plan mode.
    The script writes a file with a magic token variant."""
    result_file = OUTPUT_DIR / "script-result.txt"
    if result_file.exists():
        result_file.unlink()

    script = OUTPUT_DIR / "experiment.py"
    prompt = (
        f"Use the Agent tool to launch a subagent. "
        f"The subagent's prompt must be: "
        f"\"Run this command: uv run {script} -- then report what it printed.\" "
        f"Report the result."
    )

    result = _run_claude(
        prompt,
        "Agent,Bash(uv run *),Write",
        timeout=180
    )
    print("Script stdout:", result.stdout[:500])

    assert result_file.exists(), (
        f"Script output file not created by subagent.\n"
        f"stdout: {result.stdout[:400]}"
    )
    content = result_file.read_text()
    assert f"{MAGIC}-script" in content, (
        f"Script magic token not in result. Content: {content[:200]}"
    )


def test_05_parent_can_read_subagent_output_in_plan_mode():
    """Parent in plan mode can Read files. Critical for /derisk: main context
    reads experiment results back. Uses a pre-existing file (not from test_03)."""
    # Create a file to read - simulates experiment results existing on disk
    target = OUTPUT_DIR / "read-test.txt"
    target.write_text(f"results: {MAGIC}")

    prompt = (
        f"Read the file {target} and tell me its exact contents. "
        f"Output ONLY the file contents, nothing else."
    )

    result = _run_claude(
        prompt,
        "Read",
    )
    print("Read stdout:", result.stdout[:500])

    assert MAGIC in result.stdout, (
        f"Parent could not read subagent output during plan mode.\n"
        f"stdout: {result.stdout[:300]}"
    )


def test_06_summary():
    """Report results. Agent bypass is nondeterministic (works sometimes, not always)."""
    results = {}
    checks = [
        ("control", "control.txt", "control-ok"),
        ("direct_write", "direct.txt", "should-not-exist"),
        ("agent_write", "agent-write.txt", MAGIC),
        ("agent_script", "script-result.txt", f"{MAGIC}-script"),
    ]

    for name, filename, magic in checks:
        path = OUTPUT_DIR / filename
        if path.exists() and magic in path.read_text():
            results[name] = "WRITES"
        else:
            results[name] = "BLOCKED"

    print("\n=== Real Plan Mode + Agent Tool Results ===")
    for approach, status in results.items():
        print(f"  {approach}: {status}")

    # Hard assertions: control works, plan mode enforced
    assert results["control"] == "WRITES", "Control broken"
    assert results["direct_write"] == "BLOCKED", "Plan mode not enforced"

    # Report Agent tool status (nondeterministic - don't assert)
    agent_works = results.get("agent_write") == "WRITES"
    script_works = results.get("agent_script") == "WRITES"
    print(f"\nAgent write bypass: {'WORKS' if agent_works else 'BLOCKED this run'}")
    print(f"Agent script bypass: {'WORKS' if script_works else 'BLOCKED this run'}")

    if not agent_works and not script_works:
        print(
            "\n=> Agent bypass did NOT work this run. "
            "This is nondeterministic (model compliance varies). "
            "/derisk should run BEFORE plan mode for reliability."
        )


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long", "-s"]))
