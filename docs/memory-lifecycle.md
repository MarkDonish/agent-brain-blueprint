# Memory lifecycle (0.8.0)

Promotion is **explicit**. Session chatter is never automatically durable.

## Flow

```text
Session event
  → human/agent decides durable value
  → agent-brain memory promote
  → governed Markdown record
  → optional retrieve rebuild
```

Do **not** promote:

- temporary speculation
- raw conversation dumps
- volatile live facts without revalidation
- production claims without `confidence: verified`

## Promote

```bash
python -m agent_brain memory promote ./vault \
  --project my-app \
  --title "Markdown is canonical" \
  --conclusion "Indexes only nominate candidates." \
  --source "architecture decision" \
  --confidence verified
```

`--risk-boundary production` requires `--confidence verified`.

## Supersede

```bash
python -m agent_brain memory supersede ./vault \
  --record-id mem_01... \
  --title "Updated rule" \
  --conclusion "New durable conclusion" \
  --source "revalidation"
```

Old record → `state: superseded`. New record gets `supersedes: [old_id]`.

## Review

```bash
python -m agent_brain memory review ./vault --project my-app
python -m agent_brain memory review ./vault --project my-app --fail-if-due
```

Lists decisions/validation with past `review_after` / `next_review` or
`state: review-required`.

## Trust levels

| Signal | Meaning |
| --- | --- |
| promote write | structured, schema-checked, still not "live truth" for production |
| confidence=verified | author asserts verification method in the record |
| retrieval hit | candidate only |
| session start context | data plane pack for reading |

Control plane remains host policy + `AGENTS.md` + explicit user command.
