# Vault format and versioning

## Manifest

Every vault bootstrapped with tool **0.5.0+** includes:

```text
.agent-brain/manifest.json
```

Example:

```json
{
  "vault_format_version": 1,
  "created_with": "0.5.0",
  "minimum_tool_version": "0.5.0",
  "layout_schema": "schemas/vault_layout.json"
}
```

## Compatibility

| Situation | Behavior |
| --- | --- |
| Manifest present, version supported | Pass |
| Manifest missing (pre-0.5 vault) | `check_vault_format.py` **warns**; structure may still fail if layout requires manifest |
| Unsupported `vault_format_version` | Fail; use migration, do not hand-edit blindly |

Upgrade an older vault:

```bash
python3 scripts/write_vault_manifest.py /path/to/vault
python3 scripts/fix_vault_structure.py /path/to/vault --apply
python3 scripts/doctor.py /path/to/vault
```

## Layout SSoT

Skeleton paths and file/directory kinds live only in:

```text
schemas/vault_layout.json
```

`check_vault_structure.py`, `fix_vault_structure.py`, and bootstrap consume this file. Do not reintroduce parallel `REQUIRED_PATHS` lists.

## Stable record identity

Optional frontmatter field:

```yaml
record_id: mem_01HF7YAT00000G40R40M30E209
```

- Prefix + Crockford ULID (time-sortable, local generation)
- Prefer referencing `record_id` over fragile file paths when linking decisions, validation, and supersession
- Generate:

```bash
PYTHONPATH=scripts python3 -c "from lib.record_id import new_record_id; print(new_record_id('mem'))"
```

## Taxonomy (compat)

Keep existing `memory_type` for backward compatibility.

Prefer also setting:

| Field | Role |
| --- | --- |
| `record_type` | Shape of the artifact: task, decision, validation, handoff, claim, … |
| `knowledge_type` | Epistemic class: fact, inference, decision, workflow, lesson, evidence |
| `state` | Lifecycle: candidate, verified, active, review-required, superseded, expired, archived |

Do not treat `memory_type` alone as a full type system going forward.
