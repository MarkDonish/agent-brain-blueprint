# Architecture

## Canonical layer

Markdown is the source of truth. It is readable by people, reviewable in Git,
and usable without a particular agent product or database.

## Project layer

Each project separates its overview, active work, handoffs, docs, validation,
decisions, summaries, and source references. This avoids treating a compressed
conversation recap as an authoritative fact.

Recommended project layout:

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
00_entrypoint/            short session-start card
10_projects/              project workspaces
20_agent_catalog/         host pointers, never runtime copies
30_global_decisions/      durable cross-project decisions
40_handoffs/              vault-level handoffs and session claims
50_retrieval/             retrieval protocol notes
60_templates/             local record templates
70_inbox/                 unprocessed source pointers
80_sensitive_isolation/   hard boundary; keep out of Git
90_archive/               superseded records
```

## Retrieval layer

Keyword search, SQLite FTS, and vector retrieval may all be useful, but they
are derivative systems. A retrieval hit is a pointer, never authority to act.
Indexes should be rebuildable from the vault and excluded from Git.

## Governance layer

Durable records declare their type, source, confidence, freshness, scope, risk
boundary, review trigger, and owner. The governance checker makes omissions
visible without deciding whether the substance is true.

## Concurrency layer

Session claims are normal Markdown records. They establish a narrow intention
to change a set of vault-relative paths. The closeout checker is read-only and
detects obvious active-claim overlap; it is not a distributed lock or a defense
against a hostile local account.

## Safety layer

`doctor.py` combines structure, governance, and claim checks. The privacy scanner
is a pre-publish net for the public blueprint checkout, not a complete DLP system.
