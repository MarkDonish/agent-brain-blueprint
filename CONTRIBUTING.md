# Contributing

Thanks for helping improve a local-first multi-agent memory blueprint.

## Ground rules

1. **No private data.** Never commit real vaults, personal paths, secrets, customer
   content, chat dumps, databases, or logs.
2. **Local-first.** Prefer dogfooding a private vault, then extract only reusable
   technical pieces into this repo.
3. **Keep dependencies at zero** for runtime scripts (Python stdlib only) unless
   there is a strong, documented reason.
4. **Tests first** for behavior changes under `scripts/` or `schemas/`.

## Dev loop

```bash
make verify
```

That runs unit tests, template doctor, privacy scan, and bootstrap smoke.

Useful singles:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py templates/vault
python3 scripts/doctor.py examples/demo-vault
python3 scripts/check_privacy_scan.py .
```

## Good first contributions

- Clearer README / walkthrough wording
- Stronger fictional demo scenarios (still non-personal)
- Schema edge cases + tests
- Better doctor / claim-gate error messages
- Additional privacy-scan patterns with tests (watch false positives)

## Pull request checklist

- [ ] `make verify` passes
- [ ] Privacy scan clean (`secret_finding_count=0`, no personal paths)
- [ ] Docs updated if behavior or UX changed
- [ ] CHANGELOG note under Unreleased or next version

## Scope we will reject

- Dumping a real personal second-brain into `examples/`
- Turning claims into a network lock service without a design discussion
- Bundling embedding / vector DB runtimes as a hard dependency
- Marketing-only PRs with no technical improvement

## Security

If you find a secret-leak path in the scanner or templates, open an issue with a
**redacted** repro. Do not paste real credentials.
