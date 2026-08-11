# Why Agent Brain (not chat history)

## The multi-agent failure mode

You run Codex on a hard refactor. Claude Code polishes docs. Another session
resumes tomorrow. Without a shared, boring file system contract:

1. Each host invents its own notes layout.
2. Handoffs rot inside long chats.
3. Two sessions overwrite the same “status” file.
4. Retrieval tools surface plausible but wrong snippets.
5. Someone pastes a key into a memory file “just for later.”

## What we optimize for

| Priority | Choice |
| --- | --- |
| Durability | Markdown in Git-friendly trees |
| Auditability | Frontmatter contracts + checkers |
| Concurrency | Narrow claims, not magic locks |
| Safety | Privacy scan + isolation directory |
| Portability | No SaaS, no required vector stack |

## What we deliberately skip

- Distributed locking clusters
- Hosted multi-tenant memory products
- Treating embeddings as source of truth
- Shipping anyone’s private vault as the “example”

## Fit with Codex

Codex and similar coding agents already leave trails as files and commands.
This blueprint makes those trails **shared, shaped, and checkable** so a second
agent can start from evidence instead of folklore.
