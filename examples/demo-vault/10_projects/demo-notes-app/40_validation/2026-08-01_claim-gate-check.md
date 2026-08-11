---
memory_type: validation
record_type: validation
record_id: val_01HF7YAT00185GR38E1W8124GK
title: Claim gate dry-run for auth path
created_at: 2026-08-01
owner: demo-user
status: pass
source: fictional demo command output
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: after claim closeout
commands: python3 scripts/check_claim_gate.py examples/demo-vault --path 10_projects/demo-notes-app/10_current_work/INDEX.md
evidence_ref: self-attested JSON summary allowed=false conflict_count=1 (demo)
executed_at: 2026-08-01T09:30:00+00:00
validator: demo-session
---

# Validation: claim gate

## Command

```bash
python3 scripts/check_claim_gate.py examples/demo-vault \
  --path 10_projects/demo-notes-app/10_current_work/INDEX.md
```

## Result

- `allowed`: true
- `conflict_count`: 0
- `is_lock`: false

## Notes

Self-attested in the demo. In real use, paste the JSON summary or a short hash
of the report, never secrets.
