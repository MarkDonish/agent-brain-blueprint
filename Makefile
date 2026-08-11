PYTHON ?= python3

.PHONY: test doctor privacy bootstrap-smoke verify

test:
	$(PYTHON) -m unittest discover -s tests -v

doctor:
	$(PYTHON) scripts/doctor.py templates/vault

privacy:
	$(PYTHON) scripts/check_privacy_scan.py .

bootstrap-smoke:
	rm -rf /tmp/agent-brain-blueprint-smoke-vault
	$(PYTHON) scripts/bootstrap.py --destination /tmp/agent-brain-blueprint-smoke-vault --project example-app
	$(PYTHON) scripts/doctor.py /tmp/agent-brain-blueprint-smoke-vault
	$(PYTHON) scripts/check_claim_gate.py /tmp/agent-brain-blueprint-smoke-vault --path 10_projects/example-app/10_current_work/INDEX.md

verify: test doctor privacy bootstrap-smoke
