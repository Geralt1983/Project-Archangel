# MCP Integration Test Suite

Comprehensive test suite for the Model Context Protocol (MCP) integration in Project Archangel. This test suite ensures the reliability, performance, and correctness of the MCP bridge and enhanced task service components.

## Test Structure

### Core Test Files

- **`test_mcp_bridge.py`** - Unit tests for the MCPBridge class
- **`test_enhanced_tasks.py`** - Unit tests for the EnhancedTaskService class  
- **`test_mcp_integration.py`** - Integration tests for complete MCP workflow
- **`test_mcp_performance.py`** - Performance and reliability tests
- **`test_mcp_runner.py`** - Test runner and orchestration

### Fixtures and Test Data

- **`fixtures/mcp_responses.py`** - Mock MCP server responses and test data
- **`fixtures/test_configs.py`** - Test configuration scenarios
- **`fixtures/__init__.py`** - Fixtures package initialization

## Test Categories

### Unit Tests (`test_mcp_bridge.py`, `test_enhanced_tasks.py`)

Tests individual components in isolation with mocked dependencies.

**MCPBridge Tests:**
- Configuration loading and validation
- Connection management and health checks
- Task operations (create, read, update, list, search)
- Data mapping between Project Archangel and MCP formats
- Error handling and retry logic
- Status monitoring and reporting

**EnhancedTaskService Tests:**
- Service initialization with/without MCP
- Task operations with MCP integration
- Fallback to adapter when MCP unavailable  
- Bulk operations and error handling
- Advanced MCP-only features (search, insights)
- Service status reporting

### Integration Tests (`test_mcp_integration.py`)

Tests complete workflows with multiple components working together.

**Full Workflow Tests:**
- End-to-end task creation with database persistence
- Task updates with outbox processing
- MCP fallback to adapter scenarios
- Search and insights workflow
- Error recovery and partial service degradation
- Monitoring and health check integration

**Test Markers:**
- `@pytest.mark.integration` - Integration test marker
- Database setup with in-memory SQLite for fast testing
- Mock MCP server for consistent responses

### Performance Tests (`test_mcp_performance.py`)

Tests performance characteristics and reliability under load.

**Performance Tests:**
- Single request latency measurement
- Concurrent request throughput testing
- Memory usage monitoring under load
- Connection pool efficiency
- Bulk operation scaling
- Resource cleanup verification

**Reliability Tests:**
- Intermittent failure recovery
- Rate limiting handling
- Graceful degradation under load
- Sustained high throughput testing
- Memory stability over time

**Test Markers:**
- `@pytest.mark.performance` - Performance test marker
- Uses `psutil` for system resource monitoring
- Configurable load testing parameters

## Running Tests

### Quick Start

```bash
# Run all MCP tests
python tests/test_mcp_runner.py

# Run quick smoke test
python tests/test_mcp_runner.py --smoke

# Check test environment
python tests/test_mcp_runner.py --check-env
```

### Test Categories

```bash
# Unit tests only (fastest)
python tests/test_mcp_runner.py --unit-only

# Integration tests only
python tests/test_mcp_runner.py --integration-only

# Performance tests only (slowest)
python tests/test_mcp_runner.py --performance-only

# All tests except performance
python tests/test_mcp_runner.py --skip-performance
```

### Using pytest Directly

```bash
# Run specific test file
pytest tests/test_mcp_bridge.py -v

# Run tests with specific markers
pytest -m "not performance" -v

# Run integration tests
pytest -m integration tests/test_mcp_integration.py -v

# Run performance tests
pytest -m performance tests/test_mcp_performance.py -v
```

### Test Configuration

Tests use the project's `pytest.ini` configuration:

```ini
[pytest]
addopts = -q -m "not integration and not load and not performance"
markers =
    integration: marks tests as integration tests
    performance: marks tests as performance-heavy
```

## Test Environment Setup

### Requirements

- Python 3.8+
- pytest >= 7.0.0
- pytest-asyncio >= 0.21.0
- All Project Archangel dependencies

### Database Setup

Tests use SQLite in-memory database by default:

```python
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
```

For PostgreSQL testing, set:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/test_db"
```

### Environment Variables

```bash
# Optional: Test with real MCP server
export MCP_SERVER_HOST="localhost"
export MCP_SERVER_PORT="3231"

# Optional: ClickUp credentials for integration testing  
export CLICKUP_API_KEY="your_test_api_key"
export CLICKUP_TEAM_ID="your_test_team_id"
```

## Mock Data and Fixtures

### MCP Response Fixtures

The `MCPResponseFixtures` class provides realistic mock responses:

```python
from tests.fixtures.mcp_responses import MCPResponseFixtures

# Get sample task creation response
response = MCPResponseFixtures.successful_task_creation()

# Get custom task list
task_list = MCPResponseFixtures.task_list()

# Get search results
search_results = MCPResponseFixtures.search_results("urgent")
```

### Custom Test Data

Use `MCPTestDataBuilder` for custom test scenarios:

```python
from tests.fixtures.mcp_responses import MCPTestDataBuilder

# Build custom task
task = (MCPTestDataBuilder()
        .with_title("Custom Task")
        .with_priority(4)
        .with_assignees(["test@example.com"])
        .build_task())
```

### Configuration Fixtures

Use test configurations for different scenarios:

```python
from tests.fixtures.test_configs import get_test_config

# Get minimal test config
config_path = get_test_config("minimal")

# Get performance-optimized config
config_path = get_test_config("performance")

# Get security-focused config  
config_path = get_test_config("security")
```

## Test Patterns

### Async Test Structure

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async MCP operation"""
    # Setup
    bridge = MCPBridge(config_path="test_config.yml")
    
    # Mock dependencies
    with patch('httpx.AsyncClient') as mock_client:
        # Configure mocks
        mock_client.return_value.post.return_value = mock_response
        
        # Execute
        result = await bridge.create_task({"title": "Test"})
        
        # Assert
        assert result["external_id"] is not None
```

### Integration Test Pattern

```python
@pytest.mark.integration
class TestMCPIntegrationScenario:
    
    @pytest.fixture(scope="class")
    def db_setup(self):
        """Setup test database"""
        init()
        yield
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, db_setup):
        """Test complete workflow"""
        # Test implementation
        pass
```

### Performance Test Pattern

```python
@pytest.mark.performance
class TestMCPPerformance:
    
    @pytest.mark.asyncio
    async def test_throughput(self):
        """Test request throughput"""
        start_time = time.perf_counter()
        
        # Generate load
        tasks = [operation() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        throughput = len(results) / (end_time - start_time)
        
        assert throughput >= expected_throughput
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: MCP Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run MCP tests
      run: |
        python tests/test_mcp_runner.py --skip-performance
    
    - name: Run performance tests
      run: |
        python tests/test_mcp_runner.py --performance-only
      if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

### Test Results

Test results can be saved in JSON format:

```bash
python tests/test_mcp_runner.py --save-results mcp_results.json
```

Results include:
- Test execution summary
- Individual test timings
- Pass/fail status
- Error details
- Performance metrics

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure project root is in Python path
export PYTHONPATH="/path/to/project-archangel:$PYTHONPATH"
```

**Database Errors:**
```bash
# Initialize test database
python scripts/init_db.py
```

**Mock Server Issues:**
- Check that test fixtures are properly configured
- Verify mock responses match expected format
- Ensure async mocks are used for async operations

**Performance Test Failures:**
- Performance tests are sensitive to system load
- Run on dedicated test machines for consistent results
- Adjust thresholds based on hardware capabilities

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Coverage

Generate coverage reports:

```bash
pip install pytest-cov
pytest --cov=app.integrations --cov=app.services tests/test_mcp_*
```

## Contributing

### Adding New Tests

1. Follow existing test patterns and naming conventions
2. Use appropriate markers (`@pytest.mark.integration`, `@pytest.mark.performance`)
3. Mock external dependencies consistently
4. Include both happy path and error scenarios
5. Add performance tests for new features
6. Update fixtures for new test data needs

### Test Maintenance

- Keep mock data synchronized with actual MCP responses
- Update configuration fixtures when adding new settings
- Review and update performance thresholds periodically
- Maintain compatibility with pytest and dependency versions

### Code Quality

- Follow existing code style and structure
- Use type hints for better IDE support
- Include comprehensive docstrings
- Write clear, descriptive test names
- Group related tests in classes

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Plugin](https://pytest-asyncio.readthedocs.io/)
- [Project Archangel API Documentation](../API_DOCUMENTATION.md)
- [MCP Server Configuration](../config/mcp_server.yml)
- [ClickUp API Documentation](https://clickup.com/api)