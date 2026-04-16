# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 04: Skill Invocation from Subagents

Tests whether a skill loaded via --plugin-dir is available to subagents
spawned via the Agent tool. Critical for /derisk: the main skill formulates
experiments, then dispatches subagents to execute them (saving context window).

Hypotheses:
1. Subagent can invoke a skill via Skill tool and create files
2. Subagent inherits plugin skills from the parent session
3. Direct subagent file creation (no skill) also works as fallback
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-subagent-test")
OUTPUT_DIR = Path("/tmp/gutcheck-subagent-output")
# Run from a clean dir so we don't inherit workspace plan mode or hooks
WORK_DIR = Path("/tmp/gutcheck-subagent-workdir")


def setup_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)
    OUTPUT_DIR.mkdir(parents=True)
    # Create a clean git repo to run from (avoids inheriting workspace plan mode)
    WORK_DIR.mkdir(parents=True)
    env = {**dict(__import__("os").environ),
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init"], cwd=WORK_DIR, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=WORK_DIR, capture_output=True, env=env)

    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "experiment-runner").mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-subagent-test",
        "version": "0.0.1",
        "description": "Test skill availability in subagent context"
    }, indent=2))

    (PLUGIN_DIR / "skills" / "experiment-runner" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: experiment-runner
        description: Run a derisking experiment. Creates output files with results. Use when asked to run an experiment or test.
        allowed-tools:
          - Write
          - Bash(mkdir *)
          - Bash(uv run *)
          - Read
        ---

        # Experiment Runner

        When invoked, write "subagent-skill-success" to the file path from $ARGUMENTS.
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def test_01_subagent_can_create_files_directly():
    """Subagent can create files via Write without skill invocation.
    Baseline: Agent tool works and subagent has tool access."""
    target = OUTPUT_DIR / "subagent-direct.txt"
    if target.exists():
        target.unlink()

    prompt = (
        f"Use the Agent tool to launch a subagent with this prompt: "
        f"'Use the Write tool to create the file {target} with content "
        f"subagent-direct-success. Output only the path.' "
        f"Wait for it to finish and report the result."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Agent,Write,Bash(mkdir *)",
            "--add-dir", str(OUTPUT_DIR),
        ],
        capture_output=True, text=True, timeout=180,
        cwd=WORK_DIR  # Clean dir avoids inheriting workspace plan mode
    )
    print("Direct stdout:", result.stdout[:500])
    print("Direct stderr:", result.stderr[:500])

    assert target.exists(), (
        f"Subagent failed to create file directly.\n"
        f"stdout: {result.stdout[:400]}\nstderr: {result.stderr[:200]}"
    )
    assert "subagent-direct-success" in target.read_text()


def test_02_subagent_can_invoke_skill():
    """Subagent can invoke a plugin skill via Skill tool.
    Proves skills are inherited by subagents from parent session."""
    target = OUTPUT_DIR / "subagent-skill.txt"
    if target.exists():
        target.unlink()

    prompt = (
        f"Use the Agent tool to launch a subagent with this prompt: "
        f"'Use the Skill tool to invoke the experiment-runner skill with "
        f"argument {target}. The skill will write a file. Report what happened.' "
        f"Wait for it to finish and report the result."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Agent,Skill,Write,Bash(mkdir *)",
            "--add-dir", str(OUTPUT_DIR),
        ],
        capture_output=True, text=True, timeout=180,
        cwd=WORK_DIR
    )
    print("Skill stdout:", result.stdout[:500])
    print("Skill stderr:", result.stderr[:500])

    assert target.exists(), (
        f"Subagent failed to create file via skill invocation.\n"
        f"stdout: {result.stdout[:400]}\nstderr: {result.stderr[:200]}"
    )
    content = target.read_text()
    assert "subagent-skill-success" in content, \
        f"Skill instructions not followed in subagent. Content: {content}"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
