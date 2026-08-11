# Agent Brain Blueprint

[![Template checks](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

**A local-first, Markdown-native blueprint for shared AI-agent memory.**

Agent Brain Blueprint gives Codex, Claude Code, and other agent hosts a small,
auditable place to coordinate project context, handoffs, durable decisions,
validation evidence, and retrieval hints.

It is a **template, not a personal memory dump**. The repository contains only
generic structure, fictional examples, dependency-free checks, and English
documentation. Your real vault should stay private, outside this checkout.

## Why this exists

Most agents lose useful context between sessions, while a full conversation
archive is too large, too private, and too hard to verify. This blueprint
supports a more deliberate lifecycle:

1. Start from a short entry card and a project overview.
2. Retrieve only likely records for the current task.
3. Reopen Markdown or the live system before treating a claim as fact.
4. Record narrow handoffs, decisions, and validation evidence.
5. Keep private identity, secrets, runtime state, and generated data out of
   the shared vault.

## At a glance

```text
                         private local Git repository
+-----------------------------------------------------------------------+
|                        Markdown vault (canonical)                     |
| entry card / projects / decisions / handoffs / validation / sources   |
+----------------+---------------------+---------------------+---------+
                 |                     |                     |
        read/write protocol      governance fields     rebuildable retrieval
                 |                     |                     |
                 +-------------+-------+-------------+-------+
                               |                     |
                  Codex / Claude Code / other hosts  local search adapters
```

The Markdown records are authoritative. Retrieval tools and indexes only help
find candidates; they never replace source review or a fresh runtime check.

## What it solves

- A new agent can find the relevant project context without loading every past conversation.
- Markdown is the canonical record; indexes and search systems only nominate candidates.
- Personal memory, runtime configuration, secrets, logs, and databases stay outside the vault.
- Concurrent sessions can declare a narrow file claim before work and use a read-only closeout check.
- Durable facts carry provenance, confidence, freshness, scope, ownership, and risk boundaries.

## Design principles

1. **Markdown first.** Everything important remains readable, diffable, and portable.
2. **Retrieval is not truth.** Reopen the source Markdown or the real runtime before acting.
3. **Project before chat.** Organize by project state, handoff, validation, decision, and source material.
4. **Minimal context.** Read an entry card, then retrieve only what the task needs.
5. **No silent writes.** Claims, closeout, and promotion of durable facts are explicit.
6. **Privacy by construction.** Never put credentials, raw conversations, customer data, databases, or logs in the vault.

## Quick start

```bash
git clone <repository-url>
cd agent-brain-blueprint
python3 scripts/bootstrap.py --destination ../my-agent-brain
python3 scripts/check_memory_governance.py ../my-agent-brain
python3 scripts/check_session_claims.py ../my-agent-brain
python3 scripts/doctor.py ../my-agent-brain
```

The bootstrap command creates a new local vault from the templates. It never
copies this repository's examples into an existing vault without an explicit
destination.

Then keep `../my-agent-brain` as a private Git repository. Use the generated
[`AGENTS.md`](AGENTS.md) as a host-agnostic rule file, or translate its short
read/write protocol into the instruction system used by your agent host.

## Safe memory lifecycle

```text
session start -> entry card -> project record -> focused retrieval -> source check
                                                                     |
closeout record <- validation evidence <- narrow session claim <- change
```

For shared work, create a small claim before changing durable records and run
the read-only checker before closeout:

```bash
python3 scripts/check_session_claims.py ./my-agent-brain \
  --claims-dir 40_handoffs/session_claims
```

This is coordination support, not a lock service. The checker validates record
shape, safe vault-relative paths, overlapping claims, and symlink aliases. It
does not execute commands, write files, commit Git, restart services, or turn
self-reported dry-run evidence into independently verified proof. Read the
[session claim and closeout protocol](docs/session-claims-and-closeout.md)
before using it in a multi-session workflow.

## Repository layout

```text
AGENTS.md                         shared operating rules for agent hosts
docs/                             architecture, privacy, adoption, and closeout guidance
templates/vault/                  the bootstrap source
templates/*.md                    record templates for human and agent use
scripts/                          dependency-free validation tools
tests/                            focused regression tests for the claim checker
examples/demo-vault/              fictional, safe reference content
```

The generated vault uses these top-level areas:

```text
00_entrypoint/                    a short session-start card
10_projects/                      project workspaces
20_agent_catalog/                 host-specific pointers, never runtime copies
30_global_decisions/              durable cross-project decisions
40_handoffs/                      narrow cross-agent handoffs and claims
50_retrieval/                     retrieval protocol and optional adapters
60_templates/                     local copies of the templates
90_archive/                       historical records that are no longer current
```

## Use it with any agent host

The blueprint deliberately does not require a particular model, SDK, memory
plugin, or database. A host integration should only do four things:

1. Read the entry card and relevant project overview at session start.
2. Search the private vault to nominate relevant Markdown records.
3. Reopen the source record before acting on it.
4. Write only explicit, source-backed records through the supplied templates.

Keep host configuration, model settings, tool permissions, secrets, and
runtime state in their native locations. The vault documents coordination; it
does not become the control plane for a live agent installation. See
[adoption guidance](docs/adoption.md) for a practical integration boundary.

## Search and retrieval

Use any local keyword, FTS, or vector system you prefer. The invariant is more
important than the engine:

1. Search returns candidates only.
2. Filter candidates by project, status, scope, and freshness where possible.
3. Reopen the current Markdown source before using its claim as fact.
4. Treat runtime, production, vendor, policy, and account facts as stale until
   revalidated from the real system or primary source.

This template intentionally has no bundled vector database or model. Derived
indexes should be reproducible from the Markdown vault and ignored by Git.

## What this blueprint deliberately does not do

- It does not automatically ingest chat history or personal memories.
- It does not ship a daemon, background hook, watcher, or service restart loop.
- It does not bundle a vector database, embedding model, or cloud account.
- It does not auto-promote transient notes into durable facts.
- It does not replace code review, Git history, production validation, or
  native agent configuration.

These omissions are intentional: a memory layer is easier to audit when its
side effects are explicit and its derived systems remain optional.

## Privacy and publication boundary

Do not add any of these to the vault or this public repository:

- API keys, tokens, cookies, passwords, OAuth files, or `.env` files
- personal profiles, raw conversations, browser data, private messages, or email
- customer data, invoices, account identifiers, or production credentials
- SQLite databases, search indexes, logs, caches, binary artifacts, or model files
- absolute private paths, private project names, IP addresses, or hostnames

Use fictional names such as `example-app`, `demo-user`, and `/path/to/vault` in
documentation and tests. Review every file before publishing a derivative.
The full [privacy and publication checklist](docs/privacy.md) includes a
practical final review sequence.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_memory_governance.py templates/vault
python3 scripts/check_session_claims.py templates/vault
python3 scripts/doctor.py templates/vault
```

`doctor.py` combines the lightweight checks. It is read-only.

For the design rationale, read [architecture](docs/architecture.md). For the
field-level contract, see the [memory record template](templates/memory_record.md)
and [session claim template](templates/session_claim.md).

## License

MIT. See [LICENSE](LICENSE).
