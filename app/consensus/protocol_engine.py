"""
Consensus Discussion Protocol Engine
Implements proper consensus logic with quality gates and validation
"""

from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)

# Quality scoring constants
QUALITY_WEIGHTS = {
    'response_consistency': 0.2,
    'topic_coherence': 0.2,
    'decision_clarity': 0.25,
    'semantic_convergence': 0.15,
    'actionable_content_score': 0.15,
    'evidence_based_score': 0.05
}

# Response length thresholds
MIN_RESPONSE_LENGTH = 50
SHORT_RESPONSE_LENGTH = 100
MEDIUM_RESPONSE_LENGTH = 200

# Scoring multipliers
CONSISTENCY_BOOST = 3
CLARITY_INDICATORS_THRESHOLD = 5
ACTIONABLE_KEYWORDS_THRESHOLD = 3
EVIDENCE_INDICATORS_THRESHOLD = 2


class ProtocolType(Enum):
    CONVERGENT = "convergent"
    DIVERGENT = "divergent"  
    COLLABORATIVE = "collaborative"
    ADVERSARIAL = "adversarial"


class TerminationReason(Enum):
    CONSENSUS_REACHED = "consensus_reached"
    MAX_ROUNDS_EXCEEDED = "max_rounds_exceeded"
    QUALITY_THRESHOLD_MET = "quality_threshold_met"
    FALSE_CONSENSUS_DETECTED = "false_consensus_detected"
    MANUAL_TERMINATION = "manual_termination"


@dataclass
class QualityMetrics:
    """Response quality metrics with proper validation"""
    response_consistency: float
    topic_coherence: float
    decision_clarity: float
    semantic_convergence: float
    actionable_content_score: float
    evidence_based_score: float
    
    def overall_score(self) -> float:
        """Calculate weighted overall quality score"""
        return sum(getattr(self, metric) * weight for metric, weight in QUALITY_WEIGHTS.items())
    
    def passes_threshold(self, threshold: float = 0.6) -> bool:
        """Check if quality metrics meet minimum threshold"""
        return self.overall_score() >= threshold


@dataclass
class ConsensusConfig:
    """Configuration for consensus discussion"""
    protocol: ProtocolType
    max_rounds: int
    consensus_threshold: float = 0.7
    quality_threshold: float = 0.6
    min_response_length: int = 50
    require_actionable_content: bool = True
    require_evidence_based: bool = False
    allow_early_termination: bool = True


@dataclass
class AgentResponse:
    """Individual agent response with metadata"""
    agent_id: str
    model: str
    role: str
    content: str
    timestamp: datetime
    word_count: int
    quality_score: Optional[float] = None


@dataclass
class DiscussionRound:
    """Single round of discussion"""
    round_number: int
    responses: List[AgentResponse]
    quality_metrics: QualityMetrics
    consensus_score: float
    timestamp: datetime


@dataclass
class ConsensusResult:
    """Final consensus discussion result"""
    session_id: str
    topic: str
    config: ConsensusConfig
    rounds: List[DiscussionRound]
    termination_reason: TerminationReason
    final_consensus_score: float
    final_quality_metrics: QualityMetrics
    execution_time: float
    success: bool
    recommendations: List[str]


class QualityGate:
    """Validates response quality and usefulness"""
    
    def __init__(self, config: ConsensusConfig):
        self.config = config
        self.logger = logger.bind(component="quality_gate")
    
    def evaluate_responses(self, responses: List[AgentResponse]) -> QualityMetrics:
        """Evaluate quality of agent responses"""
        
        # Calculate response consistency (semantic similarity)
        consistency = self._calculate_consistency(responses)
        
        # Calculate topic coherence (how well responses address the topic)
        coherence = self._calculate_coherence(responses)
        
        # Calculate decision clarity (actionable recommendations)
        clarity = self._calculate_clarity(responses)
        
        # Calculate semantic convergence (vocabulary/concept alignment)
        convergence = self._calculate_convergence(responses)
        
        # Calculate actionable content score
        actionable = self._calculate_actionable_content(responses)
        
        # Calculate evidence-based score
        evidence = self._calculate_evidence_score(responses)
        
        return QualityMetrics(
            response_consistency=consistency,
            topic_coherence=coherence,
            decision_clarity=clarity,
            semantic_convergence=convergence,
            actionable_content_score=actionable,
            evidence_based_score=evidence
        )
    
    def _calculate_consistency(self, responses: List[AgentResponse]) -> float:
        """Calculate how consistent responses are with each other"""
        if len(responses) < 2:
            return 1.0
        
        # Simple heuristic: check for shared concepts and terminology
        # Use list comprehension for better performance
        all_words = [set(response.content.lower().split()) for response in responses]
        
        # Calculate overlap between responses
        if not all_words:
            return 0.0
            
        # Use early returns to avoid unnecessary computation
        try:
            common_words = set.intersection(*all_words)
            total_unique_words = set.union(*all_words)
            
            if not total_unique_words:
                return 0.0
                
            consistency = len(common_words) / len(total_unique_words)
            return min(consistency * CONSISTENCY_BOOST, 1.0)  # Boost the score as it's typically low
        except (TypeError, ValueError):
            return 0.0
    
    def _calculate_coherence(self, responses: List[AgentResponse]) -> float:
        """Calculate how well responses stay on topic"""
        # Simple heuristic: longer, substantive responses typically have better coherence
        avg_length = sum(response.word_count for response in responses) / len(responses)
        
        # Penalize very short or very generic responses
        if avg_length < self.config.min_response_length:
            return 0.3
        elif avg_length < SHORT_RESPONSE_LENGTH:
            return 0.5
        elif avg_length < MEDIUM_RESPONSE_LENGTH:
            return 0.7
        else:
            return 0.9
    
    def _calculate_clarity(self, responses: List[AgentResponse]) -> float:
        """Calculate how clear and actionable the responses are"""
        clarity_indicators = [
            "recommend", "suggest", "should", "must", "need to",
            "first", "then", "next", "finally", "step",
            "solution", "approach", "strategy", "method"
        ]
        
        total_indicators = 0
        for response in responses:
            content_lower = response.content.lower()
            indicators_found = sum(1 for indicator in clarity_indicators 
                                 if indicator in content_lower)
            total_indicators += indicators_found
        
        # Normalize by response count
        avg_indicators = total_indicators / len(responses)
        return min(avg_indicators / CLARITY_INDICATORS_THRESHOLD, 1.0)  # Cap at 1.0
    
    def _calculate_convergence(self, responses: List[AgentResponse]) -> float:
        """Calculate semantic convergence between responses"""
        # For now, use a simple approach based on response length variance
        lengths = [response.word_count for response in responses]
        if len(lengths) < 2:
            return 1.0
            
        avg_length = sum(lengths) / len(lengths)
        variance = sum((length - avg_length) ** 2 for length in lengths) / len(lengths)
        
        # Lower variance = higher convergence
        # Normalize to 0-1 scale
        normalized_variance = min(variance / (avg_length ** 2), 1.0)
        return 1.0 - normalized_variance
    
    def _calculate_actionable_content(self, responses: List[AgentResponse]) -> float:
        """Calculate how much actionable content is present"""
        actionable_keywords = [
            "implement", "create", "build", "develop", "design",
            "use", "apply", "install", "configure", "setup",
            "test", "validate", "verify", "check", "monitor"
        ]
        
        total_actionable = 0
        for response in responses:
            content_lower = response.content.lower()
            actionable_found = sum(1 for keyword in actionable_keywords 
                                 if keyword in content_lower)
            total_actionable += actionable_found
        
        avg_actionable = total_actionable / len(responses)
        return min(avg_actionable / ACTIONABLE_KEYWORDS_THRESHOLD, 1.0)  # Cap at 1.0
    
    def _calculate_evidence_score(self, responses: List[AgentResponse]) -> float:
        """Calculate how evidence-based the responses are"""
        evidence_indicators = [
            "research", "study", "evidence", "data", "statistics",
            "according to", "studies show", "research indicates",
            "evidence suggests", "data shows"
        ]
        
        total_evidence = 0
        for response in responses:
            content_lower = response.content.lower()
            evidence_found = sum(1 for indicator in evidence_indicators 
                               if indicator in content_lower)
            total_evidence += evidence_found
        
        avg_evidence = total_evidence / len(responses)
        return min(avg_evidence / EVIDENCE_INDICATORS_THRESHOLD, 1.0)  # Cap at 1.0


class ConsensusProtocol(ABC):
    """Abstract base class for consensus protocols"""
    
    @abstractmethod
    def should_continue(self, round_num: int, metrics: QualityMetrics, 
                       consensus_score: float, config: ConsensusConfig) -> bool:
        pass
    
    @abstractmethod
    def calculate_consensus(self, responses: List[AgentResponse]) -> float:
        pass


class ConvergentProtocol(ConsensusProtocol):
    """Protocol that seeks agreement and actionable solutions"""
    
    def should_continue(self, round_num: int, metrics: QualityMetrics, 
                       consensus_score: float, config: ConsensusConfig) -> bool:
        
        if round_num >= config.max_rounds:
            return False
        
        # Continue if quality is poor
        if not metrics.passes_threshold(config.quality_threshold):
            return True
        
        # Continue if consensus not reached
        if consensus_score < config.consensus_threshold:
            return True
            
        return False
    
    def calculate_consensus(self, responses: List[AgentResponse]) -> float:
        """Calculate consensus based on response agreement"""
        # For convergent protocol, consensus = consistency + clarity
        quality_gate = QualityGate(ConsensusConfig(ProtocolType.CONVERGENT, 3))
        metrics = quality_gate.evaluate_responses(responses)
        
        return (metrics.response_consistency + metrics.decision_clarity) / 2


class DivergentProtocol(ConsensusProtocol):
    """Protocol that explores different perspectives"""
    
    def should_continue(self, round_num: int, metrics: QualityMetrics, 
                       consensus_score: float, config: ConsensusConfig) -> bool:
        
        if round_num >= config.max_rounds:
            return False
        
        # For divergent protocol, continue if perspectives are too similar
        if metrics.response_consistency > 0.8:
            return True
            
        # Continue if quality is poor
        if not metrics.passes_threshold(config.quality_threshold):
            return True
            
        return False
    
    def calculate_consensus(self, responses: List[AgentResponse]) -> float:
        """For divergent protocol, 'consensus' means diverse, quality perspectives"""
        quality_gate = QualityGate(ConsensusConfig(ProtocolType.DIVERGENT, 3))
        metrics = quality_gate.evaluate_responses(responses)
        
        # Invert consistency for divergent protocol
        diversity_score = 1.0 - metrics.response_consistency
        return (diversity_score + metrics.topic_coherence) / 2


class ConsensusEngine:
    """Main engine for running consensus discussions"""
    
    def __init__(self):
        self.logger = logger.bind(component="consensus_engine")
        self.quality_gate = None
        self.protocol = None
    
    def create_protocol(self, protocol_type: ProtocolType) -> ConsensusProtocol:
        """Factory method for creating protocol instances"""
        if protocol_type == ProtocolType.CONVERGENT:
            return ConvergentProtocol()
        elif protocol_type == ProtocolType.DIVERGENT:
            return DivergentProtocol()
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")
    
    async def run_discussion(self, 
                      session_id: str,
                      topic: str, 
                      config: ConsensusConfig,
                      agent_responses_generator: Callable[[int, str], Awaitable[List[AgentResponse]]]) -> ConsensusResult:
        """Run a complete consensus discussion"""
        
        start_time = datetime.now(timezone.utc)
        self.quality_gate = QualityGate(config)
        self.protocol = self.create_protocol(config.protocol)
        
        rounds = []
        round_num = 1
        
        self.logger.info("Starting consensus discussion", 
                        session_id=session_id, topic=topic, protocol=config.protocol.value)
        
        while round_num <= config.max_rounds:
            self.logger.info("Starting discussion round", round=round_num)
            
            # Generate responses for this round
            responses = await agent_responses_generator(round_num, topic)
            
            # Evaluate quality
            metrics = self.quality_gate.evaluate_responses(responses)
            
            # Calculate consensus score
            consensus_score = self.protocol.calculate_consensus(responses)
            
            # Create round record
            discussion_round = DiscussionRound(
                round_number=round_num,
                responses=responses,
                quality_metrics=metrics,
                consensus_score=consensus_score,
                timestamp=datetime.now(timezone.utc)
            )
            rounds.append(discussion_round)
            
            self.logger.info("Round completed", 
                           round=round_num,
                           consensus_score=consensus_score,
                           quality_score=metrics.overall_score())
            
            # Check termination conditions
            should_continue = self.protocol.should_continue(
                round_num, metrics, consensus_score, config
            )
            
            if not should_continue:
                # Determine termination reason
                if round_num >= config.max_rounds:
                    termination_reason = TerminationReason.MAX_ROUNDS_EXCEEDED
                elif metrics.passes_threshold(config.quality_threshold):
                    termination_reason = TerminationReason.QUALITY_THRESHOLD_MET
                elif consensus_score >= config.consensus_threshold:
                    # Check for false consensus
                    if metrics.overall_score() < config.quality_threshold:
                        termination_reason = TerminationReason.FALSE_CONSENSUS_DETECTED
                    else:
                        termination_reason = TerminationReason.CONSENSUS_REACHED
                else:
                    termination_reason = TerminationReason.MANUAL_TERMINATION
                
                break
            
            round_num += 1
        else:
            termination_reason = TerminationReason.MAX_ROUNDS_EXCEEDED
        
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        # Generate final result
        final_round = rounds[-1] if rounds else None
        final_metrics = final_round.quality_metrics if final_round else QualityMetrics(0,0,0,0,0,0)
        final_consensus = final_round.consensus_score if final_round else 0.0
        
        success = (termination_reason in [
            TerminationReason.CONSENSUS_REACHED,
            TerminationReason.QUALITY_THRESHOLD_MET
        ])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            rounds, termination_reason, final_metrics, config
        )
        
        result = ConsensusResult(
            session_id=session_id,
            topic=topic,
            config=config,
            rounds=rounds,
            termination_reason=termination_reason,
            final_consensus_score=final_consensus,
            final_quality_metrics=final_metrics,
            execution_time=execution_time,
            success=success,
            recommendations=recommendations
        )
        
        self.logger.info("Consensus discussion completed",
                        session_id=session_id,
                        rounds_completed=len(rounds),
                        termination_reason=termination_reason.value,
                        success=success)
        
        return result
    
    def _generate_recommendations(self, 
                                rounds: List[DiscussionRound],
                                termination_reason: TerminationReason,
                                final_metrics: QualityMetrics,
                                config: ConsensusConfig) -> List[str]:
        """Generate recommendations for improving discussion quality"""
        
        recommendations = []
        
        if termination_reason == TerminationReason.FALSE_CONSENSUS_DETECTED:
            recommendations.append("False consensus detected - responses lack substance despite agreement")
            recommendations.append("Consider rephrasing the topic or requiring evidence-based responses")
        
        if final_metrics.actionable_content_score < 0.5:
            recommendations.append("Responses lack actionable content - require specific recommendations")
        
        if final_metrics.response_consistency < 0.3:
            recommendations.append("Low response consistency - agents may need clearer instructions")
        
        if final_metrics.topic_coherence < 0.5:
            recommendations.append("Poor topic coherence - consider breaking down complex topics")
        
        if len(rounds) == 1 and config.max_rounds > 1:
            recommendations.append("Discussion terminated after one round - may indicate protocol issues")
        
        if not recommendations:
            recommendations.append("Discussion completed successfully with good quality metrics")
        
        return recommendations