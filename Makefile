SHELL := /bin/bash
export PYTHONPATH := $(PWD):$(PYTHONPATH)

# Default to in-memory SQLite for unit tests unless DATABASE_URL is provided
DATABASE_URL ?= sqlite:///:memory:

.PHONY: up down ps logs dbshell init test api worker lint usage dev

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

# Unit tests default (SQLite). Use test.int for Postgres-backed tests.

test: test.unit

# Run unit tests against SQLite (no Docker required)
test.unit:
	pytest -q

# Run integration tests against Postgres in Docker
test.int: up init
	pytest -q

api:
	uvicorn app.main:app --reload

worker:
	python outbox_worker.py --limit 10

lint:
	ruff check .

usage:
	# Run Claude Code usage monitor in terminal
	# Install: pip install claude-code-usage-monitor
	@command -v claude-monitor >/dev/null 2>&1 || { \
		echo "Installing claude-code-usage-monitor..."; \
		pip install claude-code-usage-monitor 2>/dev/null || \
		pip install git+https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git; \
	}
	@export CLAUDE_CONFIG_DIR="${HOME}/Library/Application Support/Claude" && \
		claude-monitor || python -m claude_monitor

dev:
	# Start full dev environment with monitoring
	@echo "=== Archangel Development Environment ==="
	@command -v tmux >/dev/null 2>&1 && { \
		echo "Starting tmux session with API, worker, and usage monitor..."; \
		tmux new-session -d -s archangel \; \
			split-window -h 'make api' \; \
			split-window -v 'make worker' \; \
			select-pane -L \; split-window -v 'make usage' \; \
			select-pane -t 0 \; \
			send-keys 'echo "=== Archangel Dev Environment ===" && echo "API: localhost:8000" && echo "Worker: processing outbox" && echo "Usage: monitoring Claude Code"' Enter; \
		echo "Tmux session 'archangel' started. Attach with: tmux attach -t archangel"; \
	} || { \
		echo "Tmux not available. Starting components individually:"; \
		echo ""; \
		echo "Terminal 1: make api      # API server on localhost:8000"; \
		echo "Terminal 2: make worker   # Outbox worker"; \
		echo "Terminal 3: make usage    # Usage monitor"; \
		echo ""; \
		echo "Starting API server now..."; \
		make api; \
	}