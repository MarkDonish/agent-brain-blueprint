# agent-brain CLI (0.8.0)

Markdown remains the **canonical** vault data. The CLI is the **tooling runtime**.

## Install / run

From a clone (dev, no install required):

```bash
export PYTHONPATH=src:scripts
python -m agent_brain --help
# or after pip install -e .
agent-brain --help
```

Editable install:

```bash
pip install -e .
agent-brain --version
```

Legacy scripts remain supported:

```bash
python3 scripts/doctor.py ./my-vault
```

## Commands

| Command | Purpose |
| --- | --- |
| `agent-brain init --destination PATH --project NAME` | Bootstrap vault + manifest |
| `agent-brain doctor [vault]` | Format + structure + governance + claims |
| `agent-brain format [vault]` | Manifest / format version check |
| `agent-brain privacy [path]` | Secret/risk scan (secrets redacted) |
| `agent-brain migrate [vault]` | Write `.agent-brain/manifest.json` |
| `agent-brain structure-fix [vault] [--apply]` | Skeleton repair |
| `agent-brain project list [vault]` | List `10_projects/*` |
| `agent-brain project add [vault] --name SLUG` | Add project skeleton |
| `agent-brain claim acquire ...` | Create session claim file |
| `agent-brain claim gate ...` | Pre-write advisory gate |
| `agent-brain claim status ...` | Validate claims |
| `agent-brain claim close --claim PATH` | Mark claim closed |
| `agent-brain record validate [vault]` | Governance check |
| `agent-brain record id [--prefix mem]` | Generate ULID `record_id` |
| `agent-brain retrieve rebuild [vault]` | Rebuild derived FTS index |
| `agent-brain retrieve search [vault] QUERY` | FTS + filters (candidates only) |
| `agent-brain context build [vault] --project P` | Minimal context pack |
| `agent-brain memory promote\|supersede\|review` | Explicit durable memory lifecycle |
| `agent-brain session start\|end` | Host session adapters (Codex/Claude/Cursor) |

## Claim workflow

```bash
agent-brain claim acquire ./my-vault \
  --session-id 20260811-codex-auth \
  --task "Harden rate limits" \
  --path 10_projects/app/10_current_work/INDEX.md

agent-brain claim gate ./my-vault \
  --claim 40_handoffs/session_claims/<file>.md

# work...

agent-brain claim close ./my-vault \
  --claim 40_handoffs/session_claims/<file>.md
```

Gate rules (unchanged from 0.4.1+):

- pass `--session-id` or `--claim` to exclude **your** claim
- invalid existing claims fail closed
- not a distributed lock

## Data vs control plane

See [instruction-boundary.md](instruction-boundary.md). CLI never auto-executes
`commands` fields found inside memory records.
