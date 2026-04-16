# Experiment 02: Skill Runtime - File Creation & Script Execution

## Hypotheses
1. Plugin validates (baseline)
2. File creation works via `--allowedTools` WITHOUT `--dangerously-skip-permissions`
3. Script execution via `Bash(uv run *)` works (needed for /derisk experiment scripts)
4. File creation FAILS without authorization (permission model is real)

## Results: ALL PASSED (4/4)

### Key Findings

1. **File creation without nuclear permissions**: `--allowedTools "Write,Bash(mkdir *)"` is sufficient. No need for `--dangerously-skip-permissions`. This validates that SKILL.md `allowed-tools` will work in practice.

2. **`uv run` execution works**: `--allowedTools "Bash(uv run *)"` allows running Python scripts. This is critical for `/derisk` - experiments are `uv run --script` invocations.

3. **Permissions are real**: With an empty `--allowedTools ""`, Claude in `-p` mode cannot create files. The permission model is not theater - unauthorized tools genuinely fail.

### Implication for gutcheck

The `/derisk` SKILL.md needs these in `allowed-tools`:
```yaml
allowed-tools:
  - Bash(mkdir *)       # create experiment directories
  - Bash(uv run *)      # run experiment scripts
  - Write               # write experiment result files
  - Read                # read plan files
```

This set is sufficient and doesn't require blanket permissions.

## Run
```bash
uv run --script run.py
```
