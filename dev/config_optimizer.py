"""
Smart Configuration Optimizer
Leverages both Serena MCP (via Claude Code) and HTTP API for intelligent config management
"""

import yaml
import json
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class SmartConfigOptimizer:
    """
    Optimizes Project Archangel configuration using dual Serena integration
    """
    
    def __init__(self, archangel_url="http://localhost:8080"):
        self.archangel_url = archangel_url
        self.client = httpx.Client(base_url=archangel_url)
    
    def export_performance_data(self, days_back=30) -> Dict[str, Any]:
        """
        Export data for Serena MCP analysis
        """
        try:
            # Get recent task data
            response = self.client.get(f"/audit/export?limit=500")
            tasks = response.json()["tasks"]
            
            # Get weekly summaries
            weekly_response = self.client.get("/weekly")
            weekly_data = weekly_response.json()
            
            return {
                "tasks": tasks,
                "weekly_summary": weekly_data,
                "export_time": datetime.now().isoformat(),
                "analysis_prompt": {
                    "for_serena_mcp": [
                        "Analyze task classification accuracy",
                        "Identify scoring inconsistencies", 
                        "Suggest effort estimate improvements",
                        "Recommend new task types or client adjustments",
                        "Find patterns in client workload distribution"
                    ]
                }
            }
        except Exception as e:
            return {"error": f"Failed to export data: {e}"}
    
    def test_configuration_changes(self, config_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test configuration changes without deploying them
        Serena MCP could generate optimal test scenarios
        """
        test_scenarios = [
            {
                "title": "Critical database outage affecting all users",
                "description": "Primary DB cluster is down, users cannot access system",
                "client": "acme",
                "deadline": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
                "expected_classification": "bugfix",
                "expected_high_priority": True
            },
            {
                "title": "Quarterly business review preparation", 
                "description": "Compile Q3 metrics and create executive summary",
                "client": "meridian",
                "expected_classification": "report",
                "expected_medium_priority": True
            },
            {
                "title": "Setup development environment for new intern",
                "description": "Create accounts, install tools, provide documentation access",
                "client": "acme", 
                "expected_classification": "onboarding",
                "expected_low_priority": True
            }
        ]
        
        results = []
        for scenario in test_scenarios:
            try:
                response = self.client.post("/triage/run", json=scenario)
                result = response.json()
                results.append({
                    "scenario": scenario,
                    "result": result,
                    "analysis_needed": "Serena MCP could validate if results meet expectations"
                })
            except Exception as e:
                results.append({
                    "scenario": scenario,
                    "error": str(e)
                })
        
        return {
            "test_results": results,
            "serena_analysis_suggestions": [
                "Compare actual vs expected classifications",
                "Validate priority scoring accuracy",
                "Check subtask relevance and completeness", 
                "Assess effort estimate reasonableness",
                "Identify potential edge cases not covered"
            ]
        }
    
    def generate_client_profile_analysis(self, client_name: str) -> Dict[str, Any]:
        """
        Analyze client patterns for optimization
        Designed for Serena MCP enhancement via Claude Code
        """
        try:
            # Get client's task history
            export_data = self.export_performance_data()
            client_tasks = [
                task for task in export_data.get("tasks", [])
                if task.get("client") == client_name
            ]
            
            if not client_tasks:
                return {"error": f"No tasks found for client: {client_name}"}
            
            # Basic analysis
            total_tasks = len(client_tasks)
            avg_score = sum(task.get("score", 0) for task in client_tasks) / total_tasks
            task_types = {}
            for task in client_tasks:
                task_type = task.get("task_type", "unknown")
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            return {
                "client": client_name,
                "basic_stats": {
                    "total_tasks": total_tasks,
                    "average_score": round(avg_score, 3),
                    "task_type_distribution": task_types
                },
                "serena_enhancement_needed": {
                    "deep_analysis": [
                        "Pattern analysis: What types of work does this client typically need?",
                        "Timing patterns: When are their deadlines typically set?",
                        "Complexity assessment: Are effort estimates accurate for this client?",
                        "SLA analysis: Are current SLA settings appropriate?",
                        "Capacity planning: Is the daily cap optimally set?"
                    ],
                    "optimization_suggestions": [
                        "Custom task templates for common client work patterns",
                        "Adjusted scoring weights based on client-specific urgency patterns",
                        "Optimized SLA hours based on historical resolution times",
                        "Improved effort estimates based on client complexity patterns"
                    ]
                }
            }
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}

    def propose_rule_changes(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate rule change proposals based on analysis
        This would be enhanced by Serena MCP insights via Claude Code
        """
        return {
            "proposed_changes": {
                "new_task_types": {
                    "rationale": "Based on analysis, these task types appear frequently but lack specific classification",
                    "suggestions": [
                        {
                            "name": "hotfix",
                            "labels": ["urgent", "fix", "production"],
                            "default_effort_hours": 1,
                            "importance": 5,
                            "checklist": ["Identify root cause", "Apply minimal fix", "Test in staging", "Deploy with rollback plan", "Monitor metrics"]
                        },
                        {
                            "name": "maintenance", 
                            "labels": ["maintenance", "technical-debt"],
                            "default_effort_hours": 4,
                            "importance": 2,
                            "checklist": ["Document current state", "Plan improvements", "Implement changes", "Update documentation"]
                        }
                    ]
                },
                "scoring_adjustments": {
                    "rationale": "Current scoring may not reflect actual priority patterns",
                    "serena_needed": "AI analysis could identify optimal weight adjustments"
                },
                "client_optimizations": {
                    "approach": "Individual client tuning based on historical patterns",
                    "serena_role": "Analyze each client's work patterns and suggest custom parameters"
                }
            },
            "validation_plan": {
                "testing_approach": "A/B test proposed changes against current rules",
                "success_metrics": [
                    "Improved classification accuracy",
                    "Better priority alignment with actual urgency",
                    "Reduced task rework/reclassification",
                    "Higher user satisfaction with task prioritization"
                ]
            }
        }

# Example integration patterns
def example_claude_code_session():
    """
    Example of comprehensive optimization session using both Serena interfaces
    """
    return """
    # Complete optimization workflow with Claude Code + Serena MCP:
    
    ## Phase 1: Data Analysis
    Claude Code: "Export Project Archangel performance data"
    Serena MCP: "Analyze patterns and identify optimization opportunities"
    
    ## Phase 2: Configuration Design  
    Claude Code: "Based on Serena's analysis, generate new rule proposals"
    Serena MCP: "Validate proposed rules and suggest improvements"
    
    ## Phase 3: Testing
    Claude Code: "Generate comprehensive test scenarios"
    Project Archangel: "Execute tests via HTTP API"
    Serena MCP: "Analyze test results and validate improvements"
    
    ## Phase 4: Deployment
    Claude Code: "Deploy optimized configuration"
    Project Archangel: "Apply new rules in production"
    Monitoring: "Track performance improvements"
    
    ## Benefits:
    - AI-guided optimization decisions
    - Comprehensive testing before deployment  
    - Data-driven rule improvements
    - Continuous performance monitoring
    - Rapid iteration on configuration changes
    """