# /// script
# dependencies = ["pytest"]
# ///

"""
Experiment 06: Pair Skill - Classification Quality

Tests the core hypothesis of /pair: can the model reliably distinguish
mechanical steps (→ ai) from thoughtful/ownership-critical steps (→ yours)?

Method: Provide a plan with 6 steps - 3 obviously mechanical, 3 obviously
thoughtful. Ask the model to classify each as "ai" or "yours" and output
structured JSON. Check accuracy.

Also tests:
- Annotation format survives in markdown (markers don't break content)
- Scaffolding output: can the model produce a file skeleton and stop?
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_DIR = Path("/tmp/gutcheck-pair-test")
OUTPUT_DIR = Path("/tmp/gutcheck-pair-output")
WORK_DIR = Path("/tmp/gutcheck-pair-workdir")

SAMPLE_PLAN = textwrap.dedent("""\
    # Plan: Add User Authentication

    ## Step 1: Create database migration file
    Add a migration that creates the `users` table with columns: id, email,
    password_hash, created_at. Use the existing migration framework pattern
    from migrations/001_create_posts.py as a template.

    ## Step 2: Design the session token strategy
    Decide between JWT with refresh tokens vs server-side sessions with Redis.
    Consider the trade-offs: stateless vs revocability, token size vs lookup cost,
    expiry strategy. This choice affects the entire auth architecture.

    ## Step 3: Add password hashing utility
    Create src/auth/password.py with hash_password() and verify_password() using
    bcrypt. Follow the same module pattern as src/auth/tokens.py. Include type
    annotations.

    ## Step 4: Implement the core authentication logic
    Write the authenticate() function that validates credentials, creates a session,
    and handles the error cases. This is the central piece - it needs to handle
    timing attacks, account lockout thresholds, and the state machine for
    login attempts.

    ## Step 5: Generate OpenAPI schema from route definitions
    Run the schema generator on the new auth routes to produce the OpenAPI YAML.
    Copy the pattern from scripts/generate_schema.py. Update the CI config to
    include the new routes.

    ## Step 6: Define the error handling philosophy for auth failures
    Decide what information to reveal vs hide in error responses. Balance
    security (don't leak whether an email exists) against UX (helpful error
    messages). This policy will be referenced by every auth endpoint.
""")

# Ground truth: what a reasonable classification should be
EXPECTED = {
    "Step 1": "ai",     # Template-following migration, mechanical
    "Step 2": "yours",  # Architecture decision, multiple valid approaches
    "Step 3": "ai",     # Boilerplate utility following existing pattern
    "Step 4": "yours",  # Core logic, security-sensitive, needs deep understanding
    "Step 5": "ai",     # Running a generator, copying a pattern
    "Step 6": "yours",  # Policy decision, security/UX trade-off
}


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

    # Write the sample plan
    (OUTPUT_DIR / "plan.md").write_text(SAMPLE_PLAN)

    (PLUGIN_DIR / ".claude-plugin").mkdir(parents=True)
    (PLUGIN_DIR / "skills" / "pair-test").mkdir(parents=True)

    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "gutcheck-pair-test",
        "version": "0.0.1",
        "description": "Test fixture for pair classification experiment"
    }, indent=2))

    (PLUGIN_DIR / "skills" / "pair-test" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: pair-test
        description: Classify plan steps as ai or yours. Use when asked to classify or annotate a plan for pair programming.
        allowed-tools:
          - Read
          - Write
        ---

        # Pair Classification Skill

        Read the plan file provided as $ARGUMENTS.

        For each step, classify it as:
        - **ai**: Mechanical, follows existing patterns, boilerplate, repetitive.
          The developer gains nothing by typing this themselves.
        - **yours**: Requires design decisions, has multiple valid approaches,
          involves core logic the developer needs to deeply understand,
          or sets policy that other code will reference.

        Output a JSON object to a file called `classification.json` in the same
        directory as the plan. Format:
        ```json
        {
          "Step 1": {"classification": "ai", "reason": "..."},
          "Step 2": {"classification": "yours", "reason": "..."},
          ...
        }
        ```

        Be honest. Most plans have a mix. Don't default to "ai" for everything.
    """))


def teardown_module():
    for d in [PLUGIN_DIR, OUTPUT_DIR, WORK_DIR]:
        if d.exists():
            shutil.rmtree(d)


def test_01_classification_accuracy():
    """Model classifies 6 plan steps. At least 5/6 must match ground truth.
    3 steps are clearly mechanical, 3 are clearly thoughtful."""
    plan_path = OUTPUT_DIR / "plan.md"
    classification_path = OUTPUT_DIR / "classification.json"
    if classification_path.exists():
        classification_path.unlink()

    prompt = (
        f"Use the Skill tool to invoke the 'pair-test' skill with argument '{plan_path}'. "
        f"It will read the plan and write classification.json. Report what it produced."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Skill,Read,Write",
            "--add-dir", str(OUTPUT_DIR),
        ],
        capture_output=True, text=True, timeout=120,
        cwd=WORK_DIR
    )
    print("STDOUT:", result.stdout[:500])

    assert classification_path.exists(), (
        f"classification.json not created.\n"
        f"stdout: {result.stdout[:400]}"
    )

    data = json.loads(classification_path.read_text())
    print("Classification:", json.dumps(data, indent=2))

    correct = 0
    total = len(EXPECTED)
    for step, expected_class in EXPECTED.items():
        if step in data:
            got = data[step].get("classification", data[step]) if isinstance(data[step], dict) else data[step]
            if got == expected_class:
                correct += 1
                print(f"  {step}: {got} == {expected_class} ✓")
            else:
                print(f"  {step}: {got} != {expected_class} ✗")
        else:
            print(f"  {step}: MISSING ✗")

    print(f"\nAccuracy: {correct}/{total}")
    assert correct >= 5, (
        f"Classification accuracy too low: {correct}/{total}. "
        f"Model cannot reliably distinguish mechanical from thoughtful steps."
    )


def test_02_annotations_survive_in_markdown():
    """Plan annotated with HTML comment markers remains valid markdown.
    Tests that <!-- pair:yours --> style markers don't break content."""
    annotated = OUTPUT_DIR / "plan-annotated.md"
    if annotated.exists():
        annotated.unlink()

    prompt = (
        f"Read {OUTPUT_DIR / 'plan.md'} and create an annotated copy at {annotated}. "
        f"Before each step heading (## Step N), insert a marker comment: "
        f"<!-- pair:ai --> or <!-- pair:yours --> based on whether the step is "
        f"mechanical or thoughtful. Keep all original content intact."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--dangerously-skip-permissions",
            "--add-dir", str(OUTPUT_DIR),
            "--disable-slash-commands",
            "--system-prompt", "You are a helpful assistant. Follow instructions exactly."
        ],
        capture_output=True, text=True, timeout=120,
        cwd=WORK_DIR
    )
    print("Annotate stdout:", result.stdout[:500])
    print("Annotate stderr:", result.stderr[:500])

    assert annotated.exists(), f"Annotated plan not created. stdout: {result.stdout[:300]}"

    content = annotated.read_text()
    # Original content preserved
    assert "# Plan: Add User Authentication" in content, "Title missing"
    assert "## Step 1" in content, "Step 1 heading missing"
    assert "## Step 6" in content, "Step 6 heading missing"

    # Annotations present
    assert "<!-- pair:" in content, "No pair annotations found"

    # At least some yours and some ai markers
    has_yours = "<!-- pair:yours -->" in content or "<!-- pair: yours -->" in content
    has_ai = "<!-- pair:ai -->" in content or "<!-- pair: ai -->" in content
    assert has_yours and has_ai, (
        f"Expected both ai and yours markers. "
        f"yours: {has_yours}, ai: {has_ai}\n"
        f"Content preview: {content[:500]}"
    )


def test_03_scaffolding_produces_skeleton_not_implementation():
    """When told to scaffold a 'yours' step, model creates file structure
    (signatures, types, docstrings) but NOT the implementation body."""
    scaffold_dir = OUTPUT_DIR / "scaffold"
    if scaffold_dir.exists():
        shutil.rmtree(scaffold_dir)
    scaffold_dir.mkdir()

    target = scaffold_dir / "authenticate.py"

    prompt = (
        f"You are scaffolding Step 4 from this plan (the core authentication logic). "
        f"Create ONLY the file skeleton at {target}: "
        f"imports, function signature with type annotations, docstring explaining "
        f"what the developer needs to implement, and a 'raise NotImplementedError' body. "
        f"Do NOT write the actual implementation. The developer will fill it in."
    )
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--setting-sources", "",  # Isolate from user plugins/hooks
            "--dangerously-skip-permissions",
            "--add-dir", str(OUTPUT_DIR),
            "--disable-slash-commands",
            "--system-prompt", "You are a helpful assistant. Follow instructions exactly."
        ],
        capture_output=True, text=True, timeout=120,
        cwd=WORK_DIR
    )
    print("Scaffold stdout:", result.stdout[:500])
    print("Scaffold stderr:", result.stderr[:500])

    assert target.exists(), f"Scaffold file not created. stdout: {result.stdout[:300]}"

    content = target.read_text()
    print("Scaffold content:\n", content)

    # Should have structure
    assert "def " in content, "No function definition found"
    assert "authenticate" in content.lower(), "Function not named authenticate"

    # Should NOT have real implementation
    has_placeholder = (
        "NotImplementedError" in content
        or "pass" in content
        or "..." in content
        or "TODO" in content
        or "raise" in content
    )
    assert has_placeholder, (
        "Scaffold appears to contain real implementation instead of a placeholder. "
        "The developer should write this part."
    )

    # Extract executable lines (not docstrings, comments, or type annotations)
    # The function body should be ONLY raise/pass/..., not real logic
    import ast
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "authenticate" in node.name.lower():
                # Check the function body: should be just Raise/Pass/Expr(Constant)
                for stmt in node.body:
                    # Skip docstring (first Expr with string Constant)
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        continue
                    # Allow raise NotImplementedError
                    if isinstance(stmt, ast.Raise):
                        continue
                    # Allow pass
                    if isinstance(stmt, ast.Pass):
                        continue
                    # Anything else is real implementation
                    assert False, (
                        f"Scaffold has real implementation in function body: "
                        f"{ast.dump(stmt)}. Developer should write this."
                    )
    except SyntaxError:
        # If it's not valid Python, that's also a problem
        assert False, f"Scaffold is not valid Python: {content[:200]}"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=long"]))
