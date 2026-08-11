# Project overview: demo-notes-app

Fictional local notes app used only to demonstrate multi-agent memory.

## Goal

Ship password-reset flow hardening without two agent sessions overwriting each
other's handoffs.

## Current state

- Auth hardening is active work (Codex claim).
- Docs polish is parallel (Claude claim on a different path).
- Durable decision: Markdown remains the source of truth for project state.

## Where to look

| Need | Path |
| --- | --- |
| Active work | `10_current_work/INDEX.md` |
| Latest handoff | `20_handoffs/` |
| Validation | `40_validation/` |
| Decisions | `50_decisions/` |

## Out of scope for this vault

Secrets, API keys, customer notes content, production deploy credentials.
