# Getting Started with Project Archangel

## Quick Demo

To see Project Archangel in action without any setup:

```bash
cd /Users/jeremy/Projects/project-archangel
python3 -m venv venv
source venv/bin/activate
pip install pyyaml pydantic
python simple_demo.py
```

This will show you how the intelligent triage system:
- Classifies tasks by type (bugfix, report, onboarding, general)
- Extracts client names from task titles
- Applies business rules and SLA requirements
- Generates contextual checklists and subtasks
- Calculates priority scores with multiple factors
- Ranks tasks for optimal execution order

## Full Setup for Production

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your ClickUp credentials
```

### 2. Database Setup

```bash
# The app will automatically create SQLite tables
# For production, set DATABASE_URL to PostgreSQL
export DATABASE_URL="postgresql://user:pass@localhost:5432/archangel"
```

### 3. ClickUp Configuration

1. Get your ClickUp API token from https://app.clickup.com/settings/apps
2. Find your Team ID and List ID from ClickUp URLs
3. Create a webhook in ClickUp pointing to your server
4. Set the webhook secret in your .env file

### 4. Start the API Server

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8080
```

### 5. Start the Scheduler (Optional)

```bash
python -m app.scheduler
```

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
```

## API Usage Examples

### Create a task:

```bash
curl -X POST http://localhost:8080/tasks/intake \
  -H "Content-Type: application/json" \
  -d '{
    "title": "ACME payment gateway returning errors",
    "description": "Users getting 500 errors during checkout",
    "client": "acme",
    "deadline": "2025-08-15T17:00:00Z",
    "importance": 5
  }'
```

### Set up ClickUp webhook:

```bash
curl -X POST http://localhost:8080/webhooks/clickup \
  -H "X-Signature: your-hmac-signature" \
  -H "Content-Type: application/json" \
  -d '{"event": "taskCreated", "task": {"id": "123", "name": "Test"}}'
```

### Rebalance workload:

```bash
curl -X POST http://localhost:8080/rebalance/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "client_filter": "acme"}'
```

## Configuration

### Task Rules (`app/config/rules.yaml`)

- **Task types**: Define classification rules, default effort, importance, labels
- **Client settings**: SLA hours, daily capacity, importance bias
- **Scoring weights**: Adjust priority calculation factors

### Environment Variables

- `CLICKUP_TOKEN`: Your ClickUp API token
- `CLICKUP_TEAM_ID`: ClickUp team identifier  
- `CLICKUP_LIST_ID`: Default list for new tasks
- `CLICKUP_WEBHOOK_SECRET`: Webhook signing secret
- `DATABASE_URL`: Database connection string
- `PROVIDER_PRIORITY`: Order of provider preference (default: "openai,voyage")

## Key Features Demonstrated

✅ **Intelligent Classification**: Automatically categorizes tasks by content analysis  
✅ **Multi-factor Scoring**: Priority calculation using urgency, importance, SLA, aging  
✅ **Template-driven Workflows**: Generate subtasks and checklists based on task type  
✅ **Client Management**: Different SLA and capacity rules per client  
✅ **Provider Abstraction**: Easy to swap between ClickUp, Trello, Todoist  
✅ **Webhook Integration**: Bidirectional sync with project management tools  
✅ **Load Balancing**: Respect daily caps while prioritizing urgent work  
✅ **Audit Logging**: Complete change history for compliance  

## Architecture Overview

```
Intake → Triage → Classification → Scoring → Subtask Generation → Provider Sync → Audit
```

The demo shows this complete pipeline working end-to-end, processing different task types with appropriate business rules and generating the output you'd see in your project management tool.

## Next Steps

1. **Customize Rules**: Edit `app/config/rules.yaml` for your task types and clients
2. **Add Providers**: Implement Trello/Todoist adapters following the base class pattern
3. **Enhance Classification**: Train an ML model on your historical task data
4. **Add Integrations**: Connect Slack notifications, email alerts, calendar blocking
5. **Scale Up**: Deploy to Railway/Fly.io with PostgreSQL for production use

The foundation is solid and ready for your specific workflow requirements!