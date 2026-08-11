# Architecture

## Canonical layer

Markdown is the source of truth. It is readable by people, reviewable in Git,
and usable without a particular agent product or database.

## Project layer

Each project separates its overview, active work, handoffs, validation,
decisions, summaries, and source references. This avoids treating a compressed
conversation recap as an authoritative fact.

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
