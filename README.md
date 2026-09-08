# portal_TA_services — Comparison baseline

This repository hosts a controlled comparison between two AI coding assistants
building the same MVP brief: **ARRISE Solutions Portal**, a Django-based demo
portal centralizing seven fictional Talent Acquisition / HR / Security /
Data & Analytics / Operations solutions plus a local FAQ chat assistant
("Agent TA").

## How the comparison works

- `main` holds only this neutral baseline (this README and `.gitignore`) and
  nothing else. It is tagged `comparison/solutions-portal-base-v1` so both
  implementations start from the exact same commit.
- Each AI assistant works exclusively on its own branch, created from that
  tag, and must not read or reuse the other assistant's branch/commits:
  - `feature/solutions-portal-claude` — Claude Code implementation.
  - the other assistant's branch (name defined by that run).
- Neither branch merges into `main`. `main` and the comparison tag are never
  moved once created.
- Evaluation criteria, weights and expected evidence are documented per
  branch in `docs/comparison.md` (functional coverage, brand/design
  compliance, backend & data consistency, responsive/accessibility,
  reproducibility & documentation).

## Scope note

No real business data, credentials, or production integrations are part of
this exercise. All data used by either implementation is fictional/demo
data generated for the purpose of this comparison.
