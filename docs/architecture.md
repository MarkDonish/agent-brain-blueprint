# Architecture

## Canonical layer

Markdown is the source of truth. It is readable by people, reviewable in Git,
and usable without a particular agent product or database.

## Schema layer

Field contracts live in `schemas/*.json` and are loaded by `scripts/lib/schema.py`.
Frontmatter parsing lives in `scripts/lib/frontmatter.py`. Checkers must not
redefine required fields in isolation.

## Project layer

Each project separates its overview, active work, handoffs, docs, validation,
decisions, summaries, and source references.

```text
10_projects/<project>/
  PROJECT_OVERVIEW.md
  10_current_work/
  20_handoffs/
  30_docs/
  40_validation/
  50_decisions/
  60_summaries/
  90_raw_sources/
```

## Vault top-level layer

```text
00_entrypoint/
10_projects/
20_agent_catalog/
30_global_decisions/
40_handoffs/
50_retrieval/
60_templates/
70_inbox/
80_sensitive_isolation/
90_archive/
```

## Retrieval layer

Search systems may nominate candidates. A hit is never authority to act. Indexes
should be rebuildable and excluded from Git.

## Governance layer

Durable decision records require provenance fields from `schemas/memory_record.json`.
Validation/handoff/session claim paths can be checked softly.

## Concurrency layer

Session claims plus optional `check_claim_gate.py` reduce accidental overlap.
They are not distributed locks. Expired claims stop being active.

## Safety layer

`doctor.py` combines structure, governance, and claim checks with human-readable
repair hints. `check_privacy_scan.py` is a pre-publish net for the public checkout.
