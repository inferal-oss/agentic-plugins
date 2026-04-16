# agentic-plugins

Open-source agentic coding plugins by [Inferal](https://inferal.com). For Claude Code and Codex CLI.

## Plugins

### derisk

Validate assumptions in implementation plans before execution.

```bash
# Claude Code
claude /plugin install derisk@inferal-oss-agentic-plugins

# Then use:
/derisk:derisk path/to/plan.md
```

The skill walks you through:
1. What makes you nervous about this plan? (Socratic exploration)
2. Systematic assumption extraction
3. Hypothesis formulation (you choose which to test)
4. Experiment design with quality gates (in subagents)
5. Execution (parallel where possible)
6. Findings and proposed plan amendments with evidence

Experiments are stored in `.inferal/derisk/{plan-name}/experiments/` as self-contained
executables (any language). Results go to `.inferal/derisk/{plan-name}/findings.md`.

### pair

Decide who writes what in an implementation plan.

```bash
# Claude Code
claude /plugin install pair@inferal-oss-agentic-plugins

# Then use:
/pair:pair path/to/plan.md
```

The skill:
1. Suggests an involvement level (hands-on / balanced / guided) based on plan characteristics
2. Classifies each step as `ai` or `yours`
3. You override any classification with justification
4. Annotates the plan with `<!-- pair:ai -->` / `<!-- pair:yours -->` markers
5. During execution: AI scaffolds `yours` steps, you write the core logic

Custom involvement levels can be defined in `.inferal/derisk/config.md`.

## Installation

### Claude Code

Add the marketplace, then install whichever plugins you want:

```bash
claude /plugin marketplace add inferal-oss/agentic-plugins
claude /plugin install derisk@inferal-oss-agentic-plugins
claude /plugin install pair@inferal-oss-agentic-plugins
```

### Codex CLI

```bash
git clone https://github.com/inferal-oss/agentic-plugins.git ~/.agentic-plugins
mkdir -p ~/.agents/skills
ln -s ~/.agentic-plugins/plugins/derisk/skills ~/.agents/skills/derisk
ln -s ~/.agentic-plugins/plugins/pair/skills ~/.agents/skills/pair
# Restart Codex
```

See [.codex/INSTALL.md](.codex/INSTALL.md) for details.

## .inferal/derisk/ Directory

Both plugins store state in `.inferal/derisk/` at the repo root:

```
.inferal/derisk/
├── config.md                    # Repo learnings, preferences, custom pair levels
├── {plan-name}/                 # Per-plan derisking
│   ├── hypotheses.md
│   ├── experiments/
│   │   └── {name}/
│   │       ├── README.md
│   │       └── run.{ext}
│   ├── findings.md
│   └── amendments.md
└── ...
```

Add `.inferal/derisk/` to `.gitignore` or commit it: your choice. Experiments are evidence
that can be valuable to keep around.

## Dogfooding

These plugins were built using their own methodology. The `.inferal/derisk/initial-implementation/`
directory contains 9 derisking experiments from the creation of this repo.

## License

MIT
