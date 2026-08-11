# Fictional Demo Vault

This is a **complete but tiny** vault you can inspect without bootstrapping.
Everything here is fictional. No personal, customer, runtime, or production data.

Project: `demo-notes-app` (imaginary local notes app used by two agents).

## Story in 60 seconds

1. **Codex** claims the auth hardening work under `10_current_work/`.
2. **Claude Code** claims only the docs path — concurrent, non-overlapping.
3. Codex finishes a handoff and leaves a durable decision: Markdown is canonical.
4. Closeout records the claim-gate check and points at next action.

```bash
# From the repository root
python3 scripts/doctor.py examples/demo-vault
python3 scripts/check_session_claims.py examples/demo-vault
python3 scripts/check_claim_gate.py examples/demo-vault \
  --path 10_projects/demo-notes-app/60_summaries/INDEX.md
# Expected conflict (Codex already claimed current_work):
python3 scripts/check_claim_gate.py examples/demo-vault \
  --path 10_projects/demo-notes-app/10_current_work/INDEX.md
```

## Suggested reading order

1. `00_entrypoint/SESSION_START_CARD.md`
2. `10_projects/demo-notes-app/PROJECT_OVERVIEW.md`
3. `10_projects/demo-notes-app/10_current_work/INDEX.md`
4. `40_handoffs/session_claims/`
5. `10_projects/demo-notes-app/20_handoffs/`
6. `10_projects/demo-notes-app/50_decisions/`
7. `10_projects/demo-notes-app/40_validation/`

## Safety

Do **not** replace these files with real vault content in the public repository.
For your own machine, bootstrap a private vault instead:

```bash
python3 scripts/bootstrap.py --destination ../my-agent-brain --project my-app
```
