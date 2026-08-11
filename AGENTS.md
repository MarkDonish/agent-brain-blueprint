# Shared Agent-Brain Rules

This vault is a shared working memory layer. It is not the runtime source for
agent settings, credentials, plugins, model selection, or production services.

## Read order

1. Read `00_entrypoint/SESSION_START_CARD.md`.
2. Read the relevant project overview under `10_projects/`.
3. Read the current task, handoff, validation, decision, and source records in
   that order.
4. Use retrieval only to locate candidates; reopen the original Markdown or
   real runtime before making a decision.

## Write rules

- Keep records concise, source-backed, and scoped.
- Use `60_templates/memory_record.md` for durable facts and decisions.
- Create a narrow claim before modifying shared memory in a multi-session task.
- Record validation evidence before declaring a task complete.
- Preserve unrelated changes and never claim files owned by another active session.

## Never store

- Credentials, cookies, tokens, passwords, OAuth material, or `.env` files.
- Raw conversations, browser data, private messages, customer data, or account data.
- Databases, generated indexes, large logs, binary assets, or runtime cache files.

## Safety boundary

The vault documents work; it does not authorize production changes. Any fact
about a live system, provider, deployment, policy, or account needs a fresh
source check before action.
