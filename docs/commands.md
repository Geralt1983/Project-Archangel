# Project Archangel Commands

Quick reference for slash commands and their local equivalents.

## Core Commands

### /snap
Create a review snapshot for code changes.

Runs:
```bash
bash scripts/make_snapshot.sh
```

Creates: `snapshot_YYYYMMDD_HHMMSS_branch_commit.zip` containing:
- `REVIEW.md` - Change summary
- `diff.patch` - Git diff
- `files/` - Modified files
- `manifest.json` - Metadata

### /ci
Commit changes and push to remote.

Runs:
```bash
git add .
git commit -m "feat: description"
git push
```

Optional PR creation:
```bash
gh pr create --title "Title" --body "Description"
```

### /outbox:tick
Process pending outbox operations.

Runs:
```bash
python outbox_worker.py --limit 10
```

Options:
- `--limit N` - Process N items (default: 10)
- `--max-tries N` - Retry N times before dead letter (default: 5)

### /plan:day
Generate daily task plan based on available hours.

Runs:
```bash
curl -s localhost:8000/planner/daily -d '{"hours":5}'
```

Response includes:
- Prioritized task list
- Time allocations
- Decision traces

### /score:explain
Explain scoring calculation for a task.

Runs:
```bash
echo '{"title":"Task","deadline":"2025-08-12T17:00:00Z","importance":4}' | python scripts/score_explain.py
```

Input JSON fields:
- `title` - Task title
- `deadline` or `due_at` - ISO8601 timestamp
- `importance` - 1-5 scale
- `effort_hours` - Estimated hours
- `client` - amex/charis/chayah
- `created_at` - ISO8601 timestamp
- `recent_progress` - 0.0-1.0

### /memory:recent
View recent coordination events.

Runs:
```bash
curl -s localhost:8000/memory/recent?session=default&limit=20
```

### /memory:traces
View decision traces for task rebalancing.

Runs:
```bash
curl -s localhost:8000/memory/traces?session=default&limit=10
```

### /usage:monitor
Start real-time Claude Code usage monitoring.

Runs:
```bash
make usage
```

Features:
- Live token usage bars
- Burn rate predictions  
- Cost estimates
- "Time until exhaustion" alerts

### /usage:check
Check current usage predictions.

Runs:
```bash
curl -s localhost:8000/usage/predictions
```

Returns:
- Hours/minutes remaining
- Burn rate per hour
- Warning flags for 30min/10min thresholds

## Development Commands

### make up
Start Docker services (PostgreSQL).
```bash
docker compose up -d
```

### make init
Initialize database schema.
```bash
python -c "from app.db_pg import init; init()"
```

### make test
Run test suite.
```bash
pytest -q
```

### make down
Stop Docker services.
```bash
docker compose down
```

### make usage
Run Claude Code usage monitor.
```bash
make usage
```

Auto-installs monitor if missing, sets config directory.

### make dev  
Start full development environment with tmux.
```bash
make dev
```

Creates tmux session with 4 panes:
- API server (localhost:8000)
- Outbox worker
- Usage monitor  
- Command terminal

Attach with: `tmux attach -t archangel`

## Utility Commands

### Check outbox status
```bash
python -c "from app.db_pg import get_conn; from app.utils.outbox import OutboxManager; ob = OutboxManager(get_conn); print(ob.get_stats())"
```

### Clean delivered outbox items
```bash
python -c "from app.db_pg import outbox_cleanup; outbox_cleanup(retain_days=7)"
```

### View recent errors
```bash
psql $DATABASE_URL -c "select id, operation_type, error from outbox where status='failed' order by updated_at desc limit 10"
```

### Force retry stuck item
```bash
psql $DATABASE_URL -c "update outbox set status='pending', retry_count=0 where id=123"
```

## Monitoring

### View metrics
```bash
grep '\[metrics\]' logs/*.log | tail -20
```

### Watch outbox processing
```bash
watch -n 5 'python -c "from app.db_pg import get_conn; from app.utils.outbox import OutboxManager; ob = OutboxManager(get_conn); print(ob.get_stats())"'
```

## Testing Specific Components

### Test scoring only
```bash
pytest tests/test_scoring.py -v
```

### Test outbox only
```bash
pytest tests/test_outbox_integration.py -v
```

### Test retry logic
```bash
pytest tests/test_retry.py -v
```

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string

Optional:
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `PYTHONPATH` - Include project root

## Quick Fixes

### Reset test database
```bash
docker compose down -v
docker compose up -d
make init
```

### Clear all outbox items
```bash
psql $DATABASE_URL -c "truncate table outbox"
```

### Check Python dependencies
```bash
pip freeze | grep -E "(psycopg2|fastapi|pytest|httpx)"
```