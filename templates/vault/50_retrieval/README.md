# Retrieval (derived)

Indexes under `indexes/` are **rebuildable** and must stay out of Git.

```bash
python -m agent_brain retrieve rebuild ../path-to-this-vault
python -m agent_brain retrieve search ../path-to-this-vault "query" --project example-app
```

Markdown remains canonical. Search hits only nominate candidates.
