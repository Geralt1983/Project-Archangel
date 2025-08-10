# Manual Setup Guide - Docker Installation Issue

## 🐳 Fix Docker Installation

The sudo privileges issue can be resolved by:

### **Option 1: Manual Docker Desktop Installation (Recommended)**
1. Go to https://docker.com/get-started
2. Download Docker Desktop for Mac (Apple Silicon)
3. Open the `.dmg` file and drag Docker to Applications
4. Launch Docker Desktop from Applications
5. Follow the setup wizard and grant permissions when prompted

### **Option 2: Alternative - Run Without Docker**
We can run Project Archangel directly with Python while Serena is already running.

## 🐍 Run Project Archangel with Python (Alternative)

### Step 1: Set up Python environment
```bash
cd /Users/jeremy/Projects/project-archangel
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx pyyaml psycopg2-binary
```

### Step 2: Set up PostgreSQL (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Create database
createdb tasks

# Update .env DATABASE_URL
# Change from: postgresql://postgres:postgres@db:5432/tasks  
# To: postgresql://postgres@localhost:5432/tasks
```

### Step 3: Run Project Archangel API
```bash
# Make sure you're in the venv and project directory
cd /Users/jeremy/Projects/project-archangel
source venv/bin/activate

# Run the API server
uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload
```

## 🎯 Current Status

✅ **Serena MCP Server**: Running at http://127.0.0.1:24282  
✅ **ClickUp Integration**: Configured with your credentials  
✅ **Environment**: Ready with all variables set  

**Next Steps:**
1. Either install Docker Desktop manually OR use Python setup above
2. Test the integration with live task creation

## 🧪 Test Commands (Once Running)

```bash
# Test health
curl http://localhost:8080/health

# Test AI-enhanced task creation  
curl -X POST http://localhost:8080/tasks/intake \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Project Archangel Integration", 
    "description": "Testing AI-powered task orchestrator with Serena",
    "client": "internal",
    "deadline": "2025-08-12T17:00:00Z"
  }'
```

**Expected Result:**
- Task created in your ClickUp "Project 2" list
- AI enhancement from Serena (classification, subtasks, scoring)
- Response with task details and Serena policy

## 🚨 Troubleshooting Docker

If Docker installation continues to fail:

1. **Check for existing Docker**: `docker --version`
2. **Manual cleanup**: Remove any Docker remnants from Applications
3. **Permission reset**: `sudo chown -R $(whoami) /usr/local/cli-plugins/`
4. **Retry installation**: `brew install --cask docker`

## 💡 Why This Happened

The sudo privileges issue occurs because:
- Homebrew needs to create directories in system locations
- Terminal doesn't have the required permissions
- Docker Desktop installation requires admin access

**Solution**: Manual installation bypasses the Homebrew sudo requirements.