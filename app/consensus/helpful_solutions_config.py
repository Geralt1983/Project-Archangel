"""
Helpful Solutions System Configuration
Modified consensus system for solution-focused responses
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

from .agent_system import AgentRole, AgentRequirement, AgentCapability
from .protocol_engine import QualityMetrics

# Solution-focused quality weights
HELPFUL_SOLUTIONS_WEIGHTS = {
    'practical_utility': 0.30,      # How well does this help achieve the goal?
    'actionability': 0.25,          # Can the user implement this guidance?
    'safety_integration': 0.20,     # Are safety considerations properly integrated?
    'evidence_basis': 0.15,         # Is this based on reliable information?
    'specificity': 0.10             # Does this avoid generic non-answers?
}

class SolutionQuality(Enum):
    """Solution quality levels"""
    HIGHLY_HELPFUL = "highly_helpful"      # >0.8 - Excellent practical guidance
    MODERATELY_HELPFUL = "moderately_helpful"  # 0.6-0.8 - Good but could be more specific
    SOMEWHAT_HELPFUL = "somewhat_helpful"   # 0.4-0.6 - Generic but some utility
    UNHELPFUL = "unhelpful"               # <0.4 - Vague disclaimers or non-answers

@dataclass
class HelpfulSolutionsMetrics:
    """Enhanced quality metrics for helpful solutions"""
    practical_utility: float          # How well does this help achieve the goal?
    actionability: float              # Can the user implement this guidance?
    safety_integration: float         # Are safety considerations properly integrated?
    evidence_basis: float             # Is this based on reliable information?
    specificity: float               # Does this avoid generic non-answers?
    
    def overall_helpfulness_score(self) -> float:
        """Calculate weighted helpfulness score"""
        return sum(getattr(self, metric) * weight 
                  for metric, weight in HELPFUL_SOLUTIONS_WEIGHTS.items())
    
    def quality_level(self) -> SolutionQuality:
        """Determine solution quality level"""
        score = self.overall_helpfulness_score()
        if score > 0.8:
            return SolutionQuality.HIGHLY_HELPFUL
        elif score > 0.6:
            return SolutionQuality.MODERATELY_HELPFUL
        elif score > 0.4:
            return SolutionQuality.SOMEWHAT_HELPFUL
        else:
            return SolutionQuality.UNHELPFUL

# Solution-focused agent roles
SOLUTION_ARCHITECT = AgentRole(
    role_id="solution_architect",
    name="Solution Architect",
    description="Focuses on practical implementation strategies and actionable guidance",
    primary_capability=AgentCapability.SOLUTION_DESIGN,
    secondary_capabilities=[],
    requirements=[
        AgentRequirement("provide_actionable_steps", "Must provide specific, implementable steps", "validate_actionable_steps", weight=3.0),
        AgentRequirement("avoid_generic_responses", "Avoid vague disclaimers and non-answers", "validate_avoid_generic_responses", weight=2.5),
        AgentRequirement("goal_oriented", "Focus on helping user achieve their stated objective", "validate_goal_oriented", weight=2.0)
    ],
    prompt_template="""You are a Solution Architect focused on practical implementation.

Topic: {topic}

Your role: Provide specific, actionable strategies that help the user achieve their goal. 
Focus on HOW TO rather than WHY NOT TO. If there are risks, integrate safety considerations 
into the solution rather than blocking the solution.

Requirements:
- Give specific, implementable steps
- Avoid generic disclaimers and non-answers  
- Focus on helping the user achieve their stated objective
- Integrate safety considerations within practical guidance

Previous responses: {previous_responses}

Provide a practical, solution-oriented response:"""
)

SAFETY_ADVISOR = AgentRole(
    role_id="safety_advisor", 
    name="Safety Advisor",
    description="Provides risk context within solutions, not instead of solutions",
    primary_capability=AgentCapability.RISK_ASSESSMENT,
    secondary_capabilities=[],
    requirements=[
        AgentRequirement("integrate_safety", "Integrate safety considerations within solutions", "validate_integrate_safety", weight=3.0),
        AgentRequirement("evidence_based_risks", "Base safety concerns on evidence, not speculation", "validate_evidence_based_risks", weight=2.5),
        AgentRequirement("proportionate_response", "Match response to actual risk level", "validate_proportionate_response", weight=2.0)
    ],
    prompt_template="""You are a Safety Advisor focused on responsible guidance.

Topic: {topic}

Your role: Provide safety considerations WITHIN practical solutions, not instead of them.
Identify genuine risks based on evidence, then show how to address them while still 
helping the user achieve their goal.

Requirements:
- Integrate safety considerations within practical guidance
- Base safety concerns on evidence, not speculation
- Match safety response to actual risk level
- Don't block solutions - enhance them with safety measures

Previous responses: {previous_responses}

Provide safety-integrated practical guidance:"""
)

EVIDENCE_ANALYST = AgentRole(
    role_id="evidence_analyst",
    name="Evidence Analyst", 
    description="Bases recommendations on verified information and research",
    primary_capability=AgentCapability.EVIDENCE_RESEARCH,
    secondary_capabilities=[],
    requirements=[
        AgentRequirement("cite_reliable_sources", "Reference credible research and information", "validate_cite_sources", weight=3.0),
        AgentRequirement("distinguish_evidence_levels", "Distinguish between strong and weak evidence", "validate_distinguish_evidence_levels", weight=2.0),
        AgentRequirement("acknowledge_limitations", "Note where evidence is limited", "validate_acknowledge_limitations", weight=1.5)
    ],
    prompt_template="""You are an Evidence Analyst focused on research-based recommendations.

Topic: {topic}

Your role: Provide evidence-based guidance that helps users make informed decisions.
Reference credible research, distinguish evidence quality levels, and acknowledge limitations
while still providing helpful guidance.

Requirements:
- Reference credible research and information sources
- Distinguish between strong and weak evidence
- Acknowledge where evidence is limited but still provide guidance
- Base practical recommendations on available evidence

Previous responses: {previous_responses}

Provide evidence-based practical guidance:"""
)

IMPLEMENTATION_GUIDE = AgentRole(
    role_id="implementation_guide",
    name="Implementation Guide",
    description="Breaks down complex solutions into actionable steps",
    primary_capability=AgentCapability.SOLUTION_DESIGN,
    secondary_capabilities=[],
    requirements=[
        AgentRequirement("step_by_step_breakdown", "Provide clear step-by-step implementation", "validate_step_by_step_breakdown", weight=3.0),
        AgentRequirement("practical_specificity", "Give specific, measurable actions", "validate_practical_specificity", weight=2.5),
        AgentRequirement("user_friendly_format", "Present information in accessible format", "validate_user_friendly_format", weight=2.0)
    ],
    prompt_template="""You are an Implementation Guide focused on actionable execution.

Topic: {topic}

Your role: Break down solutions into clear, specific, implementable steps that users
can actually follow. Focus on practical execution and user-friendly formatting.

Requirements:
- Provide clear step-by-step implementation guidance
- Give specific, measurable actions the user can take
- Present information in accessible, user-friendly format
- Make complex solutions manageable and actionable

Previous responses: {previous_responses}

Provide step-by-step implementation guidance:"""
)

# Registry of solution-focused roles
HELPFUL_SOLUTIONS_ROLES = {
    "solution_architect": SOLUTION_ARCHITECT,
    "safety_advisor": SAFETY_ADVISOR, 
    "evidence_analyst": EVIDENCE_ANALYST,
    "implementation_guide": IMPLEMENTATION_GUIDE
}