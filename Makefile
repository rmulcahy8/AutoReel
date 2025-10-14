PY=python

.PHONY: init batch demo api lint

init:
	$(PY) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

batch:
	$(PY) -m pipeline.batch --urls-file examples/urls.txt

demo:
	@echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" > examples/urls.txt
	$(PY) -m pipeline.batch --urls-file examples/urls.txt --max 1

api:
	uvicorn api.server:app --reload --port 3001

lint:
	@if grep -nE '^[ ]+\S' Makefile; then \
		echo "❌ Makefile contains spaces instead of tabs"; \
		exit 1; \
	fi
	@echo "✅ Makefile indentation looks good"
