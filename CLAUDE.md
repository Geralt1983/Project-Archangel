# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: Project Archangel — AI-powered task orchestration with FastAPI, provider adapters (ClickUp, Trello, Todoist), a deterministic+AI triage pipeline, priority scoring, and an outbox for exactly-once provider calls.

Note on existing file: The prior WARP.md contained CLAUDE-specific guidance. That content has been retained in .snapshot_out/files/WARP.md and key rules are summarized below for Warp usage.


Quickstart commands
- Install deps: pip install -r requirements.txt
- Start Postgres (dev): docker compose up -d
- Initialize schema (uses DATABASE_URL): make init
- Run API (FastAPI/uvicorn): make api  # serves app.main:app on localhost:8000
- Run outbox worker: make worker  # or: python outbox_worker.py --limit 10
- Lint: make lint  # ruff
- Run tests (SQLite, no Docker): make test
- Run tests against Postgres: make test.int  # brings up docker and init
- Run a single test: pytest -q tests/test_file.py::TestClass::test_case
- Snapshot for review: bash scripts/make_snapshot.sh
- Usage monitor (Claude Code): make usage; check: curl -s localhost:8000/usage/predictions | jq '.predictions.minutes_remaining'
- Full dev (tmux panes for API, worker, usage): make dev

Environment and services
- DATABASE_URL
  - Unit tests default to SQLite in-memory unless set.
  - Postgres via docker-compose: postgresql://archangel:archangel@localhost:5433/archangel
- Provider credentials (env): CLICKUP_TOKEN, CLICKUP_TEAM_ID, CLICKUP_LIST_ID, CLICKUP_WEBHOOK_SECRET (and similar for Trello/Todoist)
- Serena AI integration: SERENA_ENABLED=true|false, SERENA_BASE_URL, SERENA_API_KEY. When disabled, the system runs purely deterministic triage.

Common API operations (local)
- Health: curl localhost:8000/health
- Intake a task (provider=clickup|trello|todoist):
  curl -X POST 'http://localhost:8000/tasks/intake?provider=clickup' \
    -H 'Content-Type: application/json' \
    -d '{"title":"ACME error on order import","description":"500 on POST /orders","client":"acme","deadline":"2025-08-12T17:00:00Z"}'
- Re-run triage only: curl -X POST localhost:8000/triage/run -H 'Content-Type: application/json' -d '{"title":"..."}'
- Rebalance today: curl -X POST 'http://localhost:8000/rebalance/run' -d '5.0'
- Outbox stats: curl localhost:8000/outbox/stats
- Weekly summary: curl localhost:8000/weekly
- Stale nudges: curl -X POST localhost:8000/nudges/stale/run
- ClickUp webhook creation (requires PUBLIC_BASE_URL): curl -X POST localhost:8000/providers/clickup/webhooks/create
- Score explanation from stdin: echo '{"title":"Task","deadline":"2025-08-12T17:00:00Z","importance":4}' | python scripts/score_explain.py

Provider webhooks (server endpoints)
- POST /webhooks/clickup  (HMAC SHA256 via X-Signature)
- POST /webhooks/trello   (HMAC SHA1 via X-Trello-Webhook)
- POST /webhooks/todoist  (HMAC SHA256 base64 via X-Todoist-Hmac-Sha256)
Deduplication: delivery IDs are stored in events; repeated deliveries are ignored.

High-level architecture
- Entry (FastAPI): app.api defines routes; app.main exposes the app for uvicorn.
- Triage pipeline:
  1) normalize/classify/fill_defaults (app.triage)
  2) deterministic checklist/subtasks generation (app.subtasks)
  3) scoring via compute_score (app.scoring) with client rules (app.config)
  4) optional AI refinement via Serena MCP (app.triage_serena → app.mcp_client), applied conservatively
- Orchestration and planning:
  - Intake uses an orchestrator to compute recommended actions and score metadata; rebalancing endpoint compares orchestrator output with traditional planner.
  - Traditional planner (app.balancer.plan_today) applies fairness boosts computed by app.scheduler.compute_fairness_deficits.
- Outbox pattern (reliability):
  - app.utils.outbox.OutboxManager persists provider operations with idempotency_key = sha256(provider|operation|endpoint|payload) and selects ready batches using FOR UPDATE SKIP LOCKED (Postgres) or a process-wide lock (SQLite).
  - outbox_worker.py picks, marks inflight/delivered/failed, retries with exponential backoff, and dead-letters after N attempts.
- Database layer (app.db_pg):
  - Supports SQLite (dev/unit tests) and Postgres (docker). Tables: events (webhook dedupe), tasks (payload+score), outbox (queue). Utility functions: seen_delivery, save_task, map_upsert/map_get_internal, outbox_cleanup.
- Providers:
  - app.providers.clickup/trello/todoist implement create_task/subtasks/checklist and webhook verification; ClickUp adds robust retry handling. Provider selection is parameterized per request.
- Schedulers/Automation (app.scheduler):
  - daily_reeval rescoring; weekly_checkins posts Slack summaries; hourly_stale_nudge boosts scores for inactivity and posts nudges.
- Coordination hooks (app.coord.hooks):
  - Persist pre_task/post_edit/notify/post_task/decision_trace events to swarm_memory for auditability; also print concise [coord] logs.

Important project rules (from CLAUDE.md, adapted for Warp)
- Names: Use Amex, Charis, Chayah (exact casing). Timezone: PT for timestamps in communication.
- Always run: make test before proposing/committing changes. Before PRs: bash scripts/make_snapshot.sh
- Databases: Prefer Postgres for production/integration; SQLite only for unit tests.
- Idempotency: All provider operations must use idempotency keys (enforced by outbox).
- Retry policy: Retry only 429, 500, 502, 503, 504. Do not retry 400/401/403/404/409.
- Secrets: Never log provider secrets or webhook bodies; environment variables are required for credentials.

Notes and tips specific to this repo
- Single test runs default to SQLite. For Postgres-backed tests, run: make test.int (brings up docker and initializes schema).
- DB shell examples:
  - SQLite file path: set DATABASE_URL=sqlite:///./dev.db then make dbshell
  - Postgres (docker): DATABASE_URL=postgresql://archangel:archangel@localhost:5433/archangel make dbshell
- If SERENA is unavailable or disabled (SERENA_ENABLED=false), the system uses deterministic triage and scoring.

Suggested improvements to the previous WARP.md
- Relocate CLAUDE-specific instructions to CLAUDE.md (already preserved in .snapshot_out/files/WARP.md).
- Keep this WARP.md focused on:
  - How to build/run/test/lint
  - How to operate common workflows (intake, rebalance, outbox)
  - The architecture “big picture” that spans multiple modules
