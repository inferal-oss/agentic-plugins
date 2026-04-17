# agentic-plugins

Open-source agentic coding plugins by [Inferal](https://inferal.com). For Claude Code and Codex CLI.

## Plugins

### derisk

Validate assumptions in implementation plans before execution.

```bash
# Claude Code
claude plugin install derisk@agentic-plugins

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
claude plugin install pair@agentic-plugins

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

### verify

Build an evidence chain for a claim. Not just for code: works for any factual
statement where "sounds right" isn't enough.

```bash
# Claude Code
claude plugin install verify@agentic-plugins

# Then use:
/verify:verify "Stripe supports idempotency keys on POST in API version 2024-12"
/verify:verify                          # extract candidate claims from the last turn
/verify:verify --reverify <claim-slug>  # re-run a prior package
```

The skill walks you through:
1. Pick the statement(s) to verify (from the last turn, a file, or supplied directly)
2. Socratic decomposition: if this were true, what would we observe? How would we know if it's false?
3. Source hunt with explicit credibility tiers (A: specs/RFCs, B: primary source code/papers, … E: community Q&A, F: hearsay)
4. Hard-evidence push: if a runnable test can settle it, write one with a negative control
5. Verdict (VERIFIED / LIKELY_TRUE / MIXED / UNCLEAR / LIKELY_FALSE / REFUTED / UNVERIFIABLE) with the full evidence chain
6. Re-verification: the package stores machine-readable metadata and content hashes so future re-runs can detect when cited sources have changed

Packages live in `.inferal/verification/{claim-slug}/` and include the claim,
ranked sources with excerpts, any experiments, and a dated verdict.

## Installation

### Claude Code

Add the marketplace, then install whichever plugins you want:

```bash
claude plugin marketplace add inferal-oss/agentic-plugins
claude plugin install derisk@agentic-plugins
claude plugin install pair@agentic-plugins
claude plugin install verify@agentic-plugins
```

### Codex CLI

```bash
git clone https://github.com/inferal-oss/agentic-plugins.git ~/.agentic-plugins
mkdir -p ~/.agents/skills
ln -s ~/.agentic-plugins/plugins/derisk/skills ~/.agents/skills/derisk
ln -s ~/.agentic-plugins/plugins/pair/skills ~/.agents/skills/pair
ln -s ~/.agentic-plugins/plugins/verify/skills ~/.agents/skills/verify
# Restart Codex
```

See [.codex/INSTALL.md](.codex/INSTALL.md) for details.

## .inferal/ Directories

Each plugin stores state under `.inferal/` at the repo root:

```
.inferal/derisk/                     # derisk + pair
├── config.md                        # Repo learnings, preferences, custom pair levels
└── {plan-name}/                     # Per-plan derisking
    ├── hypotheses.md
    ├── experiments/
    │   └── {name}/
    │       ├── README.md
    │       └── run.{ext}
    ├── findings.md
    └── amendments.md

.inferal/verification/               # verify
├── config.md                        # Tooling notes for this repo
└── {claim-slug}/                    # Per-claim evidence package
    ├── claim.md                     # Claim + Socratic decomposition
    ├── sources.md                   # Ranked source list with excerpts
    ├── experiments/                 # Optional runnable checks
    │   └── {name}/
    │       ├── README.md
    │       ├── run.{ext}
    │       └── evidence/            # Raw captured output
    ├── evidence.json                # Machine-readable metadata for re-verify
    └── verdict.md                   # Verdict + reasoning (append-only)
```

Add `.inferal/` to `.gitignore` or commit it: your choice. Experiments and
evidence packages are valuable to keep around.

## Dogfooding

These plugins were built using their own methodology. The `.inferal/derisk/initial-implementation/`
directory contains 9 derisking experiments from the creation of this repo.

## License

MIT
