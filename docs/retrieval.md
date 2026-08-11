# Retrieval and context (0.7.0)

## Principle

```text
Markdown = canonical truth
SQLite FTS5 = derived, rebuildable nomination layer
```

Never act on a search hit without reopening the source Markdown (and live systems
for production / external / account facts).

## Index location

```text
50_retrieval/indexes/fts.sqlite
```

- gitignored (`indexes/`, `*.sqlite`)
- safe to delete
- rebuild anytime

## Rebuild

```bash
export PYTHONPATH=src:scripts
python -m agent_brain retrieve rebuild ./my-vault
# or
python3 scripts/rebuild_index.py ./my-vault
```

## Search

```bash
python -m agent_brain retrieve search ./my-vault "rate limit" \
  --project demo-notes-app \
  --record-type decision \
  --limit 10
```

Pipeline:

```text
hard filters (project/type/state/…)
  → FTS5 MATCH
  → bm25 rank
  → drop expired/superseded (default)
  → return candidates with path to reopen
```

## Context builder

```bash
python -m agent_brain context build ./my-vault \
  --project demo-notes-app \
  --task "harden password reset" \
  --max-tokens 16000
```

Pack order (high → low priority):

1. Project overview  
2. Current work  
3. Active decisions  
4. Latest validation  
5. Latest handoff  
6. FTS candidates for `--task`  
7. Summaries index  

Budget uses a simple `chars/4` token estimate. Archive / superseded / expired
records are excluded by default.

## What this is not

- Not a vector database  
- Not an embedding service  
- Not authority to execute memory `commands` fields  
