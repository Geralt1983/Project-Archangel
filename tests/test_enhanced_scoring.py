"""
Test suite for the enhanced scoring algorithm
Demonstrates improvements over the traditional scoring approach
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.scoring import compute_score as traditional_score
from app.scoring_enhanced import (
    compute_enhanced_score,
    compute_score_with_details,
    EnhancedScoringEngine,
    FuzzyLogicEngine,
    TaskUrgencyLevel,
    TaskComplexityLevel
)


class TestEnhancedScoringAlgorithm:
    """Test suite for enhanced scoring algorithm"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = EnhancedScoringEngine()
        self.fuzzy = FuzzyLogicEngine()
        
        # Standard rules configuration
        self.rules = {
            "clients": {
                "acme": {
                    "importance_bias": 1.2,
                    "sla_hours": 48,
                    "priority_multiplier": 1.5,
                    "urgency_threshold": 0.8,
                    "complexity_preference": 0.3
                },
                "beta_corp": {
                    "importance_bias": 0.8,
                    "sla_hours": 72,
                    "priority_multiplier": 1.0,
                    "urgency_threshold": 0.6,
                    "complexity_preference": 0.7
                }
            }
        }
        
        self.now = datetime.now(timezone.utc)
    
    def test_fuzzy_logic_urgency_classification(self):
        """Test fuzzy logic urgency classification"""
        # Critical urgency (< 4 hours)
        urgency_2h = self.fuzzy.fuzzy_urgency(2.0)
        assert urgency_2h["critical"] > 0.5
        assert urgency_2h["high"] < 0.5
        
        # High urgency (4-24 hours)
        urgency_12h = self.fuzzy.fuzzy_urgency(12.0)
        assert urgency_12h["high"] > 0.5
        assert urgency_12h["critical"] < 0.5
        assert urgency_12h["medium"] < 0.5
        
        # Medium urgency (1-7 days)
        urgency_3d = self.fuzzy.fuzzy_urgency(72.0)
        assert urgency_3d["medium"] > 0.5
        
        # Low urgency (> 7 days)
        urgency_10d = self.fuzzy.fuzzy_urgency(240.0)
        assert urgency_10d["low"] > 0.5
    
    def test_fuzzy_logic_complexity_classification(self):
        """Test fuzzy logic complexity classification"""
        # Simple task
        complexity_1h = self.fuzzy.fuzzy_complexity(1.0)
        assert complexity_1h["simple"] > 0.5
        
        # Moderate task
        complexity_4h = self.fuzzy.fuzzy_complexity(4.0)
        assert complexity_4h["moderate"] > 0.5
        
        # Complex task
        complexity_12h = self.fuzzy.fuzzy_complexity(12.0)
        assert complexity_12h["complex"] > 0.5
        
        # Epic task
        complexity_30h = self.fuzzy.fuzzy_complexity(30.0)
        assert complexity_30h["epic"] > 0.5
    
    def test_enhanced_vs_traditional_scoring(self):
        """Compare enhanced scoring with traditional scoring"""
        # High-priority urgent task
        urgent_task = {
            "client": "acme",
            "importance": 5.0,
            "effort_hours": 2.0,
            "deadline": (self.now + timedelta(hours=4)).isoformat(),
            "created_at": (self.now - timedelta(hours=1)).isoformat(),
            "recent_progress": 0.0,
            "task_type": "bugfix",
            "assigned_provider": "clickup",
            "historical_similar_tasks": 5
        }
        
        # Traditional score
        trad_score = traditional_score(urgent_task, self.rules)
        
        # Enhanced score
        enhanced_result = compute_score_with_details(urgent_task, self.rules)
        enhanced_score = enhanced_result['score']
        
        # Enhanced should provide better discrimination for urgent tasks
        assert enhanced_score >= trad_score
        assert enhanced_result['confidence'] > 0.5
        assert enhanced_result['metadata']['urgency_level'] == TaskUrgencyLevel.HIGH.value
        
        print(f"Traditional score: {trad_score:.3f}")
        print(f"Enhanced score: {enhanced_score:.3f}")
        print(f"Confidence: {enhanced_result['confidence']:.3f}")
        print(f"Method scores: {enhanced_result['method_scores']}")
    
    def test_adaptive_ensemble_weighting(self):
        """Test adaptive ensemble method weighting"""
        task = {
            "client": "beta_corp",
            "importance": 3.0,
            "effort_hours": 6.0,
            "deadline": (self.now + timedelta(days=2)).isoformat(),
            "created_at": (self.now - timedelta(hours=6)).isoformat(),
            "recent_progress": 0.2
        }
        
        # Get initial weights
        initial_weights = self.engine.method_weights.copy()
        
        # Simulate performance feedback
        self.engine.update_performance_feedback('fuzzy_mcdm', True)
        self.engine.update_performance_feedback('fuzzy_mcdm', True)
        self.engine.update_performance_feedback('traditional', False)
        
        # Weights should adapt
        new_weights = self.engine.method_weights
        assert new_weights['fuzzy_mcdm'] > initial_weights['fuzzy_mcdm']
        assert new_weights['traditional'] < initial_weights['traditional']
        
        print(f"Initial weights: {initial_weights}")
        print(f"Adapted weights: {new_weights}")
    
    def test_confidence_and_uncertainty_quantification(self):
        """Test confidence and uncertainty quantification"""
        # Task with clear priority signals
        clear_task = {
            "client": "acme",
            "importance": 5.0,
            "effort_hours": 1.0,
            "deadline": (self.now + timedelta(hours=2)).isoformat(),
            "created_at": (self.now - timedelta(hours=1)).isoformat(),
            "recent_progress": 0.0
        }
        
        # Task with ambiguous priority signals
        ambiguous_task = {
            "client": "beta_corp",
            "importance": 2.5,
            "effort_hours": 8.0,
            "deadline": (self.now + timedelta(days=5)).isoformat(),
            "created_at": (self.now - timedelta(days=2)).isoformat(),
            "recent_progress": 0.5
        }
        
        clear_result = compute_score_with_details(clear_task, self.rules)
        ambiguous_result = compute_score_with_details(ambiguous_task, self.rules)
        
        # Clear task should have higher confidence, lower uncertainty
        assert clear_result['confidence'] > ambiguous_result['confidence']
        assert clear_result['uncertainty'] < ambiguous_result['uncertainty']
        
        print(f"Clear task - Confidence: {clear_result['confidence']:.3f}, Uncertainty: {clear_result['uncertainty']:.3f}")
        print(f"Ambiguous task - Confidence: {ambiguous_result['confidence']:.3f}, Uncertainty: {ambiguous_result['uncertainty']:.3f}")
    
    def test_context_aware_scoring(self):
        """Test context-aware scoring based on task type and history"""
        # Bugfix task (should get priority boost)
        bugfix_task = {
            "client": "acme",
            "importance": 3.0,
            "effort_hours": 4.0,
            "deadline": (self.now + timedelta(days=1)).isoformat(),
            "created_at": self.now.isoformat(),
            "task_type": "bugfix",
            "historical_similar_tasks": 10
        }
        
        # Feature task (normal priority)
        feature_task = {
            "client": "acme",
            "importance": 3.0,
            "effort_hours": 4.0,
            "deadline": (self.now + timedelta(days=1)).isoformat(),
            "created_at": self.now.isoformat(),
            "task_type": "feature",
            "historical_similar_tasks": 3
        }
        
        bugfix_result = compute_score_with_details(bugfix_task, self.rules)
        feature_result = compute_score_with_details(feature_task, self.rules)
        
        # Bugfix should score higher due to context awareness
        assert bugfix_result['score'] > feature_result['score']
        
        # Check ML adaptive scores
        bugfix_ml = bugfix_result['method_scores']['ml_adaptive']
        feature_ml = feature_result['method_scores']['ml_adaptive']
        assert bugfix_ml > feature_ml
        
        print(f"Bugfix ML score: {bugfix_ml:.3f}")
        print(f"Feature ML score: {feature_ml:.3f}")
    
    def test_client_specific_preferences(self):
        """Test client-specific complexity preferences"""
        complex_task = {
            "client": "beta_corp",  # High complexity preference (0.7)
            "importance": 4.0,
            "effort_hours": 16.0,  # Complex task
            "deadline": (self.now + timedelta(days=3)).isoformat(),
            "created_at": self.now.isoformat()
        }
        
        simple_task = {
            "client": "acme",  # Low complexity preference (0.3)
            "importance": 4.0,
            "effort_hours": 1.0,  # Simple task
            "deadline": (self.now + timedelta(days=3)).isoformat(),
            "created_at": self.now.isoformat()
        }
        
        complex_result = compute_score_with_details(complex_task, self.rules)
        simple_result = compute_score_with_details(simple_task, self.rules)
        
        # Check fuzzy MCDM scores respect client preferences
        complex_fuzzy = complex_result['method_scores']['fuzzy_mcdm']
        simple_fuzzy = simple_result['method_scores']['fuzzy_mcdm']
        
        print(f"Complex task (beta_corp): {complex_fuzzy:.3f}")
        print(f"Simple task (acme): {simple_fuzzy:.3f}")
        print(f"Complex task metadata: {complex_result['metadata']}")
        print(f"Simple task metadata: {simple_result['metadata']}")
    
    def test_performance_degradation_handling(self):
        """Test handling of tasks with poor progress"""
        stuck_task = {
            "client": "acme",
            "importance": 4.0,
            "effort_hours": 8.0,
            "deadline": (self.now + timedelta(days=2)).isoformat(),
            "created_at": (self.now - timedelta(days=3)).isoformat(),
            "recent_progress": 0.1,  # Stuck task
            "dependencies": ["task-1", "task-2", "task-3"]  # Many dependencies
        }
        
        normal_task = {
            "client": "acme",
            "importance": 4.0,
            "effort_hours": 8.0,
            "deadline": (self.now + timedelta(days=2)).isoformat(),
            "created_at": (self.now - timedelta(days=1)).isoformat(),
            "recent_progress": 0.0,  # Fresh task
            "dependencies": []
        }
        
        stuck_result = compute_score_with_details(stuck_task, self.rules)
        normal_result = compute_score_with_details(normal_task, self.rules)
        
        # Traditional scoring should penalize stuck task
        assert stuck_result['method_scores']['traditional'] < normal_result['method_scores']['traditional']
        
        # ML adaptive should consider dependency complexity
        stuck_ml = stuck_result['score_details']['ml_adaptive']['dependency_factor']
        normal_ml = normal_result['score_details']['ml_adaptive']['dependency_factor']
        assert stuck_ml < normal_ml
        
        print(f"Stuck task score: {stuck_result['score']:.3f}")
        print(f"Normal task score: {normal_result['score']:.3f}")
    
    def test_ensemble_method_comparison(self):
        """Compare all three scoring methods on various task types"""
        test_cases = [
            {
                "name": "Critical Bugfix",
                "task": {
                    "client": "acme",
                    "importance": 5.0,
                    "effort_hours": 2.0,
                    "deadline": (self.now + timedelta(hours=2)).isoformat(),
                    "created_at": self.now.isoformat(),
                    "task_type": "bugfix"
                }
            },
            {
                "name": "Complex Feature",
                "task": {
                    "client": "beta_corp",
                    "importance": 3.0,
                    "effort_hours": 20.0,
                    "deadline": (self.now + timedelta(weeks=2)).isoformat(),
                    "created_at": self.now.isoformat(),
                    "task_type": "feature"
                }
            },
            {
                "name": "SLA Pressure",
                "task": {
                    "client": "acme",
                    "importance": 3.5,
                    "effort_hours": 4.0,
                    "deadline": (self.now + timedelta(days=3)).isoformat(),
                    "created_at": (self.now - timedelta(hours=40)).isoformat(),  # Near SLA limit
                    "task_type": "enhancement"
                }
            }
        ]
        
        print("\n=== Ensemble Method Comparison ===")
        for case in test_cases:
            result = compute_score_with_details(case["task"], self.rules)
            print(f"\n{case['name']}:")
            print(f"  Traditional: {result['method_scores']['traditional']:.3f}")
            print(f"  Fuzzy MCDM:  {result['method_scores']['fuzzy_mcdm']:.3f}")
            print(f"  ML Adaptive: {result['method_scores']['ml_adaptive']:.3f}")
            print(f"  Ensemble:    {result['score']:.3f}")
            print(f"  Confidence:  {result['confidence']:.3f}")
            print(f"  Urgency:     {result['metadata']['urgency_level']}")
            print(f"  Complexity:  {result['metadata']['complexity_level']}")


if __name__ == "__main__":
    # Run basic demonstration
    test_suite = TestEnhancedScoringAlgorithm()
    test_suite.setup_method()
    
    print("=== Enhanced Scoring Algorithm Demonstration ===")
    test_suite.test_enhanced_vs_traditional_scoring()
    print()
    test_suite.test_confidence_and_uncertainty_quantification()
    print()
    test_suite.test_ensemble_method_comparison()