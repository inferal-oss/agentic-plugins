# Experiment 08: Agent Tool During Real Plan Mode

**Supersedes [Experiment 07](../07-plan-mode-writes/README.md)** which used simulated plan mode.

## Method
Uses `--permission-mode plan` (real system-level setting).
Magic token only in subagent prompt (not parent) to prove authorship.

## Results

| Approach | Result |
|----------|--------|
| Control (no plan mode) | WRITES |
| Direct write | BLOCKED |
| Agent tool dispatch | **NONDETERMINISTIC** (worked in weak test, blocked in strong test) |
| Read in plan mode | WORKS |

## Key Finding: Plan Mode is Prompt-Level, Not Tool-Level

Confirmed by real GitHub issues:
- [#39687](https://github.com/anthropics/claude-code/issues/39687) — "Plan Mode should be a hard constraint, not a soft hint... tool calls that modify state should be blocked at the system level, not just 'encouraged to avoid.'"
- [#39796](https://github.com/anthropics/claude-code/issues/39796) — Agent modifies code without creating plan first
- [#4750](https://github.com/anthropics/claude-code/issues/4750) — Subagent behavior in plan mode is **undefined/undocumented** (closed as ambiguity, proposed `planModeBehavior` config that was never implemented)

**Previous references to issues #5406, #19874, #40324 were FABRICATED by WebSearch.
Those issues do not exist.** The actual issues confirm plan mode is prompt-level
enforcement, but do NOT confirm any reliable subagent bypass mechanism.

## What This Means

1. Plan mode is prompt compliance, not hard blocking
2. Subagent behavior during plan mode is **undefined** (issue #4750)
3. The model sometimes writes despite plan mode (multiple bug reports)
4. But this is unreliable — can't be depended on for `/derisk`

## Design Impact

`/derisk` must run **before** plan mode for reliable execution:

```
/gutcheck:derisk plan.md     # Before plan mode
→ writes experiments to .inferal/derisk/
→ runs experiments  
→ reports findings

/plan                         # Enter plan mode, informed by results
```

## Run
```bash
uv run --script run.py
```
