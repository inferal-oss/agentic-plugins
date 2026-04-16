# Experiment 07: Writing During Simulated Plan Mode

**NOTE: This experiment used `--system-prompt` to simulate plan mode, NOT real
`--permission-mode plan`. Results are INCOMPLETE. See [Experiment 08](../08-plan-mode-task-tool/README.md)
for the real plan mode test, which found that Agent tool subagents CAN write.**

## Method
Simulated plan mode via `--system-prompt` with restriction text.

## Results (simulated only)

| Approach | Status |
|----------|--------|
| Direct write | BLOCKED |
| Normal skill | BLOCKED |
| `context: fork` skill | BLOCKED |
| Subagent (Agent tool) | BLOCKED |

## Why These Results Were Wrong

`--system-prompt` replaces the entire system prompt with plan mode text. The model
follows it faithfully in `-p` mode. But this is stricter than real plan mode because:
- Real plan mode adds restrictions as a system reminder, not the whole prompt
- Real plan mode's Agent tool dispatch creates subagents that don't inherit the restriction
- The model in `-p` mode is more compliant with restrictions than in interactive mode

**Experiment 08 proves Agent tool subagents escape real plan mode.** `/derisk` can
dispatch experiment execution via subagents during planning.

## Run
```bash
uv run --script run.py
```
