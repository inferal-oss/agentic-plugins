# Experiment 03: Skill Invocation & allowed-tools Behavior

## Hypotheses
1. No tool authorization → Write blocked (negative control)
2. Full skill invocation pipeline works: Skill tool → load SKILL.md → follow instructions → create file
3. SKILL.md `allowed-tools` does NOT override `--allowedTools` session ceiling
4. Permissions don't leak across runs

## Results: ALL PASSED (4/4)

### Key Finding: What `allowed-tools` Actually Does

`allowed-tools` in SKILL.md is **auto-approval within existing permissions**, not privilege escalation.

| Scenario | Write works? | Why |
|----------|-------------|-----|
| `--allowedTools ""` | No | Nothing authorized |
| `--allowedTools "Skill"`, skill has `allowed-tools: Write` | No | Session ceiling = Skill only |
| `--allowedTools "Skill,Write"`, skill invoked | Yes | Write authorized at session AND skill level |
| Interactive mode, user's default perms | Yes (no prompt) | `allowed-tools` auto-approves |

**For gutcheck in practice:** Users invoke `/gutcheck:derisk` interactively. Their default permission mode already allows Write, Bash, Read. The skill's `allowed-tools` ensures these are auto-approved (no per-use "Allow Write?" dialogs) while the skill is active. This is the correct UX.

### Pipeline Verification

test_02 proved the full end-to-end: `claude -p` → Skill tool invokes `write-test` → skill instructions loaded → model follows them → file created with expected content (`skill-invocation-success`). The skill invocation mechanism works.

### Security Model Confirmed

test_03 proved `allowed-tools` is not a security hole: a skill cannot escalate beyond the session's permission ceiling. This is the correct behavior — `--allowedTools` (or the user's permission mode) is the hard boundary.

## Run
```bash
uv run --script run.py
```
