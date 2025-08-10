# 🚀 Project Archangel - Deployment Guide

Complete guide to deploy and launch your intelligent task orchestrator with AI integration.

## 🎯 Deployment Options

### **Option 1: Local Development with AI** (Recommended)
Full-featured development setup with Serena MCP integration

### **Option 2: Local Development without AI**  
Basic setup using mock AI server

### **Option 3: Production Cloud Deployment**
Railway, Fly.io, or other cloud platforms

---

## 🏠 **Option 1: Local Development with AI**

### **Step 1: Prerequisites**
```bash
# Install uv package manager (for Serena)
brew install uv    # macOS
# OR: curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker (if not already installed)
# Download from: https://docker.com/get-started

# Verify installations
uv --version
docker --version
docker-compose --version
```

### **Step 2: Set Up Serena MCP Server**
```bash
# Clone and set up Serena
git clone https://github.com/oraios/serena
cd serena
cp .env.example .env
# Optional: Edit .env to add AI provider keys (OpenAI, Anthropic, etc.)

# Start Serena MCP server
uv run serena start-mcp-server
# ✅ Serena running at: http://localhost:24282
# ✅ Dashboard: http://localhost:24282/dashboard/index.html
```

### **Step 3: Configure Project Archangel**
```bash
# Navigate to Project Archangel
cd /Users/jeremy/Projects/project-archangel

# Copy and configure environment
cp .env.example .env
```

**Edit `.env` file:**
```env
# Core settings
PORT=8080
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasks
PUBLIC_BASE_URL=https://your-public-host  # or ngrok URL for webhooks

# Serena AI integration (✅ ENABLED)
SERENA_BASE_URL=http://localhost:24282
SERENA_API_KEY=your_serena_key
SERENA_TIMEOUT_SECONDS=20
SERENA_ENABLED=true

# Slack notifications (get webhook URL from Slack)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# ClickUp credentials (get from ClickUp API settings)
CLICKUP_TOKEN=pk_your_clickup_token
CLICKUP_TEAM_ID=your_team_id
CLICKUP_LIST_ID=your_list_id
CLICKUP_WEBHOOK_SECRET=your_webhook_secret

# Optional: Trello credentials
TRELLO_KEY=your_trello_key
TRELLO_TOKEN=your_trello_token
TRELLO_LIST_ID=your_trello_list_id
TRELLO_WEBHOOK_SECRET=your_trello_secret

# Optional: Todoist credentials  
TODOIST_TOKEN=your_todoist_token
TODOIST_PROJECT_ID=your_todoist_project_id
TODOIST_WEBHOOK_SECRET=your_todoist_secret
```

### **Step 4: Launch Project Archangel**
```bash
# Start all services
docker compose up --build

# ✅ Services starting:
# - PostgreSQL database (port 5432)
# - Project Archangel API (port 8080)
# - Hourly nudge worker
# - Database auto-migration
```

**Verify deployment:**
```bash
# Test health endpoint
curl http://localhost:8080/health
# Expected: {"ok": true}

# Test AI-enhanced task creation
curl -X POST http://localhost:8080/tasks/intake \
  -H "Content-Type: application/json" \
  -d '{
    "title": "ACME database error affecting users",
    "description": "Users getting 500 errors on login",
    "client": "acme",
    "deadline": "2025-08-12T17:00:00Z"
  }'

# Expected response with AI enhancement:
# {
#   "id": "tsk_xxxx",
#   "provider": "clickup", 
#   "external_id": "clickup_task_id",
#   "status": "triaged",
#   "score": 0.85,
#   "subtasks_created": 5,
#   "checklist_items": 5,
#   "serena_policy": {"hold_creation": false, "requires_review": false}
# }
```

---

## 🏗️ **Option 2: Local Development without AI**

If you want to start without Serena AI integration:

### **Step 1: Configure for Mock AI**
```bash
cd /Users/jeremy/Projects/project-archangel
cp .env.example .env
```

**Edit `.env` for mock mode:**
```env
# Disable Serena AI
SERENA_ENABLED=false
# OR point to mock server
SERENA_BASE_URL=http://localhost:9000

# Rest of configuration same as Option 1
```

### **Step 2: Start Mock Server (Optional)**
```bash
# Terminal 1: Start mock Serena
cd dev
uvicorn serena_mock:app --port 9000 --reload
# ✅ Mock AI at: http://localhost:9000
```

### **Step 3: Launch Project Archangel**
```bash
# Terminal 2: Start main system
docker compose up --build
# ✅ System running with deterministic triage
```

---

## ☁️ **Option 3: Production Cloud Deployment**

### **Railway Deployment**

**Step 1: Prepare for Railway**
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
```

**Step 2: Deploy PostgreSQL**
```bash
railway project new project-archangel-db
railway add postgresql
# Note the DATABASE_URL from Railway dashboard
```

**Step 3: Deploy Serena MCP**
```bash
railway project new serena-mcp
railway up serena/
# Set environment variables in Railway dashboard
```

**Step 4: Deploy Project Archangel**
```bash
railway project new project-archangel
railway up .
# Configure environment variables in Railway dashboard
```

### **Fly.io Deployment**

**Step 1: Install Fly CLI**
```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

**Step 2: Create fly.toml**
```toml
app = "project-archangel"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"
  SERENA_ENABLED = "true"

[[services]]
  http_checks = []
  internal_port = 8080
  protocol = "tcp"
  
  [services.concurrency]
    hard_limit = 25
    soft_limit = 20

  [[services.ports]]
    handlers = ["http"]
    port = 80
    force_https = true

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

[experimental]
  auto_rollback = true
```

**Step 3: Deploy**
```bash
# Create Fly app
fly apps create project-archangel

# Add PostgreSQL
fly postgres create --name project-archangel-db

# Deploy application
fly deploy

# Set environment variables
fly secrets set CLICKUP_TOKEN=pk_your_token
fly secrets set SERENA_BASE_URL=https://your-serena-instance
fly secrets set DATABASE_URL="your_postgres_url"
```

---

## 🔧 **Configuration Guide**

### **Required Environment Variables**

**Core System:**
```env
PORT=8080                                    # API port
DATABASE_URL=postgresql://user:pass@host/db # PostgreSQL connection
PUBLIC_BASE_URL=https://your-domain.com     # For webhook creation
```

**AI Integration:**
```env
SERENA_BASE_URL=http://localhost:24282      # Serena MCP endpoint
SERENA_ENABLED=true                         # Enable AI features
SERENA_TIMEOUT_SECONDS=20                   # AI timeout
```

**Notifications:**
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/... # Slack webhook for alerts
```

**Provider Credentials (at least one required):**

**ClickUp:**
```env
CLICKUP_TOKEN=pk_your_token                 # API token
CLICKUP_TEAM_ID=your_team_id               # Team ID
CLICKUP_LIST_ID=your_list_id               # Default list
CLICKUP_WEBHOOK_SECRET=your_secret         # Webhook verification
```

**Trello (optional):**
```env
TRELLO_KEY=your_app_key                    # App key
TRELLO_TOKEN=your_user_token               # User token  
TRELLO_LIST_ID=your_list_id                # Default list
TRELLO_WEBHOOK_SECRET=your_secret          # Webhook verification
```

**Todoist (optional):**
```env
TODOIST_TOKEN=your_api_token               # API token
TODOIST_PROJECT_ID=your_project_id         # Default project
TODOIST_WEBHOOK_SECRET=your_client_secret  # Webhook verification
```

### **Getting API Credentials**

**ClickUp:**
1. Go to ClickUp → Settings → Apps → Generate API Token
2. Get Team ID from URL: `https://app.clickup.com/{team_id}/`
3. Get List ID: Create list → Share → Copy list ID from URL

**Slack:**
1. Create Slack App → Incoming Webhooks → Add New Webhook
2. Copy webhook URL to `SLACK_WEBHOOK_URL`

**Trello:**
1. Get API Key: https://trello.com/app-key
2. Generate Token: Click "Token" link on API key page
3. Get List ID: Open list → Add `.json` to URL → Find ID

**Todoist:**
1. Go to Todoist → Settings → Integrations → API token
2. Get Project ID from project share URL

---

## 🧪 **Testing Your Deployment**

### **Step 1: Health Check**
```bash
curl http://localhost:8080/health
# Expected: {"ok": true}
```

### **Step 2: Test Task Creation**
```bash
# Test with ClickUp (AI-enhanced)
curl -X POST http://localhost:8080/tasks/intake \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fix user login timeout",
    "description": "Users experiencing 30-second delays", 
    "client": "acme",
    "deadline": "2025-08-12T17:00:00Z"
  }'

# Test with Trello
curl -X POST "http://localhost:8080/tasks/intake?provider=trello" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Weekly metrics report",
    "description": "Compile Q3 performance data",
    "client": "meridian"
  }'
```

### **Step 3: Test Automation Features**
```bash
# Test weekly summary
curl -X POST http://localhost:8080/checkins/weekly/run

# Test stale nudge
curl -X POST http://localhost:8080/nudges/stale/run

# Test rebalancing
curl -X POST http://localhost:8080/rebalance/run
```

### **Step 4: Create ClickUp Webhook**
```bash
# Auto-create webhook (requires PUBLIC_BASE_URL)
curl -X POST http://localhost:8080/providers/clickup/webhooks/create
# Expected: {"ok": true, "webhook": {...}, "callback": "..."}
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

**Database Connection Error:**
```bash
# Check PostgreSQL is running
docker compose ps
# Reset database
docker compose down -v && docker compose up --build
```

**Serena Connection Error:**
```bash
# Check Serena is running
curl http://localhost:24282/health
# Disable AI temporarily
export SERENA_ENABLED=false
```

**Webhook Creation Fails:**
- Set `PUBLIC_BASE_URL` in `.env`
- Use ngrok for local webhook testing: `ngrok http 8080`

**Tasks Not Creating:**
- Verify provider credentials in `.env`
- Check API token permissions
- Test provider connection manually

### **Logs and Debugging**
```bash
# View application logs
docker compose logs -f api

# View database logs  
docker compose logs -f db

# Check specific service
docker compose logs -f nudge_worker

# Debug mode
docker compose up --build -d && docker compose logs -f
```

---

## 🎯 **Production Checklist**

### **Security**
- [ ] Set strong `WEBHOOK_SECRET` values
- [ ] Use HTTPS for `PUBLIC_BASE_URL`
- [ ] Rotate API tokens regularly
- [ ] Enable database SSL/TLS
- [ ] Set up monitoring and alerting

### **Performance**  
- [ ] Configure database connection pooling
- [ ] Set appropriate `SERENA_TIMEOUT_SECONDS`
- [ ] Monitor API response times
- [ ] Scale horizontally if needed

### **Reliability**
- [ ] Set up database backups
- [ ] Configure health checks
- [ ] Set up log aggregation
- [ ] Test disaster recovery procedures

### **Monitoring**
- [ ] Set up uptime monitoring
- [ ] Monitor webhook delivery success
- [ ] Track AI enhancement usage
- [ ] Monitor task processing times

---

## 🎉 **You're Ready!**

Your intelligent task orchestrator is now deployed with:

✅ **AI-Powered Triage** - Smart task classification and scoring  
✅ **Multi-Provider Support** - ClickUp, Trello, Todoist integration  
✅ **Real-Time Tracking** - Webhook-based activity monitoring  
✅ **Automated Nudging** - Slack notifications for stale tasks  
✅ **Intelligent Rebalancing** - AI-driven workload optimization  
✅ **Production Ready** - Secure, scalable, and reliable  

**Access Points:**
- **API**: http://localhost:8080  
- **Health**: http://localhost:8080/health  
- **Serena Dashboard**: http://localhost:24282/dashboard/index.html  
- **API Docs**: http://localhost:8080/docs (FastAPI auto-docs)

Start orchestrating your tasks with AI! 🚀🧠