# Experiment 04: Skill Invocation from Subagents

## Hypotheses
1. Subagent can create files directly via Write (baseline)
2. Subagent can invoke a plugin skill via Skill tool (skills inherited from parent)

## Results: ALL PASSED (2/2)

### Key Findings

1. **Subagents inherit plugin skills**: A skill loaded via `--plugin-dir` in the parent session is available to subagents spawned via the Agent tool.
2. **Full pipeline works in subagent**: Agent tool → subagent → Skill tool → SKILL.md loaded → instructions followed → file created with expected content.
3. **Direct file creation also works**: Subagents can use Write/Bash directly without skill invocation (fallback path).

### Implication for gutcheck

`/derisk` can formulate experiments in the main context, then dispatch subagents to execute them:
- Saves main context window from experiment output noise
- Each experiment runs in isolation
- Skill's `allowed-tools` auto-approve in the subagent context
- Results written to `.inferal/derisk/derisk/experiments/` persist on disk for the parent to read

## Run
```bash
uv run --script run.py
```
