# Project Archangel - Render Cloud Deployment Guide

## 🚀 Quick Deploy to Render

Project Archangel is optimized for deployment on Render's cloud platform with automatic scaling, managed databases, and zero-downtime deployments.

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your Project Archangel code should be in a GitHub repo
3. **Provider API Keys**: Collect your ClickUp, Trello, and Todoist API credentials

## 🎯 Deployment Options

### Option 1: Blueprint Deployment (Recommended)

1. **Fork/Clone Repository**: Ensure your code is in a GitHub repository
2. **Connect to Render**: 
   - Go to [render.com/dashboard](https://render.com/dashboard)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
3. **Configure Services**: Render will automatically detect `render.yaml` and create:
   - Web Service (API)
   - Worker Service (Outbox Processing)
   - PostgreSQL Database
   - Redis Database

### Option 2: Manual Service Creation

If you prefer manual setup:

#### 1. Create PostgreSQL Database
```bash
# In Render Dashboard
New + → PostgreSQL
Name: project-archangel-db
Database: archangel
User: archangel
Plan: Starter (or higher for production)
```

#### 2. Create Redis Database
```bash
# In Render Dashboard  
New + → Redis
Name: project-archangel-redis
Plan: Starter (or higher for production)
```

#### 3. Create Web Service
```bash
# In Render Dashboard
New + → Web Service
Repository: your-github-repo
Name: project-archangel-api
Environment: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### 4. Create Worker Service
```bash
# In Render Dashboard
New + → Background Worker
Repository: your-github-repo
Name: project-archangel-worker
Environment: Python
Build Command: pip install -r requirements.txt
Start Command: python outbox_worker.py --daemon
```

## ⚙️ Environment Configuration

### Required Environment Variables

Set these in your Render service environment variables:

#### Database Configuration
```bash
DATABASE_URL=postgresql://archangel:password@host:port/archangel
REDIS_URL=redis://host:port
```

#### Application Settings
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8080
TRACING_ENABLED=false
SERENA_ENABLED=false  # Set to true if using Serena MCP
```

#### Provider Integration
```bash
# ClickUp
CLICKUP_TOKEN=your_clickup_token
CLICKUP_TEAM_ID=your_team_id
CLICKUP_LIST_ID=your_list_id
CLICKUP_WEBHOOK_SECRET=your_webhook_secret

# Trello
TRELLO_KEY=your_trello_api_key
TRELLO_TOKEN=your_trello_token
TRELLO_LIST_ID=your_list_id
TRELLO_WEBHOOK_SECRET=your_webhook_secret

# Todoist
TODOIST_TOKEN=your_todoist_token
TODOIST_PROJECT_ID=your_project_id
TODOIST_WEBHOOK_SECRET=your_webhook_secret
```

#### Security
```bash
JWT_SECRET_KEY=your-super-secret-jwt-key
ENCRYPTION_KEY=your-32-byte-encryption-key
```

### Environment Variable Setup in Render

1. **Go to your service** in Render Dashboard
2. **Click "Environment"** tab
3. **Add each variable** with the key-value pairs above
4. **Save changes** - service will automatically redeploy

## 🔧 Database Setup

### Automatic Setup (Blueprint)
If using blueprint deployment, databases are automatically created and configured.

### Manual Setup
If creating databases manually:

1. **PostgreSQL**: 
   - Render automatically creates the database
   - Tables will be created on first API call
   - No manual migration needed

2. **Redis**:
   - Automatically configured
   - Used for caching and session storage

## 🌐 Domain Configuration

### Custom Domain (Optional)
1. **In Render Dashboard**: Go to your web service
2. **Click "Settings"** → "Custom Domains"
3. **Add your domain**: e.g., `api.yourcompany.com`
4. **Configure DNS**: Point to Render's provided CNAME

### Default URL
Your service will be available at:
```
https://your-service-name.onrender.com
```

## 📊 Monitoring & Health Checks

### Health Check Endpoints
- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /health/detailed`
- **Metrics**: `GET /metrics`

### Render Monitoring
- **Logs**: Available in Render Dashboard
- **Metrics**: CPU, memory, and request metrics
- **Alerts**: Configure in service settings

## 🔄 Deployment Process

### Automatic Deployments
- **GitHub Integration**: Automatic deployment on push to main branch
- **Preview Deployments**: Available for pull requests
- **Rollback**: Easy rollback to previous versions

### Manual Deployment
```bash
# Trigger manual deployment
# In Render Dashboard → Your Service → Manual Deploy
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check build logs in Render Dashboard
# Common causes:
# - Missing dependencies in requirements.txt
# - Python version mismatch
# - Environment variable issues
```

#### 2. Database Connection Issues
```bash
# Verify DATABASE_URL format
# Check database service is running
# Ensure proper credentials
```

#### 3. Service Not Starting
```bash
# Check start command in render.yaml
# Verify PORT environment variable
# Check application logs
```

#### 4. Health Check Failures
```bash
# Verify /health endpoint returns 200
# Check database connectivity
# Ensure all required services are running
```

### Debug Commands
```bash
# View logs in Render Dashboard
# Check environment variables
# Verify service status
```

## 📈 Scaling Configuration

### Auto-Scaling
- **Web Service**: Configure auto-scaling based on CPU/memory
- **Worker Service**: Scale based on queue depth
- **Database**: Upgrade plan for higher performance

### Performance Optimization
```bash
# Environment variables for performance
WORKER_PROCESSES=4
MAX_CONNECTIONS=100
CACHE_TTL=3600
```

## 🔒 Security Considerations

### Production Security
1. **Environment Variables**: Never commit secrets to code
2. **HTTPS**: Automatically enabled by Render
3. **Database Security**: Managed by Render
4. **Access Control**: Configure IP restrictions if needed

### Security Headers
The application includes security headers:
- CORS configuration
- Rate limiting
- Input validation
- SQL injection protection

## 📞 Support

### Render Support
- **Documentation**: [render.com/docs](https://render.com/docs)
- **Community**: [render.com/community](https://render.com/community)
- **Status**: [status.render.com](https://status.render.com)

### Project Archangel Support
- **Issues**: GitHub repository issues
- **Documentation**: See README.md and other docs
- **Community**: Project discussions

## 🎉 Success Checklist

- [ ] Service deployed successfully
- [ ] Health checks passing
- [ ] Database connected
- [ ] Environment variables configured
- [ ] Provider integrations working
- [ ] Custom domain configured (optional)
- [ ] Monitoring set up
- [ ] Security measures in place

## 🚀 Next Steps

After successful deployment:

1. **Test API Endpoints**: Verify all endpoints work
2. **Configure Webhooks**: Set up provider webhooks
3. **Monitor Performance**: Watch metrics and logs
4. **Scale as Needed**: Adjust resources based on usage
5. **Set Up Alerts**: Configure monitoring alerts

---

**Your Project Archangel instance is now live on Render! 🎉**

For additional help, refer to the main [README.md](README.md) and [API_DOCUMENTATION.md](API_DOCUMENTATION.md).
