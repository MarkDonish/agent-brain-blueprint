# Session Claims and Closeout

## Purpose

A claim records the narrow memory files one session expects to edit. It reduces
accidental overlap between agents without becoming a background service or a
distributed lock.

## Trusted local filesystem only

The checker validates record shape, path containment, expiry, and known
conflicts on a trusted, non-concurrent local filesystem. It does **not**:

- lock files
- stop another process from writing
- independently execute dry-run commands
- prove dry-run evidence is true or fresh

Use host permissions, Git review, and human approval for stronger integrity.

## Required fields

Defined in `schemas/session_claim.json`:

- `session_id`, `task`, `claimed_at`, `status`
- `planned_paths` (vault-relative only)
- `dry_run_status`, `dry_run_command`, `dry_run_evidence`
- `closeout_state`, `closeout_summary`, `next_action`

Recommended optional fields:

- `claimed_by` — agent/host identity string
- `expires_at` — ISO-8601 timestamp; when elapsed, the claim is no longer active

## Active claim rules

A claim is active when:

1. `status` is `active` or `blocked`
2. `closeout_state` is not `closed`
3. `expires_at` is missing/unparsable-as-not-expired, or still in the future

Expired claims emit a warning by default and are excluded from conflict
detection. Use `--fail-on-expired` to harden CI.

## Workflow

1. Copy `templates/session_claim.md` into `40_handoffs/session_claims/`.
2. Fill session identity, planned paths, `claimed_by`, and `expires_at`.
3. Before contested writes, run the claim gate:

```bash
python3 scripts/check_claim_gate.py ../my-agent-brain \
  --path 10_projects/example-app/10_current_work/INDEX.md
```

4. Run a dry-run or equivalent read-only validation and summarize its result.
5. Run `scripts/check_session_claims.py` before closeout.
6. Mark the claim closed only when the planned scope is complete.

## Dry-run fields are self-attested

`dry_run_*` values are metadata written by the claiming session. The checker
only validates presence/shape. Independent proof still requires re-running the
command or inspecting the cited evidence path.

## Path safety

`planned_paths` and gate `--path` values must be vault-relative. Absolute paths,
`~`, `..`, empty segments, and backslashes are rejected. Ancestor/descendant
paths conflict with each other.
