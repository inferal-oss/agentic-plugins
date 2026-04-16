# Dogfooding: gutcheck derisked itself

This directory contains the derisking experiments from the gutcheck plugin's creation.
The plugin was built using its own methodology: identify risks, formulate hypotheses,
design experiments, run them, and use findings to shape the design.

9 experiments, 31/33 tests pass (2 expected failures).

See [findings.md](findings.md) for the full results summary.
See [experiments/](experiments/) for all experiment scripts and READMEs.

## What was derisked

- Plugin format works for both Claude Code and Codex CLI
- Skills can create files via allowed-tools
- Skill invocation pipeline (Skill tool -> SKILL.md -> output)
- Subagents inherit plugin skills
- Codex discovers skills at runtime (magic token proof)
- Pair classification quality (5/6+ accuracy on obvious cases)
- Plan mode behavior (writes blocked; ExitPlanMode -> work -> EnterPlanMode works)

## Running the experiments

```bash
for exp in experiments/*/run.py; do
  echo "=== $(dirname $exp | xargs basename) ==="
  uv run --script "$exp"
  echo
done
```

Note: experiments use `--setting-sources ""` for isolation from user plugins and hooks.
