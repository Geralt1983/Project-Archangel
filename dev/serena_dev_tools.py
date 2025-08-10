"""
Serena MCP Development Tools
Integration between Claude Code MCP and Project Archangel HTTP API
"""

import httpx
import json
from typing import Dict, List, Any

class SerenaDevTools:
    def __init__(self, archangel_base="http://localhost:8080"):
        self.archangel_base = archangel_base
        self.client = httpx.Client(base_url=archangel_base)
    
    def test_task_with_serena_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a task through Archangel and analyze results
        This would be enhanced by Claude Code using Serena MCP to provide insights
        """
        # Send to Project Archangel
        response = self.client.post("/tasks/intake", json=task_data)
        result = response.json()
        
        return {
            "archangel_result": result,
            "suggested_analysis": [
                "Claude Code + Serena MCP could analyze:",
                "- Classification accuracy",
                "- Subtask relevance", 
                "- Score reasonableness",
                "- Missing patterns"
            ]
        }
    
    def compare_triage_approaches(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare deterministic vs AI triage across multiple tasks
        """
        results = []
        
        for task in tasks:
            # Test with AI
            ai_result = self.client.post("/tasks/intake", json=task).json()
            
            # Test with deterministic (Serena disabled)
            # This would require a way to toggle Serena for single requests
            
            results.append({
                "task": task,
                "ai_enhanced": ai_result,
                "analysis_needed": "Serena MCP could provide deeper insights here"
            })
        
        return {"comparison_results": results}
    
    def validate_rules_with_ai(self, rules_path: str = "app/config/rules.yaml"):
        """
        Use Serena MCP (via Claude Code) to validate business rules
        """
        return {
            "suggestion": "Claude Code could read rules.yaml and ask Serena MCP:",
            "questions": [
                "Are these client SLA hours realistic?",
                "Do the scoring weights make sense?", 
                "What task types are we missing?",
                "Are the effort estimates accurate?"
            ]
        }

# Example usage patterns for Claude Code + Serena MCP integration
class SerenaIntegrationPatterns:
    
    @staticmethod
    def rule_optimization_workflow():
        """
        Workflow for optimizing rules using both Serena interfaces
        """
        return {
            "steps": [
                "1. Claude Code queries Serena MCP for rule suggestions",
                "2. Generate test tasks covering edge cases", 
                "3. Run tests through Project Archangel HTTP API",
                "4. Analyze results with Serena MCP insights",
                "5. Iterate on rules based on analysis",
                "6. Deploy optimized configuration"
            ],
            "benefits": [
                "AI-guided rule tuning",
                "Comprehensive test coverage",
                "Rapid iteration cycles",
                "Data-driven optimization"
            ]
        }
    
    @staticmethod
    def client_onboarding_analysis():
        """
        Use Serena to analyze optimal settings for new clients
        """
        return {
            "approach": [
                "1. Claude Code asks Serena MCP to analyze client characteristics",
                "2. Generate recommended SLA/capacity/bias settings",
                "3. Test recommendations via Archangel API",
                "4. Validate with historical data patterns",
                "5. Provide tuned client configuration"
            ]
        }
    
    @staticmethod
    def performance_monitoring():
        """
        Monitor and optimize system performance using dual Serena access
        """
        return {
            "monitoring_strategy": [
                "1. Export task data via /audit/export",
                "2. Claude Code + Serena MCP analyze patterns",
                "3. Identify classification/scoring issues", 
                "4. Generate improvement recommendations",
                "5. A/B test changes via HTTP API",
                "6. Measure performance improvements"
            ]
        }