# Privacy and Publication Checklist

This repository must remain a reusable template. Your real vault belongs in a
private location outside the public checkout.

## Never publish

- personal names, private addresses, private paths, hostnames, IP addresses, or account IDs
- API keys, tokens, cookies, passwords, OAuth files, `.env` files, or credentials
- raw chat exports, browser data, emails, customer data, invoices, or contracts
- databases, vector indexes, logs, caches, screenshots, media, or model files
- real project codenames that reveal private business or personal plans

## Safe placeholders

Use placeholders such as:

- `/path/to/vault`
- `example-app`
- `demo-user`
- `YYYY-MM-DD`

## Pre-publish commands

```bash
python3 scripts/check_privacy_scan.py .
python3 scripts/check_privacy_scan.py . --strict
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py templates/vault
```

`--strict` also fails on home paths, emails, and IPv4-looking strings. Review
every finding even if you choose to keep an intentional example.

Before publishing a derivative:

1. Run the privacy scanner.
2. Inspect `git status` and `git diff`.
3. Search for `/Users/`, `.env`, `BEGIN PRIVATE`, and real project names.
4. Have another person or agent read the README and examples as if they were public.
