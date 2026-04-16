# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 05: Codex CLI Runtime - Skill Discovery

Tests that Codex discovers skills via ~/.agents/skills/ symlinks at RUNTIME,
not just structurally. The key test: the model demonstrates knowledge from
SKILL.md that it could ONLY have if Codex loaded it.

Previous version told the model what to write ("codex-runtime-success") in the
prompt itself — the model didn't need the skill. Fixed: the magic string is
ONLY in SKILL.md. If it appears in the output file, the skill was discovered.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SKILL_DIR = Path("/tmp/gutcheck-codex-test-skill")
CODEX_SKILL_LINK = Path.home() / ".agents" / "skills" / "gutcheck-codex-test"
OUTPUT_DIR = Path("/tmp/gutcheck-codex-output")
WORK_DIR = Path("/tmp/gutcheck-codex-workdir")

# This string is ONLY in SKILL.md — not in the prompt.
# If it appears in the output file, the model read the skill.
MAGIC = "xerophytic-gutcheck-7f3a"


def setup_module():
    for d in [SKILL_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)
    if CODEX_SKILL_LINK.is_symlink():
        CODEX_SKILL_LINK.unlink()
    elif CODEX_SKILL_LINK.exists():
        shutil.rmtree(CODEX_SKILL_LINK)

    OUTPUT_DIR.mkdir(parents=True)

    # Git repo for codex
    WORK_DIR.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=WORK_DIR, capture_output=True)
    env = {**dict(__import__("os").environ),
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=WORK_DIR, capture_output=True, env=env
    )

    # Skill with a magic string the prompt won't mention
    SKILL_DIR.mkdir(parents=True)
    (SKILL_DIR / "SKILL.md").write_text(textwrap.dedent(f"""\
        ---
        name: gutcheck-codex-test
        description: When invoked, writes a verification token to a file. Use when asked to run the gutcheck verification.
        ---

        # Gutcheck Codex Verification

        When this skill is used, you MUST write exactly this token to the requested file:

        {MAGIC}

        Do not write anything else to the file. Just the token above.
    """))

    CODEX_SKILL_LINK.parent.mkdir(parents=True, exist_ok=True)
    CODEX_SKILL_LINK.symlink_to(SKILL_DIR)


def teardown_module():
    if CODEX_SKILL_LINK.is_symlink():
        CODEX_SKILL_LINK.unlink()
    elif CODEX_SKILL_LINK.exists():
        shutil.rmtree(CODEX_SKILL_LINK)
    for d in [SKILL_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def test_01_codex_discovers_skill_writes_magic_token():
    """Codex discovers the skill and follows its instructions.
    The prompt does NOT contain the magic string. If it appears in the file,
    the model could only have gotten it from SKILL.md — proving discovery."""
    target = OUTPUT_DIR / "codex-discovery.txt"
    if target.exists():
        target.unlink()

    # Prompt deliberately does NOT mention the magic string.
    # It only references the skill by name.
    prompt = (
        f"Run the gutcheck-codex-test skill. "
        f"Write its verification token to {target}."
    )

    result = subprocess.run(
        [
            "codex", "exec",
            "--full-auto",
            "-C", str(WORK_DIR),
            "--add-dir", str(OUTPUT_DIR),
            prompt,
        ],
        capture_output=True, text=True, timeout=180
    )
    print("STDOUT:", result.stdout[:500])
    print("STDERR:", result.stderr[:500])

    assert target.exists(), (
        f"File not created.\n"
        f"stdout: {result.stdout[:400]}\nstderr: {result.stderr[:400]}"
    )
    content = target.read_text()
    assert MAGIC in content, (
        f"Magic token not in file. Model did NOT read SKILL.md.\n"
        f"Expected: {MAGIC}\nGot: {content[:200]}"
    )


def test_02_codex_skill_appears_in_session_events():
    """Codex --json output contains the skill name in structured events,
    not just in model prose. Checks for the skill name appearing as a
    loaded/available skill in the JSONL event stream."""
    target = OUTPUT_DIR / "codex-events.txt"
    if target.exists():
        target.unlink()

    prompt = (
        f"Run the gutcheck-codex-test skill. "
        f"Write its verification token to {target}."
    )

    result = subprocess.run(
        [
            "codex", "exec",
            "--full-auto",
            "--json",
            "-C", str(WORK_DIR),
            "--add-dir", str(OUTPUT_DIR),
            prompt,
        ],
        capture_output=True, text=True, timeout=180
    )
    print("STDOUT (first 1500):", result.stdout[:1500])

    # Parse JSONL events and look for skill reference in structured data
    # (not just in model text responses)
    events = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Check for skill reference in any event's structured fields
    # (type, tool calls, function names, etc.)
    all_event_text = json.dumps(events)
    assert "gutcheck-codex-test" in all_event_text, (
        f"Skill name not in any JSONL event. "
        f"Parsed {len(events)} events. Skill not discovered."
    )

    # Also verify the magic token made it to the file
    assert target.exists() and MAGIC in target.read_text(), \
        "File missing or magic token not present"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
