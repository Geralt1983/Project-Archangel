# Dual Serena Integration Guide

This guide explains how to leverage both Serena integrations for maximum effectiveness:

1. **Serena HTTP API** - Production integration in Project Archangel
2. **Serena MCP Server** - Development and optimization tool via Claude Code

## 🎯 Integration Advantages

### **HTTP API (Production)**
- Real-time task enhancement in production
- Reliable, fast triage and rebalancing  
- Graceful fallback to deterministic logic
- Audit trail and performance monitoring

### **MCP Server (Development)**
- Interactive AI consultation during development
- Deep analysis of configuration and performance
- Advanced optimization suggestions
- Comprehensive test case generation

## 🚀 Powerful Workflow Examples

### 1. Rule Optimization Workflow

```python
# Step 1: Claude Code session with Serena MCP
from dev.config_optimizer import SmartConfigOptimizer

optimizer = SmartConfigOptimizer()

# Export current performance data
data = optimizer.export_performance_data()
print("Claude Code: Ask Serena MCP to analyze this performance data")
print(json.dumps(data["analysis_prompt"], indent=2))

# Step 2: Serena MCP provides insights (via Claude Code)
# "Based on the data, I suggest adding 'hotfix' task type and adjusting ACME's SLA"

# Step 3: Test proposed changes
test_results = optimizer.test_configuration_changes({
    "new_task_types": ["hotfix"],
    "client_adjustments": {"acme": {"sla_hours": 2}}
})

# Step 4: Validate with Serena MCP analysis
print("Serena MCP: Analyze these test results for accuracy and completeness")
```

### 2. Client Onboarding Analysis

```python
# Analyze new client patterns
client_analysis = optimizer.generate_client_profile_analysis("newcorp")

# Claude Code asks Serena MCP:
# "Based on this client profile, what are the optimal SLA, capacity, and bias settings?"

# Test recommended settings
settings = {
    "sla_hours": 6,  # Serena recommendation
    "daily_cap_hours": 4, 
    "importance_bias": 1.3
}

test_scenarios = [
    {"title": "NewCorp API integration issue", "client": "newcorp"},
    {"title": "NewCorp monthly report", "client": "newcorp"}
]

for scenario in test_scenarios:
    result = optimizer.client.post("/tasks/intake", json=scenario)
    print(f"Test result: {result.json()}")
```

### 3. Performance Monitoring Loop

```python
# Continuous optimization cycle
def optimization_cycle():
    """
    Automated optimization using both Serena integrations
    """
    # 1. Export recent performance data
    data = optimizer.export_performance_data(days_back=7)
    
    # 2. Claude Code + Serena MCP analyze trends
    # "Are classifications becoming less accurate?"
    # "Which clients need SLA adjustments?"
    # "What new patterns are emerging?"
    
    # 3. Generate improvement proposals
    proposals = optimizer.propose_rule_changes(data)
    
    # 4. Test proposals via HTTP API
    test_results = optimizer.test_configuration_changes(proposals)
    
    # 5. Serena MCP validates improvements
    # "These changes show 15% better priority accuracy"
    
    # 6. Deploy if validated
    return "Ready for deployment" if validated else "Needs more iteration"
```

## 🔧 Development Setup

### Prerequisites
```bash
# 1. Serena MCP Server (for Claude Code integration)
cd serena && uv run serena start-mcp-server

# 2. Project Archangel (HTTP API integration)  
cd project-archangel && docker compose up --build

# 3. Claude Code with Serena MCP configured
claude mcp add-json "serena" \
'{"command":"uvx","args":["--from","git+https://github.com/oraios/serena","serena-mcp-server"]}'
```

### Optimization Session Template

1. **Start Claude Code session**
2. **Load optimization tools:**
   ```python
   from dev.interactive_optimization import InteractiveOptimizer
   from dev.config_optimizer import SmartConfigOptimizer
   
   optimizer = InteractiveOptimizer()
   config_optimizer = SmartConfigOptimizer()
   ```

3. **Analyze current state with Serena MCP:**
   ```
   "Analyze Project Archangel's current rules and suggest improvements"
   ```

4. **Generate and test improvements:**
   ```python
   # Export data for analysis
   data = config_optimizer.export_performance_data()
   
   # Test proposed changes
   results = config_optimizer.test_configuration_changes(proposals)
   ```

5. **Deploy optimized configuration**

## 📊 Success Metrics

Track optimization effectiveness:

- **Classification Accuracy**: % of tasks correctly classified
- **Priority Alignment**: Correlation between assigned and actual priority  
- **SLA Performance**: % of tasks completed within SLA
- **User Satisfaction**: Feedback on task prioritization
- **System Efficiency**: Time saved through automation

## 🎯 Advanced Use Cases

### Dynamic Rule Adaptation
- Monitor task patterns in real-time
- Automatically suggest rule adjustments
- A/B test configuration changes
- Deploy improvements based on performance data

### Client-Specific Optimization  
- Analyze individual client work patterns
- Generate custom task templates
- Optimize SLA and capacity settings
- Provide tailored service levels

### Predictive Analytics
- Forecast workload distribution  
- Predict SLA risks before they occur
- Suggest proactive capacity adjustments
- Optimize team scheduling

## 🚀 Next Steps

1. **Start with rule analysis** - Use Serena MCP to analyze current configuration
2. **Generate test scenarios** - Create comprehensive test cases for validation
3. **Iterate rapidly** - Use both integrations for quick optimization cycles  
4. **Monitor continuously** - Track performance and adapt rules over time
5. **Scale intelligently** - Apply learnings to new clients and use cases

The dual Serena integration gives you both production reliability and development agility - the best of both worlds for intelligent task orchestration! 🧠✨