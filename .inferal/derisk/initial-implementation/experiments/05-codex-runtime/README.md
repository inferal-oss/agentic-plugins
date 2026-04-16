# Experiment 05: Codex CLI Runtime Validation

## Hypotheses
1. Codex exec discovers a skill symlinked to `~/.agents/skills/` and can create files
2. Skill metadata (SKILL.md frontmatter) is valid and accessible at discovery path
3. Codex session events reference the skill (proof of discovery)

## Results: ALL PASSED (3/3)

### Key Findings

1. **Codex discovers symlinked skills at runtime**: `codex exec --full-auto` found and used the skill from `~/.agents/skills/gutcheck-codex-test` symlink. File created with expected content.
2. **Skill metadata valid**: SKILL.md with `name` and `description` frontmatter parsed correctly.
3. **Skill appears in session JSON**: `--json` output includes `gutcheck-codex-test` references, confirming the skill was loaded into the session context.

### Implication for gutcheck

The dual-target distribution strategy is fully validated at runtime:
- **Claude Code**: install via marketplace, skills discovered from plugin
- **Codex CLI**: clone repo, symlink `skills/` to `~/.agents/skills/gutcheck`, restart Codex

Same SKILL.md files, both platforms confirmed working end-to-end.

## Run
```bash
uv run --script run.py
```
