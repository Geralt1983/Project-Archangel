"""
Helpful Solutions System Demonstration
Shows how the system provides practical guidance instead of generic disclaimers
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.consensus.helpful_solutions_service import HelpfulSolutionsService
from app.consensus.consensus_service import ModelClient
from app.consensus.protocol_engine import ProtocolType

class DemoModelClient(ModelClient):
    """Demo client showing different response styles"""
    
    async def generate_response(self, model: str, prompt: str, max_tokens: int = 1000) -> str:
        # Extract topic from prompt
        topic_start = prompt.find("Topic: ") + 7
        topic_end = prompt.find("\n", topic_start)
        topic = prompt[topic_start:topic_end] if topic_start > 6 else "general query"
        
        if "solution_architect" in prompt:
            return self._generate_solution_architect_response(model, topic)
        elif "safety_advisor" in prompt:
            return self._generate_safety_advisor_response(model, topic)
        elif "evidence_analyst" in prompt:
            return self._generate_evidence_analyst_response(model, topic)
        elif "implementation_guide" in prompt:
            return self._generate_implementation_response(model, topic)
        else:
            return f"General response from {model} about {topic}"
    
    def _generate_solution_architect_response(self, model: str, topic: str) -> str:
        return """Strategic optimization approach for nicotine replacement therapy (NRT) and productivity:

**Implementation Framework:**
1. **Baseline Establishment**: Start with 7mg patch for consistent blood levels (6-8 hour onset, 16-24 hour duration)
2. **Strategic Enhancement**: Use 2mg gum for targeted focus periods (30-45 minute onset, 2-3 hour duration)
3. **Timing Protocol**: Gum 30 minutes before high-concentration tasks, maximum 4 pieces per day
4. **Productivity Tracking**: Monitor focus duration, task completion rates, and cognitive performance metrics

**Optimization Strategy:**
- Morning: Apply patch for baseline coverage
- Pre-focus sessions: 2mg gum for cognitive boost
- Afternoon: Second gum if needed for sustained performance
- Evening: Avoid gum 4+ hours before sleep to prevent insomnia

This approach leverages the pharmacokinetic profiles of both delivery methods for sustained baseline with targeted peaks."""
    
    def _generate_safety_advisor_response(self, model: str, topic: str) -> str:
        return """Safety-integrated NRT optimization with health monitoring:

**Safe Implementation Guidelines:**
1. **Maximum Limits**: Total daily nicotine should not exceed 14mg (7mg patch + max 8mg gum)
2. **Monitoring Protocol**: Track heart rate, sleep quality, and tolerance indicators daily
3. **Tolerance Management**: If effectiveness decreases, adjust timing rather than increasing dose
4. **Health Checkpoints**: Monitor for cardiovascular symptoms, sleep disruption, or dependency increases

**Risk Mitigation Strategies:**
- Start with lower gum frequency (2 pieces/day) to assess tolerance
- If experiencing side effects (nausea, headache, rapid heart rate), reduce gum usage first
- Maintain hydration (8+ glasses water) to support nicotine metabolism
- Schedule healthcare consultation if using for >12 weeks or experiencing adverse effects

**Safety Integration**: This approach maintains therapeutic benefits while minimizing health risks through systematic monitoring and graduated dosing."""
    
    def _generate_evidence_analyst_response(self, model: str, topic: str) -> str:
        return """Evidence-based analysis of NRT and cognitive performance:

**Research Foundation:**
- Meta-analysis by Heishman et al. (2010) shows nicotine improves attention and working memory in both smokers and non-smokers
- Pharmacokinetic studies indicate 7mg patches provide stable 10-15ng/ml plasma levels
- Gum provides rapid 5-10ng/ml peaks within 30 minutes (Benowitz et al., 2009)
- Productivity research shows optimal cognitive enhancement at 2-4mg nicotine doses (Newhouse et al., 2004)

**Evidence Quality:**
- Strong evidence: Nicotine's cognitive enhancement effects (Level 1 evidence, multiple RCTs)
- Moderate evidence: Optimal dosing for productivity (clinical studies, some individual variation)
- Limited evidence: Long-term cognitive benefits vs. tolerance (more research needed)

**Clinical Application:**
Based on available evidence, the 7mg patch + 2mg gum combination provides scientifically supported cognitive enhancement with established safety profiles when used within recommended limits."""
    
    def _generate_implementation_response(self, model: str, topic: str) -> str:
        return """Step-by-step implementation guide for NRT productivity optimization:

**Week 1-2: Baseline Establishment**
1. Day 1: Apply 7mg patch upon waking (upper arm/torso rotation)
2. Days 1-3: No gum - establish patch baseline and monitor effects
3. Days 4-7: Add 1 piece gum before most demanding daily task
4. Track: Energy levels, focus duration, sleep quality, side effects

**Week 3-4: Optimization Phase**
1. Identify 2-3 daily peak performance windows
2. Time gum intake 30 minutes before these periods
3. Maximum: 2 pieces gum per day, 4+ hours apart
4. Monitor: Task completion rates, cognitive performance, tolerance signs

**Daily Implementation Schedule:**
- 7:00 AM: Apply fresh patch, remove previous day's patch
- 9:30 AM: First gum piece (before morning focus session)
- 2:00 PM: Optional second piece (before afternoon tasks)
- 6:00 PM: No gum after this time to preserve sleep

**Tracking Metrics:**
- Focus session duration and quality (1-10 scale)
- Task completion percentage
- Sleep onset time and quality
- Side effects (headache, nausea, heart rate)

**Adjustment Protocol:** Week 5+, adjust timing and frequency based on tracked effectiveness data."""

async def demonstrate_helpful_solutions():
    """Demonstrate the helpful solutions system"""
    print("🔬 Helpful Solutions System Demonstration")
    print("=" * 50)
    
    # Create service with demo client
    demo_client = DemoModelClient()
    service = HelpfulSolutionsService(demo_client)
    
    # Example topic that would typically get disclaimer responses
    topic = "How to optimize 7mg nicotine patch usage with 2mg gum boosts for daily productivity while managing health considerations and tolerance"
    
    print(f"🎯 Topic: {topic}\n")
    
    # Run helpful solutions discussion
    result = await service.run_helpful_discussion(
        topic=topic,
        models=["claude", "gpt", "grok"],
        max_rounds=2,
        helpfulness_threshold=0.6,
        protocol=ProtocolType.DIVERGENT
    )
    
    # Create formatted response
    formatted_response = service.create_helpful_response_format(result)
    
    # Display results
    print("📊 HELPFUL SOLUTIONS ANALYSIS")
    print("-" * 30)
    
    if 'helpful_solutions_metrics' in formatted_response:
        metrics = formatted_response['helpful_solutions_metrics']
        print(f"Overall Helpfulness Score: {metrics['overall_helpfulness_score']:.3f}")
        print(f"Quality Level: {metrics['quality_level']}")
        print(f"Practical Utility: {metrics['practical_utility']:.3f}")
        print(f"Actionability: {metrics['actionability']:.3f}")
        print(f"Safety Integration: {metrics['safety_integration']:.3f}")
        print(f"Evidence Basis: {metrics['evidence_basis']:.3f}")
        print(f"Specificity: {metrics['specificity']:.3f}")
        
        print("\n🎯 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(formatted_response.get('helpful_recommendations', []), 1):
            print(f"{i}. {rec}")
    
    print(f"\n✅ Discussion Status: {formatted_response['status']}")
    print(f"📈 Rounds Completed: {formatted_response['rounds_completed']}")
    print(f"⚡ Termination Reason: {formatted_response['termination_reason']}")
    
    # Show example responses (first round)
    if formatted_response['rounds']:
        print(f"\n🗣️  SOLUTION-FOCUSED RESPONSES (Sample)")
        print("-" * 40)
        first_round = formatted_response['rounds'][0]
        for response in first_round['responses']:
            role = response['role']
            content = response['content'][:200] + "..." if len(response['content']) > 200 else response['content']
            print(f"\n{role.upper()}:")
            print(content)
    
    return formatted_response

if __name__ == "__main__":
    # Run the demonstration
    result = asyncio.run(demonstrate_helpful_solutions())
    print(f"\n🎉 Demonstration completed successfully!")
    print(f"System designed to provide practical solutions instead of generic disclaimers.")