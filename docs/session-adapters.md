# Session adapters (0.8.0)

Host-agnostic helpers for Codex, Claude Code, Cursor, and similar CLIs.

## Session start

```bash
python -m agent_brain session start ./vault \
  --project my-app \
  --task "fix login" \
  --session-id 20260812-codex-1 \
  --json --meta-only
```

Returns:

- paths to session card / overview / current work
- suggested `context build` / `claim acquire` / `claim gate` commands
- optional packed context document
- control-plane vs data-plane reminder

**Does not** write claims or run tools silently.

## Session end

```bash
python -m agent_brain session end ./vault \
  --project my-app \
  --session-id 20260812-codex-1 \
  --claim 40_handoffs/session_claims/....md \
  --close-claim \
  --write-handoff \
  --handoff-summary "Finished rate-limit tests; docs remain open."
```

Returns a closeout checklist. Optional actions:

- close a claim file
- write a project handoff

**Does not** auto-promote durable memory or execute validation commands.

## Recommended host loop

```text
session start
  → claim acquire
  → claim gate --claim ...
  → work
  → validation record (manual/self-attested with evidence)
  → memory promote (only durable items)
  → session end (--close-claim / --write-handoff as needed)
```
