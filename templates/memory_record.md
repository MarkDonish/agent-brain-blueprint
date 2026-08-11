---
# Record type: durable memory / decision
# Checked by: scripts/check_memory_governance.py (strict for decisions)
# Required: memory_type, source, confidence, freshness, scope, risk_boundary, next_review, owner
# Optional: record_id (stable ULID), record_type, knowledge_type, state, review_after, supersedes
# Generate record_id: python3 -c "from scripts.lib.record_id import new_record_id; print(new_record_id())"
# or from repo root with PYTHONPATH=scripts: from lib.record_id import new_record_id

memory_type: decision
record_type: decision
knowledge_type: decision
record_id: mem_01HF7YAT00000G40R40M30E209
title: A clear, durable statement
created_at: 2026-01-01
updated_at: 2026-01-01
state: active
source: original document / command output / commit / primary source / user confirmation
source_path_or_url: /path/to/source-or-url
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2026-02-01
review_after: 2026-02-01
owner: demo-user
---

# Title

## Conclusion

State the durable conclusion in one to three sentences.

## Evidence

- Source: `source_path_or_url`
- Verification method: file comparison / command output / primary source / live check
- Evidence status: verified / inferred / pending / information-missing

## Scope and expiry

Explain where this record applies and what must happen before it is treated as
current again.

## Action rule

Write a concrete future rule. Do not turn an inference into a mandatory rule.
