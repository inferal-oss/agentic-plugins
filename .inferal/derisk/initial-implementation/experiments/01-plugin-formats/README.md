# Experiment 01: Plugin Format & Distribution

## Hypotheses
1. Claude Code plugin validates with `.claude-plugin/plugin.json` + `skills/`
2. SKILL.md frontmatter parses with required fields
3. `allowed-tools` covers all gutcheck needs (Write, mkdir, uv run, Read)
4. Codex discovers skills via `~/.agents/skills/` symlinks
5. Same SKILL.md file serves both platforms
6. Marketplace JSON validates with subdirectory plugin source
7. Full marketplace lifecycle works: add, install, verify, uninstall, remove
8. Installed plugin has skills on disk at expected location

## Results: ALL PASSED (8/8)

### Key Findings

1. **Plugin validates** with minimal structure: just `plugin.json` + `skills/name/SKILL.md`
2. **Frontmatter fields**: `name`, `description`, `allowed-tools` all recognized
3. **Permission coverage**: `Write`, `Bash(mkdir *)`, `Bash(uv run *)`, `Read` all declarable in `allowed-tools`
4. **Codex symlink**: `~/.agents/skills/name -> skills/name` makes SKILL.md accessible
5. **Shared files**: Both platforms resolve to the same physical SKILL.md
6. **Marketplace format**: requires `owner` object, plugin `source` as relative subdir (e.g. `./plugins/gutcheck`). No `$schema`, no `source: "."`
7. **E2E install works**: `claude plugin marketplace add <local-path>` + `install` + `list --json` + `uninstall` + `marketplace remove` - full lifecycle confirmed
8. **Skills survive install**: after install, `skills/derisk-test/SKILL.md` exists at install path with all content intact (including `allowed-tools` with `Bash(uv run *)`)

## Run
```bash
uv run --script run.py
```
