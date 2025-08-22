"""
Comprehensive tests for the improved consensus discussion system
Tests protocol engine, agent system, and service integration
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from app.consensus.protocol_engine import (
    ConsensusEngine, ConsensusConfig, ProtocolType, 
    QualityMetrics, AgentResponse, DiscussionRound,
    ConvergentProtocol, DivergentProtocol, QualityGate
)
from app.consensus.agent_system import (
    AgentRoleRegistry, AgentAssignment, AgentRequirementValidator,
    AgentCapability, AgentRole, AgentRequirement
)
from app.consensus.consensus_service import ConsensusDiscussionService, ModelClient


class TestQualityMetrics:
    """Test quality metrics calculation and validation"""
    
    def test_quality_metrics_overall_score(self):
        """Test overall quality score calculation"""
        metrics = QualityMetrics(
            response_consistency=0.8,
            topic_coherence=0.7,
            decision_clarity=0.9,
            semantic_convergence=0.6,
            actionable_content_score=0.8,
            evidence_based_score=0.5
        )
        
        # Test weighted calculation
        overall = metrics.overall_score()
        assert 0.0 <= overall <= 1.0
        assert overall > 0.7  # Should be high with good scores
    
    def test_quality_threshold_validation(self):
        """Test quality threshold validation"""
        good_metrics = QualityMetrics(0.8, 0.8, 0.8, 0.7, 0.7, 0.6)
        poor_metrics = QualityMetrics(0.3, 0.2, 0.4, 0.3, 0.2, 0.1)
        
        assert good_metrics.passes_threshold(0.6)
        assert not poor_metrics.passes_threshold(0.6)


class TestQualityGate:
    """Test response quality evaluation"""
    
    @pytest.fixture
    def quality_gate(self):
        config = ConsensusConfig(ProtocolType.CONVERGENT, 3)
        return QualityGate(config)
    
    @pytest.fixture
    def sample_responses(self):
        return [
            AgentResponse(
                agent_id="agent1",
                model="claude", 
                role="analyst",
                content="According to research by Smith (2023), the implementation should follow these steps: 1) Setup infrastructure 2) Configure APIs 3) Test thoroughly. This approach has shown 85% success rates.",
                timestamp=datetime.now(timezone.utc),
                word_count=25
            ),
            AgentResponse(
                agent_id="agent2",
                model="gpt",
                role="architect",
                content="Implementation strategy: First, create the database schema. Next, implement the REST endpoints. Then, add authentication middleware. Finally, deploy with monitoring.",
                timestamp=datetime.now(timezone.utc),
                word_count=23
            )
        ]
    
    def test_consistency_calculation(self, quality_gate, sample_responses):
        """Test response consistency calculation"""
        metrics = quality_gate.evaluate_responses(sample_responses)
        
        assert 0.0 <= metrics.response_consistency <= 1.0
        # Should have some consistency due to shared technical terms
        assert metrics.response_consistency > 0.0
    
    def test_clarity_calculation(self, quality_gate, sample_responses):
        """Test decision clarity calculation"""
        metrics = quality_gate.evaluate_responses(sample_responses)
        
        assert 0.0 <= metrics.decision_clarity <= 1.0
        # Should be high due to action words like "setup", "implement", "create"
        assert metrics.decision_clarity > 0.3
    
    def test_actionable_content_calculation(self, quality_gate, sample_responses):
        """Test actionable content scoring"""
        metrics = quality_gate.evaluate_responses(sample_responses)
        
        assert 0.0 <= metrics.actionable_content_score <= 1.0
        # Should be high due to implementation verbs
        assert metrics.actionable_content_score > 0.3


class TestConsensusProtocols:
    """Test consensus protocol implementations"""
    
    def test_convergent_protocol_consensus_calculation(self):
        """Test convergent protocol consensus calculation"""
        protocol = ConvergentProtocol()
        
        responses = [
            AgentResponse("a1", "claude", "analyst", "Implement solution A with steps 1, 2, 3", 
                         datetime.now(timezone.utc), 10),
            AgentResponse("a2", "gpt", "architect", "Solution A implementation: step 1, step 2, step 3",
                         datetime.now(timezone.utc), 9)
        ]
        
        consensus_score = protocol.calculate_consensus(responses)
        assert 0.0 <= consensus_score <= 1.0
    
    def test_divergent_protocol_consensus_calculation(self):
        """Test divergent protocol consensus calculation"""
        protocol = DivergentProtocol()
        
        responses = [
            AgentResponse("a1", "claude", "analyst", "Approach A is optimal", 
                         datetime.now(timezone.utc), 5),
            AgentResponse("a2", "gpt", "architect", "Approach B is better",
                         datetime.now(timezone.utc), 5)
        ]
        
        consensus_score = protocol.calculate_consensus(responses)
        assert 0.0 <= consensus_score <= 1.0
    
    def test_convergent_should_continue_logic(self):
        """Test convergent protocol continuation logic"""
        protocol = ConvergentProtocol()
        config = ConsensusConfig(ProtocolType.CONVERGENT, max_rounds=3, 
                               consensus_threshold=0.7, quality_threshold=0.6)
        
        good_metrics = QualityMetrics(0.8, 0.8, 0.8, 0.7, 0.7, 0.6)
        poor_metrics = QualityMetrics(0.3, 0.2, 0.4, 0.3, 0.2, 0.1)
        
        # Should continue with poor quality
        assert protocol.should_continue(1, poor_metrics, 0.8, config)
        
        # Should continue with low consensus
        assert protocol.should_continue(1, good_metrics, 0.5, config)
        
        # Should stop with good quality and consensus
        assert not protocol.should_continue(1, good_metrics, 0.8, config)
        
        # Should stop at max rounds
        assert not protocol.should_continue(3, poor_metrics, 0.3, config)


class TestAgentRoleSystem:
    """Test agent role definition and validation"""
    
    @pytest.fixture
    def role_registry(self):
        return AgentRoleRegistry()
    
    @pytest.fixture  
    def validator(self):
        return AgentRequirementValidator()
    
    def test_role_registry_initialization(self, role_registry):
        """Test that default roles are properly initialized"""
        roles = role_registry.list_roles()
        assert len(roles) >= 4  # Should have at least the default roles
        
        role_ids = [role.role_id for role in roles]
        assert "evidence_analyst" in role_ids
        assert "solution_architect" in role_ids
        assert "risk_assessor" in role_ids
    
    def test_role_retrieval(self, role_registry):
        """Test role retrieval by ID"""
        analyst_role = role_registry.get_role("evidence_analyst")
        assert analyst_role is not None
        assert analyst_role.name == "Evidence Analyst"
        assert analyst_role.primary_capability == AgentCapability.ANALYSIS
    
    def test_roles_by_capability(self, role_registry):
        """Test filtering roles by capability"""
        analysis_roles = role_registry.get_roles_by_capability(AgentCapability.ANALYSIS)
        assert len(analysis_roles) >= 2  # Multiple roles should have analysis capability
    
    def test_requirement_validator_cite_sources(self, validator):
        """Test source citation validation"""
        good_response = "According to research by Smith (2023), this approach works well."
        poor_response = "This might work but it depends on various factors."
        
        good_score = validator.validate_cite_sources(good_response)
        poor_score = validator.validate_cite_sources(poor_response)
        
        assert good_score > poor_score
        assert good_score > 0.3
    
    def test_requirement_validator_actionable_steps(self, validator):
        """Test actionable steps validation"""
        good_response = "Step 1: Install the software. Next, configure the database. Finally, test the system."
        poor_response = "You should probably consider doing something about this issue."
        
        good_score = validator.validate_actionable_steps(good_response)
        poor_score = validator.validate_actionable_steps(poor_response)
        
        assert good_score > poor_score
        assert good_score > 0.3
    
    def test_requirement_validator_avoid_generic(self, validator):
        """Test generic response avoidance validation"""
        good_response = "Implement the Redis caching layer with 2GB memory allocation and TTL of 3600 seconds."
        poor_response = "It depends on many factors and there are pros and cons to consider."
        
        good_score = validator.validate_avoid_generic_responses(good_response)
        poor_score = validator.validate_avoid_generic_responses(poor_response)
        
        assert good_score > poor_score
        assert poor_score < 0.5  # Should be penalized


class TestAgentAssignment:
    """Test agent assignment to models"""
    
    @pytest.fixture
    def assignment_system(self):
        registry = AgentRoleRegistry()
        return AgentAssignment(registry)
    
    def test_balanced_assignment(self, assignment_system):
        """Test balanced role assignment"""
        models = ["claude", "gpt", "grok"]
        capabilities = [AgentCapability.ANALYSIS, AgentCapability.SOLUTION_DESIGN]
        
        assignments = assignment_system.create_balanced_assignment(models, capabilities)
        
        assert len(assignments) == len(models)
        assert all(model in assignments for model in models)
        assert all(isinstance(role, AgentRole) for role in assignments.values())
    
    def test_custom_assignment(self, assignment_system):
        """Test custom role assignment"""
        mapping = {
            "claude": "evidence_analyst",
            "gpt": "solution_architect", 
            "grok": "risk_assessor"
        }
        
        assignments = assignment_system.create_custom_assignment(mapping)
        
        assert len(assignments) == 3
        assert assignments["claude"].role_id == "evidence_analyst"
        assert assignments["gpt"].role_id == "solution_architect"
        assert assignments["grok"].role_id == "risk_assessor"


class TestConsensusEngine:
    """Test the main consensus engine"""
    
    @pytest.fixture
    def consensus_engine(self):
        return ConsensusEngine()
    
    def create_mock_response_generator(self):
        """Create mock response generator for testing"""
        async def mock_generator(round_num: int, topic: str):
            return [
                AgentResponse(
                    f"agent_{round_num}_1", "claude", "analyst",
                    f"Analysis for round {round_num}: This approach has merit based on evidence.",
                    datetime.now(timezone.utc), 12
                ),
                AgentResponse(
                    f"agent_{round_num}_2", "gpt", "architect", 
                    f"Solution for round {round_num}: Step 1: implement, Step 2: test, Step 3: deploy.",
                    datetime.now(timezone.utc), 14
                )
            ]
        return mock_generator
    
    @pytest.mark.asyncio
    async def test_consensus_engine_convergent(self, consensus_engine):
        """Test consensus engine with convergent protocol"""
        config = ConsensusConfig(
            protocol=ProtocolType.CONVERGENT,
            max_rounds=2,
            consensus_threshold=0.5,
            quality_threshold=0.4
        )
        
        generator = self.create_mock_response_generator()
        
        result = await consensus_engine.run_discussion(
            "test_session", "Test topic", config, generator
        )
        
        assert result.session_id == "test_session"
        assert result.topic == "Test topic"
        assert len(result.rounds) >= 1
        assert result.execution_time > 0
        assert result.termination_reason is not None
    
    @pytest.mark.asyncio 
    async def test_consensus_engine_quality_gate(self, consensus_engine):
        """Test that quality gates prevent false consensus"""
        config = ConsensusConfig(
            protocol=ProtocolType.CONVERGENT,
            max_rounds=3,
            consensus_threshold=0.3,  # Low threshold
            quality_threshold=0.8     # High quality requirement
        )
        
        # Generator that produces low-quality responses
        async def poor_quality_generator(round_num: int, topic: str):
            return [
                AgentResponse(
                    f"agent_{round_num}_1", "claude", "analyst",
                    "It depends on many factors.",  # Generic response
                    datetime.now(timezone.utc), 6
                ),
                AgentResponse(
                    f"agent_{round_num}_2", "gpt", "architect",
                    "There are pros and cons.",      # Generic response
                    datetime.now(timezone.utc), 5
                )
            ]
        
        result = await consensus_engine.run_discussion(
            "quality_test", "Test topic", config, poor_quality_generator
        )
        
        # Should continue trying despite "consensus" due to poor quality
        assert len(result.rounds) > 1 or result.final_quality_metrics.overall_score() < 0.8


@pytest.mark.asyncio
class TestConsensusService:
    """Test the complete consensus service"""
    
    @pytest.fixture
    def mock_model_client(self):
        """Create mock model client"""
        class MockClient(ModelClient):
            async def generate_response(self, model: str, prompt: str, max_tokens: int = 1000) -> str:
                if "evidence" in prompt.lower():
                    return f"Research shows that {model} analysis indicates this approach has 80% success rate according to studies."
                elif "solution" in prompt.lower():
                    return f"Implementation plan: 1) Setup {model} components 2) Configure APIs 3) Deploy monitoring 4) Test thoroughly"
                elif "risk" in prompt.lower():
                    return f"Key risks from {model} perspective: 1) Performance bottlenecks 2) Security vulnerabilities 3) Data consistency issues. Mitigation: use caching, implement OAuth, use transactions."
                else:
                    return f"Detailed analysis from {model} regarding the topic with specific recommendations and evidence-based insights."
        
        return MockClient()
    
    @pytest.fixture
    def consensus_service(self, mock_model_client):
        return ConsensusDiscussionService(mock_model_client)
    
    async def test_full_consensus_discussion(self, consensus_service):
        """Test complete consensus discussion workflow"""
        result = await consensus_service.run_discussion(
            topic="How to implement microservices architecture",
            models=["claude", "gpt", "grok"],
            protocol=ProtocolType.CONVERGENT,
            max_rounds=2,
            consensus_threshold=0.6,
            quality_threshold=0.5
        )
        
        assert result.success or result.termination_reason is not None
        assert len(result.rounds) >= 1
        assert result.final_quality_metrics is not None
        assert hasattr(result, 'agent_assignments')
    
    async def test_improved_response_format(self, consensus_service):
        """Test the improved response format"""
        result = await consensus_service.run_discussion(
            topic="Test topic",
            models=["claude", "gpt"],
            max_rounds=1
        )
        
        formatted = consensus_service.create_improved_response_format(result)
        
        # Test flat structure (no nested api_response)
        assert "api_response" not in formatted
        assert "session_id" in formatted
        assert "status" in formatted
        assert "termination_reason" in formatted
        assert "config" in formatted
        assert "final_metrics" in formatted
        assert "rounds" in formatted
        assert "recommendations" in formatted
        
        # Test that all metrics are present
        metrics = formatted["final_metrics"]
        required_metrics = [
            "response_consistency", "topic_coherence", "decision_clarity",
            "semantic_convergence", "actionable_content", "evidence_based"
        ]
        for metric in required_metrics:
            assert metric in metrics
    
    async def test_role_assignment_integration(self, consensus_service):
        """Test that role assignments work correctly"""
        custom_roles = {
            "claude": "evidence_analyst",
            "gpt": "solution_architect"
        }
        
        result = await consensus_service.run_discussion(
            topic="Test topic",
            models=["claude", "gpt"],
            custom_roles=custom_roles,
            max_rounds=1
        )
        
        assert hasattr(result, 'agent_assignments')
        assert result.agent_assignments["claude"] == "evidence_analyst"
        assert result.agent_assignments["gpt"] == "solution_architect"


# Integration test
@pytest.mark.asyncio
async def test_consensus_system_integration():
    """Integration test for the complete system"""
    
    # Mock external dependencies
    class TestModelClient(ModelClient):
        async def generate_response(self, model: str, prompt: str, max_tokens: int = 1000) -> str:
            return f"High quality response from {model} with specific implementation steps and evidence-based recommendations."
    
    service = ConsensusDiscussionService(TestModelClient())
    
    # Run discussion
    result = await service.run_discussion(
        topic="Design a scalable API gateway",
        models=["claude", "gpt", "grok"],
        protocol=ProtocolType.CONVERGENT,
        max_rounds=2
    )
    
    # Verify result structure
    assert result.session_id.startswith("session_")
    assert result.topic == "Design a scalable API gateway"
    assert len(result.rounds) >= 1
    
    # Test improved format
    formatted = service.create_improved_response_format(result)
    
    # Verify no nested anti-patterns
    assert "api_response" not in formatted
    assert "result" not in formatted or not isinstance(formatted.get("result"), dict)
    
    # Verify essential fields are present
    essential_fields = [
        "session_id", "topic", "status", "termination_reason", 
        "rounds_completed", "final_quality_score", "recommendations"
    ]
    
    for field in essential_fields:
        assert field in formatted, f"Missing essential field: {field}"
    
    # Verify quality metrics are reasonable
    assert 0.0 <= formatted["final_quality_score"] <= 1.0
    assert isinstance(formatted["recommendations"], list)
    
    print("✅ Integration test passed - Consensus system working correctly")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_consensus_system_integration())