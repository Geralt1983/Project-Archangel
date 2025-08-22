"""
Helpful Solutions Service
Integration service for solution-oriented consensus discussions
"""

from typing import Dict, List, Any, Optional
from .consensus_service import ConsensusDiscussionService, ModelClient
from .protocol_engine import ProtocolType, ConsensusConfig, ConsensusResult
from .agent_system import AgentAssignment
from .helpful_solutions_config import HELPFUL_SOLUTIONS_ROLES, HelpfulSolutionsMetrics
from .helpful_solutions_validator import HelpfulSolutionsValidator
import structlog

logger = structlog.get_logger(__name__)

class HelpfulSolutionsService:
    """Service for running helpful, solution-focused consensus discussions"""
    
    def __init__(self, model_client: ModelClient):
        self.base_service = ConsensusDiscussionService(model_client)
        self.validator = HelpfulSolutionsValidator()
        self.logger = logger.bind(component="helpful_solutions_service")
    
    async def run_helpful_discussion(self,
                                   topic: str,
                                   models: List[str] = None,
                                   max_rounds: int = 3,
                                   helpfulness_threshold: float = 0.7,
                                   protocol: ProtocolType = ProtocolType.DIVERGENT) -> ConsensusResult:
        """
        Run a solution-focused consensus discussion
        
        Args:
            topic: The question or problem to address
            models: List of model names to use
            max_rounds: Maximum discussion rounds
            helpfulness_threshold: Minimum helpfulness score required
            protocol: DIVERGENT recommended for solution diversity
        """
        
        if not models:
            models = ["claude", "gpt", "grok"]
            
        # Create role assignments using helpful solutions roles
        role_assignments = self._create_helpful_role_assignments(models)
        
        self.logger.info("Starting helpful solutions discussion",
                        topic=topic[:100],
                        models=models,
                        helpfulness_threshold=helpfulness_threshold)
        
        # Run consensus discussion with helpful solutions configuration
        result = await self.base_service.run_discussion(
            topic=topic,
            models=models,
            protocol=protocol,
            max_rounds=max_rounds,
            consensus_threshold=0.6,  # Lower consensus requirement for divergent solutions
            quality_threshold=helpfulness_threshold,
            custom_roles={model: role.role_id for model, role in role_assignments.items()}
        )
        
        # Evaluate using helpful solutions metrics
        helpful_metrics = self._evaluate_helpfulness(result)
        result.helpful_solutions_metrics = helpful_metrics
        
        # Generate helpful solutions recommendations
        result.helpful_recommendations = self._generate_helpful_recommendations(
            result, helpful_metrics
        )
        
        self.logger.info("Helpful solutions discussion completed",
                        session_id=result.session_id,
                        helpfulness_score=helpful_metrics.overall_helpfulness_score(),
                        quality_level=helpful_metrics.quality_level().value)
        
        return result
    
    def _create_helpful_role_assignments(self, models: List[str]) -> Dict[str, Any]:
        """Assign helpful solutions roles to models"""
        role_keys = list(HELPFUL_SOLUTIONS_ROLES.keys())
        assignments = {}
        
        for i, model in enumerate(models):
            role_key = role_keys[i % len(role_keys)]
            assignments[model] = HELPFUL_SOLUTIONS_ROLES[role_key]
            
        return assignments
    
    def _evaluate_helpfulness(self, result: ConsensusResult) -> HelpfulSolutionsMetrics:
        """Evaluate the helpfulness of the consensus result"""
        all_responses = []
        for round_obj in result.rounds:
            all_responses.extend(round_obj.responses)
        
        return self.validator.evaluate_helpful_solutions(all_responses)
    
    def _generate_helpful_recommendations(self, 
                                        result: ConsensusResult, 
                                        metrics: HelpfulSolutionsMetrics) -> List[str]:
        """Generate recommendations for improving solution helpfulness"""
        recommendations = []
        
        if metrics.practical_utility < 0.6:
            recommendations.append(
                "Responses need more actionable, practical guidance that directly addresses the user's goal"
            )
        
        if metrics.actionability < 0.6:
            recommendations.append(
                "Break down recommendations into specific, implementable steps with clear instructions"
            )
        
        if metrics.safety_integration < 0.5:
            recommendations.append(
                "Integrate safety considerations within practical solutions rather than blocking them"
            )
        
        if metrics.evidence_basis < 0.5:
            recommendations.append(
                "Strengthen evidence basis with references to research or credible sources"
            )
        
        if metrics.specificity < 0.6:
            recommendations.append(
                "Avoid generic disclaimers and provide more specific, detailed guidance"
            )
        
        # Quality level recommendations
        if metrics.quality_level().value == "unhelpful":
            recommendations.append(
                "Response quality is insufficient - focus on practical solutions rather than disclaimers"
            )
        elif metrics.quality_level().value == "somewhat_helpful":
            recommendations.append(
                "Good foundation but needs more specificity and actionable details"
            )
        elif metrics.quality_level().value == "highly_helpful":
            recommendations.append(
                "Excellent helpful guidance that balances practicality with appropriate considerations"
            )
        
        if not recommendations:
            recommendations.append(
                "Discussion achieved good balance of helpful solutions with appropriate safety integration"
            )
        
        return recommendations
    
    def create_helpful_response_format(self, result: ConsensusResult) -> Dict[str, Any]:
        """Create response format optimized for helpful solutions"""
        base_format = self.base_service.create_improved_response_format(result)
        
        # Add helpful solutions specific metrics
        helpful_metrics = getattr(result, 'helpful_solutions_metrics', None)
        if helpful_metrics:
            base_format.update({
                "helpful_solutions_metrics": {
                    "overall_helpfulness_score": helpful_metrics.overall_helpfulness_score(),
                    "quality_level": helpful_metrics.quality_level().value,
                    "practical_utility": helpful_metrics.practical_utility,
                    "actionability": helpful_metrics.actionability,
                    "safety_integration": helpful_metrics.safety_integration,
                    "evidence_basis": helpful_metrics.evidence_basis,
                    "specificity": helpful_metrics.specificity
                },
                "helpful_recommendations": getattr(result, 'helpful_recommendations', [])
            })
        
        return base_format

# Factory function
async def create_helpful_solutions_service(model_client: ModelClient = None) -> HelpfulSolutionsService:
    """Factory function to create helpful solutions service"""
    if not model_client:
        model_client = ModelClient()  # Use default/mock client
    return HelpfulSolutionsService(model_client)