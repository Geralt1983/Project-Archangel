"""
Consensus Discussion System
A complete refactoring of the consensus discussion system with proper architecture
"""

from .protocol_engine import (
    ConsensusEngine,
    ConsensusConfig,
    ConsensusResult,
    ProtocolType,
    TerminationReason,
    QualityMetrics,
    AgentResponse,
    QualityGate
)

from .agent_system import (
    AgentRoleRegistry,
    AgentAssignment,
    AgentRequirementValidator,
    AgentRole,
    AgentRequirement,
    AgentCapability,
    agent_role_registry
)

from .consensus_service import (
    ConsensusDiscussionService,
    ModelClient
)

__all__ = [
    # Protocol Engine
    'ConsensusEngine',
    'ConsensusConfig', 
    'ConsensusResult',
    'ProtocolType',
    'TerminationReason',
    'QualityMetrics',
    'AgentResponse',
    'QualityGate',
    
    # Agent System
    'AgentRoleRegistry',
    'AgentAssignment',
    'AgentRequirementValidator',
    'AgentRole',
    'AgentRequirement', 
    'AgentCapability',
    'agent_role_registry',
    
    # Service
    'ConsensusDiscussionService',
    'ModelClient'
]