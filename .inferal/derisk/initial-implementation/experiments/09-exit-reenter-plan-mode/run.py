# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 09: Exit Plan Mode → Write → Re-enter (ISOLATED)

Previous runs were contaminated by ~/.claude/settings.json (superpowers plugin,
auto mode, hooks, etc). This version uses --setting-sources "" to load NO settings
while keeping OAuth auth from ~/.claude.json.

Tests whether /derisk can: exit plan mode → write experiments → re-enter plan mode.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

OUTPUT_DIR = Path("/tmp/gutcheck-exitreenter-output")
WORK_DIR = Path("/tmp/gutcheck-exitreenter-workdir")

MAGIC = "exitreenter-isolated-9v2k"


def setup_module():
    for d in [OUTPUT_DIR, WORK_DIR]:
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

    # Pre-create experiment script for test_03
    (OUTPUT_DIR / "experiment.py").write_text(textwrap.dedent(f"""\
        from pathlib import Path
        out = Path(__file__).parent / "experiment-result.txt"
        out.write_text("{MAGIC}-script-ok")
        print(f"wrote {{out}}")
    """))


def teardown_module():
    for d in [OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def _run_isolated(prompt, allowed_tools, timeout=120, permission_mode="plan"):
    """Run claude -p with full isolation: no plugins, no hooks, no user settings."""
    return subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",        # NO settings (no plugins, hooks, auto mode)
            "--disable-slash-commands",      # No built-in skills interfering
            "--allowedTools", allowed_tools,
            "--add-dir", str(OUTPUT_DIR),
            "--permission-mode", permission_mode,
        ],
        capture_output=True, text=True, timeout=timeout,
        cwd=WORK_DIR
    )


def test_01_isolated_plan_mode_blocks_direct_write():
    """Baseline: plan mode blocks Write in a clean, isolated session."""
    target = OUTPUT_DIR / "direct.txt"
    if target.exists():
        target.unlink()

    result = _run_isolated(
        f"Write '{MAGIC}' to {target} using the Write tool.",
        "Write"
    )
    print("Direct stdout:", result.stdout[:500])
    assert not target.exists(), "Direct write succeeded in isolated plan mode!"


def test_02_exit_plan_mode_then_write():
    """ExitPlanMode → Write. Uses --dangerously-skip-permissions to auto-approve
    the ExitPlanMode prompt (simulates user clicking approve)."""
    target = OUTPUT_DIR / "exit-write.txt"
    if target.exists():
        target.unlink()

    result = subprocess.run(
        [
            "claude", "-p",
            (f"You are in plan mode. To run a derisking experiment, you need to "
             f"exit plan mode first. Call ExitPlanMode, then use Write to create "
             f"{target} with content '{MAGIC}'. Report each step."),
            "--setting-sources", "",
            "--disable-slash-commands",
            "--allowedTools", "ExitPlanMode,Write,Bash(mkdir *)",
            "--add-dir", str(OUTPUT_DIR),
            "--permission-mode", "plan",
            "--dangerously-skip-permissions",  # Auto-approve ExitPlanMode
        ],
        capture_output=True, text=True, timeout=180,
        cwd=WORK_DIR
    )
    print("Exit+Write stdout:", result.stdout[:800])
    print("Exit+Write stderr:", result.stderr[:300])

    exists = target.exists()
    content = target.read_text() if exists else ""
    print(f"File exists: {exists}")
    if exists:
        print(f"Content: {content}")

    assert exists, f"File not created after ExitPlanMode. stdout: {result.stdout[:500]}"
    assert MAGIC in content, f"Wrong content: {content}"


def test_03_exit_run_script_reenter():
    """Full /derisk cycle: exit → run experiment script → read result → re-enter."""
    result_file = OUTPUT_DIR / "experiment-result.txt"
    if result_file.exists():
        result_file.unlink()

    script = OUTPUT_DIR / "experiment.py"

    result = subprocess.run(
        [
            "claude", "-p",
            (f"You are derisking a plan. Follow these steps exactly: "
             f"1. Call ExitPlanMode to leave plan mode. "
             f"2. Run: uv run {script} "
             f"3. Read {result_file} and report its contents. "
             f"4. Call EnterPlanMode to re-enter plan mode. "
             f"Report the outcome of each step."),
            "--setting-sources", "",
            "--disable-slash-commands",
            "--allowedTools", "ExitPlanMode,EnterPlanMode,Bash(uv run *),Read",
            "--add-dir", str(OUTPUT_DIR),
            "--permission-mode", "plan",
            "--dangerously-skip-permissions",
        ],
        capture_output=True, text=True, timeout=180,
        cwd=WORK_DIR
    )
    print("Full cycle stdout:", result.stdout[:1000])
    print("Full cycle stderr:", result.stderr[:300])

    exists = result_file.exists()
    content = result_file.read_text() if exists else ""
    print(f"Script result exists: {exists}")
    if exists:
        print(f"Content: {content}")

    # Check if re-enter was attempted
    stdout_lower = result.stdout.lower()
    entered_plan = "enterplanmode" in stdout_lower or "enter plan" in stdout_lower
    print(f"Re-enter attempted: {entered_plan}")


def test_04_summary():
    """Report results."""
    results = {}
    checks = [
        ("direct_write", "direct.txt", MAGIC),
        ("exit_then_write", "exit-write.txt", MAGIC),
        ("exit_run_script", "experiment-result.txt", f"{MAGIC}-script-ok"),
    ]

    for name, filename, magic in checks:
        path = OUTPUT_DIR / filename
        if path.exists() and magic in path.read_text():
            results[name] = "WORKS"
        else:
            results[name] = "BLOCKED"

    print("\n=== Isolated Exit-Reenter Results ===")
    for approach, status in results.items():
        print(f"  {approach}: {status}")

    assert results["direct_write"] == "BLOCKED", "Plan mode not enforced"

    if results["exit_then_write"] == "WORKS":
        print("\n=> ExitPlanMode + Write WORKS in isolated session!")
        print("=> /derisk can: exit plan mode → write experiments → re-enter")
    else:
        print("\n=> ExitPlanMode + Write still blocked even in isolated session")
        print("=> /derisk must run before plan mode")


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long", "-s"]))
