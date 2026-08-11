# Architecture

Agent Brain Blueprint is a documentation and coordination layer for agents. It
does not replace a host's native configuration, permissions, runtime state, or
the systems where production work actually happens.

```text
                         authoritative record
                    +--------------------------+
                    |  private Markdown vault   |
                    |  reviewed in local Git    |
                    +-------------+------------+
                                  |
      +---------------------------+---------------------------+
      |                           |                           |
 project organization       governance metadata       retrieval adapters
      |                           |                           |
 overviews, tasks,          source, confidence,       keyword, FTS, vector
 handoffs, evidence         freshness, scope          candidates only
      +---------------------------+---------------------------+
                                  |
                    host-specific instructions
                 Codex / Claude Code / other agents
```

## Canonical record layer

Markdown is the source of truth. It is readable by people, reviewable in Git,
and usable without a particular agent product or database.

Canonical records should be small enough to review and specific enough to
verify. A chat summary may point to a decision, but it should not silently
become the decision record itself.

## Project layer

Each project separates its overview, active work, handoffs, validation,
decisions, summaries, and source references. This avoids treating a compressed
conversation recap as an authoritative fact.

The entry card gives every session a low-cost starting point. It should point to
project overviews and current work instead of attempting to preload the whole
vault.

## Retrieval layer

Keyword search, SQLite FTS, and vector retrieval may all be useful, but they
are derivative systems. A retrieval hit is a pointer, never authority to act.
Indexes should be rebuildable from the vault and excluded from Git.

The safe retrieval sequence is: search, filter, reopen the source Markdown,
then validate live or time-sensitive claims against their real system or
primary source.

## Governance layer

Durable records declare their type, source, confidence, freshness, scope, risk
boundary, review trigger, and owner. The governance checker makes omissions
visible without deciding whether the substance is true.

The field contract creates a useful distinction: a record can be well-formed
without being fresh, and a retrieval hit can be relevant without being
authoritative. Agents still need to assess the source and perform any required
real-world validation.

## Coordination layer

Session claims are normal Markdown records. They establish a narrow intention
to change a set of vault-relative paths. The closeout checker is read-only and
detects obvious active-claim overlap; it is not a distributed lock or a defense
against a hostile local account.

Claims work best for trusted collaborators on a non-concurrent local
filesystem. They make ownership and unresolved work visible, but they do not
provide transaction isolation, consensus, or complete protection against
time-of-check/time-of-use races.

## Host boundary

Each agent host should keep its own model settings, tool configuration,
credentials, permission model, and runtime artifacts outside the vault. A host
may read this blueprint's instruction and record templates, but the blueprint
must not be treated as a runtime control plane.

This separation keeps the vault portable and reduces the chance that a public
template accidentally contains sensitive machine state.

## Explicit non-goals

This architecture intentionally excludes automatic chat ingestion, hidden
background writers, automatic fact promotion, hosted storage, bundled vector
infrastructure, and service lifecycle management. Those components may be
added locally if they remain optional, auditable, reproducible, and outside the
canonical record path.
