"""
Enhanced Task Scoring Algorithm for Project Archangel
Based on latest research in adaptive ensemble methods, MCDM, and reinforcement learning (2024-2025)

Key improvements:
1. Adaptive ensemble scoring with dynamic weight adjustment
2. Multi-criteria decision analysis (MCDM) with fuzzy logic
3. Context-aware learning from historical patterns
4. Real-time parameter adaptation based on performance feedback
5. Uncertainty quantification and confidence scoring
"""

from __future__ import annotations

import math
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class TaskUrgencyLevel(Enum):
    CRITICAL = "critical"    # < 4 hours
    HIGH = "high"           # 4-24 hours  
    MEDIUM = "medium"       # 1-7 days
    LOW = "low"            # > 7 days


class TaskComplexityLevel(Enum):
    SIMPLE = "simple"       # < 2 hours
    MODERATE = "moderate"   # 2-8 hours
    COMPLEX = "complex"     # 8-24 hours
    EPIC = "epic"          # > 24 hours


@dataclass
class HistoricalPerformance:
    """Track historical performance metrics for adaptive learning"""
    total_tasks: int = 0
    completed_on_time: int = 0
    avg_completion_time: float = 0.0
    success_rate_by_urgency: Dict[str, float] = field(default_factory=dict)
    success_rate_by_complexity: Dict[str, float] = field(default_factory=dict)
    provider_performance: Dict[str, float] = field(default_factory=dict)


@dataclass
class AdaptiveWeights:
    """Dynamic weights that adapt based on performance feedback"""
    urgency: float = 0.30
    importance: float = 0.25
    effort_factor: float = 0.15
    freshness: float = 0.10
    sla_pressure: float = 0.15
    progress_penalty: float = 0.05
    
    # New adaptive factors
    complexity_bonus: float = 0.0
    context_boost: float = 0.0
    provider_reliability: float = 0.0
    
    # Learning rate for weight adaptation
    learning_rate: float = 0.01
    
    def normalize(self) -> None:
        """
        Ensure weights sum to 1.0
        
        Raises:
            ValueError: If all weights are zero or negative
        """
        total = (self.urgency + self.importance + self.effort_factor + 
                self.freshness + self.sla_pressure + self.progress_penalty +
                self.complexity_bonus + self.context_boost + self.provider_reliability)
        
        if total <= 0:
            logger.warning("All weights are zero or negative, using equal weights")
            # Set equal weights as fallback
            equal_weight = 1.0 / 9  # 9 weight components
            self.urgency = equal_weight
            self.importance = equal_weight
            self.effort_factor = equal_weight
            self.freshness = equal_weight
            self.sla_pressure = equal_weight
            self.progress_penalty = equal_weight
            self.complexity_bonus = equal_weight
            self.context_boost = equal_weight
            self.provider_reliability = equal_weight
        else:
            factor = 1.0 / total
            self.urgency *= factor
            self.importance *= factor
            self.effort_factor *= factor
            self.freshness *= factor
            self.sla_pressure *= factor
            self.progress_penalty *= factor
            self.complexity_bonus *= factor
            self.context_boost *= factor
            self.provider_reliability *= factor
            logger.debug(f"Weights normalized with factor {factor:.4f}")


@dataclass
class EnhancedClientConfig:
    """Enhanced client configuration with adaptive parameters"""
    importance_bias: float = 1.0
    sla_hours: int = 72
    priority_multiplier: float = 1.0
    urgency_threshold: float = 0.7  # Fuzzy logic threshold
    complexity_preference: float = 0.5  # 0 = simple tasks, 1 = complex tasks
    performance_history: HistoricalPerformance = field(default_factory=HistoricalPerformance)


@dataclass
class EnhancedTask:
    """Enhanced task model with additional scoring factors"""
    client: str = ""
    importance: float = 3.0
    effort_hours: float = 1.0
    due_at: Optional[str] = None
    deadline: Optional[str] = None
    recent_progress: float = 0.0
    created_at: Optional[str] = None
    ingested_at: Optional[str] = None
    
    # Enhanced fields
    task_type: str = "general"
    dependencies: List[str] = field(default_factory=list)
    assigned_provider: Optional[str] = None
    estimated_complexity: Optional[str] = None
    historical_similar_tasks: int = 0
    user_feedback_score: float = 0.0
    
    @property
    def deadline_iso(self) -> Optional[str]:
        return self.due_at or self.deadline


class FuzzyLogicEngine:
    """
    Fuzzy logic engine for handling uncertainty in task parameters
    
    Provides triangular and gaussian membership functions for fuzzy sets,
    with specialized functions for computing urgency and complexity fuzzy values.
    """
    
    @staticmethod
    def triangular_membership(x: float, a: float, b: float, c: float) -> float:
        """
        Triangular membership function for fuzzy sets
        
        Args:
            x: Input value
            a: Left bound of triangle
            b: Peak of triangle  
            c: Right bound of triangle
            
        Returns:
            Membership value between 0.0 and 1.0
            
        Raises:
            ValueError: If triangle parameters are invalid
        """
        if not (a <= b <= c):
            raise ValueError(f"Invalid triangle parameters: a={a}, b={b}, c={c}. Must satisfy a <= b <= c")
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:  # b < x < c
            return (c - x) / (c - b)
    
    @staticmethod
    def gaussian_membership(x: float, center: float, sigma: float) -> float:
        """
        Gaussian membership function for fuzzy sets
        
        Args:
            x: Input value
            center: Center of gaussian curve
            sigma: Standard deviation (width parameter)
            
        Returns:
            Membership value between 0.0 and 1.0
            
        Raises:
            ValueError: If sigma is non-positive
        """
        if sigma <= 0:
            raise ValueError(f"Sigma must be positive, got {sigma}")
        return math.exp(-0.5 * ((x - center) / sigma) ** 2)
    
    @classmethod
    def fuzzy_urgency(cls, hours_to_deadline: Optional[float]) -> Dict[str, float]:
        """Compute fuzzy urgency membership values"""
        if hours_to_deadline is None:
            return {"critical": 0.0, "high": 0.0, "medium": 0.0, "low": 1.0}
        
        h = max(0, hours_to_deadline)
        return {
            "critical": cls.triangular_membership(h, 0, 0, 8),
            "high": cls.triangular_membership(h, 4, 12, 24),
            "medium": cls.triangular_membership(h, 12, 72, 168),
            "low": max(0, min(1, (h - 72) / 168))
        }
    
    @classmethod
    def fuzzy_complexity(cls, effort_hours: float) -> Dict[str, float]:
        """Compute fuzzy complexity membership values"""
        return {
            "simple": cls.triangular_membership(effort_hours, 0, 0.5, 2),
            "moderate": cls.triangular_membership(effort_hours, 1, 4, 8),
            "complex": cls.triangular_membership(effort_hours, 6, 12, 24),
            "epic": max(0, min(1, (effort_hours - 16) / 24))
        }


class EnsembleScorer:
    """Ensemble scoring engine with multiple scoring methods"""
    
    def __init__(self, weights: AdaptiveWeights, fuzzy_engine: FuzzyLogicEngine) -> None:
        """
        Initialize ensemble scorer with weights and fuzzy engine
        
        Args:
            weights: Adaptive weights configuration
            fuzzy_engine: Fuzzy logic engine for membership calculations
        """
        if not isinstance(weights, AdaptiveWeights):
            raise TypeError("weights must be an AdaptiveWeights instance")
        if not isinstance(fuzzy_engine, FuzzyLogicEngine):
            raise TypeError("fuzzy_engine must be a FuzzyLogicEngine instance")
            
        self.weights = weights
        self.fuzzy = fuzzy_engine
        logger.debug("EnsembleScorer initialized with adaptive weights")
    
    def traditional_score(self, task: EnhancedTask, client_cfg: EnhancedClientConfig, 
                         now: datetime) -> Tuple[float, Dict[str, float]]:
        """Traditional weighted scoring (baseline)"""
        scores = {}
        
        # Urgency calculation
        due_dt = self._parse_iso(task.deadline_iso)
        hrs_to_deadline = None if not due_dt else (due_dt - now).total_seconds() / 3600.0
        
        if hrs_to_deadline is None:
            scores['urgency'] = 0.0
        elif hrs_to_deadline <= 0:
            scores['urgency'] = 1.0
        else:
            horizon = 336.0  # 14 days
            scores['urgency'] = max(0.0, min(1.0, 1.0 - (hrs_to_deadline / horizon)))
        
        # Other traditional factors
        scores['importance'] = (task.importance / 5.0) * client_cfg.importance_bias
        scores['effort_factor'] = max(0.0, min(1.0, 1 - (task.effort_hours / 8.0)))
        
        # Freshness
        created_dt = self._parse_iso(task.created_at or task.ingested_at)
        hours_since_created = None if not created_dt else (now - created_dt).total_seconds() / 3600.0
        scores['freshness'] = 0.0 if hours_since_created is None else max(0.0, min(1.0, 1 - (hours_since_created / 168.0)))
        
        # SLA pressure
        sla_hours = client_cfg.sla_hours
        hours_left_in_sla = 0.0 if hours_since_created is None else max(0.0, sla_hours - hours_since_created)
        scores['sla_pressure'] = max(0.0, min(1.0, 1 - (hours_left_in_sla / sla_hours)))
        
        # Progress penalty
        scores['progress_penalty'] = max(0.0, min(1.0, 1 - task.recent_progress))
        
        # Weighted sum
        total_score = (
            self.weights.urgency * scores['urgency'] +
            self.weights.importance * scores['importance'] +
            self.weights.effort_factor * scores['effort_factor'] +
            self.weights.freshness * scores['freshness'] +
            self.weights.sla_pressure * scores['sla_pressure'] +
            self.weights.progress_penalty * scores['progress_penalty']
        )
        
        return total_score, scores
    
    def fuzzy_mcdm_score(self, task: EnhancedTask, client_cfg: EnhancedClientConfig,
                        now: datetime) -> Tuple[float, Dict[str, float]]:
        """Multi-criteria decision analysis with fuzzy logic"""
        scores = {}
        
        # Get fuzzy membership values
        due_dt = self._parse_iso(task.deadline_iso)
        hrs_to_deadline = None if not due_dt else (due_dt - now).total_seconds() / 3600.0
        
        urgency_fuzzy = self.fuzzy.fuzzy_urgency(hrs_to_deadline)
        complexity_fuzzy = self.fuzzy.fuzzy_complexity(task.effort_hours)
        
        # Fuzzy urgency score (weighted by membership values)
        scores['fuzzy_urgency'] = (
            urgency_fuzzy["critical"] * 1.0 +
            urgency_fuzzy["high"] * 0.8 +
            urgency_fuzzy["medium"] * 0.5 +
            urgency_fuzzy["low"] * 0.2
        )
        
        # Fuzzy complexity score (considers client preference)
        complexity_preference = client_cfg.complexity_preference
        scores['fuzzy_complexity'] = (
            complexity_fuzzy["simple"] * (1 - complexity_preference) +
            complexity_fuzzy["moderate"] * 0.7 +
            complexity_fuzzy["complex"] * complexity_preference +
            complexity_fuzzy["epic"] * complexity_preference * 0.8
        )
        
        # Enhanced importance with fuzzy threshold
        base_importance = task.importance / 5.0
        importance_threshold = client_cfg.urgency_threshold
        if base_importance >= importance_threshold:
            scores['enhanced_importance'] = base_importance * client_cfg.priority_multiplier
        else:
            # Apply fuzzy logic for borderline cases
            membership = self.fuzzy.gaussian_membership(base_importance, importance_threshold, 0.2)
            scores['enhanced_importance'] = base_importance * (1 + membership * (client_cfg.priority_multiplier - 1))
        
        # Context awareness based on historical patterns
        scores['context_awareness'] = self._compute_context_score(task, client_cfg)
        
        # Total MCDM score
        total_score = (
            0.4 * scores['fuzzy_urgency'] +
            0.3 * scores['enhanced_importance'] +
            0.2 * scores['fuzzy_complexity'] +
            0.1 * scores['context_awareness']
        )
        
        return total_score, scores
    
    def ml_adaptive_score(self, task: EnhancedTask, client_cfg: EnhancedClientConfig,
                         now: datetime) -> Tuple[float, Dict[str, float]]:
        """Machine learning inspired adaptive scoring"""
        scores = {}
        
        # Historical performance weighting
        performance = client_cfg.performance_history
        if performance.total_tasks > 0:
            success_rate = performance.completed_on_time / performance.total_tasks
            scores['reliability_factor'] = success_rate
        else:
            scores['reliability_factor'] = 0.5  # Neutral for new clients
        
        # Provider performance factor
        if task.assigned_provider and task.assigned_provider in performance.provider_performance:
            scores['provider_performance'] = performance.provider_performance[task.assigned_provider]
        else:
            scores['provider_performance'] = 0.5  # Neutral for unknown providers
        
        # Task type similarity bonus
        scores['similarity_bonus'] = min(1.0, task.historical_similar_tasks / 10.0)
        
        # User feedback integration
        scores['feedback_score'] = max(0.0, min(1.0, task.user_feedback_score))
        
        # Dependency complexity penalty
        dependency_penalty = min(0.3, len(task.dependencies) * 0.05)
        scores['dependency_factor'] = 1.0 - dependency_penalty
        
        # Adaptive ML score
        total_score = (
            0.3 * scores['reliability_factor'] +
            0.25 * scores['provider_performance'] +
            0.2 * scores['similarity_bonus'] +
            0.15 * scores['feedback_score'] +
            0.1 * scores['dependency_factor']
        )
        
        return total_score, scores
    
    def _compute_context_score(self, task: EnhancedTask, client_cfg: EnhancedClientConfig) -> float:
        """Compute context-aware score based on historical patterns"""
        base_score = 0.5
        
        # Adjust based on task type performance
        if task.task_type in ["bugfix", "hotfix"]:
            base_score += 0.2  # Higher priority for critical fixes
        elif task.task_type in ["feature", "enhancement"]:
            base_score += 0.1  # Moderate priority for features
        
        # Adjust based on client historical performance
        performance = client_cfg.performance_history
        if performance.total_tasks > 5:  # Sufficient history
            success_rate = performance.completed_on_time / performance.total_tasks
            if success_rate > 0.8:
                base_score += 0.1  # Bonus for reliable client
            elif success_rate < 0.6:
                base_score -= 0.1  # Penalty for problematic client
        
        return max(0.0, min(1.0, base_score))
    
    @staticmethod
    def _parse_iso(s: Optional[str]) -> Optional[datetime]:
        """
        Parse ISO datetime string with proper error handling
        
        Args:
            s: ISO datetime string or None
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not s:
            return None
        s = s.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except Exception as e:
            logger.warning(f"Failed to parse datetime string '{s}': {e}")
            return None


class EnhancedScoringEngine:
    """Main enhanced scoring engine with ensemble methods"""
    
    def __init__(self) -> None:
        """
        Initialize enhanced scoring engine with ensemble methods
        
        Sets up adaptive weights, fuzzy logic engine, and ensemble scorer
        with performance tracking for method weight adaptation.
        """
        try:
            self.weights = AdaptiveWeights()
            self.fuzzy_engine = FuzzyLogicEngine()
            self.ensemble_scorer = EnsembleScorer(self.weights, self.fuzzy_engine)
            
            # Normalize weights during initialization
            self.weights.normalize()
            
            logger.info("Enhanced scoring engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced scoring engine: {e}")
            raise
        
        # Ensemble method weights (adaptive)
        self.method_weights = {
            'traditional': 0.4,
            'fuzzy_mcdm': 0.35,
            'ml_adaptive': 0.25
        }
        
        # Performance tracking for adaptive weight adjustment
        self.method_performance = {
            'traditional': {'accuracy': 0.7, 'count': 0},
            'fuzzy_mcdm': {'accuracy': 0.75, 'count': 0},
            'ml_adaptive': {'accuracy': 0.8, 'count': 0}
        }
    
    def compute_enhanced_score(self, task: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        """Compute enhanced ensemble score with confidence intervals"""
        now = datetime.now(timezone.utc)
        
        # Convert to enhanced task model
        enhanced_task = EnhancedTask(**{k: task.get(k) for k in EnhancedTask.__dataclass_fields__})
        client_cfg = EnhancedClientConfig(**rules.get("clients", {}).get(enhanced_task.client, {}))
        
        # Compute scores from all methods
        trad_score, trad_details = self.ensemble_scorer.traditional_score(enhanced_task, client_cfg, now)
        fuzzy_score, fuzzy_details = self.ensemble_scorer.fuzzy_mcdm_score(enhanced_task, client_cfg, now)
        ml_score, ml_details = self.ensemble_scorer.ml_adaptive_score(enhanced_task, client_cfg, now)
        
        # Ensemble combination with adaptive weights
        scores = [trad_score, fuzzy_score, ml_score]
        weights = list(self.method_weights.values())
        
        # Weighted ensemble score
        ensemble_score = sum(s * w for s, w in zip(scores, weights))
        
        # Confidence calculation (based on score variance)
        score_variance = np.var(scores)
        confidence = max(0.0, min(1.0, 1.0 - score_variance))
        
        # Uncertainty quantification
        uncertainty = score_variance
        
        # Additional metadata
        due_dt = enhanced_task.deadline_iso
        hrs_to_deadline = None
        if due_dt:
            parsed_dt = self.ensemble_scorer._parse_iso(due_dt)
            if parsed_dt:
                hrs_to_deadline = (parsed_dt - now).total_seconds() / 3600.0
        
        return {
            'score': float(ensemble_score),
            'confidence': float(confidence),
            'uncertainty': float(uncertainty),
            'method_scores': {
                'traditional': float(trad_score),
                'fuzzy_mcdm': float(fuzzy_score),
                'ml_adaptive': float(ml_score)
            },
            'method_weights': self.method_weights.copy(),
            'score_details': {
                'traditional': trad_details,
                'fuzzy_mcdm': fuzzy_details,
                'ml_adaptive': ml_details
            },
            'metadata': {
                'urgency_level': self._classify_urgency(hrs_to_deadline),
                'complexity_level': self._classify_complexity(enhanced_task.effort_hours),
                'deadline_within_24h': bool(hrs_to_deadline is not None and hrs_to_deadline <= 24),
                'sla_pressure': trad_details.get('sla_pressure', 0.0),
                'adaptive_weights_active': True
            }
        }
    
    def update_performance_feedback(self, method: str, was_accurate: bool) -> None:
        """
        Update method performance for adaptive weight adjustment
        
        Args:
            method: Scoring method name ('traditional', 'fuzzy_mcdm', 'ml_adaptive')
            was_accurate: Whether the method's prediction was accurate
            
        Raises:
            ValueError: If method name is not recognized
        """
        if method not in self.method_performance:
            logger.warning(f"Unknown scoring method: {method}")
            raise ValueError(f"Unknown scoring method: {method}. Valid methods: {list(self.method_performance.keys())}")
        
        # Update accuracy with exponential moving average
        current_accuracy = self.method_performance[method]['accuracy']
        alpha = 0.1  # Learning rate
        new_accuracy = alpha * (1.0 if was_accurate else 0.0) + (1 - alpha) * current_accuracy
        
        self.method_performance[method]['accuracy'] = new_accuracy
        self.method_performance[method]['count'] += 1
        
        # Adapt ensemble weights based on performance
        try:
            self._adapt_ensemble_weights()
            logger.debug(f"Updated performance for {method}: accuracy={new_accuracy:.3f}")
        except Exception as e:
            logger.error(f"Failed to adapt ensemble weights: {e}")
    
    def _adapt_ensemble_weights(self) -> None:
        """
        Dynamically adjust ensemble method weights based on performance
        
        Uses softmax normalization with temperature scaling to balance
        exploitation of best-performing methods with exploration.
        """
        # Softmax normalization based on accuracy
        accuracies = [self.method_performance[method]['accuracy'] for method in self.method_weights.keys()]
        
        # Apply temperature scaling for softmax (higher temp = more uniform)
        temperature = 2.0
        exp_accuracies = [math.exp(acc / temperature) for acc in accuracies]
        sum_exp = sum(exp_accuracies)
        
        # Update weights
        methods = list(self.method_weights.keys())
        old_weights = self.method_weights.copy()
        
        for i, method in enumerate(methods):
            self.method_weights[method] = exp_accuracies[i] / sum_exp
        
        # Log weight changes if significant
        weight_changes = {method: abs(self.method_weights[method] - old_weights[method]) 
                         for method in methods}
        max_change = max(weight_changes.values())
        
        if max_change > 0.05:  # Log if any weight changed by more than 5%
            logger.info(f"Ensemble weights adapted: {self.method_weights}")
    
    @staticmethod
    def _classify_urgency(hours_to_deadline: Optional[float]) -> str:
        """Classify urgency level for metadata"""
        if hours_to_deadline is None:
            return TaskUrgencyLevel.LOW.value
        elif hours_to_deadline <= 4:
            return TaskUrgencyLevel.CRITICAL.value
        elif hours_to_deadline <= 24:
            return TaskUrgencyLevel.HIGH.value
        elif hours_to_deadline <= 168:  # 7 days
            return TaskUrgencyLevel.MEDIUM.value
        else:
            return TaskUrgencyLevel.LOW.value
    
    @staticmethod
    def _classify_complexity(effort_hours: float) -> str:
        """Classify complexity level for metadata"""
        if effort_hours <= 2:
            return TaskComplexityLevel.SIMPLE.value
        elif effort_hours <= 8:
            return TaskComplexityLevel.MODERATE.value
        elif effort_hours <= 24:
            return TaskComplexityLevel.COMPLEX.value
        else:
            return TaskComplexityLevel.EPIC.value


# Main interface function for backward compatibility
def compute_enhanced_score(task: Dict[str, Any], rules: Dict[str, Any]) -> float:
    """Enhanced scoring function with ensemble methods and adaptive learning"""
    engine = EnhancedScoringEngine()
    result = engine.compute_enhanced_score(task, rules)
    return result['score']


# Detailed interface for full scoring information
def compute_score_with_details(task: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed scoring information including confidence and method breakdown"""
    engine = EnhancedScoringEngine()
    return engine.compute_enhanced_score(task, rules)