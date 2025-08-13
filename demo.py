#!/usr/bin/env python3
"""
Demo script for Project Archangel - Intelligent Task Orchestrator

This script demonstrates the core functionality without requiring 
external services like ClickUp.
"""

from datetime import datetime, timezone, timedelta
from app.models import TaskIntake, Task
from app.triage import normalize_task_input, classify_task, fill_task_defaults
from app.scoring import compute_score
from app.subtasks import build_checklist_and_subtasks
from app.config import load_rules

def demo_task_processing():
    """Demonstrate the complete task processing pipeline."""
    print("🚀 Project Archangel Demo - Intelligent Task Orchestrator")
    print("=" * 60)
    
    # Sample tasks to process
    sample_tasks = [
        {
            "title": "ACME login system returning 500 errors",
            "description": "Users can't log in due to server errors",
            "client": "acme",
            "deadline": "2025-08-12T17:00:00Z",
            "importance": 5
        },
        {
            "title": "Generate monthly analytics dashboard for Meridian",
            "description": "Create comprehensive report with user metrics",
            "client": "meridian",
            "importance": 3
        },
        {
            "title": "[CLIENT_X] Setup new project access and permissions",
            "description": "Provision accounts for new team members",
            "client": "unknown",
            "importance": 2
        },
        {
            "title": "Update API documentation for v2 endpoints",
            "description": "Document recent changes to REST API",
            "client": "internal",
            "importance": 2
        }
    ]
    
    # Load rules
    rules = load_rules()
    print(f"\n📋 Loaded rules with {len(rules['task_types'])} task types and {len(rules['clients'])} clients")
    
    processed_tasks = []
    
    for i, task_data in enumerate(sample_tasks, 1):
        print(f"\n{'='*60}")
        print(f"🔄 Processing Task {i}: {task_data['title']}")
        print(f"{'='*60}")
        
        # Step 1: Convert to TaskIntake model
        if 'deadline' in task_data and task_data['deadline']:
            task_data['deadline'] = datetime.fromisoformat(task_data['deadline'].replace('Z', '+00:00'))
        
        task_intake = TaskIntake(**task_data)
        print(f"📝 Original: {task_intake.title} (client: {task_intake.client})")
        
        # Step 2: Normalize
        task = normalize_task_input(task_intake)
        print(f"🆔 Generated ID: {task.id}")
        
        # Step 3: Classify
        classify_task(task)
        print(f"🏷️  Classified as: {task.task_type}")
        print(f"👤 Client: {task.client}")
        
        # Step 4: Fill defaults
        fill_task_defaults(task)
        print(f"⚖️  Importance: {task.importance}/5")
        print(f"⏱️  Effort: {task.effort_hours}h")
        print(f"🏷️  Labels: {', '.join(task.labels)}")
        if task.client_sla_hours:
            print(f"📅 SLA: {task.client_sla_hours}h")
        
        # Step 5: Score
        score = compute_score(task, rules)
        task.score = score
        print(f"📊 Priority Score: {score:.3f}")
        
        # Step 6: Generate checklist and subtasks
        checklist, subtasks = build_checklist_and_subtasks(task, rules)
        task.checklist = checklist
        task.subtasks = subtasks
        
        print(f"\n✅ Checklist ({len(checklist)} items):")
        for item in checklist:
            print(f"   • {item}")
        
        print(f"\n📋 Subtasks ({len(subtasks)} items):")
        for subtask in subtasks:
            effort = f" ({subtask.effort_hours}h)" if subtask.effort_hours else ""
            print(f"   • {subtask.title}{effort}")
        
        processed_tasks.append(task)
        print("\n✅ Task processed successfully!")
    
    # Step 7: Show final prioritization
    print(f"\n{'='*60}")
    print("📊 FINAL PRIORITIZATION (by score)")
    print(f"{'='*60}")
    
    # Sort by score (higher = more priority)
    sorted_tasks = sorted(processed_tasks, key=lambda t: t.score or 0, reverse=True)
    
    for i, task in enumerate(sorted_tasks, 1):
        urgency_indicator = "🚨" if task.score and task.score > 0.7 else "⚠️" if task.score and task.score > 0.5 else "📝"
        deadline_str = f" (due: {task.deadline.strftime('%m/%d %H:%M')})" if task.deadline else ""
        print(f"{i}. {urgency_indicator} {task.title}")
        print(f"   Score: {task.score:.3f} | Type: {task.task_type} | Client: {task.client}{deadline_str}")
        print(f"   Effort: {task.effort_hours}h | Importance: {task.importance}/5")
        print()
    
    # Step 8: Simulate what would be sent to ClickUp
    print(f"{'='*60}")
    print("🔗 SIMULATED CLICKUP INTEGRATION")
    print(f"{'='*60}")
    
    for task in sorted_tasks[:2]:  # Show top 2 tasks
        print("\n📤 Would create in ClickUp:")
        print(f"   Title: {task.title}")
        print(f"   Description: {task.description}")
        print(f"   Tags: {', '.join(task.labels)}")
        print(f"   Priority: {_map_importance_to_priority(task.importance)}")
        if task.deadline:
            print(f"   Due Date: {task.deadline.isoformat()}")
        
        print(f"   📋 Would create {len(task.subtasks)} subtasks:")
        for subtask in task.subtasks:
            print(f"      • {subtask.title}")
        
        print(f"   ✅ Would add {len(task.checklist)} checklist items:")
        for item in task.checklist[:3]:  # Show first 3
            print(f"      • {item}")
        if len(task.checklist) > 3:
            print(f"      ... and {len(task.checklist) - 3} more")
    
    print(f"\n🎉 Demo complete! Processed {len(processed_tasks)} tasks successfully.")
    print("💡 In production, these would be automatically created in ClickUp/Trello/Todoist")

def _map_importance_to_priority(importance: int) -> str:
    """Map importance to ClickUp priority names."""
    mapping = {5: "Urgent", 4: "High", 3: "Normal", 2: "Low", 1: "Low"}
    return mapping.get(importance, "Normal")

def demo_scoring_details():
    """Show detailed scoring breakdown for a sample task."""
    print(f"\n{'='*60}")
    print("📊 DETAILED SCORING BREAKDOWN")
    print(f"{'='*60}")
    
    # Create a sample task with deadline pressure
    now = datetime.now(timezone.utc)
    task = Task(
        id="demo_score",
        title="Critical bug in payment system",
        description="Users can't complete purchases",
        client="meridian",
        task_type="bugfix",
        importance=5,
        effort_hours=3,
        deadline=now + timedelta(hours=6),  # 6 hours from now
        client_sla_hours=24,
        created_at=now - timedelta(hours=8),  # 8 hours old
        recent_progress=0.1  # Some progress made
    )
    
    rules = load_rules()
    
    print(f"Task: {task.title}")
    print(f"Client: {task.client} (SLA: {task.client_sla_hours}h)")
    print(f"Importance: {task.importance}/5")
    print(f"Effort: {task.effort_hours}h")
    print(f"Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"Progress: {task.recent_progress:.1%}")
    
    # Calculate score with breakdown
    from app.config import get_client_config
    
    client_config = get_client_config(task.client)
    scoring_config = rules.get("scoring", {})
    
    # Calculate individual components
    hours_to_deadline = (task.deadline - now).total_seconds() / 3600
    urgency = max(0, min(1, 1 - hours_to_deadline / 168))  # 168 hours = 1 week
    
    importance_bias = client_config.get("importance_bias", 1.0)
    importance = min(1.0, (task.importance / 5.0) * importance_bias)
    
    effort_factor = min(1.0, task.effort_hours / 8.0)
    
    hours_since_created = (now - task.created_at).total_seconds() / 3600
    freshness = max(0, min(1, 1 - hours_since_created / 168))
    
    hours_to_sla = task.client_sla_hours - hours_since_created
    sla_pressure = max(0, min(1, 1 - hours_to_sla / 72))
    
    recent_progress_inverse = 1 - task.recent_progress
    
    aging_boost = min(0.5, (hours_since_created / 24) * rules["defaults"]["aging_boost_per_day"] / 100)
    
    print("\n📊 Score Components:")
    print(f"   Urgency (deadline): {urgency:.3f} (weight: {scoring_config['urgency_weight']:.2f})")
    print(f"   Importance + bias: {importance:.3f} (weight: {scoring_config['importance_weight']:.2f})")
    print(f"   Effort factor: {effort_factor:.3f} (weight: {scoring_config['effort_weight']:.2f})")  
    print(f"   Freshness: {freshness:.3f} (weight: {scoring_config['freshness_weight']:.2f})")
    print(f"   SLA pressure: {sla_pressure:.3f} (weight: {scoring_config['sla_weight']:.2f})")
    print(f"   Progress inverse: {recent_progress_inverse:.3f} (weight: {scoring_config['progress_weight']:.2f})")
    print(f"   Aging boost: {aging_boost:.3f}")
    
    final_score = compute_score(task, rules)
    print(f"\n🎯 Final Score: {final_score:.3f}")
    
    if final_score > 0.8:
        print("🚨 CRITICAL PRIORITY - Immediate attention required!")
    elif final_score > 0.6:
        print("⚠️  HIGH PRIORITY - Should be worked on today")
    elif final_score > 0.4:
        print("📝 MEDIUM PRIORITY - Schedule within 2-3 days")
    else:
        print("📋 LOW PRIORITY - Can be scheduled later")

if __name__ == "__main__":
    demo_task_processing()
    demo_scoring_details()