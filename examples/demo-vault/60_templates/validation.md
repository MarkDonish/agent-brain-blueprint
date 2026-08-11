---
# Record type: validation evidence
# Checked by: scripts/check_memory_governance.py (soft unless --strict-soft)
# Required under soft schema: memory_type, status, owner

memory_type: validation
title: Validation for example object
created_at: 2026-01-01
status: pass
owner: demo-user
source: local command output
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: when the validated surface changes
evidence: exit code 0; see command block
commands: python3 -m unittest discover -s tests -v
---

# Validation: object under test

## Goal

What must be true.

## Commands or checks

```bash
# record the exact read-only or test command used
```

## Result

Short factual result. Prefer counts, exit codes, hashes, or report paths over
raw log dumps.

## Gaps

What remains untested.
