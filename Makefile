# Rutas relativas desde la raíz
COMPOSE_FILE=deploy/docker/docker-compose.yaml
ENV_FILE=deploy/.env

# Python interpreter — override at call site: make test PYTHON=/path/to/python
PYTHON ?= python

.PHONY: up down shell logs preprocess train merge test coverage lint fmt

up:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d --remove-orphans trainer

down:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down

shell:
	docker exec -it aegf_trainer /bin/bash

logs:
	docker exec -it aegf_trainer docker logs -f aegf_trainer

preprocess:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) run \
		--user 0 \
		--name aegf_trainer \
		--cpuset-cpus="$(CPU_SET)" \
		trainer
train:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) run --user 0 trainer

merge:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) run --rm merger

quantize:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) run --rm quantizer

# ── Development targets ───────────────────────────────────────────────────────

## test: Run the full test suite without coverage (fast local iteration).
test:
	$(PYTHON) -m pytest tests/ -q -p no:randomly -p no:warnings

## coverage: Run tests with coverage; fails if < 90 % on tracked modules.
coverage:
	$(PYTHON) -m pytest tests/ \
		--cov=src/audit \
		--cov=src/utils \
		--cov=src/factory \
		--cov=src/curation \
		--cov=src/discovery \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=90 \
		-p no:randomly -p no:warnings

## lint: Static type check with pyright (install separately: pip install pyright).
lint:
	$(PYTHON) -m pyright src/ 2>&1 || echo "[lint] pyright not installed — skipping"

## fmt: Auto-format with ruff (install separately: pip install ruff).
fmt:
	$(PYTHON) -m ruff format src/ tests/ 2>&1 || echo "[fmt] ruff not installed — skipping"