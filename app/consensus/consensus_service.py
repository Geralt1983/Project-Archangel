"""
Consensus Discussion Service
Main service that integrates protocol engine, agent system, and external model APIs
"""

from typing import Dict, List, Any, Optional, Callable
import uuid
from datetime import datetime, timezone
import structlog

from .protocol_engine import (
    ConsensusEngine, ConsensusConfig, ProtocolType, 
    ConsensusResult, AgentResponse, QualityMetrics
)
from .agent_system import (
    AgentRoleRegistry, AgentAssignment, AgentRequirementValidator,
    agent_role_registry, AgentCapability
)

logger = structlog.get_logger(__name__)


class ModelClient:
    """Interface for external model APIs"""
    
    async def generate_response(self, 
                              model: str, 
                              prompt: str, 
                              max_tokens: int = 1000) -> str:
        """Generate response from external model"""
        # This would integrate with actual model APIs
        # For now, return placeholder
        return f"Mock response from {model} for prompt: {prompt[:100]}..."


class ConsensusDiscussionService:
    """Main service for running consensus discussions"""
    
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client
        self.consensus_engine = ConsensusEngine()
        self.role_registry = agent_role_registry
        self.agent_assignment = AgentAssignment(self.role_registry)
        self.validator = AgentRequirementValidator()
        self.logger = logger.bind(component="consensus_service")
    
    async def run_discussion(self,
                           topic: str,
                           models: List[str] = None,
                           protocol: ProtocolType = ProtocolType.CONVERGENT,
                           max_rounds: int = 3,
                           consensus_threshold: float = 0.7,
                           quality_threshold: float = 0.6,
                           custom_roles: Dict[str, str] = None) -> ConsensusResult:
        """
        Run a complete consensus discussion
        
        Args:
            topic: Discussion topic
            models: List of model names to use
            protocol: Discussion protocol (convergent/divergent)
            max_rounds: Maximum discussion rounds
            consensus_threshold: Minimum consensus score to reach
            quality_threshold: Minimum quality score required
            custom_roles: Optional custom model->role mapping
        """
        
        # Input validation
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")
        if max_rounds < 1 or max_rounds > 10:
            raise ValueError("Max rounds must be between 1 and 10")
        if not (0.0 <= consensus_threshold <= 1.0):
            raise ValueError("Consensus threshold must be between 0.0 and 1.0")
        if not (0.0 <= quality_threshold <= 1.0):
            raise ValueError("Quality threshold must be between 0.0 and 1.0")
        
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        if not models:
            models = ["claude", "gpt", "grok"]
        
        self.logger.info("Starting consensus discussion",
                        session_id=session_id,
                        topic=topic,
                        models=models,
                        protocol=protocol.value)
        
        # Create configuration
        config = ConsensusConfig(
            protocol=protocol,
            max_rounds=max_rounds,
            consensus_threshold=consensus_threshold,
            quality_threshold=quality_threshold,
            require_actionable_content=True,
            require_evidence_based=protocol == ProtocolType.CONVERGENT
        )
        
        # Assign roles to models
        if custom_roles:
            role_assignments = self.agent_assignment.create_custom_assignment(custom_roles)
        else:
            # Auto-assign based on protocol requirements
            required_capabilities = self._get_required_capabilities(protocol)
            role_assignments = self.agent_assignment.create_balanced_assignment(
                models, required_capabilities
            )
        
        # Create response generator function
        async def generate_responses(round_num: int, discussion_topic: str) -> List[AgentResponse]:
            responses = []
            
            for model in models:
                role = role_assignments.get(model)
                if not role:
                    self.logger.warning("No role assigned to model", model=model)
                    continue
                
                # Generate prompt from role template
                prompt = role.prompt_template.format(
                    topic=discussion_topic,
                    previous_responses="" if round_num == 1 else self._format_previous_responses(responses)
                )
                
                # Generate response
                try:
                    content = await self.model_client.generate_response(model, prompt)
                    
                    response = AgentResponse(
                        agent_id=f"{model}_{role.role_id}_{uuid.uuid4().hex[:8]}",
                        model=model,
                        role=role.role_id,
                        content=content,
                        timestamp=datetime.now(timezone.utc),
                        word_count=len(content.split())
                    )
                    
                    # Validate response against role requirements
                    validation_scores = self.validator.validate_response(
                        content, role.requirements
                    )
                    
                    # Calculate weighted quality score
                    total_weight = sum(req.weight for req in role.requirements)
                    weighted_score = sum(
                        validation_scores.get(req.name, 0.0) * req.weight 
                        for req in role.requirements
                    )
                    response.quality_score = weighted_score / total_weight if total_weight > 0 else 0.0
                    
                    responses.append(response)
                    
                    self.logger.info("Generated agent response",
                                   model=model, 
                                   role=role.role_id,
                                   word_count=response.word_count,
                                   quality_score=response.quality_score)
                    
                except (ValueError, TypeError, RuntimeError) as e:
                    self.logger.error("Failed to generate response", 
                                    model=model, error=str(e))
                except Exception as e:
                    self.logger.error("Unexpected error generating response", 
                                    model=model, error=str(e), exc_info=True)
            
            return responses
        
        # Run the discussion
        result = await self.consensus_engine.run_discussion(
            session_id, topic, config, generate_responses
        )
        
        # Add role assignment info to result
        result.agent_assignments = {
            model: role.role_id for model, role in role_assignments.items()
        }
        
        self.logger.info("Consensus discussion completed",
                        session_id=session_id,
                        success=result.success,
                        rounds=len(result.rounds),
                        termination_reason=result.termination_reason.value)
        
        return result
    
    def _get_required_capabilities(self, protocol: ProtocolType) -> List[AgentCapability]:
        """Get required capabilities based on protocol type"""
        if protocol == ProtocolType.CONVERGENT:
            return [
                AgentCapability.ANALYSIS,
                AgentCapability.SOLUTION_DESIGN,
                AgentCapability.QUALITY_VALIDATION
            ]
        elif protocol == ProtocolType.DIVERGENT:
            return [
                AgentCapability.ANALYSIS,
                AgentCapability.RISK_ASSESSMENT,
                AgentCapability.EVIDENCE_RESEARCH
            ]
        else:
            return [AgentCapability.ANALYSIS]
    
    def _format_previous_responses(self, responses: List[AgentResponse]) -> str:
        """Format previous responses for context"""
        if not responses:
            return ""
        
        formatted = "\n\nPrevious responses:\n"
        for response in responses[-3:]:  # Last 3 responses for context
            formatted += f"\n{response.role} ({response.model}):\n{response.content[:200]}...\n"
        
        return formatted
    
    def create_improved_response_format(self, result: ConsensusResult) -> Dict[str, Any]:
        """Create improved, flattened response format"""
        
        # Convert rounds to simple format
        rounds_data = []
        for round_obj in result.rounds:
            round_data = {
                "round_number": round_obj.round_number,
                "timestamp": round_obj.timestamp.isoformat(),
                "consensus_score": round_obj.consensus_score,
                "quality_metrics": {
                    "overall_score": round_obj.quality_metrics.overall_score(),
                    "response_consistency": round_obj.quality_metrics.response_consistency,
                    "topic_coherence": round_obj.quality_metrics.topic_coherence,
                    "decision_clarity": round_obj.quality_metrics.decision_clarity,
                    "actionable_content": round_obj.quality_metrics.actionable_content_score,
                    "evidence_based": round_obj.quality_metrics.evidence_based_score
                },
                "responses": [
                    {
                        "agent_id": resp.agent_id,
                        "model": resp.model,
                        "role": resp.role,
                        "content": resp.content,
                        "word_count": resp.word_count,
                        "quality_score": resp.quality_score
                    }
                    for resp in round_obj.responses
                ]
            }
            rounds_data.append(round_data)
        
        # Create flattened response structure
        return {
            "session_id": result.session_id,
            "topic": result.topic,
            "status": "completed" if result.success else "failed",
            "termination_reason": result.termination_reason.value,
            "execution_time": result.execution_time,
            
            # Configuration
            "config": {
                "protocol": result.config.protocol.value,
                "max_rounds": result.config.max_rounds,
                "consensus_threshold": result.config.consensus_threshold,
                "quality_threshold": result.config.quality_threshold
            },
            
            # Results
            "rounds_completed": len(result.rounds),
            "final_consensus_score": result.final_consensus_score,
            "final_quality_score": result.final_quality_metrics.overall_score(),
            "consensus_reached": result.final_consensus_score >= result.config.consensus_threshold,
            "quality_threshold_met": result.final_quality_metrics.passes_threshold(result.config.quality_threshold),
            
            # Detailed metrics
            "final_metrics": {
                "response_consistency": result.final_quality_metrics.response_consistency,
                "topic_coherence": result.final_quality_metrics.topic_coherence,
                "decision_clarity": result.final_quality_metrics.decision_clarity,
                "semantic_convergence": result.final_quality_metrics.semantic_convergence,
                "actionable_content": result.final_quality_metrics.actionable_content_score,
                "evidence_based": result.final_quality_metrics.evidence_based_score
            },
            
            # Agent assignments
            "agent_assignments": getattr(result, 'agent_assignments', {}),
            
            # Discussion rounds
            "rounds": rounds_data,
            
            # Recommendations
            "recommendations": result.recommendations,
            
            # Success indicators
            "issues_detected": [
                "low_quality" if result.final_quality_metrics.overall_score() < 0.5 else None,
                "false_consensus" if (result.final_consensus_score > 0.7 and 
                                    result.final_quality_metrics.overall_score() < 0.5) else None,
                "premature_termination" if (len(result.rounds) == 1 and 
                                          result.config.max_rounds > 1) else None
            ],
            
            # Token usage (placeholder)
            "token_usage": {
                "total_input": sum(len(r.content.split()) * 1.3 for round_obj in result.rounds 
                                 for r in round_obj.responses),  # Rough estimate
                "total_output": sum(len(r.content.split()) for round_obj in result.rounds 
                                  for r in round_obj.responses)
            }
        }


# Usage example and testing
async def test_consensus_service():
    """Test the consensus service with mock responses"""
    
    class MockModelClient(ModelClient):
        async def generate_response(self, model: str, prompt: str, max_tokens: int = 1000) -> str:
            # Generate different response styles based on model
            if model == "claude":
                return f"Evidence-based analysis: Based on research studies, the approach to {prompt[-50:]} shows significant merit. According to Johnson et al. (2023), similar methodologies have demonstrated 78% effectiveness rates."
            elif model == "gpt":
                return f"Solution Design: Here's a practical implementation approach: 1) First, setup the infrastructure components 2) Next, configure the API endpoints 3) Then, implement the validation logic 4) Finally, deploy with monitoring systems."
            elif model == "grok":
                return f"Risk Assessment: Key risks to consider: 1) Performance bottlenecks under high load 2) Security vulnerabilities in API authentication 3) Data consistency issues during concurrent operations. Mitigation: Implement rate limiting, use OAuth 2.0, and employ database transactions."
            else:
                return f"Generic response from {model} regarding the topic."
    
    service = ConsensusDiscussionService(MockModelClient())
    
    # Test convergent protocol
    result = await service.run_discussion(
        topic="How to implement a scalable microservices architecture",
        models=["claude", "gpt", "grok"],
        protocol=ProtocolType.CONVERGENT,
        max_rounds=2,
        consensus_threshold=0.6,
        quality_threshold=0.5
    )
    
    # Format response
    formatted_response = service.create_improved_response_format(result)
    
    return formatted_response


# Initialize service instance
async def create_consensus_service() -> ConsensusDiscussionService:
    """Factory function to create consensus service"""
    model_client = ModelClient()  # Would use real client in production
    return ConsensusDiscussionService(model_client)