PYTHON ?= python3

.PHONY: test doctor privacy bootstrap-smoke demo-doctor verify

test:
	$(PYTHON) -m unittest discover -s tests -v

doctor:
	$(PYTHON) scripts/doctor.py templates/vault

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

bootstrap-smoke:
	rm -rf /tmp/agent-brain-blueprint-smoke-vault
	$(PYTHON) scripts/bootstrap.py --destination /tmp/agent-brain-blueprint-smoke-vault --project example-app
	$(PYTHON) scripts/doctor.py /tmp/agent-brain-blueprint-smoke-vault
	$(PYTHON) scripts/check_claim_gate.py /tmp/agent-brain-blueprint-smoke-vault --path 10_projects/example-app/10_current_work/INDEX.md

verify: test doctor demo-doctor privacy bootstrap-smoke
