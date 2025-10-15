SYSTEM_PY ?= python
VENV_PY := .venv/bin/python

.PHONY: init batch demo api lint check-venv

init:
	$(SYSTEM_PY) -m venv .venv
	$(VENV_PY) -m pip install -r requirements.txt

check-venv:
	@if [ ! -x "$(VENV_PY)" ]; then \
		echo "❌ Virtualenv Python not found at $(VENV_PY). Run 'make init' first."; \
		exit 1; \
	fi

batch: check-venv
	$(VENV_PY) -m pipeline.batch --urls-file examples/urls.txt

demo: check-venv
	@echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" > examples/urls.txt
	$(VENV_PY) -m pipeline.batch --urls-file examples/urls.txt --max 1

api: check-venv
	$(VENV_PY) -m uvicorn api.server:app --reload --port 3001

lint:
	@if grep -nE '^[ ]+\S' Makefile; then \
		echo "❌ Makefile contains spaces instead of tabs"; \
		exit 1; \
	fi
	@echo "✅ Makefile indentation looks good"
