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
	$(PYTHON) scripts/bootstrap.py --destination /tmp/agent-brain-blueprint-smoke-vault
	$(PYTHON) scripts/doctor.py /tmp/agent-brain-blueprint-smoke-vault

verify: test doctor privacy bootstrap-smoke
