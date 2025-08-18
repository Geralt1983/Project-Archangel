# Project Archangel - System Design

## Overview
Project Archangel is an AI-powered task orchestration system that intelligently balances workload across multiple task management providers (ClickUp, Trello, Todoist, etc.) using sophisticated scoring algorithms, outbox patterns, and reliability mechanisms.

## System Architecture

### Core Components

#### 1. Provider Abstraction Layer
```
┌─────────────────────────────────────────────────────────────┐
│                    Provider Interface                       │
├─────────────────────────────────────────────────────────────┤
│  ClickUp Provider  │  Trello Provider  │  Todoist Provider  │
│   Provider         │    Provider       │    Provider        │
└─────────────────────────────────────────────────────────────┘
```

**Responsibilities:**
- Unified API for task operations (CRUD)
- Provider-specific authentication and rate limiting
- Error handling and retry logic
- Webhook integration for real-time updates

#### 2. Task Orchestration Engine
```
┌───────────────────────────────────────────────────────┐
│                 Task Orchestrator                     │
├───────────────────────────────────────────────────────┤
│  • Intelligent Routing                               │
│  • Load Balancing                                    │
│  • Scoring Algorithm                                 │
│  • Provider Health Monitoring                       │
└───────────────────────────────────────────────────────┘
```

**Scoring Algorithm:**
```python
score = (
    0.30 * urgency +          # deadline pressure
    0.25 * importance +       # client importance  
    0.15 * effort_factor +    # prefer small wins
    0.10 * freshness +        # newer tasks
    0.15 * sla_pressure +     # SLA compliance
    0.05 * recent_progress_inv # stuck tasks
)
```

#### 3. Outbox Pattern Implementation
```
┌─────────────────────────────────────────────────────────┐
│                    Outbox System                       │
├─────────────────────────────────────────────────────────┤
│  Task Queue  →  Outbox Worker  →  Provider APIs        │
│     ↓              ↓                  ↓                │
│  PostgreSQL    Retry Logic       Idempotency Keys      │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Exactly-once delivery guarantee
- Exponential backoff with jitter
- Dead letter queue for failed operations
- Transaction-safe operations

#### 4. Normalizer & Balancer
```
┌─────────────────────────────────────────────────────────┐
│                 Task Processing                         │
├─────────────────────────────────────────────────────────┤
│  Raw Input  →  Normalizer  →  Balancer  →  Provider    │
│      ↓           ↓            ↓            ↓           │
│   Deduplication  Format      Scoring     Delivery      │
│   Estimation     Validation   Routing     Tracking     │
└─────────────────────────────────────────────────────────┘
```

### Data Architecture

#### Database Schema
```sql
-- Core entities
CREATE TABLE providers (
    id UUID PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'clickup', 'trello', 'todoist'
    config JSONB NOT NULL,
    health_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    provider_id UUID REFERENCES providers(id),
    external_id VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    status task_status NOT NULL,
    priority INTEGER DEFAULT 1,
    effort_hours DECIMAL(4,2),
    deadline TIMESTAMP,
    assignee VARCHAR(100),
    score DECIMAL(5,3),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    provider_id UUID REFERENCES providers(id),
    operation_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    idempotency_key VARCHAR(255) UNIQUE,
    status outbox_status DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    error_message TEXT
);
```

#### Task Status Flow
```
pending → assigned → in_progress → completed
    ↓         ↓           ↓           ↓
  blocked   review    on_hold     archived
```

### API Design

#### REST Endpoints
```yaml
# Task Management
POST   /api/tasks                 # Create task
GET    /api/tasks                 # List tasks with filtering
GET    /api/tasks/{id}            # Get specific task
PUT    /api/tasks/{id}            # Update task
DELETE /api/tasks/{id}            # Archive task

# Provider Management  
GET    /api/providers             # List providers
POST   /api/providers             # Add provider
PUT    /api/providers/{id}        # Update provider config
GET    /api/providers/{id}/health # Provider health check

# Balancing & Analytics
POST   /api/planner/daily         # Generate daily plan
GET    /api/analytics/workload    # Workload distribution
GET    /api/analytics/performance # Performance metrics

# System Operations
GET    /api/health                # System health
GET    /api/usage/predictions     # Usage monitoring
POST   /api/outbox/process        # Manual outbox processing
```

#### Webhook Integration
```yaml
# Provider Webhooks
POST   /api/webhooks/clickup      # ClickUp task updates
POST   /api/webhooks/trello       # Trello card changes  
POST   /api/webhooks/todoist      # Todoist item modifications

# Internal Events
POST   /api/events/task-created   # Internal task creation
POST   /api/events/provider-down  # Provider failure notification
```

### Provider Integration Patterns

#### ClickUp Integration
```python
class ClickUpProvider:
    def __init__(self, api_token: str, team_id: str):
        self.client = ClickUpClient(api_token)
        self.team_id = team_id
    
    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        # Map internal task format to ClickUp format
        clickup_task = self._map_to_clickup(task_data)
        response = await self.client.create_task(clickup_task)
        return self._map_from_clickup(response)
    
    def _map_to_clickup(self, task: TaskCreate) -> dict:
        return {
            "name": task.title,
            "description": task.description,
            "priority": self._map_priority(task.priority),
            "due_date": task.deadline.timestamp() if task.deadline else None,
            "assignees": [self._get_user_id(task.assignee)] if task.assignee else []
        }
```

#### Trello Integration
```python
class TrelloProvider:
    def __init__(self, api_key: str, api_token: str, board_id: str):
        self.client = TrelloClient(api_key, api_token)
        self.board_id = board_id
    
    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        card_data = {
            "name": task_data.title,
            "desc": task_data.description,
            "idList": self._get_list_id(task_data.status),
            "due": task_data.deadline.isoformat() if task_data.deadline else None
        }
        response = await self.client.create_card(card_data)
        return self._map_from_trello(response)
```

#### Todoist Integration 
```python
class TodoistProvider:
    def __init__(self, api_token: str, project_id: str):
        self.client = TodoistClient(api_token)
        self.project_id = project_id
    
    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        todoist_task = {
            "content": task_data.title,
            "description": task_data.description,
            "project_id": self.project_id,
            "priority": self._map_priority(task_data.priority),
            "due_datetime": task_data.deadline.isoformat() if task_data.deadline else None
        }
        response = await self.client.create_task(todoist_task)
        return self._map_from_todoist(response)
```

### Reliability & Observability

#### Circuit Breaker Pattern
```python
class ProviderCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, provider_func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = await provider_func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()
            raise
```

#### Monitoring & Alerting
```python
# Metrics Collection
@metrics.timer("provider.operation.duration")
@metrics.counter("provider.operation.count")
async def execute_provider_operation(provider: str, operation: str, **kwargs):
    try:
        result = await provider_registry[provider].execute(operation, **kwargs)
        metrics.increment(f"provider.{provider}.success")
        return result
    except Exception as e:
        metrics.increment(f"provider.{provider}.error")
        logger.error(f"Provider {provider} operation {operation} failed: {e}")
        raise
```

### Security & Compliance

#### Authentication & Authorization
- **API Keys**: Per-provider authentication tokens stored encrypted
- **Webhook Signatures**: Verify webhook authenticity using provider signatures
- **Rate Limiting**: Per-provider rate limits to respect API quotas
- **Audit Logging**: All operations logged with user context and timestamps

#### Data Protection
- **Encryption at Rest**: Sensitive data encrypted in PostgreSQL
- **Encryption in Transit**: All API calls use TLS 1.3
- **PII Handling**: Task content and user data handled according to privacy policies
- **Backup & Recovery**: Automated backups with point-in-time recovery

### Performance Characteristics

#### Scalability Targets
- **Throughput**: 1,000 tasks/minute across all providers
- **Latency**: <200ms for task routing decisions
- **Availability**: 99.9% uptime (8.7 hours/year downtime)
- **Consistency**: Eventual consistency with conflict resolution

#### Optimization Strategies
- **Connection Pooling**: Persistent connections to provider APIs
- **Caching**: Redis caching for provider metadata and user preferences
- **Batch Operations**: Bulk operations where provider APIs support them
- **Background Processing**: Async task processing with worker queues

### Deployment Architecture

#### Container Strategy
```yaml
services:
  api:           # FastAPI application server
  worker:        # Outbox worker process  
  db:            # PostgreSQL database
  redis:         # Caching and session storage
  prometheus:    # Metrics collection
  grafana:       # Monitoring dashboards
  jaeger:        # Distributed tracing
```

#### Infrastructure Requirements
- **Compute**: 2 CPU cores, 4GB RAM minimum per service
- **Storage**: 100GB PostgreSQL, 10GB Redis
- **Network**: Load balancer with SSL termination
- **Monitoring**: Prometheus/Grafana stack with alerting

This design provides a robust, scalable foundation for intelligent task orchestration across multiple providers while maintaining reliability, observability, and security standards.