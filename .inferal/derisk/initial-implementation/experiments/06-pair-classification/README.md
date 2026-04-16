# Experiment 06: Pair Skill - Classification Quality

## Hypotheses
1. Model can classify plan steps as ai/yours with >= 5/6 accuracy on obvious cases
2. HTML comment annotations (<!-- pair:yours -->) survive in markdown without breaking content
3. Scaffolding produces structure (signatures, types) but NOT implementation body

## Method
Sample plan with 6 steps:
- Step 1 (ai): DB migration following existing template
- Step 2 (yours): Session token strategy decision (architecture)
- Step 3 (ai): Password hashing utility following existing pattern
- Step 4 (yours): Core auth logic (security-sensitive, state machine)
- Step 5 (ai): Running schema generator, copy existing pattern
- Step 6 (yours): Error handling philosophy (policy decision)

Ground truth threshold: 5/6 correct.

## Run
```bash
uv run --script run.py
```
