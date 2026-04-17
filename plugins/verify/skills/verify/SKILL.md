---
name: verify
description: >
  Establish an evidence chain for claims. Decomposes statements via Socratic
  questioning, hunts for sources ranked by credibility tier, strives for hard
  empirical evidence, and produces re-runnable verification packages. Use when
  a claim's truth-status matters and you need more than "sounds plausible".
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebSearch
  - WebFetch
  - Bash(mkdir *)
  - Bash(uv run *)
  - Bash(chmod *)
  - Bash(sh *)
  - Bash(bash *)
  - Bash(curl *)
  - Bash(jq *)
  - Bash(git *)
  - Agent
  - AskUserQuestion
argument-hint: "[statement | path | --reverify <claim-slug>]"
---

# Verify: Build an Evidence Chain for a Claim

Turn a claim into a verdict backed by traceable evidence. Prefer hard evidence
(runnable tests, authoritative specs) over plausibility. Save every package so
the verdict can be re-audited or re-run later.

**Announce at start:** "Using the verify skill to build an evidence chain."

**Guiding principle:** A claim is not "true because it sounds right". It is
true because a specific, traceable source says so, or because a reproducible
observation shows it. If neither is available, the verdict is UNVERIFIABLE, not
LIKELY_TRUE. Refuse to launder vibes into verdicts.

## The Process

Seven phases. Phases 1-3 are read-only and safe in plan mode. Phases 4-7 write
to `.inferal/verification/`.

---

## Phase 1: Discovery

**Goal:** Understand what tools are available for verification in this environment.

Check if `.inferal/verification/config.md` exists:
- **If yes:** Read it. Verify anything version-sensitive is still current. Update
  stale entries.
- **If no:** Scan for:
  - Network tools (curl, wget, http)
  - Data tools (jq, yq, xmlstarlet)
  - Language runtimes relevant to likely claims (python via uv, node, go, rust)
  - Documentation the repo exposes (README, docs/, man pages)
  - Existing `.inferal/verification/` packages

Write `.inferal/verification/config.md` in prose. Keep it short: what matters
for constructing experiments and where to reach authoritative sources.

**Exit criterion:** You know what's available to run and probe.

---

## Phase 2: Claim Intake

**Goal:** Identify the exact statement(s) to verify.

### Input resolution

Resolve `$ARGUMENTS`:

| Argument form | Action |
|--------------|--------|
| `--reverify <slug>` | Load `.inferal/verification/<slug>/` and skip to Phase 7 |
| A file path (`foo.md`) | Read the file; treat its contents as source material |
| A quoted statement | Use directly as the candidate claim |
| Empty | Use AskUserQuestion to ask what to verify |

When empty and recent assistant output is in context, offer the user four
options via AskUserQuestion:
1. Verify a specific statement from the last assistant turn (user pastes it)
2. Let the skill extract candidate claims from the last turn and pick one
3. Let the skill extract candidate claims from the last N turns (ask for N)
4. User supplies a fresh claim

### Claim extraction

When extracting from a turn, look for declarative factual statements only:
- **Include:** "Library X supports Y.", "The HTTP spec mandates Z.", "This
  function is O(log n).", "Policy P was introduced in version V."
- **Exclude:** opinions, hedged claims ("might", "could"), questions,
  stylistic suggestions, first-person reports of actions taken.

Present extracted claims as a numbered list via AskUserQuestion. The user
picks which to verify (multiSelect), edits wording, or adds their own.

### Per-claim slug

For each selected claim, generate a short kebab-case slug from its essence
(e.g., `stripe-idempotency-v2024-12`, `tcp-nagle-default-on`). Slug must be
unique under `.inferal/verification/`: suffix `-2`, `-3` if collisions.

**Exit criterion:** A list of claims, each with a slug and verbatim text,
confirmed by the user.

---

## Phase 3: Socratic Decomposition

**Goal:** Turn each claim into sub-assertions that can actually be tested.

Most "claims" are bundles. "Stripe supports idempotency" hides: which API
version, which endpoints, what key format, what the retry semantics are.
Decompose before hunting sources, or you will chase the wrong evidence.

For each claim, answer these questions in writing:

1. **If this were true, what would we observe?** List the empirical
   consequences. An observable consequence is a test candidate.
2. **If this were false, what would we observe instead?** List the
   counter-observations. A good test distinguishes the two.
3. **What would refute it?** The cheapest counterexample that would falsify
   the claim. If you cannot name one, the claim is vague: go back and tighten
   it.
4. **Where would the authoritative answer live?** Name the specific document
   (RFC number, spec section, vendor API reference page, source file path).
   "The internet" is not an answer.
5. **What are the hidden qualifiers?** Versions, platforms, configurations,
   edge cases that change the answer.

The output is a decomposition with sub-assertions:

```
Claim: "Stripe supports idempotency keys."

Sub-assertions:
  A. The Stripe REST API accepts an `Idempotency-Key` HTTP header on POST
     endpoints in API version 2024-12.
  B. Replaying the same key within 24h returns the original response, not a
     duplicate resource.
  C. Replaying after 24h creates a new resource.

Authoritative sources to seek:
  - Stripe API Reference: https://stripe.com/docs/api/idempotent_requests
  - Stripe changelog for 2024-12
  - Stripe Python SDK source for retry helper

Empirical tests possible:
  - Sub-assertion A: curl a known sandbox endpoint with the header and inspect
    response. Runnable.
  - Sub-assertion B: same, replay within 24h. Runnable.
  - Sub-assertion C: time-dependent. Skip or simulate with date manipulation
    if the API exposes it. Otherwise rely on documentation.

Hidden qualifiers:
  - API version (2024-12 specifically; older versions differ)
  - Only POST, not GET/PUT
  - Sandbox vs live may have different retention windows
```

Write this per-claim decomposition to
`.inferal/verification/{slug}/claim.md` at the start of Phase 4.

**Exit criterion:** Each claim has sub-assertions, candidate sources, and
candidate tests identified.

---

## Phase 4: Source Hunt

**Goal:** Locate evidence ranked by credibility tier.

### Credibility tiers

Always prefer higher tiers. Cite the tier next to every source.

| Tier | Source type | Examples |
|------|------------|----------|
| **A** | Primary specifications and vendor authoritative docs | RFC, ISO/IEEE/ANSI standard, W3C/WHATWG spec, language reference, official API docs, vendor whitepaper, government statute |
| **B** | Peer-reviewed literature, established books, source code of the subject | Published paper, standard textbook, the actual source code of the library/system in question, merged PR from project maintainer |
| **C** | Maintainer statements in public channels | Closed issue from a listed maintainer, official blog post, conference talk by the author, changelog |
| **D** | Reputable secondary sources | Major-publication technical articles, well-regarded community docs (MDN, cppreference), widely cited answers |
| **E** | Community knowledge | Stack Overflow answers without maintainer endorsement, community tutorials, AI-generated summaries |
| **F** | Hearsay | Unattributed claims, forum posts without context, blog posts citing no source |

### Rules of the hunt

- **At least two independent sources** for any VERIFIED verdict. Two Stack
  Overflow answers from different users do not count as independent if both
  lack primary citation.
- **Follow citations up-tier.** If a Tier D source cites a Tier A source,
  read the Tier A source. Do not stop at the summary.
- **Check dates.** A Tier A source that is out of date can be wrong. Note
  the publication date and the version of the subject it describes.
- **Note disagreement.** If sources disagree, record both and their tiers.
  Disagreement is itself evidence.
- **Do not fabricate sources.** If you cannot find a URL, do not invent one.
  Log the search queries you tried and mark the sub-assertion as
  source-starved.

### Dispatch independent claims to subagents

When verifying multiple claims, dispatch a subagent (Agent tool) per claim
for parallel source hunting. Each subagent:
1. Reads the claim's decomposition.
2. Performs WebSearch + WebFetch (and any local Grep/Read).
3. Returns a ranked source list with verbatim excerpts, URLs, dates, and tiers.

**Exit criterion:** Each sub-assertion has a ranked source list with excerpts
saved to memory, ready for writing in Phase 5.

---

## Phase 5: Hard-Evidence Push

**Goal:** Wherever possible, turn a documentary claim into a reproducible test.

Documentation can be wrong, out of date, or misread. A passing test with a
negative control is stronger than a Tier A page. For each sub-assertion ask:

- **Can I run something that would fail loudly if the claim were false?**
- **Can I observe the subject directly** (curl the API, read the source,
  reproduce the bug, measure the timing)?
- **Can I construct a negative control** that would pass only if the
  mechanism weren't in effect?

If yes, build an experiment under `.inferal/verification/{slug}/experiments/{name}/`.

### Experiment contract

Every experiment MUST satisfy all of the following:

- **`README.md`** states the hypothesis (what sub-assertion(s) it tests),
  method (what the script does and against what), and expected output (what
  the pass case looks like).
- **`run.{ext}`** is self-contained and runnable with a single command
  (e.g., `bash run.sh`, `uv run --script run.py`, `cargo run`, etc.). Any
  language that fits. No reliance on state outside the experiment directory
  beyond documented external services (e.g., a public API).
- **Exit code is the verdict:** the script exits `0` iff the evidence
  supports the sub-assertion(s); it exits non-zero with a clear reason when
  the evidence refutes them. No ambiguous exits.
- **Raw evidence is captured** into an `evidence/` subdirectory alongside
  the script: API responses, HTML, stdout, HTTP status codes, computed
  summaries. Re-verification must be able to inspect the raw data without
  re-running the script, and can diff captures across runs.
- **Include a negative control** whenever feasible: the same script also
  probes a scenario where the mechanism should NOT be present, and confirms
  the expected failure. A passing positive test plus a passing negative
  control together rule out "the script always passes".

### Disqualifying anti-patterns

An experiment that exhibits any of the following is not evidence and must be
fixed or discarded:

| Anti-pattern | What it looks like | How to fix |
|--------------|---------------------|------------|
| **Fixture self-verification** | Script writes `X`, then checks that `X` exists. Proves only that the script's own setup ran. | Test must exercise something outside the script's own writes: an external API, an installed tool's behavior, a file created by a separate process. |
| **Missing negative control** | Script shows the mechanism exists, but nothing demonstrates the result would differ if the mechanism weren't in effect. Classic failure mode for permission/auth/idempotency tests. | Add a companion probe that removes or inverts the mechanism and verifies the opposite outcome. |
| **Claims vs proof** | `README.md` says "proves X" but the script just prints a literal or echoes an input. | The passing path must be caused by the mechanism under test, not by the script's own instructions. Use values that can only exist if the mechanism worked. |
| **Magic-token gap** | Script probes "who did X" using an identifier that appears in both the prompt and the output; the output contains the token because the prompt put it there, not because the mechanism did. | Put the identifying string only where the mechanism would inject it; never in the input. Its appearance downstream is then the signal. |
| **Redundancy** | Two experiments under the same claim test the same thing with different wording. | Merge or delete one. Every experiment must prove something distinct. |
| **Missing isolation** | Result changes depending on the caller's environment, installed plugins, or ambient auth state. | Pin or strip the environment (`env -i`, explicit `--config`, `--setting-sources ""`, no-plugin mode). Document what is isolated and why. |

When empirical verification is impossible (historical claims, intent,
future-tense claims, private systems): state why, and lean on Tier A/B
documentation with at least two independent sources.

**Exit criterion:** Every sub-assertion has either (a) a runnable experiment
with clean pass/fail or (b) a documented reason it can only be text-verified.

---

## Phase 6: Evidence Package

**Goal:** Write the package to disk in a durable, re-runnable layout.

Create, per claim:

```
.inferal/verification/{slug}/
├── claim.md           # claim text + decomposition (from Phase 3)
├── sources.md         # ranked source list with excerpts (from Phase 4)
├── experiments/       # optional, from Phase 5
│   └── {name}/
│       ├── README.md
│       ├── run.{ext}
│       └── evidence/  # raw output captured by run
├── evidence.json      # machine-readable metadata (see below)
└── verdict.md         # final verdict + reasoning
```

### claim.md

Verbatim claim, date captured, source turn or file, and the Phase 3
decomposition. This is the immutable record of what was asked.

### sources.md

One section per source. Include:

```markdown
## Source 1 — Tier A

- **URL:** https://datatracker.ietf.org/doc/html/rfc9110#section-9.3.3
- **Title:** RFC 9110 §9.3.3 POST
- **Author / publisher:** IETF
- **Date accessed:** 2026-04-17
- **Date of source:** 2022-06
- **Supports sub-assertion:** A
- **Excerpt:**
  > The POST method requests that the target resource process the
  > representation enclosed in the request according to the resource's own
  > semantics. ...
- **Notes:** Exact wording; no later errata affecting this paragraph.
```

### experiments/ — unchanged from Phase 5

Keep experiments self-contained so re-verification can re-run them without
reading the rest of the package.

### evidence.json (machine-readable, for re-verify)

```json
{
  "slug": "stripe-idempotency-v2024-12",
  "claim": "Stripe supports idempotency keys on POST in API version 2024-12.",
  "captured_at": "2026-04-17",
  "verdict": "VERIFIED",
  "sub_assertions": [
    {
      "id": "A",
      "text": "The Stripe REST API accepts an Idempotency-Key header on POST endpoints in 2024-12.",
      "result": "VERIFIED",
      "sources": [
        {"tier": "A", "url": "https://...", "accessed": "2026-04-17", "sha256_of_fetched_content": "..."}
      ],
      "experiments": ["post-accepts-header"]
    }
  ],
  "experiments": [
    {
      "name": "post-accepts-header",
      "runner": "bash run.sh",
      "last_run_at": "2026-04-17",
      "last_exit_code": 0,
      "evidence_files": ["evidence/response.json"]
    }
  ]
}
```

Storing `sha256_of_fetched_content` lets re-verification detect when a cited
page has changed since capture. If you can't compute the hash (large pages,
paywalled content), omit the field and note it.

### verdict.md

One of:

| Verdict | Requirement |
|---------|------------|
| **VERIFIED** | Every sub-assertion has either a passing experiment with negative control OR ≥2 independent Tier A/B sources that agree. |
| **LIKELY_TRUE** | Tier B/C sources agree, no strong counter-evidence, but no empirical test and no Tier A source found. |
| **MIXED** | Some sub-assertions verified, others not. Break down per sub-assertion. |
| **UNCLEAR** | Sources disagree, or only Tier D/E evidence available. |
| **LIKELY_FALSE** | Evidence weighs against the claim, but no decisive refutation. |
| **REFUTED** | An experiment fails OR ≥1 Tier A/B source directly contradicts. |
| **UNVERIFIABLE** | No path to evidence: private system, historical intent, tautological, or unfalsifiable as stated. Say so. Do not upgrade to LIKELY_TRUE. |

`verdict.md` must state the verdict, cite the evidence chain leading to it,
and list what would *change* the verdict (stronger sources, a specific test).

### Present to the user

After writing the package, present:
- The verdict and one-line reasoning.
- The path to the package.
- Any sub-assertions that are UNVERIFIABLE or whose evidence is Tier D/E only,
  so the user can decide whether to invest more.

**Exit criterion:** Package exists on disk, user has seen the verdict.

---

## Phase 7: Re-verification

**Goal:** Re-audit a prior verification package. Triggered by
`/verify:verify --reverify <slug>` or after the user requests a re-check.

Steps:

1. Load `.inferal/verification/{slug}/evidence.json`.
2. For each source with a stored hash: refetch the URL (best-effort) and
   compare. If the content changed or the URL is dead, flag it.
3. For each experiment: re-run `run.{ext}`. Compare exit code and key output
   fields (where the run.md documents them) against the previous run.
4. For each sub-assertion: recompute status from the refreshed evidence.
5. Compute a new top-level verdict.
6. Append (do not overwrite) a dated reverification block to `verdict.md`:

```markdown
## Reverification — 2026-06-01

- Source 1: still VERIFIED (hash unchanged).
- Source 2: URL returns 404. Flagged.
- Experiment post-accepts-header: PASS (exit 0).
- New verdict: VERIFIED (was VERIFIED).
- Changes needed: update Source 2 with a replacement citation.
```

Update `evidence.json` to record the new run, but keep the original capture
timestamps on sources that did not change.

**Exit criterion:** Up-to-date verdict, with historical verdicts preserved.

---

## Notes

### When to use this skill vs derisk

- **derisk:** Validates assumptions in an implementation plan before coding.
  Oriented around plan execution.
- **verify:** Establishes the truth-status of a standalone claim. Oriented
  around correctness of a statement, no plan required.

Both persist evidence under `.inferal/`. They do not share state.

### Non-software claims

Nothing in this skill is software-specific. "Aspirin was synthesized in 1897"
decomposes the same way: sub-assertions (by whom? where published?),
Tier A sources (primary literature, patent records), empirical impossibility
(historical fact, no runnable test), verdict backed by ≥2 independent Tier A/B
sources.

Use the same credibility tiers with domain-appropriate substitutions (for
legal claims, Tier A is the statute text; for medical claims, Tier A is the
peer-reviewed primary study or regulatory filing).

### Refusing to upgrade weak evidence

If a user pushes for a VERIFIED verdict on Tier D/E evidence alone, refuse.
Offer UNCLEAR or LIKELY_TRUE as the honest alternative. The value of this
skill is its willingness to say "we don't know" when that is the true answer.

### Committing the package

The user chooses whether to gitignore `.inferal/verification/` or commit it.
Committing gives the team a shared evidence history; gitignoring keeps
per-developer working state local.
