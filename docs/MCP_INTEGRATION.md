# ClickUp MCP Server Integration Guide

This document provides comprehensive guidance for integrating the ClickUp MCP (Model Context Protocol) server with Project Archangel to enable AI-enhanced task management capabilities.

## Overview

The ClickUp MCP server integration adds advanced AI-powered task management features to Project Archangel while maintaining full compatibility with existing workflows. This hybrid approach combines the reliability of our existing ClickUp adapter with the enhanced capabilities of the MCP server.

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Project         │    │ MCP Bridge       │    │ ClickUp MCP     │
│ Archangel       │←──→│ Integration      │←──→│ Server          │
│ Core System     │    │ Layer            │    │ (AI Interface)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Existing        │    │ Unified Task     │    │ ClickUp API     │
│ ClickUp Adapter │    │ Operations       │    │ (Enhanced)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

### Core Capabilities
- **Intelligent Fallback**: Automatic fallback to existing adapter when MCP server is unavailable
- **Enhanced Task Operations**: Advanced search, filtering, and task manipulation
- **AI-Powered Insights**: Task analytics, time tracking, and relationship analysis
- **Document Management**: Integration with ClickUp documents and workspaces
- **Member Resolution**: Advanced user lookup by email, username, or ID
- **Bulk Operations**: Efficient handling of multiple task operations

### Advanced Features
- **Semantic Search**: AI-powered task search beyond basic text matching
- **Task Insights**: Comprehensive task analytics and relationship mapping
- **Workspace Intelligence**: Cross-workspace task coordination and insights
- **Performance Optimization**: Intelligent caching and request batching
- **Health Monitoring**: Real-time server health and fallback detection

## Installation and Setup

### Prerequisites

1. **Node.js v18.0.0+** for MCP server
2. **ClickUp API Key** and **Team ID**
3. **Project Archangel** running with existing ClickUp integration

### Step 1: Install ClickUp MCP Server

```bash
# Using NPX (recommended for testing)
npx @taazkareem/clickup-mcp-server

# Or install globally
npm install -g @taazkareem/clickup-mcp-server
clickup-mcp-server
```

### Step 2: Configure Environment Variables

Add to your `.env` file:

```env
# MCP Server Configuration
MCP_SERVER_ENABLED=true
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=3231

# ClickUp MCP Authentication (reuse existing credentials)
CLICKUP_API_KEY=pk_your_api_key_here
CLICKUP_TEAM_ID=your_team_id_here
CLICKUP_WORKSPACE_ID=your_workspace_id  # Optional
CLICKUP_SPACE_ID=your_space_id          # Optional
CLICKUP_LIST_ID=your_list_id            # Optional
```

### Step 3: Update Requirements

Add MCP integration dependencies:

```bash
# Add to requirements.txt
pyyaml>=6.0  # For configuration management
```

### Step 4: Configure MCP Server

Edit `config/mcp_server.yml` to customize the integration:

```yaml
server:
  host: "127.0.0.1"
  port: 3231
  endpoint: "/mcp"
  
features:
  enabled_tools:
    - "create_task"
    - "get_task"
    - "update_task"
    - "search_tasks"
    - "get_task_insights"
    
integration:
  bridge_enabled: true
  fallback_to_adapter: true
  sync_with_outbox: true
```

## Usage

### Basic Integration

```python
from app.services.enhanced_tasks import EnhancedTaskService
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager

# Initialize components
adapter = ClickUpAdapter(token, team_id, list_id, webhook_secret)
outbox = OutboxManager()

# Create enhanced service
async with EnhancedTaskService(adapter, outbox) as task_service:
    # Will automatically initialize MCP if available
    
    # Create task (uses MCP if available, adapter as fallback)
    task = await task_service.create_task({
        "title": "AI-Enhanced Task",
        "description": "Created with MCP integration",
        "priority": 4,
        "deadline": "2025-08-25T17:00:00Z"
    })
    
    # Advanced search (MCP only feature)
    try:
        results = await task_service.search_tasks(
            "urgent tasks due this week",
            filters={"priority": [1, 2]}
        )
    except MCPBridgeError:
        # MCP not available, use basic listing
        results = await task_service.list_tasks({"status_filter": "open"})
```

### Task Insights and Analytics

```python
# Get comprehensive task insights (MCP feature)
async def analyze_task_performance(task_id: str):
    async with EnhancedTaskService(adapter, outbox) as service:
        try:
            insights = await service.get_task_insights(task_id)
            
            return {
                "task_info": insights["task"],
                "time_spent": insights["time_tracking"],
                "collaboration": len(insights["comments"]),
                "team_size": len(insights["members"])
            }
        except MCPBridgeError:
            # Fallback to basic task info
            task = await service.get_task(task_id)
            return {"task_info": task}
```

### Bulk Operations

```python
# Efficient bulk updates
async def rebalance_workload(updates: List[Dict]):
    async with EnhancedTaskService(adapter, outbox) as service:
        results = await service.bulk_update_tasks(updates)
        
        success_count = sum(1 for r in results if r["success"])
        error_count = len(results) - success_count
        
        return {
            "processed": len(results),
            "successful": success_count,
            "errors": error_count
        }
```

## API Reference

### MCPBridge Class

#### Methods

##### `async connect()`
Establish connection to MCP server with health checking.

##### `async create_task(task_data: Dict) -> Dict`
Create task using MCP server with automatic fallback.

**Parameters:**
- `task_data`: Task information in Project Archangel format

**Returns:** Created task data with external_id

##### `async search_tasks(query: str, filters: Dict = None) -> List[Dict]`
AI-powered semantic task search (MCP only feature).

**Parameters:**
- `query`: Natural language search query
- `filters`: Additional filters (priority, status, etc.)

**Returns:** List of matching tasks

##### `async get_server_status() -> Dict`
Get comprehensive MCP server status and capabilities.

### EnhancedTaskService Class

#### Methods

##### `async initialize_mcp(config_path: str = "config/mcp_server.yml")`
Initialize MCP bridge with specified configuration.

##### `async get_task_insights(task_id: str) -> Dict`
Get comprehensive task analytics and insights (MCP feature).

**Returns:**
```python
{
    "task": {...},          # Basic task info
    "time_tracking": {...}, # Time tracking data
    "comments": [...],      # Task comments
    "members": [...]        # Task team members
}
```

##### `async bulk_update_tasks(updates: List[Dict]) -> List[Dict]`
Perform bulk task updates with error handling.

**Parameters:**
```python
updates = [
    {"task_id": "123", "data": {"priority": 5}},
    {"task_id": "456", "data": {"status": "completed"}}
]
```

## Configuration Reference

### Server Configuration (`config/mcp_server.yml`)

```yaml
server:
  host: "127.0.0.1"               # MCP server host
  port: 3231                      # MCP server port
  endpoint: "/mcp"                # MCP endpoint path
  transport: "http"               # Transport type (http/sse)
  connection_timeout: 10          # Connection timeout (seconds)
  request_timeout: 30             # Request timeout (seconds)
  max_retries: 3                  # Maximum retry attempts

authentication:
  clickup_api_key: "${CLICKUP_API_KEY}"
  team_id: "${CLICKUP_TEAM_ID}"
  workspace_id: "${CLICKUP_WORKSPACE_ID:-}"
  space_id: "${CLICKUP_SPACE_ID:-}"
  list_id: "${CLICKUP_LIST_ID:-}"

features:
  enabled_tools:                  # List of enabled MCP tools
    - "create_task"
    - "get_task"
    - "update_task"
    - "search_tasks"
    # ... see full list in config file
  
  disabled_tools:                 # Disabled tools (security)
    - "delete_doc"
    - "create_webhook"

performance:
  max_concurrent_requests: 5      # Concurrent request limit
  request_batch_size: 10          # Batch size for bulk ops
  cache_ttl: 300                  # Cache TTL (seconds)
  
  tool_timeouts:                  # Tool-specific timeouts
    default: 30
    list_tasks: 60
    search_tasks: 60

integration:
  bridge_enabled: true            # Enable MCP bridge
  fallback_to_adapter: true       # Enable adapter fallback
  sync_with_outbox: true          # Outbox integration
  use_idempotency_keys: true      # Idempotency support
  
  priority_mapping:               # Priority mapping (Archangel -> ClickUp)
    1: 4  # Low -> Low
    2: 3  # Normal -> Normal
    3: 3  # Medium -> Normal
    4: 2  # High -> High
    5: 1  # Urgent -> Urgent
    
  status_mapping:                 # Status mapping (ClickUp -> Archangel)
    open: "pending"
    "in progress": "in_progress"
    done: "completed"

monitoring:
  metrics_enabled: true           # Enable metrics collection
  tracing_enabled: true           # Enable request tracing
  error_rate_threshold: 0.05      # 5% error rate threshold
  response_time_threshold: 5000   # 5s response time threshold
```

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MCP_SERVER_ENABLED` | Enable MCP integration | No | `false` |
| `MCP_SERVER_HOST` | MCP server host | No | `127.0.0.1` |
| `MCP_SERVER_PORT` | MCP server port | No | `3231` |
| `CLICKUP_API_KEY` | ClickUp API key | Yes | - |
| `CLICKUP_TEAM_ID` | ClickUp team ID | Yes | - |
| `CLICKUP_WORKSPACE_ID` | ClickUp workspace ID | No | - |
| `CLICKUP_SPACE_ID` | ClickUp space ID | No | - |
| `CLICKUP_LIST_ID` | ClickUp list ID | No | - |

## Data Mapping

### Task Format Mapping

**Project Archangel → MCP/ClickUp:**

| Archangel Field | MCP Field | ClickUp Field | Notes |
|----------------|-----------|---------------|-------|
| `title` | `name` | `name` | Direct mapping |
| `description` | `description` | `description` | Direct mapping |
| `deadline` | `due_date` | `due_date` | ISO 8601 → epoch ms |
| `priority` | `priority` | `priority` | 1-5 → 4-1 mapping |
| `labels` | `tags` | `tags` | Array of strings |
| `assignee` | `assignees[0]` | `assignees` | Single → array |

**MCP/ClickUp → Project Archangel:**

| MCP Field | Archangel Field | Transformation |
|-----------|----------------|----------------|
| `id` | `external_id` | Direct mapping |
| `name` | `title` | Direct mapping |
| `assignees` | `assignee` | Take first assignee |
| `priority` | `priority` | Reverse priority mapping |
| `status` | `status` | Status mapping via config |

### Priority Mapping

| Project Archangel | ClickUp | Description |
|------------------|---------|-------------|
| 1 | 4 | Low priority |
| 2 | 3 | Normal priority |
| 3 | 3 | Medium priority |
| 4 | 2 | High priority |
| 5 | 1 | Urgent priority |

## Error Handling

### Fallback Strategy

The integration implements a multi-level fallback strategy:

1. **MCP Server Available**: Use MCP for enhanced operations
2. **MCP Server Unavailable**: Automatic fallback to existing adapter
3. **Adapter Unavailable**: Return appropriate error messages
4. **Both Unavailable**: Graceful degradation with cached data

### Error Types

```python
from app.integrations.mcp_bridge import MCPBridgeError, MCPServerUnavailableError

try:
    result = await task_service.search_tasks("urgent tasks")
except MCPServerUnavailableError:
    # MCP server is down, use basic operations
    result = await task_service.list_tasks({"priority": 5})
except MCPBridgeError as e:
    # Configuration or integration error
    logger.error(f"MCP integration error: {e}")
```

### Health Monitoring

```python
# Check integration health
async def check_mcp_health():
    async with EnhancedTaskService(adapter, outbox) as service:
        status = await service.get_service_status()
        
        return {
            "mcp_available": status["mcp_available"],
            "adapter_available": status["adapter_available"],
            "server_health": status.get("mcp_status", {})
        }
```

## Testing

### Running Tests

```bash
# Run all MCP integration tests
python tests/test_mcp_runner.py

# Run specific test categories
pytest -m unit tests/test_mcp_bridge.py -v
pytest -m integration tests/test_mcp_integration.py -v
pytest -m performance tests/test_mcp_performance.py -v

# Run smoke test for quick validation
python tests/test_mcp_runner.py --smoke
```

### Test Configuration

Create `tests/.env.test` for test configuration:

```env
# Test MCP server (use different port)
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=3232
MCP_SERVER_ENABLED=true

# Test ClickUp credentials (use test workspace)
CLICKUP_API_KEY=test_api_key
CLICKUP_TEAM_ID=test_team_id
```

### Mock Testing

```python
# Use mock fixtures for unit tests
from tests.fixtures.mcp_responses import MockMCPResponses

@pytest.fixture
async def mock_mcp_service():
    mock_responses = MockMCPResponses()
    
    # Create service with mocked MCP bridge
    async with EnhancedTaskService(mock_adapter, mock_outbox) as service:
        service.mcp_bridge = mock_responses.create_mock_bridge()
        yield service
```

## Performance Considerations

### Optimization Settings

```yaml
# config/mcp_server.yml
performance:
  max_concurrent_requests: 5      # Tune based on ClickUp rate limits
  request_batch_size: 10          # Batch size for bulk operations
  cache_ttl: 300                  # 5-minute cache for frequent requests
  
  tool_timeouts:
    default: 30                   # Default timeout
    list_tasks: 60                # Longer timeout for listing
    search_tasks: 60              # Longer timeout for search
```

### Monitoring Metrics

The integration exposes Prometheus metrics:

- `mcp_requests_total{tool, status}` - Total requests by tool and status
- `mcp_request_duration_seconds{tool}` - Request duration histogram
- `mcp_server_available{endpoint}` - Server availability gauge

### Performance Benchmarks

Expected performance characteristics:

- **Single Task Operation**: <200ms (MCP) vs <100ms (adapter)
- **Bulk Operations**: ~50ms per task for updates
- **Search Operations**: <2s for typical queries
- **Memory Usage**: <50MB additional overhead
- **Concurrent Requests**: Up to 5 concurrent (configurable)

## Troubleshooting

### Common Issues

#### MCP Server Connection Failed

**Symptoms:** `MCPServerUnavailableError` or connection timeouts

**Solutions:**
1. Verify MCP server is running: `curl http://127.0.0.1:3231/health`
2. Check network connectivity and firewall settings
3. Verify configuration in `config/mcp_server.yml`
4. Check MCP server logs for errors

#### Authentication Errors

**Symptoms:** 401/403 errors from ClickUp API

**Solutions:**
1. Verify `CLICKUP_API_KEY` is valid and has required permissions
2. Check `CLICKUP_TEAM_ID` matches your ClickUp workspace
3. Ensure API key has access to specified workspace/space/list
4. Verify rate limiting isn't exceeded

#### Slow Performance

**Symptoms:** High response times, timeouts

**Solutions:**
1. Tune `max_concurrent_requests` in configuration
2. Increase `cache_ttl` for frequently accessed data
3. Use bulk operations instead of individual requests
4. Monitor ClickUp API rate limits

#### Data Mapping Issues

**Symptoms:** Incorrect priority/status values, missing fields

**Solutions:**
1. Review `priority_mapping` and `status_mapping` in config
2. Check field mapping in `_map_task_to_mcp()` and `_map_task_from_mcp()`
3. Verify ClickUp workspace configuration matches expectations

### Debug Mode

Enable debug logging:

```yaml
# config/mcp_server.yml
security:
  log_level: "DEBUG"

logging:
  enable_request_logging: true
  enable_response_logging: true  # Enable for debugging only
```

### Health Checks

```bash
# Check MCP server health
curl http://127.0.0.1:3231/health

# Check integration status via API
curl http://localhost:8000/api/tasks/mcp/status

# Run diagnostic tests
python tests/test_mcp_runner.py --smoke
```

## Migration Guide

### From Adapter-Only to MCP Integration

1. **Backup Current Configuration**
   ```bash
   cp .env .env.backup
   ```

2. **Install MCP Server**
   ```bash
   npm install -g @taazkareem/clickup-mcp-server
   ```

3. **Update Configuration**
   - Add MCP environment variables
   - Create `config/mcp_server.yml`
   - Test with existing adapter as fallback

4. **Gradual Migration**
   ```python
   # Start with fallback enabled
   config["integration"]["fallback_to_adapter"] = True
   
   # Test MCP operations
   await task_service.search_tasks("test query")
   
   # Monitor performance and stability
   status = await task_service.get_service_status()
   ```

5. **Full Migration**
   - Disable fallback after validation
   - Remove redundant adapter calls
   - Optimize MCP configuration

### Rollback Plan

If issues arise, rollback steps:

1. **Disable MCP Integration**
   ```env
   MCP_SERVER_ENABLED=false
   ```

2. **Restart Services**
   ```bash
   docker compose restart api worker
   ```

3. **Verify Adapter Functionality**
   ```bash
   curl http://localhost:8000/api/tasks
   ```

## Security Considerations

### API Key Management

- Store ClickUp API keys in environment variables only
- Use separate API keys for different environments
- Regularly rotate API keys
- Monitor API key usage and access logs

### Network Security

```yaml
# config/mcp_server.yml
security:
  validate_responses: true        # Validate all MCP responses
  sanitize_inputs: true          # Sanitize user inputs
  max_request_size: 1048576      # 1MB request limit
  max_response_size: 10485760    # 10MB response limit
```

### Logging Security

```yaml
logging:
  log_sensitive_data: false      # Never log sensitive data
  enable_request_logging: true   # Log requests (without bodies)
  enable_response_logging: false # Disable response logging in production
```

## Future Enhancements

### Planned Features

1. **Advanced AI Operations**
   - Task sentiment analysis
   - Workload prediction
   - Automated task categorization

2. **Enhanced Integrations**
   - Multi-provider MCP support
   - Real-time collaboration features
   - Advanced workflow automation

3. **Performance Improvements**
   - GraphQL-style query optimization
   - Enhanced caching strategies
   - Streaming data updates

### Contributing

To contribute to the MCP integration:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/mcp-enhancement`
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## Support

For issues and questions:

- **Project Issues**: [GitHub Issues](https://github.com/project-archangel/issues)
- **MCP Server Issues**: [ClickUp MCP Server Repository](https://github.com/taazkareem/clickup-mcp-server)
- **ClickUp API**: [ClickUp API Documentation](https://clickup.com/api)

## Changelog

### v1.0.0 (2025-08-22)
- Initial MCP integration implementation
- Hybrid adapter/MCP architecture
- Comprehensive test suite
- Performance monitoring and health checks
- Full documentation and examples