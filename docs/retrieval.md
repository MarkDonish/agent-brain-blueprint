# Retrieval, generations, graph, and context (0.10.0)

## Principle

```text
Markdown = canonical truth
SQLite FTS5 = derived, rebuildable nomination layer
```

Never act on a search hit without reopening the source Markdown (and live systems
for production / external / account facts).

## Index location

```text
50_retrieval/indexes/current.json
50_retrieval/indexes/generations/<generation_id>/{fts.sqlite,manifest.json}
```

- `current.json` is an atomic pointer. A generation is built in a sibling
  staging directory, checked for SQLite integrity/schema/coverage, and then
  renamed into `generations/` before the pointer is replaced.
- `indexes/` and `*.sqlite` are derived and safe to delete. A healthy previous
  generation is retained when a build fails.
- Older vaults with only `50_retrieval/indexes/fts.sqlite` remain readable.

### Coverage contract

`source_count` counts eligible canonical Markdown only. Markdown below safety
boundaries such as `80_sensitive_isolation`, `90_archive`, `private`, `logs`,
or `indexes` is reported as `blocked_source_count` and its paths are exposed;
it is never silently treated as indexed. `coverage_complete` is true only when
every eligible source is indexed, no source is missing/stale, the generation is
valid, and no blocked Markdown exists. `check` is read-only; `refresh` compares
content fingerprints and publishes only when added/modified/deleted files are
found; unchanged refreshes are no-ops.

The scanner resolves the vault layout before deriving records. It supports the
public `blueprint-en-v1` paths and the local `agent-brain-zh-v1` paths (for
example `10_项目工作区/<项目>/50_事实与决策`). Project names and record types
are normalized through the same adapter used by structure checks and context
building. Ambiguous English/Chinese core markers fail closed.

## Rebuild

```bash
export PYTHONPATH=src:scripts
python -m agent_brain retrieve rebuild ./my-vault
# inspect without writing
python -m agent_brain retrieve status ./my-vault
python -m agent_brain retrieve check ./my-vault
# explicit changed-only refresh (writes derived files only)
python -m agent_brain retrieve refresh ./my-vault
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

`--detail scout|verify|auditor` (aliases `compact|default|full`) controls the
evidence budget. Scout returns metadata and relation summaries, verify adds a
short preview, and auditor adds bounded evidence plus `truncated` and
`limitations`. Results include `generation_id`, coverage, and a stable
generation-bound `next_cursor`; a cursor from a newer generation fails closed.
Inactive records are filtered before pagination.

Pipeline:

```text
hard filters (project/type/state/…)
  → FTS5 MATCH
  → drop expired/superseded (default)
  → deterministic navigation-page path weighting
  → return candidates with path to reopen
```

The derived SQLite also contains `nodes` and `relations`. Directory edges
(`BELONGS_TO`, `HANDOFF_FOR`) and explicit frontmatter references
(`VALIDATES`, `SUPERSEDES`, `DERIVED_FROM`, `NEXT_STEP`) retain evidence,
source path, and confidence. Similar prose never creates an edge; an explicit
reference that cannot resolve is returned with `unresolved_ref`.

```bash
python -m agent_brain graph query ./my-vault --project demo-notes-app
python -m agent_brain graph query ./my-vault --relation-type VALIDATES --limit 20
```

## Context builder

```bash
python -m agent_brain context build ./my-vault \
  --project demo-notes-app \
  --task "harden password reset" \
  --max-tokens 16000 --profile verify
```

Context accepts `scout|verify|auditor` and `compact|default|full` aliases and
returns the generation/coverage metadata plus an explicit `truncated` flag.
Compact packs are metadata-first and materially smaller than full packs.

Pack order (high → low priority):

1. Project overview  
2. Current work  
3. Active decisions  
4. Latest validation  
5. Latest handoff  
6. FTS candidates for `--task`  
7. Summaries index  

The logical sections above map to either vocabulary; a Chinese project uses
`00_项目总览.md`, `10_当前任务`, `20_交接记录`, `40_验证记录`, and the other
configured project directories without copying or renaming source records.

Budget uses a simple `chars/4` token estimate. Archive / superseded / expired
records are excluded by default.

## What this is not

- Not a vector database  
- Not an embedding service  
- Not authority to execute memory `commands` fields  
