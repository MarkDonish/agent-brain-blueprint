# Privacy and Publication Checklist

This repository must remain a reusable template. Your real vault belongs in a
private location outside the public checkout.

## Keep out of both the template and a public derivative

Before publishing, verify that the repository contains none of the following:

- personal names, addresses, private paths, hostnames, IP addresses, or account IDs
- API keys, tokens, cookies, passwords, OAuth files, `.env` files, or credentials
- raw chat exports, browser data, emails, customer data, invoices, or contracts
- databases, vector indexes, logs, caches, screenshots, media, or model files

Do not assume that an apparently harmless example is safe. Project names,
directory names, task titles, commit messages, screenshots, and test fixtures
can all reveal private context.

## Safe public examples

Use placeholders such as `/path/to/vault`, `example-app`, `demo-user`, and
`sample-task`. Keep all examples fictional, deterministic, and small. Derived
artifacts must be rebuilt locally rather than published.

## Before every publication

1. Inspect the complete staged diff, including renamed and newly added files.
2. Scan text content for private paths, personal names, hostnames, account
   identifiers, credentials, and accidental copies of real notes.
3. Confirm that ignored files include environment files, caches, databases,
   indexes, logs, and generated artifacts.
4. Read the README, documentation, templates, tests, and examples as an
   external visitor would.
5. Ask a second reviewer or agent to look specifically for contextual leaks.
6. Check the public repository page after pushing; titles, descriptions, and
   rendered documents are part of the publication surface.

## Operational boundary

This blueprint is intentionally not a secret-management system, a personal
profile store, or a runtime configuration directory. Store sensitive data in
the appropriate private system, and write only a minimal, non-sensitive pointer
when a coordination record needs to refer to it.
