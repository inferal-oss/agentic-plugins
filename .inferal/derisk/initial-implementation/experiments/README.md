# Gutcheck Derisking Experiments

All experiments run with `--setting-sources ""` for full isolation from user
plugins, hooks, and settings. Auth preserved via `~/.claude.json` (OAuth).

## Results Summary

| # | Experiment | Tests | Status | Key Finding |
|---|-----------|-------|--------|-------------|
| 01 | [Plugin Format & Distribution](01-plugin-formats/) | 5/5 | Pass | Plugin validates, marketplace e2e install/uninstall works, skills survive on disk, Codex symlink resolves to same file |
| 02 | [Skill Runtime](02-skill-runtime/) | 3/3 | Pass | Write + `uv run` work via `--allowedTools` without nuclear perms. Empty allowedTools blocks everything (permission model real) |
| 03 | [Skill Invocation & allowed-tools](03-skill-allowed-tools/) | 2/2 | Pass | Skill tool → SKILL.md → instructions → output pipeline works. `allowed-tools` is auto-approval within session ceiling, not privilege escalation |
| 04 | [Skills in Subagents](04-skill-in-subagent/) | 2/2 | Pass | Subagents inherit plugin skills. Full pipeline: Agent → Skill → SKILL.md → file created |
| 05 | [Codex Runtime](05-codex-runtime/) | 2/2 | Pass | Codex discovers symlinked skills at runtime (magic token proof). Skill referenced in JSONL session events |
| 06 | [Pair Classification](06-pair-classification/) | 3/3 | Pass | Model classifies mechanical vs thoughtful steps with >= 5/6 accuracy. Annotations survive in markdown. Scaffolding produces skeleton only (AST-verified) |
| 07 | [Plan Mode Writes](07-plan-mode-writes/) | 6/6 | Pass | Real `--permission-mode plan` blocks ALL direct write approaches: skill, `context: fork`, subagent. See [08](08-plan-mode-task-tool/) for Agent tool and [09](09-exit-reenter-plan-mode/) for the working solution |
| 08 | [Plan Mode Agent Tool](08-plan-mode-task-tool/) | 4/6 | 2 expected fail | Agent subagent CANNOT bypass plan mode (confirmed with isolation; earlier "nondeterministic" result was contamination from user settings). Read works in plan mode |
| 09 | [Exit-Reenter Plan Mode](09-exit-reenter-plan-mode/) | 4/4 | Pass | ExitPlanMode → Write → `uv run` → Read → EnterPlanMode all work. Interactive approval of ExitPlanMode untestable in `-p` mode but every piece validated individually |

**31/33 pass, 2 expected failures.**

## Isolation

Previous runs were contaminated by `~/.claude/settings.json`:
- Superpowers plugin intercepted prompts (triggered plan mode on "scaffolding")
- Auto mode (`defaultMode: "auto"`) changed permission behavior
- RTK hook rewrote Bash commands
- Extended thinking and effort level affected model behavior

Fix: `--setting-sources ""` loads NO settings while preserving OAuth auth.
This was the single biggest improvement to test reliability.

## Key Design Decisions Validated

### Plugin Distribution (dual-target)
- **Claude Code**: marketplace format with `./plugins/gutcheck/` subdirectory. Install via `claude /plugin marketplace add`
- **Codex CLI**: clone repo, symlink `skills/` to `~/.agents/skills/gutcheck`. No plan mode to worry about
- Same SKILL.md files serve both platforms

### Permission Model
- `allowed-tools` in SKILL.md = auto-approval (no per-use dialogs), NOT privilege escalation
- Session-level `--allowedTools` is the hard ceiling
- `--add-dir` needed for Write to paths outside working directory
- Bash sandbox is separate from Write permissions

### Plan Mode
- Real `--permission-mode plan` is a hard boundary for writes
- No skill, fork, or subagent escapes it
- **Solution: ExitPlanMode → work → EnterPlanMode**
- Codex has no plan mode (sandbox + approval policies instead)

### Fabricated Sources Warning
WebSearch hallucinated GitHub issues #5406, #19874, #40324. These DO NOT EXIST.
Real issues confirming plan mode is prompt-level: [#39687](https://github.com/anthropics/claude-code/issues/39687), [#39796](https://github.com/anthropics/claude-code/issues/39796).
Subagent behavior during plan mode is undefined: [#4750](https://github.com/anthropics/claude-code/issues/4750).

## /derisk Workflow (validated)

```
Plan mode active, plan exists
→ /gutcheck:derisk invoked
→ Socratic risk exploration (read-only, works in plan mode)
→ Skill calls ExitPlanMode (user approves)
→ Writes experiment scripts to .inferal/derisk/derisk/experiments/
→ Executes experiments (uv run or subagents)
→ Reads results back
→ Calls EnterPlanMode
→ Reports findings in plan mode context
```

## /pair Workflow (validated)

```
Plan exists (any format)
→ /gutcheck:pair invoked
→ Classifies each step as "ai" or "yours" (>= 5/6 accuracy on obvious cases)
→ Annotates plan with <!-- pair:ai --> / <!-- pair:yours --> markers
→ For "yours" steps during execution: creates skeleton (signatures + docstring + NotImplementedError), stops for developer to write
→ Developer can override classification with justification
```

## Running All Experiments

```bash
for exp in .inferal/derisk/derisk/experiments/*/run.py; do
  echo "=== $(dirname $exp | xargs basename) ==="
  uv run --script "$exp"
  echo
done
```
