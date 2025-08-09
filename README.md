# Project Archangel - Intelligent Task Orchestrator

A production-ready task orchestrator that automatically triages, prioritizes, and syncs tasks to ClickUp with intelligent classification and template-driven workflows.

## Quick Start

```bash
cp .env.example .env
# Add your ClickUp credentials to .env
docker compose up --build
```

## Demo

Test the system with a sample task:

```bash
curl -X POST http://localhost:8080/tasks/intake \
  -H "Content-Type: application/json" \
  -d '{
    "title": "ACME error on order import",
    "description": "500 on POST /orders",
    "client": "acme",
    "deadline": "2025-08-12T17:00:00Z"
  }'
```

Expected response:
```json
{
  "id": "tsk_xxxx",
  "provider": "clickup",
  "external_id": "cu_task_id",
  "status": "triaged",
  "score": 0.83,
  "subtasks_created": 5,
  "checklist_items": 5
}
```

## API Endpoints

- `POST /tasks/intake` - Process and create tasks
- `POST /webhooks/clickup` - Receive ClickUp webhooks (HMAC verified)
- `POST /triage/run` - Re-run triage on existing tasks
- `POST /rebalance/run` - Recompute all task scores
- `GET /health` - Health check

## Key Features

✅ **Intelligent Classification**: Auto-detects bugfix/report/onboarding/general task types  
✅ **Multi-factor Scoring**: Urgency, importance, SLA pressure, aging, client bias  
✅ **Template Workflows**: Generates contextual checklists and subtasks  
✅ **ClickUp Integration**: Native subtasks, checklists, webhooks with HMAC verification  
✅ **Provider Abstraction**: Easy to swap ClickUp for Trello/Todoist  
✅ **Webhook Security**: Signature verification prevents unauthorized access  
✅ **Rate Limiting**: Exponential backoff with jitter for API calls  
✅ **Idempotent Operations**: Duplicate webhook delivery protection  

## Configuration

Edit `app/config/rules.yaml` to customize:

- **Task Types**: Classification rules, default effort, importance, labels
- **Client Settings**: SLA hours, daily capacity, importance bias  
- **Scoring Weights**: Adjust priority calculation factors

## Acceptance Tests

- ✅ Intake creates ClickUp task + subtasks + checklist from single JSON payload
- ✅ Webhook with wrong signature rejected with 401
- ✅ Duplicate webhook delivery IDs are deduped  
- ✅ Score increases as deadline approaches
- ✅ Easy provider swap by injecting different adapter
- ✅ Rebalance recomputes scores without duplicates

## Architecture

```
Intake → Triage → Classification → Scoring → Subtask Generation → ClickUp API
```

Simple, focused, production-ready.

## Next Steps

1. **Add Your Credentials**: Update `.env` with ClickUp API token, team ID, list ID
2. **Customize Rules**: Edit task types and client configs in `rules.yaml`
3. **Deploy**: Use Docker Compose for local, Railway/Fly.io for production
4. **Extend Providers**: Implement Trello/Todoist adapters using the base interface

Built for reliability and easy extension. 🚀