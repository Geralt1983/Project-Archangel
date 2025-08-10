# Project Archangel - Intelligent Task Orchestrator

A production-ready task orchestrator that automatically triages, prioritizes, and syncs tasks to ClickUp with intelligent classification and template-driven workflows. Now enhanced with **Serena MCP** for AI-powered decision making.

## Quick Start

### 1. Setup Serena MCP Server (Optional but Recommended)

```bash
# Install uv package manager
brew install uv    # or: curl -LsSf https://astral.sh/uv/install.sh | sh

# Get Serena MCP server
git clone https://github.com/oraios/serena
cd serena
cp .env.example .env   # edit if you want provider keys later

# Start the MCP server with dashboard
uv run serena start-mcp-server
# Dashboard: http://localhost:24282/dashboard/index.html
```

### 2. Setup Project Archangel

```bash
cp .env.example .env
# Add your ClickUp credentials and Serena URL to .env
docker compose up --build
```

## Demo

Test with different providers and AI enhancement:

**ClickUp with Serena AI (default):**
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

**Trello:**
```bash
curl -X POST "http://localhost:8080/tasks/intake?provider=trello" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Meridian weekly report",
    "description": "Need metrics pull",
    "client": "meridian"
  }'
```

**Todoist:**
```bash
curl -X POST "http://localhost:8080/tasks/intake?provider=todoist" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "ACME onboarding access", 
    "description": "Provision SSO",
    "client": "acme"
  }'
```

Expected response with Serena enhancement:
```json
{
  "id": "tsk_xxxx",
  "provider": "clickup|trello|todoist",
  "external_id": "provider_task_id",
  "status": "triaged", 
  "score": 0.83,
  "subtasks_created": 5,
  "checklist_items": 5,
  "serena_policy": {
    "hold_creation": false,
    "requires_review": false
  }
}
```

## API Endpoints

### Core Operations
- `POST /tasks/intake?provider=clickup|trello|todoist` - Process and create tasks (AI-enhanced)
- `POST /triage/run` - Re-run triage with Serena AI
- `POST /rebalance/run` - AI-powered workload rebalancing

### Webhooks
- `POST /webhooks/clickup` - Receive ClickUp webhooks (HMAC SHA256 verified)
- `POST /webhooks/trello` - Receive Trello webhooks (HMAC SHA1 verified) 
- `POST /webhooks/todoist` - Receive Todoist webhooks (HMAC SHA256 verified)

### Automation
- `POST /nudges/stale/run` - Manual stale task nudges
- `POST /checkins/weekly/run` - Trigger weekly Slack summary
- `GET /weekly` - Weekly summary by client

### Management
- `POST /providers/clickup/webhooks/create` - Auto-create ClickUp webhooks
- `GET /tasks/map/{provider}/{external_id}` - Inspect task mapping
- `GET /audit/export` - Export task data for AI training
- `POST /audit/outcomes` - Record task outcomes for feedback
- `GET /health` - Health check

## Key Features

✅ **AI-Powered Triage**: Serena MCP analyzes and classifies tasks intelligently  
✅ **Smart Decomposition**: Context-aware subtasks and checklists generation  
✅ **Advanced Scoring**: Multi-factor priority with AI overrides and client bias  
✅ **Intelligent Rebalancing**: AI-driven workload distribution across clients  
✅ **Multi-Provider Support**: ClickUp, Trello, Todoist with native features  
✅ **Real-Time Activity Tracking**: Precise staleness detection via webhooks  
✅ **PostgreSQL Backend**: Scalable JSONB storage with task mapping  
✅ **Automated Nudging**: Hourly stale task notifications to Slack  
✅ **Webhook Security**: HMAC signature verification prevents unauthorized access  
✅ **Rate Limiting**: Exponential backoff with jitter for API calls  
✅ **Graceful Degradation**: Falls back to deterministic logic when AI unavailable  

## Configuration

### Environment Variables

```env
# Core settings
PORT=8080
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasks
PUBLIC_BASE_URL=https://your-public-host
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

# Serena AI integration
SERENA_BASE_URL=http://localhost:24282
SERENA_API_KEY=your_serena_key
SERENA_TIMEOUT_SECONDS=20
SERENA_ENABLED=true

# Provider credentials
CLICKUP_TOKEN=your_clickup_token
CLICKUP_TEAM_ID=your_clickup_team
CLICKUP_LIST_ID=your_clickup_list
CLICKUP_WEBHOOK_SECRET=your_clickup_webhook_secret
```

### Business Rules

Edit `app/config/rules.yaml` to customize:

- **Task Types**: AI classification rules, effort estimates, importance levels
- **Client Settings**: SLA hours, daily capacity, importance bias  
- **Scoring Weights**: Priority calculation factors and aging boosts
- **Stale Detection**: Nudge timing and Slack notification thresholds

## AI Enhancement Details

### Serena MCP Integration

**Intelligent Classification:**
- Analyzes task titles/descriptions for semantic meaning
- Identifies task types: bugfix, report, onboarding, general
- Generates appropriate labels and effort estimates

**Smart Decomposition:**
- Creates context-aware subtasks based on task type and client
- Generates relevant checklists for quality assurance
- Adapts templates based on historical patterns

**Advanced Scoring:**
- Multi-factor priority calculation with AI insights
- Client-specific importance biasing
- Deadline pressure and SLA risk assessment
- Score overrides with explanatory reasoning

**Workload Rebalancing:**
- Optimizes task distribution across team capacity
- Respects client daily caps and urgent overrides
- Provides rationale for planning decisions

### Fallback Strategy

The system gracefully handles AI unavailability:
- **Timeouts**: Falls back to deterministic triage within 20 seconds
- **Service Down**: Uses local classification rules and scoring
- **Toggle Control**: `SERENA_ENABLED=false` for pure deterministic mode
- **Conservative Application**: AI suggestions enhance rather than replace baseline logic

## Architecture

```
Intake → Serena AI Analysis → Enhanced Triage → Classification → Scoring → 
Subtask Generation → Provider API → Real-time Activity Tracking → 
Automated Nudging → Slack Notifications
```

### AI-Enhanced Flow

1. **Task Intake**: Normalize and create deterministic baseline
2. **AI Analysis**: Send to Serena MCP for intelligent enhancement  
3. **Smart Application**: Conservatively apply AI suggestions
4. **Provider Creation**: Generate tasks with AI-optimized structure
5. **Activity Tracking**: Monitor real-time updates via webhooks
6. **Intelligent Nudging**: AI-informed stale task identification
7. **Learning Loop**: Export outcomes for continuous AI improvement

## Testing

### Acceptance Tests

- ✅ Serena AI enhances task classification and decomposition
- ✅ Graceful fallback when AI service unavailable
- ✅ Intake creates provider tasks + subtasks + checklist from single payload
- ✅ Webhook with wrong signature rejected with 401  
- ✅ Duplicate webhook delivery IDs are deduped
- ✅ Score increases as deadline approaches with AI insights
- ✅ Easy provider swap by injecting different adapter
- ✅ Rebalance uses AI optimization with local fallback

### Development Testing

```bash
# Test AI integration
SERENA_ENABLED=true python -m pytest tests/test_serena_toggle.py

# Test fallback mode  
SERENA_ENABLED=false python -m pytest tests/test_serena_toggle.py

# Test task mapping
python -m pytest tests/test_webhook_idempotent.py
```

## Production Deployment

### Railway/Fly.io with Serena

1. **Deploy Serena MCP**: Host Serena server on cloud platform
2. **Update Environment**: Point `SERENA_BASE_URL` to hosted Serena
3. **Configure Scaling**: Set appropriate timeouts and capacity limits
4. **Monitor Performance**: Use audit export for AI model feedback

### High Availability Setup

- **Multiple Serena Instances**: Load balance AI requests
- **Circuit Breaker**: Automatic fallback on consecutive failures  
- **Caching Layer**: Cache frequent AI responses for performance
- **Monitoring**: Track AI response times and accuracy metrics

## Next Steps

1. **Add Your Credentials**: Update `.env` with ClickUp API tokens and Serena URL
2. **Customize AI Rules**: Configure business logic in `rules.yaml`
3. **Deploy with AI**: Use Docker Compose locally, cloud platforms for production
4. **Monitor Performance**: Use Serena dashboard and audit endpoints
5. **Extend Intelligence**: Add more AI providers or custom ML models

Built for reliability, intelligence, and easy extension. 🚀🧠

## Development

### With Real Serena MCP Server

```bash
# Terminal 1: Start Serena
cd serena
uv run serena start-mcp-server

# Terminal 2: Start Project Archangel  
cd project-archangel
docker compose up --build
```

### With Mock Server (No AI)

```bash
# Terminal 1: Start mock
cd dev && uvicorn serena_mock:app --port 9000 --reload

# Terminal 2: Start with mock
export SERENA_BASE_URL=http://localhost:9000
docker compose up --build
```

The system seamlessly switches between real AI and deterministic fallback based on configuration.