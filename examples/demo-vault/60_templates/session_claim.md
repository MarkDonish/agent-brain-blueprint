---
# Record type: session claim
# Checked by: scripts/check_session_claims.py (and soft governance)
# Required fields: session_id, task, claimed_at, status, planned_paths,
# dry_run_*, closeout_*, next_action
# Optional but recommended: claimed_by, expires_at
# Note: dry_run_* is self-attested metadata, not independent proof.

memory_type: session-handoff
source: current session and read-only validation
confidence: pending
freshness: valid only for this session; review before closeout
scope: project / agent / current session
risk_boundary: limited to planned paths; does not authorize runtime or production changes
next_review: before closeout or when the session is resumed
owner: demo-user
claimed_by: demo-agent

session_id: YYYYMMDD-HHMM-agent-short-id
task: One-sentence task objective
claimed_at: 2026-01-01T00:00:00+00:00
expires_at: 2026-01-01T08:00:00+00:00
status: active
planned_paths:
  - 10_projects/example-app/10_current_work/INDEX.md
source_paths:
  - 10_projects/example-app/PROJECT_OVERVIEW.md
dry_run_status: pending
dry_run_command: Record a read-only command or check
dry_run_evidence: Record a short result, count, hash, or report path
closeout_state: open
closeout_summary: Not closed
next_action: Run the dry-run and verify claim conflicts
---

# Session Claim

Do not put secrets, raw conversations, databases, or large logs in this file.

`dry_run_*` fields are self-reported. Use `scripts/check_claim_gate.py` before writes
to detect active claim conflicts. This is not a distributed lock.
