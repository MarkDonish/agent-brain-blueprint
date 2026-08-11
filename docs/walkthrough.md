# Walkthrough: multi-agent memory in five minutes

Audience: you already run more than one coding agent (Codex, Claude Code, …)
and keep losing state across sessions.

## 1. Read the pain map

| Without a vault | With this blueprint |
| --- | --- |
| Each agent invents its own notes folder | One project tree under `10_projects/` |
| Handoffs live in chat | Handoff Markdown with next action |
| Two sessions edit the same file | Narrow claims + claim gate |
| “Done” means “I think so” | Validation record before closeout |

## 2. Run the fictional demo

From the repository root:

```bash
python3 scripts/doctor.py examples/demo-vault
python3 scripts/check_session_claims.py examples/demo-vault

# Free path — nobody claimed summaries yet
python3 scripts/check_claim_gate.py examples/demo-vault \
  --path 10_projects/demo-notes-app/60_summaries/INDEX.md

# Claimed path — Codex already owns current_work
python3 scripts/check_claim_gate.py examples/demo-vault \
  --path 10_projects/demo-notes-app/10_current_work/INDEX.md
```

What you should see:

- doctor: structure + governance + claims pass
- two active claims with **different** planned paths
- free path gate: `allowed=true`
- claimed path gate: `allowed=false` with a conflict pointing at the Codex claim

## 3. Follow the story files

1. `examples/demo-vault/00_entrypoint/SESSION_START_CARD.md`
2. `examples/demo-vault/10_projects/demo-notes-app/PROJECT_OVERVIEW.md`
3. `examples/demo-vault/40_handoffs/session_claims/`
4. `examples/demo-vault/10_projects/demo-notes-app/20_handoffs/`
5. `examples/demo-vault/10_projects/demo-notes-app/50_decisions/`
6. `examples/demo-vault/10_projects/demo-notes-app/40_validation/`

## 4. Bootstrap your private vault

```bash
python3 scripts/bootstrap.py --destination /path/to/my-agent-brain --project my-app
python3 scripts/doctor.py /path/to/my-agent-brain
```

Copy a claim template from `60_templates/session_claim.md` (or repo
`templates/session_claim.md`) before multi-session edits.

## 5. Before you publish anything derived from a vault

```bash
python3 scripts/check_privacy_scan.py .
```

Never publish real claims with private absolute paths, customer content, or secrets.

## What this is not

- Not a distributed lock service
- Not a vector database
- Not a place to store credentials
- Not a dump of your private Agent-Brain

## Next docs

- [Architecture](architecture.md)
- [Session claims and closeout](session-claims-and-closeout.md)
- [Privacy](privacy.md)
