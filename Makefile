PYTHON ?= python3
export PYTHONPATH := src:scripts$(if $(PYTHONPATH),:$(PYTHONPATH),)
AB := $(PYTHON) -m agent_brain

.PHONY: test doctor privacy privacy-strict bootstrap-smoke demo-doctor cli-smoke verify

test:
	$(PYTHON) -m unittest discover -s tests -v

doctor:
	$(PYTHON) scripts/doctor.py templates/vault
	$(PYTHON) scripts/check_vault_format.py templates/vault --require-manifest

demo-doctor:
	$(PYTHON) scripts/doctor.py examples/demo-vault
	$(PYTHON) scripts/check_session_claims.py examples/demo-vault
	# Free path: no claim owns summaries yet → allowed
	$(PYTHON) scripts/check_claim_gate.py examples/demo-vault --path 10_projects/demo-notes-app/60_summaries/INDEX.md
	# Foreign session without exclusion: Codex owns current_work → conflict
	$(PYTHON) -c 'import json,subprocess,sys; p=subprocess.run([sys.executable,"scripts/check_claim_gate.py","examples/demo-vault","--path","10_projects/demo-notes-app/10_current_work/INDEX.md"],capture_output=True,text=True); r=json.loads(p.stdout); assert r.get("allowed") is False and r.get("conflict_count",0)>=1, r; print("demo foreign conflict ok")'
	# Owner session excludes self → allowed
	$(PYTHON) scripts/check_claim_gate.py examples/demo-vault --session-id 20260801-0900-codex-auth --path 10_projects/demo-notes-app/10_current_work/INDEX.md
	$(PYTHON) scripts/check_claim_gate.py examples/demo-vault --claim 40_handoffs/session_claims/2026-08-01_codex-auth-claim.md

privacy:
	$(PYTHON) scripts/check_privacy_scan.py .

privacy-strict:
	$(PYTHON) scripts/check_privacy_scan.py . --strict

bootstrap-smoke:
	@tmp="$$(mktemp -d "$${TMPDIR:-/tmp}/agent-brain-bootstrap-smoke.XXXXXX")"; \
	$(PYTHON) scripts/bootstrap.py --destination "$$tmp/vault" --project example-app && \
	$(PYTHON) scripts/doctor.py "$$tmp/vault" && \
	$(PYTHON) scripts/check_claim_gate.py "$$tmp/vault" --path 10_projects/example-app/10_current_work/INDEX.md; \
	status=$$?; rm -rf "$$tmp"; exit $$status

cli-smoke:
	@tmp="$$(mktemp -d "$${TMPDIR:-/tmp}/agent-brain-cli-smoke.XXXXXX")"; \
	$(AB) --version && \
	$(AB) init --destination "$$tmp/vault" --project cli-app && \
	$(AB) doctor "$$tmp/vault" && \
	$(AB) project list "$$tmp/vault" && \
	$(AB) claim acquire "$$tmp/vault" --session-id smoke --task "cli smoke" --path 10_projects/cli-app/10_current_work/INDEX.md --filename smoke-claim.md && \
	$(AB) claim gate "$$tmp/vault" --claim 40_handoffs/session_claims/smoke-claim.md && \
	$(AB) retrieve rebuild "$$tmp/vault" && \
	$(AB) retrieve search "$$tmp/vault" "current work" --project cli-app --limit 5 && \
	$(AB) context build "$$tmp/vault" --project cli-app --task "cli smoke" --max-tokens 2000 --json --meta-only && \
	$(AB) memory promote "$$tmp/vault" --project cli-app --title "Smoke decision" --conclusion "CLI smoke promotes only explicit durable notes." --source "cli-smoke" --confidence verified && \
	$(AB) memory review "$$tmp/vault" --project cli-app && \
	$(AB) session start "$$tmp/vault" --project cli-app --task "smoke" --json --meta-only && \
	$(AB) privacy "$$tmp"; \
	status=$$?; rm -rf "$$tmp"; exit $$status

verify: test doctor demo-doctor privacy privacy-strict bootstrap-smoke cli-smoke
