# CLAUDE.md

This file provides guidance to Claude Code when working with Project Archangel.

## Mission

Project Archangel is an AI-powered task orchestration system that balances workload across providers (Amex, Charis, Chayah) using sophisticated scoring algorithms, outbox patterns, and reliability mechanisms.

## House Rules

1. **Name Corrections**: Always use Amex (not Amit), Charis (not Chris), Chayah (not Chaya)
2. **Timezone**: All times in PT (Pacific Time)
3. **No Secrets**: Never log raw provider secrets, webhook bodies, or API tokens
4. **Test First**: Always run `make test` before proposing changes
5. **Snapshot Always**: Run `bash scripts/make_snapshot.sh` before PRs
6. **Database**: Prefer PostgreSQL for production, SQLite only for unit tests
7. **Idempotency**: All provider operations must use idempotency keys

## Workflows

### Core Commands

#### `/snap`
Create review snapshot for code changes
```bash
bash scripts/make_snapshot.sh
```

#### `/ci`
Commit changes and optionally create PR
```bash
git add . && git commit -m "feat: description" && git push
# Optional: gh pr create --title "Title" --body "Description"
```

#### `/outbox:tick`
Process outbox queue manually
```bash
python outbox_worker.py --limit 10
```

#### `/plan:day`
Generate daily task plan
```bash
curl -s localhost:8000/planner/daily -d '{"hours":5}'
```

#### `/score:explain`
Explain scoring for a task (pipe JSON task)
```bash
echo '{"title":"Task","deadline":"2025-08-12T17:00:00Z","importance":4}' | python scripts/score_explain.py
```

## Always Run Checks

Before committing:
1. `make test` - Run test suite
2. `bash scripts/make_snapshot.sh` - Generate review bundle
3. Verify no secrets in code
4. Check for proper name usage (Amex, Charis, Chayah)

## Guardrails

- **No External Calls in Unit Tests**: Mock all provider APIs
- **No Hardcoded Secrets**: Use environment variables
- **Retry Policy**: Only retry 429, 500, 502, 503, 504
- **Don't Retry**: 400, 401, 403, 404, 409

## Decision Trace Format

When rebalancing tasks, always emit traces in this format:
```
* moved <taskA> above <taskB>:
  * urgency +0.062
  * SLA +0.045  
  * staleness -0.010
  = Δscore +0.097 → rank #5 → #3
```

## Mode Switching

### Normalizer Mode
When processing raw input tasks:
- Dedupe by title/client
- Rewrite to next physical action  
- Add effort estimate (1-8 hours)
- Add outcome verb (complete, review, implement, fix)
- Set deadline confidence (firm, soft, none)

### Balancer Mode
When redistributing workload:
- Apply fairness boost to underloaded providers
- Enforce WIP limits (default: 10 active)
- Apply staleness penalties (>72h = boost)
- Produce decision trace for moves

### Provider Ops Mode
When generating provider operations:
- Create outbox entries with idempotency keys
- Set proper headers for each provider
- Use webhook signatures where available
- Schedule retries with exponential backoff

## Scoring Algorithm

```python
score = (
    0.30 * urgency +      # deadline pressure
    0.25 * importance +   # client importance
    0.15 * effort_factor + # prefer small wins
    0.10 * freshness +    # newer tasks
    0.15 * sla_pressure + # SLA compliance  
    0.05 * recent_progress_inv  # stuck tasks
)
```

Urgency is continuous: `1.0 - (hours_to_deadline / 336h)`
Micro tie-breaker: `(-hours_to_deadline * 1e-9)`

## Logging Standards

- Use `[metrics]` prefix for counters
- Redact tokens as `***` in logs
- Hash delivery IDs for correlation
- Never log full request bodies with secrets

## Testing

```bash
# Local development
docker compose up -d  # Start PostgreSQL
make init            # Initialize schema
make test            # Run tests

# CI runs automatically on push
# Snapshot job creates PR artifacts
```

## Architecture Notes

- **Outbox Pattern**: Ensures exactly-once delivery
- **Idempotency Keys**: SHA256 of `provider|endpoint|payload`
- **Retry**: Exponential backoff with jitter, cap at 60s
- **Circuit Breaker**: After 5 failures, dead letter
- **FOR UPDATE SKIP LOCKED**: PostgreSQL row locking for workers

## Common Tasks

- Add provider: Extend `app/providers/`
- Modify scoring: Edit `app/scoring.py`
- Add API endpoint: Update `app/api.py`
- Change retry logic: Edit `app/utils/retry.py`
- Adjust outbox: Modify `app/utils/outbox.py`