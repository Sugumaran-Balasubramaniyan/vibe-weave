.PHONY: run test demo

HOST ?= 0.0.0.0
PORT ?= 8000

run:
	@echo "Starting GlassBox Sentinel on http://${HOST}:${PORT}"
	PYTHONPATH=. .venv/bin/uvicorn app.main:app --host ${HOST} --port ${PORT} --reload

test:
	PYTHONPATH=. .venv/bin/pytest tests/ -v

demo:
	@echo "Running demo scenario..."
	@echo "See scripts/demo.sh for manual demo steps"

clean:
	rm -rf .venv __pycache__ *.pyc

install:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
