SHELL := /bin/bash
export PYTHONPATH := $(PWD):$(PYTHONPATH)

.PHONY: up down ps logs dbshell init test api worker lint

up:
	docker compose up -d
	@echo "Waiting for Postgres health..."
	@for i in {1..40}; do \
		HEALTH=$$(docker inspect --format='{{json .State.Health.Status}}' archangel_db 2>/dev/null || echo '"starting"'); \
		if [[ $$HEALTH == '"healthy"' ]]; then echo "DB is healthy"; exit 0; fi; \
		sleep 1; \
	done; \
	echo "DB not healthy in time" && exit 1

down:
	docker compose down -v

ps:
	docker compose ps

logs:
	docker compose logs -f db

dbshell:
	psql "$$DATABASE_URL"

init:
	python -c "from app.db_pg import init; init(); print('Tables ready')"

test: up init
	pytest -q

api:
	uvicorn app.main:app --reload

worker:
	python outbox_worker.py --limit 10

lint:
	ruff check .
EOF < /dev/null