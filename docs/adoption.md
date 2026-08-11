# Adopting the Blueprint

This guide explains how to use the blueprint with an existing agent host while
keeping the memory vault separate from private host configuration.

## 1. Create a private vault

Bootstrap a new directory from this repository and initialize it as a private
Git repository. Do not place the vault inside a public template checkout, and
do not copy real records back into this repository.

```bash
python3 scripts/bootstrap.py --destination /path/to/private-vault
```

## 2. Give the host a minimal read protocol

At the beginning of a task, the agent should read:

1. `00_entrypoint/SESSION_START_CARD.md`
2. the relevant project overview under `10_projects/`
3. only the task, handoff, validation, decision, and source records needed for
   the current work

An agent instruction file can point to this sequence. Avoid asking every new
session to read every historical record; selective retrieval is the purpose of
the vault structure.

## 3. Keep retrieval derivative

You may add local keyword search, SQLite FTS, or vector retrieval. Keep its
database, indexes, embeddings, and model artifacts outside version control.
Search results nominate records; the host must reopen the matching Markdown
file before relying on it.

## 4. Write through explicit record types

Use the included templates for durable memory records and session claims.
Durable records need provenance, confidence, freshness, scope, risk boundary,
review trigger, and an owner. Before shared edits, create a narrow claim that
lists only the paths the session actually plans to change.

## 5. Close out with evidence

Before declaring work complete, record validation evidence and close the
session claim. Run the read-only session checker to expose malformed records or
obvious overlap:

```bash
python3 scripts/check_session_claims.py /path/to/private-vault \
  --claims-dir 40_handoffs/session_claims
```

The checker supports coordination in a trusted, non-concurrent local setup. It
does not acquire locks, perform runtime validation, or guarantee safe behavior
against concurrent filesystem changes.

## Host-specific data stays native

Never move credentials, model configuration, tool permissions, browser data,
plugins, local databases, or production runtime state into the vault. The
vault holds human-readable coordination records, not an agent host's operating
system.
