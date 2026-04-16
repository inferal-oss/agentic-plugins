---
name: derisk
description: >
  Validate assumptions in implementation plans before execution. Identifies risks
  through Socratic exploration, formulates testable hypotheses, designs and runs
  experiments, and proposes plan amendments with evidence. Use before executing
  any non-trivial plan, or when a plan feels risky.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(mkdir *)
  - Bash(uv run *)
  - Bash(chmod *)
  - Bash(sh *)
  - Bash(bash *)
  - Agent
  - ExitPlanMode
  - EnterPlanMode
  - AskUserQuestion
argument-hint: "[plan file path or description]"
---

# Derisk: Validate Assumptions Before Execution

Identify what could go wrong in a plan, test those assumptions with experiments,
and propose amendments backed by evidence. Do this before writing any implementation code.

**Announce at start:** "Using the derisk skill to validate assumptions in this plan."

## The Process

Six phases, each with clear entry and exit criteria. Follow them in order.
Phases 1-3 are read-only (safe in plan mode). Phases 4-5 require writes.

---

## Phase 1: Discovery

**Goal:** Understand what tools and patterns are available in this repo.

Check if `.inferal/derisk/config.md` exists:
- **If yes:** Read it. Check if the information is still current (file dates, tool versions).
  Update anything stale.
- **If no:** Scan the repo to discover:
  - Languages used (check file extensions, build files, lockfiles)
  - Test frameworks (pytest, jest, cargo test, go test, etc.)
  - Build tools (make, cargo, npm, uv, gradle, etc.)
  - CI configuration (GitHub Actions, etc.)
  - Any existing `.inferal/derisk/` directories from prior derisking sessions

Write findings to `.inferal/derisk/config.md` in prose. This file is the skill's memory
for this repo. Keep it concise: what matters for designing experiments.

**Exit criterion:** You know what languages and tools are available for experiments.

---

## Phase 2: Socratic Exploration

**Goal:** Surface risks the developer already senses but may not have articulated.

This phase is read-only. It works in plan mode.

### Start from intuition

Ask the developer, one question at a time:

1. "What makes you nervous about this plan?"
2. For each answer, probe one level deeper: "What specifically could go wrong there?"
3. "What's the part you're least sure about?"
4. "Is there anything in this plan you haven't done before?"
5. Continue until the developer says they've covered everything.

Do not rush this. The developer's gut often knows where the risk is before any
systematic analysis can find it.

### Then do systematic analysis

Read the plan (from `$ARGUMENTS` or ask for it). Accept any format: markdown,
clayers XML, plain text description, or a URL to a plan file.

Extract embedded assumptions by category:

| Category | What to look for |
|----------|-----------------|
| **Behavioral** | "This library/API does X." "This function returns Y." |
| **Structural** | "These components compose this way." "This data flows through Z." |
| **Performance** | "This will be fast enough." "This scales to N." |
| **Compatibility** | "A works with B." "This version supports that feature." |
| **Environmental** | "This tool is available." "This service is running." |

**Exit criterion:** A list of risks (developer-identified + systematic). Present
the combined list to the developer.

---

## Phase 3: Hypothesis Formulation

**Goal:** Turn risks into testable hypotheses the developer approves.

For each risk, write:

- **Hypothesis:** One-sentence falsifiable claim. Example: "The Stripe API v2024-12
  supports idempotency keys on payment intent creation."
- **Risk if wrong:** What breaks in the plan if this assumption is false.
- **Cost:** Cheap (a quick script, under 30 seconds), Medium (needs setup or
  network calls), Expensive (needs infrastructure, external service, or long runtime).
- **Method:** How to test it. Be specific: what script to write, what to check.

Present the full list to the developer via AskUserQuestion. Options:
- Run all
- Select which to run (developer picks)
- Add more hypotheses the skill missed
- Skip derisking (developer accepts the risk)

**Exit criterion:** Developer-approved list of hypotheses to test.

---

## Phase 4: Experiment Design

**Goal:** Create self-contained, runnable experiments for each hypothesis.

### Plan mode handling

If plan mode is active (Claude Code only; Codex has no plan mode):
1. Tell the developer: "I need to exit plan mode to write and run experiments.
   You will see an ExitPlanMode prompt. This is expected."
2. Call ExitPlanMode. The developer approves.
3. Proceed with writing.

After experiments complete (end of Phase 5), call EnterPlanMode to return.

### Create the directory structure

```
.inferal/derisk/{plan-name}/
├── hypotheses.md
├── experiments/
│   ├── {experiment-name}/
│   │   ├── README.md
│   │   └── run.{ext}
│   └── ...
├── findings.md          (written in Phase 6)
└── amendments.md        (written in Phase 6)
```

Use a descriptive slug for `{plan-name}` (e.g., `add-auth-feature`, `migrate-database`).

### Design each experiment

For each approved hypothesis, dispatch a **subagent** (via the Agent tool) to design
and write the experiment. This keeps each experiment's context isolated and allows
parallel design when hypotheses are independent.

The subagent's job:
1. Create `experiments/{experiment-name}/README.md` with: hypothesis, method, expected result
2. Create `experiments/{experiment-name}/run.{ext}` as a self-contained executable
   - Use whatever language fits: shell script, Python, Rust, Go, etc.
   - The script must be runnable with a single command (e.g., `bash run.sh`, `uv run --script run.py`)
   - The script must produce clear pass/fail output
   - The script must exit 0 on pass, non-zero on fail

### Quality gate: review before running

**This is the most important step.** Each subagent MUST self-review the experiment
for these anti-patterns before reporting it as ready:

| Anti-pattern | What it looks like | How to fix |
|---|---|---|
| **Fixture self-verification** | Test creates a file, then checks the file exists. Proves nothing about external behavior. | Test must exercise something outside the test's own setup. |
| **Missing negative control** | Test shows X works, but nothing proves X would fail without the mechanism. Permission tests are classic: if you don't prove unauthorized access fails, you haven't proved authorization works. | Add a companion test that removes the mechanism and verifies failure. |
| **Claims vs proof** | Docstring says "proves Codex discovers the skill" but the test just writes a file to /tmp. The model could write that file without any skill discovery. | Use magic tokens: put a unique string ONLY in the thing being tested, never in the prompt. If it appears in output, the mechanism worked. |
| **Missing isolation** | Results change when user plugins, hooks, or settings are present vs absent. | Use `--setting-sources ""` (Claude Code) or equivalent isolation. Document what is isolated and why. |
| **Redundancy** | Two experiments test the same thing with different wording. | Merge or delete one. Every experiment must prove something unique. |
| **Magic token gap** | Testing "who did X" but the prompt tells the model what to write. The model did not need the mechanism to produce the output. | The identifying string must only appear where the mechanism would inject it, never in the prompt. |

The subagent reports its review. If any anti-pattern is found, fix it before proceeding.

**Exit criterion:** All experiments written, reviewed, and ready to run.

---

## Phase 5: Execution

**Goal:** Run experiments and collect results.

Dispatch experiment execution to subagents via the Agent tool:
- One subagent per experiment, or batch independent experiments together
- Run independent experiments in parallel (multiple Agent calls in one message)
- Each subagent:
  1. Runs the experiment script
  2. Captures stdout/stderr
  3. Checks exit code (0 = pass, non-zero = fail)
  4. Reports: PASS/FAIL + captured output + any output files created

Collect all results.

**Exit criterion:** Every experiment has a PASS/FAIL result with captured output.

---

## Phase 6: Findings and Plan Amendment

**Goal:** Consolidate results and propose plan changes backed by evidence.

### Re-enter plan mode

If you exited plan mode in Phase 4, call EnterPlanMode now. The findings
and amendments are read-only analysis: they belong in plan mode context.

### Write findings

Create `.inferal/derisk/{plan-name}/findings.md`:

```markdown
# Findings: {plan-name}

## Summary
- X hypotheses tested
- Y validated, Z invalidated, W inconclusive

## Results

### {hypothesis-name}: VALIDATED
**Hypothesis:** ...
**Evidence:** experiment produced expected output. See `experiments/{name}/`.

### {hypothesis-name}: INVALIDATED
**Hypothesis:** ...
**Evidence:** experiment showed [specific failure]. See `experiments/{name}/`.
**Impact:** [what this means for the plan]

### {hypothesis-name}: INCONCLUSIVE
**Hypothesis:** ...
**Evidence:** [why the result is ambiguous]
**Recommendation:** [what to do: re-test with better method, accept risk, etc.]
```

### Write amendments

Create `.inferal/derisk/{plan-name}/amendments.md`:

```markdown
# Proposed Plan Amendments: {plan-name}

## Amendment 1: [short description]
**Triggered by:** [hypothesis-name] INVALIDATED [evidence: experiment-name]
**Change:** [what to change in the plan]
**If not changed:** [what goes wrong]

## Amendment 2: ...
```

### Present to developer

Show the findings summary and proposed amendments. The developer decides
which amendments to accept. Update the plan accordingly (or let the developer
do it manually in their editor).

---

## Notes

### Experiment language choice

Use whatever language fits the hypothesis:
- **Shell scripts** for CLI tools, environment checks, network probes
- **Python** for API testing, data validation, complex logic
- **The project's own language** for testing library behavior, compilation, type checking
- **Any language** available in `.inferal/derisk/config.md`

When using Python, prefer `uv run --script` with PEP 723 inline dependencies.
When using shell, prefer `bash` or `sh` for portability.

### Experiments are evidence

Experiments are not throwaway. They persist in `.inferal/derisk/{plan-name}/experiments/`.
If a problem occurs during execution that was tested during derisking, the experiment
is the first place to look: did we test for this? Did the test pass? Was the test valid?

The developer chooses whether to gitignore `.inferal/derisk/` or commit it.

### Handling large plans

For plans with many steps, focus derisking on the highest-risk assumptions.
Not every step needs an experiment. The Socratic phase helps identify which
risks are worth the cost of validation.

### Re-running after plan changes

If the plan changes after derisking (e.g., amendments are accepted), the developer
can re-run `/gutcheck:derisk` on the updated plan. The skill will read existing
findings and focus on new or changed assumptions.
