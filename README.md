# Agent Brain Blueprint

A local-first, Markdown-native operating model for shared AI-agent memory.

This repository is a reusable blueprint, not a personal memory dump. It gives
Codex, Claude Code, and other agents a small, auditable place to share project
state, handoffs, durable decisions, validation records, and retrieval hints.

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
git clone https://github.com/your-account/agent-brain-blueprint.git
cd agent-brain-blueprint
python3 scripts/bootstrap.py --destination ../my-agent-brain
python3 scripts/check_memory_governance.py ../my-agent-brain
python3 scripts/check_session_claims.py ../my-agent-brain
python3 scripts/doctor.py ../my-agent-brain
```

The bootstrap command creates a new local vault from the templates. It never
copies this repository's examples into an existing vault without an explicit
destination.

## Repository layout

```text
AGENTS.md                         shared operating rules for agent hosts
docs/                             architecture, privacy, and closeout guidance
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

## Session claims and closeout

Before changing shared memory, create a session claim from
`templates/session_claim.md`. It lists the session, narrow planned paths,
source material, dry-run evidence, and closeout state.

```bash
python3 scripts/check_session_claims.py ./my-agent-brain \
  --claims-dir 40_handoffs/session_claims
```

The checker is read-only. It validates fields, safe vault-relative paths,
ancestor/descendant collisions, and same-target symlink aliases. It does not
lock files, run commands, commit Git, restart services, or treat self-reported
dry-run evidence as independently verified proof. See
[the closeout protocol](docs/session-claims-and-closeout.md) for the trusted,
non-concurrent local-filesystem boundary.

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

## Privacy boundary

Do not add any of these to the vault or this public repository:

- API keys, tokens, cookies, passwords, OAuth files, or `.env` files
- personal profiles, raw conversations, browser data, private messages, or email
- customer data, invoices, account identifiers, or production credentials
- SQLite databases, search indexes, logs, caches, binary artifacts, or model files
- absolute private paths, private project names, IP addresses, or hostnames

Use fictional names such as `example-app`, `demo-user`, and `/path/to/vault` in
documentation and tests. Review every file before publishing a derivative.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_memory_governance.py templates/vault
python3 scripts/check_session_claims.py templates/vault
python3 scripts/doctor.py templates/vault
```

`doctor.py` combines the lightweight checks. It is read-only.

## License

MIT. See [LICENSE](LICENSE).
