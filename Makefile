.PHONY: venv install up down test lint train seed-data api worker

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

up:
	docker compose up --build -d

down:
	docker compose down --remove-orphans

test:
	$(VENV)/bin/pytest -q

lint:
	$(VENV)/bin/ruff check .

seed-data:
	$(PYTHON) -m training.scripts.generate_synthetic_data

train:
	$(PYTHON) -m training.scripts.train_model

api:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	$(PYTHON) -m app.workers.runner
