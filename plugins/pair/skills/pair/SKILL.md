---
name: pair
description: >
  Classify plan steps as AI-written or developer-written based on importance,
  complexity, and ownership value. Annotates plans with authorship markers and
  guides execution: AI scaffolds, developer writes core logic. Use after writing
  a plan and before execution to decide who writes what.
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
argument-hint: "[plan file path]"
---

# Pair: Authorship Allocation for Plan Steps

Decide who writes what. Classify each step in a plan as `ai` (mechanical, AI writes)
or `yours` (thoughtful, developer writes with AI guidance).

**Announce at start:** "Using the pair skill to decide who writes what in this plan."

## Step 1: Read Config and Plan

1. Check `.inferal/derisk/config.md` for saved involvement level preference and custom levels.
   If it does not exist, that is fine: defaults apply.
2. Read the plan from `$ARGUMENTS`. Accept markdown, XML, or plain text.
3. If no argument provided, use AskUserQuestion to ask for the plan file path.

## Step 2: Suggest Involvement Level

Analyze the plan to suggest an initial level. Consider these factors:

| Factor | Pushes toward more `yours` | Pushes toward more `ai` |
|--------|---------------------------|------------------------|
| Importance: production-critical, security, compliance | high | low |
| Size: many files, cross-cutting changes | large | small, localized |
| Impact: public API, data model, architecture boundary | high | internal only |
| Complexity: novel algorithm, concurrency, state machines | high | routine patterns |

Use AskUserQuestion to present the suggestion and let the developer choose:

**Built-in levels:**

| Level | What AI does | What developer writes |
|-------|-------------|----------------------|
| **Hands-on** | Only boilerplate, config, imports | All logic, all decisions, all tests |
| **Balanced** (default) | Mechanical steps, pattern-following | Core logic, architecture, policy decisions |
| **Guided** | Most implementation with developer oversight | Only the hardest design decisions |

**Custom levels:** If `.inferal/derisk/config.md` defines additional levels, include them
in the choices. Teams can define levels like:

```markdown
## Custom Pair Levels

### Review-only
AI writes everything. Developer reviews every file before commit.
Classification: all steps ai, but execution pauses for review after each.

### Teaching
Like hands-on, but AI explains WHY each decision matters before developer writes.
For onboarding new team members to the codebase.
```

Save the chosen level to `.inferal/derisk/config.md` so it persists across sessions.
The developer can change it anytime by re-running the skill.

## Step 3: Classify Each Step

For each step in the plan, classify using the chosen involvement level and these signals:

| Signal | Points toward `yours` | Points toward `ai` |
|--------|----------------------|---------------------|
| Involves a design decision | yes | no |
| Has multiple valid approaches | yes | no |
| Will be debugged by a human later | yes | less likely |
| Follows an established pattern | no | yes |
| Is mostly structural or repetitive | no | yes |
| Creates a new abstraction | yes | no |
| Requires domain knowledge | yes | no |

**How the level shifts the threshold:**
- **Hands-on**: borderline steps go to `yours`. Only obviously mechanical work is `ai`.
- **Balanced**: use the signals table as-is. Roughly even split on typical plans.
- **Guided**: borderline steps go to `ai`. Only clearly ownership-critical work is `yours`.
- **Custom levels**: follow whatever the level definition says.

## Step 4: Present Classifications and Allow Overrides

Show the developer each step with its classification and a one-line reason.

Example output:

```
Step 1: Create database migration .............. ai (follows existing template)
Step 2: Design session token strategy .......... yours (architecture decision, multiple approaches)
Step 3: Add password hashing utility ........... ai (boilerplate following existing pattern)
Step 4: Implement core auth logic .............. yours (security-sensitive, needs deep understanding)
Step 5: Generate OpenAPI schema ................ ai (running a generator, copy existing pattern)
Step 6: Define error handling philosophy ....... yours (policy decision, security/UX trade-off)
```

The developer can override any classification. When they do, ask for justification.
Log overrides as `<!-- pair:override reason="..." -->` in the annotated plan.

## Step 5: Annotate the Plan

Ask the developer: annotate in-place or create a copy?

Insert markers before each step heading:

```markdown
<!-- pair:ai -->
## Step 1: Create database migration
...

<!-- pair:yours -->
## Step 2: Design session token strategy
...

<!-- pair:override reason="I already know which token strategy to use" -->
<!-- pair:ai -->
## Step 2: Design session token strategy
...
```

Write the annotated plan.

## Step 6: Execution Guidance

This section documents how execution skills should handle `yours` steps.
The pair skill itself does not execute the plan. It annotates it.

When an execution skill encounters a `<!-- pair:yours -->` step:

1. **Scaffold.** Create the file and function skeleton: imports, function signatures
   with type annotations, a docstring explaining what needs to be implemented, and
   a placeholder body (`raise NotImplementedError`, `todo!()`, `// TODO`, etc.).
   Do NOT write any implementation logic.

2. **Contextualize.** Show the developer:
   - Relevant interfaces this code must satisfy
   - Related code they should look at
   - Constraints from the plan or architecture
   - What the tests expect (if tests exist)

3. **Pair-program.** Walk through the logic step by step. At each decision point,
   ask the developer what to do. Do not decide for them. Examples:
   - "How should this handle the empty case?"
   - "What's the retry strategy here?"
   - "This could be a map or a fold: which feels right for this domain?"

4. **Review.** After the developer writes the code, read it. Note anything that
   seems off (potential bugs, missing edge cases, inconsistencies with the plan).
   Do not rewrite their code. Suggest, then move on.

When an execution skill encounters a `<!-- pair:ai -->` step:

Execute normally. The developer chose to let AI handle this.
