# Session Claims and Closeout

## Purpose

A claim records the narrow memory files one session expects to edit. It reduces
accidental overlap between agents without becoming a background service.

## Workflow

1. Copy `templates/session_claim.md` into `40_handoffs/session_claims/`.
2. Fill in the session identifier, task, planned paths, and source pointers.
3. Run a dry-run or equivalent read-only validation and summarize its result.
4. Run `scripts/check_session_claims.py` before closeout.
5. Mark the claim closed only when the planned scope is complete and unresolved
   work is recorded for the next session.

## Important limits

The checker validates record shape, path containment, and known conflicts. Its
dry-run fields are self-attested metadata: it does not execute commands or
independently establish freshness, truth, or completion. It is designed for a
trusted, non-concurrent local filesystem and does not guarantee protection from
an attacker or a concurrent filesystem replacement between checking and read.

Use Git review, host permissions, and explicit human approval for stronger
integrity or authorization needs.
