"""
Enhanced Scoring Algorithm Test Suite
Tests the advanced scoring features including fuzzy logic, ensemble methods, and adaptive learning.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from app.scoring_enhanced import (
    compute_enhanced_score,
    compute_score_with_details,
    EnhancedScoringEngine,
    FuzzyLogicEngine,
    TaskUrgencyLevel,
    TaskComplexityLevel
)


class TestFuzzyLogicEngine:
    """Test fuzzy logic engine functionality"""
    
    def test_triangular_membership(self):
        """Test triangular membership function"""
        # Test normal case
        assert FuzzyLogicEngine.triangular_membership(5, 0, 5, 10) == 1.0
        assert FuzzyLogicEngine.triangular_membership(2.5, 0, 5, 10) == 0.5
        assert FuzzyLogicEngine.triangular_membership(0, 0, 5, 10) == 0.0
        assert FuzzyLogicEngine.triangular_membership(10, 0, 5, 10) == 0.0
        
        # Test edge cases
        assert FuzzyLogicEngine.triangular_membership(15, 0, 5, 10) == 0.0
        assert FuzzyLogicEngine.triangular_membership(-5, 0, 5, 10) == 0.0
    
    def test_gaussian_membership(self):
        """Test gaussian membership function"""
        # Test center point
        assert abs(FuzzyLogicEngine.gaussian_membership(5, 5, 1) - 1.0) < 0.01
        
        # Test one standard deviation away
        assert abs(FuzzyLogicEngine.gaussian_membership(6, 5, 1) - 0.607) < 0.01
    
    def test_fuzzy_urgency(self):
        """Test fuzzy urgency classification"""
        # Critical urgency (< 4 hours)
        critical = FuzzyLogicEngine.fuzzy_urgency(2)
        assert critical['critical'] > 0.5
        
        # High urgency (4-24 hours)
        high = FuzzyLogicEngine.fuzzy_urgency(12)
        assert high['high'] > 0.5
        
        # Medium urgency (1-7 days)
        medium = FuzzyLogicEngine.fuzzy_urgency(72)
        assert medium['medium'] > 0.5
        
        # Low urgency (> 7 days)
        low = FuzzyLogicEngine.fuzzy_urgency(200)
        assert low['low'] > 0.5


class TestEnhancedScoring:
    """Test enhanced scoring algorithm"""
    
    def test_basic_enhanced_scoring(self):
        """Test basic enhanced scoring functionality"""
        task = {
            "client": "acme",
            "importance": 4.0,
            "effort_hours": 6.0,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_type": "bugfix",
            "assigned_provider": "clickup"
        }
        
        score = compute_enhanced_score(task, {})
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_detailed_scoring(self):
        """Test detailed scoring with confidence and metadata"""
        task = {
            "client": "beta_corp",
            "importance": 3.0,
            "effort_hours": 4.0,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_type": "report",
            "assigned_provider": "trello"
        }
        
        result = compute_score_with_details(task, {})
        
        # Check required fields
        assert 'score' in result
        assert 'confidence' in result
        assert 'uncertainty' in result
        assert 'metadata' in result
        assert 'method_scores' in result
        
        # Check value ranges
        assert 0.0 <= result['score'] <= 1.0
        assert 0.0 <= result['confidence'] <= 1.0
        assert 0.0 <= result['uncertainty'] <= 1.0
        
        # Check metadata
        assert 'urgency_level' in result['metadata']
        assert 'complexity_level' in result['metadata']
        assert result['metadata']['urgency_level'] in [level.value for level in TaskUrgencyLevel]
        assert result['metadata']['complexity_level'] in [level.value for level in TaskComplexityLevel]
    
    def test_adaptive_learning(self):
        """Test adaptive learning functionality"""
        engine = EnhancedScoringEngine()
        
        # Test performance feedback
        engine.update_performance_feedback('fuzzy_mcdm', was_accurate=True)
        engine.update_performance_feedback('traditional', was_accurate=False)
        
        # Verify weights adapt (this is a basic test - actual adaptation depends on implementation)
        assert hasattr(engine, 'weights')
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with missing data
        task_minimal = {"client": "test"}
        score = compute_enhanced_score(task_minimal, {})
        assert 0.0 <= score <= 1.0
        
        # Test with extreme values
        task_extreme = {
            "client": "test",
            "importance": 10.0,  # Beyond normal range
            "effort_hours": 1000.0,  # Very large
            "deadline": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        score = compute_enhanced_score(task_extreme, {})
        assert 0.0 <= score <= 1.0
        
        # Test with past deadline
        task_overdue = {
            "client": "test",
            "importance": 3.0,
            "effort_hours": 2.0,
            "deadline": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        score = compute_enhanced_score(task_overdue, {})
        assert 0.0 <= score <= 1.0


class TestScoringConsistency:
    """Test scoring consistency and reproducibility"""
    
    def test_score_reproducibility(self):
        """Test that same input produces same output"""
        task = {
            "client": "acme",
            "importance": 4.0,
            "effort_hours": 6.0,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_type": "bugfix"
        }
        
        score1 = compute_enhanced_score(task, {})
        score2 = compute_enhanced_score(task, {})
        
        assert abs(score1 - score2) < 0.001  # Should be identical
    
    def test_score_monotonicity(self):
        """Test that higher importance leads to higher scores"""
        base_task = {
            "client": "acme",
            "effort_hours": 6.0,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_type": "bugfix"
        }
        
        task_low = {**base_task, "importance": 1.0}
        task_high = {**base_task, "importance": 5.0}
        
        score_low = compute_enhanced_score(task_low, {})
        score_high = compute_enhanced_score(task_high, {})
        
        assert score_high >= score_low  # Higher importance should not decrease score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])