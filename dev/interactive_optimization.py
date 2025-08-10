"""
Interactive Optimization Tools
For Claude Code sessions with Serena MCP integration
"""

import yaml
import json
from pathlib import Path

class InteractiveOptimizer:
    """
    Tools for Claude Code to optimize Project Archangel using Serena MCP
    """
    
    def __init__(self, project_root="/Users/jeremy/Projects/project-archangel"):
        self.project_root = Path(project_root)
        self.rules_path = self.project_root / "app/config/rules.yaml"
    
    def analyze_current_rules(self):
        """
        Load current rules for Serena MCP analysis
        Claude Code can ask Serena: "What improvements would you suggest for these rules?"
        """
        with open(self.rules_path) as f:
            rules = yaml.safe_load(f)
        
        return {
            "current_rules": rules,
            "serena_questions": [
                "Are the task type classifications comprehensive?",
                "Do the effort estimates align with reality?",
                "Are client SLA hours and caps optimally set?",
                "What patterns might we be missing?"
            ]
        }
    
    def generate_test_scenarios(self, focus_area="classification"):
        """
        Generate test scenarios for specific optimization areas
        Claude Code + Serena MCP could generate comprehensive test cases
        """
        scenarios = {
            "classification": [
                {"title": "Database timeout on user queries", "expected_type": "bugfix"},
                {"title": "Monthly revenue dashboard", "expected_type": "report"},
                {"title": "Setup new team member access", "expected_type": "onboarding"},
                {"title": "Review API documentation", "expected_type": "general"}
            ],
            "scoring": [
                {"title": "Critical prod outage", "client": "acme", "deadline": "2025-08-09T18:00:00Z", "expected_high_score": True},
                {"title": "Low priority cleanup", "client": "meridian", "expected_low_score": True}
            ],
            "decomposition": [
                {"title": "Implement user authentication", "expected_subtasks": ["Design", "Implement", "Test", "Deploy"]},
                {"title": "Fix login bug", "expected_checklist": ["Reproduce", "Debug", "Fix", "Test"]}
            ]
        }
        
        return {
            "scenarios": scenarios.get(focus_area, []),
            "serena_enhancement": f"Serena MCP could generate additional {focus_area} test cases based on patterns"
        }
    
    def suggest_rule_improvements(self, analysis_results):
        """
        Template for rule improvement suggestions from Serena MCP
        """
        return {
            "improvement_template": {
                "task_types": {
                    "suggested_additions": ["hotfix", "maintenance", "research"],
                    "effort_adjustments": "Serena could suggest based on historical data"
                },
                "scoring_weights": {
                    "current_issues": "May need rebalancing based on actual outcomes",
                    "serena_recommendation": "AI could optimize weights based on success patterns"
                },
                "client_tuning": {
                    "individual_optimization": "Each client may need custom parameters",
                    "serena_analysis": "AI could identify client-specific patterns"
                }
            }
        }

    def create_optimization_experiment(self, hypothesis):
        """
        Structure an A/B test for rule optimization
        """
        return {
            "experiment_design": {
                "hypothesis": hypothesis,
                "test_group": "New rule configuration",
                "control_group": "Current rules",
                "metrics": [
                    "Classification accuracy",
                    "User satisfaction with priority",
                    "Task completion time",
                    "SLA adherence"
                ],
                "serena_role": [
                    "Generate test scenarios",
                    "Analyze result patterns", 
                    "Suggest next iterations",
                    "Validate statistical significance"
                ]
            }
        }

# Integration examples for Claude Code sessions
class ClaudeCodeIntegration:
    
    @staticmethod
    def example_session_workflow():
        """
        Example of how Claude Code + Serena MCP could optimize Project Archangel
        """
        return """
        # Example Claude Code session with Serena MCP:
        
        1. "Load Project Archangel rules and analyze with Serena"
        2. Serena suggests: "Add 'hotfix' task type for urgent patches"
        3. "Generate test cases for hotfix classification"
        4. "Test the new rules against sample tasks"
        5. "Compare old vs new results and measure improvement"
        6. "Deploy optimized rules to Project Archangel"
        
        Benefits:
        - AI-guided optimization
        - Rapid prototyping of rule changes  
        - Comprehensive testing before deployment
        - Data-driven decision making
        """
    
    @staticmethod 
    def client_onboarding_example():
        return """
        # Onboarding new client with Serena MCP assistance:
        
        Claude Code: "Analyze this client profile and suggest optimal settings"
        Client: "TechCorp - B2B SaaS, 24/7 operations, regulatory compliance focus"
        
        Serena MCP suggests:
        - SLA: 4 hours (compliance-critical)
        - Daily cap: 6 hours (high complexity expected)
        - Importance bias: 1.8 (premium client)
        - Special task types: compliance, audit, security
        
        Claude Code: "Test these settings with sample TechCorp tasks"
        Result: Optimal configuration ready for deployment
        """

    @staticmethod
    def performance_analysis_example():
        return """
        # Performance analysis workflow:
        
        1. Export recent task data from Project Archangel
        2. Claude Code + Serena MCP analyze patterns:
           - Which tasks are frequently reclassified?
           - Are effort estimates accurate?
           - Do priorities align with actual urgency?
        3. Identify optimization opportunities
        4. Generate and test improved rules
        5. Measure performance gains
        """