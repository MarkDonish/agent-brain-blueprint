---
# Record type: durable memory / decision
# Checked by: scripts/check_memory_governance.py (strict for decisions)
# Required: memory_type, source, confidence, freshness, scope, risk_boundary, next_review, owner

memory_type: decision
title: A clear, durable statement
created_at: 2026-01-01
updated_at: 2026-01-01
source: original document / command output / commit / primary source / user confirmation
source_path_or_url: /path/to/source-or-url
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2026-02-01
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
