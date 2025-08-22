"""
Semantic Agent Role System
Defines specialized agent roles with specific requirements and capabilities
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


class AgentCapability(Enum):
    ANALYSIS = "analysis"
    SOLUTION_DESIGN = "solution_design"
    RISK_ASSESSMENT = "risk_assessment"
    EVIDENCE_RESEARCH = "evidence_research"
    IMPLEMENTATION = "implementation"
    QUALITY_VALIDATION = "quality_validation"


@dataclass
class AgentRequirement:
    """Specific requirement for an agent response"""
    name: str
    description: str
    validator: str  # Function name to validate this requirement
    weight: float = 1.0  # Importance weight


@dataclass
class AgentRole:
    """Defines a semantic role for an agent"""
    role_id: str
    name: str
    description: str
    primary_capability: AgentCapability
    secondary_capabilities: List[AgentCapability]
    requirements: List[AgentRequirement]
    prompt_template: str
    expected_model: Optional[str] = None


class AgentRequirementValidator:
    """Validates agent responses against their role requirements"""
    
    def __init__(self):
        self.logger = logger.bind(component="agent_validator")
    
    def validate_cite_sources(self, response: str) -> float:
        """Validate that response cites sources or evidence"""
        source_indicators = [
            "according to", "research shows", "studies indicate",
            "evidence suggests", "data shows", "report states",
            "study found", "research indicates", "source:",
            "reference:", "citation:", "see:", "cf."
        ]
        
        response_lower = response.lower()
        citations_found = sum(1 for indicator in source_indicators 
                            if indicator in response_lower)
        
        # Score based on number of citations found
        return min(citations_found / 2, 1.0)
    
    def validate_avoid_generic_responses(self, response: str) -> float:
        """Validate that response avoids generic/template language"""
        generic_phrases = [
            "it depends", "there are many factors", "this is complex",
            "it's important to", "you should consider", "there are pros and cons",
            "on the one hand", "it varies", "in general", "typically",
            "usually", "often", "sometimes", "it's complicated"
        ]
        
        response_lower = response.lower()
        generic_count = sum(1 for phrase in generic_phrases 
                          if phrase in response_lower)
        
        # Penalize generic language
        penalty = min(generic_count / len(generic_phrases), 0.5)
        return max(1.0 - penalty, 0.0)
    
    def validate_actionable_steps(self, response: str) -> float:
        """Validate that response contains actionable steps"""
        action_indicators = [
            "step 1", "first,", "1.", "next,", "then,", "finally,",
            "implement", "create", "build", "setup", "configure",
            "install", "run", "execute", "test", "deploy",
            "should:", "must:", "need to:", "action:"
        ]
        
        response_lower = response.lower()
        actions_found = sum(1 for indicator in action_indicators 
                          if indicator in response_lower)
        
        return min(actions_found / 3, 1.0)
    
    def validate_implementation_details(self, response: str) -> float:
        """Validate that response includes implementation specifics"""
        detail_indicators = [
            "function", "class", "method", "code", "syntax",
            "library", "framework", "api", "endpoint", "database",
            "config", "file", "directory", "command", "script",
            "example:", "code:", "```", "implementation:"
        ]
        
        response_lower = response.lower()
        details_found = sum(1 for indicator in detail_indicators 
                          if indicator in response_lower)
        
        return min(details_found / 4, 1.0)
    
    def validate_specific_risks(self, response: str) -> float:
        """Validate that response identifies specific risks"""
        risk_indicators = [
            "risk:", "danger:", "warning:", "caution:", "issue:",
            "problem:", "vulnerability:", "threat:", "concern:",
            "limitation:", "drawback:", "downside:", "pitfall:",
            "could fail", "might break", "potential issue"
        ]
        
        response_lower = response.lower()
        risks_found = sum(1 for indicator in risk_indicators 
                        if indicator in response_lower)
        
        return min(risks_found / 2, 1.0)
    
    def validate_mitigation_strategies(self, response: str) -> float:
        """Validate that response includes mitigation strategies"""
        mitigation_indicators = [
            "mitigation:", "solution:", "prevention:", "workaround:",
            "alternative:", "backup plan:", "fallback:", "contingency:",
            "to prevent", "to avoid", "to mitigate", "to reduce",
            "instead", "alternatively", "however", "but"
        ]
        
        response_lower = response.lower()
        mitigations_found = sum(1 for indicator in mitigation_indicators 
                              if indicator in response_lower)
        
        return min(mitigations_found / 2, 1.0)
    
    def validate_response(self, response: str, requirements: List[AgentRequirement]) -> Dict[str, float]:
        """Validate response against all requirements"""
        scores = {}
        
        for requirement in requirements:
            validator_method = getattr(self, requirement.validator, None)
            if validator_method:
                try:
                    score = validator_method(response)
                    scores[requirement.name] = score
                except (AttributeError, ValueError, TypeError) as e:
                    self.logger.warning(f"Validation failed for {requirement.name}: {e}")
                    scores[requirement.name] = 0.0
                except Exception as e:
                    self.logger.error(f"Unexpected validation error for {requirement.name}: {e}", exc_info=True)
                    scores[requirement.name] = 0.0
            else:
                self.logger.warning(f"Unknown validator: {requirement.validator}")
                scores[requirement.name] = 0.0
        
        return scores


class AgentRoleRegistry:
    """Registry of available agent roles"""
    
    def __init__(self):
        self.roles: Dict[str, AgentRole] = {}
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize standard agent roles"""
        
        # Evidence Analyst Role
        evidence_analyst = AgentRole(
            role_id="evidence_analyst",
            name="Evidence Analyst",
            description="Provides evidence-based analysis with citations and research",
            primary_capability=AgentCapability.ANALYSIS,
            secondary_capabilities=[AgentCapability.EVIDENCE_RESEARCH],
            requirements=[
                AgentRequirement(
                    "cite_sources", 
                    "Must cite sources, research, or evidence",
                    "validate_cite_sources",
                    weight=2.0
                ),
                AgentRequirement(
                    "avoid_generic", 
                    "Must avoid generic or template responses",
                    "validate_avoid_generic_responses", 
                    weight=1.5
                )
            ],
            prompt_template="""You are an Evidence Analyst. Provide fact-based analysis supported by research, data, or credible sources. 

Requirements:
- Cite specific sources, studies, or evidence
- Avoid generic statements like "it depends" or "there are many factors"
- Provide concrete findings and data points
- Reference credible research when available

Topic: {topic}

Provide your evidence-based analysis:""",
            expected_model="claude"
        )
        
        # Solution Architect Role
        solution_architect = AgentRole(
            role_id="solution_architect",
            name="Solution Architect", 
            description="Designs practical, actionable solutions with implementation details",
            primary_capability=AgentCapability.SOLUTION_DESIGN,
            secondary_capabilities=[AgentCapability.IMPLEMENTATION],
            requirements=[
                AgentRequirement(
                    "actionable_steps",
                    "Must provide specific, actionable steps",
                    "validate_actionable_steps",
                    weight=2.0
                ),
                AgentRequirement(
                    "implementation_details",
                    "Must include implementation specifics",
                    "validate_implementation_details",
                    weight=1.8
                ),
                AgentRequirement(
                    "avoid_generic",
                    "Must avoid generic responses",
                    "validate_avoid_generic_responses",
                    weight=1.2
                )
            ],
            prompt_template="""You are a Solution Architect. Design practical, implementable solutions with specific steps and technical details.

Requirements:
- Provide numbered, actionable steps
- Include specific implementation details (code, tools, configurations)
- Avoid vague recommendations like "you should consider"
- Focus on concrete, practical solutions

Topic: {topic}

Design your solution:""",
            expected_model="gpt"
        )
        
        # Risk Assessor Role
        risk_assessor = AgentRole(
            role_id="risk_assessor", 
            name="Risk Assessor",
            description="Identifies specific risks, limitations, and mitigation strategies",
            primary_capability=AgentCapability.RISK_ASSESSMENT,
            secondary_capabilities=[AgentCapability.ANALYSIS],
            requirements=[
                AgentRequirement(
                    "specific_risks",
                    "Must identify specific risks and limitations", 
                    "validate_specific_risks",
                    weight=2.0
                ),
                AgentRequirement(
                    "mitigation_strategies",
                    "Must provide concrete mitigation strategies",
                    "validate_mitigation_strategies", 
                    weight=1.8
                ),
                AgentRequirement(
                    "avoid_generic",
                    "Must avoid generic risk statements",
                    "validate_avoid_generic_responses",
                    weight=1.0
                )
            ],
            prompt_template="""You are a Risk Assessor. Identify specific risks, potential failures, and provide concrete mitigation strategies.

Requirements:
- Identify specific, concrete risks (not generic warnings)
- Explain potential failure modes and their impact
- Provide actionable mitigation strategies for each risk
- Avoid vague statements like "there are risks involved"

Topic: {topic}

Assess the risks and provide mitigation strategies:""",
            expected_model="grok"
        )
        
        # Quality Validator Role
        quality_validator = AgentRole(
            role_id="quality_validator",
            name="Quality Validator",
            description="Validates solutions for completeness, correctness, and quality",
            primary_capability=AgentCapability.QUALITY_VALIDATION,
            secondary_capabilities=[AgentCapability.ANALYSIS],
            requirements=[
                AgentRequirement(
                    "specific_criteria",
                    "Must use specific quality criteria",
                    "validate_specific_risks",  # Reuse validator for specificity
                    weight=1.8
                ),
                AgentRequirement(
                    "actionable_improvements",
                    "Must suggest actionable improvements",
                    "validate_actionable_steps",
                    weight=1.5
                )
            ],
            prompt_template="""You are a Quality Validator. Evaluate the proposed solution for completeness, correctness, and quality.

Requirements:
- Use specific quality criteria (functionality, security, performance, maintainability)
- Identify gaps or weaknesses in the solution
- Suggest specific improvements with actionable steps
- Validate that the solution addresses the original requirements

Topic: {topic}
Previous responses to validate: {previous_responses}

Provide your quality assessment:""",
            expected_model="claude"
        )
        
        # Register all roles
        for role in [evidence_analyst, solution_architect, risk_assessor, quality_validator]:
            self.register_role(role)
    
    def register_role(self, role: AgentRole):
        """Register a new agent role"""
        self.roles[role.role_id] = role
        logger.info("Registered agent role", role_id=role.role_id, name=role.name)
    
    def get_role(self, role_id: str) -> Optional[AgentRole]:
        """Get agent role by ID"""
        return self.roles.get(role_id)
    
    def list_roles(self) -> List[AgentRole]:
        """List all available roles"""
        return list(self.roles.values())
    
    def get_roles_by_capability(self, capability: AgentCapability) -> List[AgentRole]:
        """Get roles that have specific capability"""
        return [
            role for role in self.roles.values()
            if capability in [role.primary_capability] + role.secondary_capabilities
        ]


class AgentAssignment:
    """Manages assignment of roles to models"""
    
    def __init__(self, role_registry: AgentRoleRegistry):
        self.role_registry = role_registry
        self.logger = logger.bind(component="agent_assignment")
    
    def create_balanced_assignment(self, 
                                 available_models: List[str],
                                 required_capabilities: List[AgentCapability]) -> Dict[str, AgentRole]:
        """Create balanced role assignment for available models"""
        
        assignments = {}
        
        # Get roles that match required capabilities
        candidate_roles = []
        for capability in required_capabilities:
            candidate_roles.extend(self.role_registry.get_roles_by_capability(capability))
        
        # Remove duplicates while preserving order
        unique_roles = []
        seen = set()
        for role in candidate_roles:
            if role.role_id not in seen:
                unique_roles.append(role)
                seen.add(role.role_id)
        
        # Assign roles to models
        for i, model in enumerate(available_models):
            if i < len(unique_roles):
                role = unique_roles[i]
                # Check if role has model preference
                if role.expected_model and role.expected_model != model:
                    self.logger.info("Role assigned to non-preferred model", 
                                   role=role.role_id, preferred=role.expected_model, assigned=model)
                
                assignments[model] = role
            else:
                # If more models than roles, assign fallback role
                fallback_role = self.role_registry.get_role("evidence_analyst")
                if fallback_role:
                    assignments[model] = fallback_role
        
        self.logger.info("Created agent assignments", 
                        assignments={k: v.role_id for k, v in assignments.items()})
        
        return assignments
    
    def create_custom_assignment(self, model_role_mapping: Dict[str, str]) -> Dict[str, AgentRole]:
        """Create custom assignment from model -> role_id mapping"""
        assignments = {}
        
        for model, role_id in model_role_mapping.items():
            role = self.role_registry.get_role(role_id)
            if role:
                assignments[model] = role
            else:
                self.logger.warning("Unknown role ID", role_id=role_id, model=model)
        
        return assignments


# Initialize global registry
agent_role_registry = AgentRoleRegistry()