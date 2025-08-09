# Project Archangel - Intelligent Task Orchestrator

A smart task management system that automatically triages, prioritizes, and distributes work across different project management platforms (ClickUp, Trello, Todoist).

## Overview

Project Archangel intelligently processes incoming tasks from various sources (email, Slack, API), applies business rules for classification and prioritization, generates appropriate subtasks and checklists, and syncs everything to your preferred project management tool.

## Features

- **Multi-source intake**: Email aliases, forms, Slack commands, direct API
- **Intelligent triage**: Automatic task classification, effort estimation, and priority scoring
- **Template-driven subtasks**: Generate contextual subtasks and checklists based on task type
- **Provider adapters**: ClickUp (default), Trello, Todoist support
- **SLA monitoring**: Track client commitments and aging tasks
- **Load balancing**: Respect daily caps and ensure fair distribution
- **Webhook integration**: Bidirectional sync with PM tools
- **Audit logging**: Complete change history

## Quick Start

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Fill in your ClickUp credentials
   ```

2. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

3. **Create a task**
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

## Architecture

```
Email/Form/Slack → API → Triage Pipeline → Rules Engine → Provider Adapters → ClickUp/Trello/Todoist
                           ↓                     ↓
                    Priority Scorer      Subtask Generator
                           ↓                     ↓
                    Postgres Store ←→ Audit Logs
```

## Configuration

Task rules and client settings are managed via YAML files in `app/config/`:

- `rules.yaml` - Task types, checklists, subtasks, and scoring parameters
- Client-specific SLA and capacity settings
- Template-driven subtask generation

## API Endpoints

- `POST /tasks/intake` - Accept new tasks for triage
- `POST /webhooks/{provider}` - Receive provider webhooks
- `POST /triage/run` - Re-run triage for specific tasks
- `POST /rebalance/run` - Execute load balancing
- `GET /health` - Health check

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run locally
uvicorn app.api:app --reload
```

## Deployment

Supports one-click deployment to Railway, Fly.io, or any Docker-compatible platform.

Required environment variables:
- `CLICKUP_TOKEN`
- `CLICKUP_TEAM_ID` 
- `CLICKUP_LIST_ID`
- `CLICKUP_WEBHOOK_SECRET`
- `DATABASE_URL`

## License

MIT