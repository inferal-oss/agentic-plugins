# Installing for Codex CLI

Codex discovers skills via `~/.agents/skills/` symlinks.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/inferal-oss/agentic-plugins.git ~/.agentic-plugins
   ```

2. Symlink the plugins you want:
   ```bash
   mkdir -p ~/.agents/skills

   # derisk plugin
   ln -s ~/.agentic-plugins/plugins/derisk/skills ~/.agents/skills/derisk

   # pair plugin
   ln -s ~/.agentic-plugins/plugins/pair/skills ~/.agents/skills/pair

   # verify plugin
   ln -s ~/.agentic-plugins/plugins/verify/skills ~/.agents/skills/verify
   ```

3. Restart Codex to discover the skills.

## Verify

```bash
ls -la ~/.agents/skills/derisk  # Should show: derisk/SKILL.md
ls -la ~/.agents/skills/pair    # Should show: pair/SKILL.md
ls -la ~/.agents/skills/verify  # Should show: verify/SKILL.md
```

## Updating

```bash
cd ~/.agentic-plugins && git pull
```

Skills update instantly through the symlinks.

## Uninstalling

```bash
rm ~/.agents/skills/derisk
rm ~/.agents/skills/pair
rm ~/.agents/skills/verify
```

Optionally delete the clone: `rm -rf ~/.agentic-plugins`
