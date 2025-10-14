PY=python

init:
$(PY) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

batch:
$(PY) -m pipeline.batch --urls-file examples/urls.txt

demo:
@echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" > examples/urls.txt
$(PY) -m pipeline.batch --urls-file examples/urls.txt --max 1

api:
uvicorn api.server:app --reload --port 3001
