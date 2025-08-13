#!/usr/bin/env python3
"""
Simplified demo for Project Archangel - without database dependencies

This script demonstrates the core functionality without requiring 
external libraries beyond pydantic and pyyaml.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from datetime import datetime, timezone
from app.models import TaskIntake, Task
from app.config import load_rules, get_task_type_config, get_client_config

def normalize_task_input(task_input: TaskIntake) -> Task:
    """Convert TaskIntake to full Task model with generated ID."""
    import uuid
    
    task_id = f"tsk_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"{task_input.source}_{hash(task_input.title)}_{task_input.client}"
    now = datetime.now(timezone.utc)
    
    return Task(
        id=task_id,
        title=task_input.title.strip(),
        description=task_input.description.strip() if task_input.description else "",
        client=task_input.client.lower().strip(),
        project=task_input.project,
        deadline=task_input.deadline,
        importance=task_input.importance,
        effort_hours=task_input.effort_hours,
        labels=task_input.labels.copy(),
        source=task_input.source,
        meta=task_input.meta.copy(),
        created_at=now,
        updated_at=now,
        idempotency_key=idempotency_key,
        recent_progress=0.0
    )

def classify_task(task: Task) -> None:
    """Classify task type based on title and description content."""
    title_lower = task.title.lower()
    description_lower = (task.description or "").lower()
    combined_text = f"{title_lower} {description_lower}"
    
    # Check for explicit client prefix in title like [ACME]
    if task.client == "unknown":
        import re
        client_match = re.search(r'\[(\w+)\]', task.title)
        if client_match:
            task.client = client_match.group(1).lower()
            # Remove client prefix from title
            task.title = re.sub(r'\[\w+\]\s*', '', task.title).strip()
    
    # Classify task type
    if any(keyword in combined_text for keyword in ["fix", "error", "fail", "bug", "500", "broken", "crash"]):
        task.task_type = "bugfix"
    elif any(keyword in combined_text for keyword in ["report", "analysis", "dashboard", "metrics", "data"]):
        task.task_type = "report"
    elif any(keyword in combined_text for keyword in ["setup", "onboard", "access", "provision", "install", "configure"]):
        task.task_type = "onboarding"
    else:
        task.task_type = "general"

def fill_task_defaults(task: Task) -> None:
    """Fill in default values based on task type and client configuration."""
    task_type_config = get_task_type_config(task.task_type)
    client_config = get_client_config(task.client)
    
    # Set default effort hours if not provided
    if not task.effort_hours:
        task.effort_hours = task_type_config.get("default_effort_hours", 2.0)
    
    # Set default importance if not provided or invalid
    if not task.importance or task.importance < 1 or task.importance > 5:
        task.importance = task_type_config.get("importance", 3)
    
    # Add task type labels
    task_type_labels = task_type_config.get("labels", [])
    task.labels.extend([label for label in task_type_labels if label not in task.labels])
    
    # Set client SLA hours
    if not task.client_sla_hours:
        task.client_sla_hours = client_config.get("sla_hours", 72)

def compute_score(task: Task, rules=None) -> float:
    """Compute priority score for a task using weighted formula."""
    if rules is None:
        rules = load_rules()
    
    scoring_config = rules.get("scoring", {})
    weights = {
        "urgency": scoring_config.get("urgency_weight", 0.30),
        "importance": scoring_config.get("importance_weight", 0.25),
        "effort": scoring_config.get("effort_weight", 0.15),
        "freshness": scoring_config.get("freshness_weight", 0.10),
        "sla": scoring_config.get("sla_weight", 0.15),
        "progress": scoring_config.get("progress_weight", 0.05),
    }
    
    now = datetime.now(timezone.utc)
    
    # 1. Urgency: higher score for closer deadlines
    urgency = 0.0
    if task.deadline:
        if task.deadline.tzinfo is None:
            deadline = task.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline = task.deadline
        
        hours_to_deadline = (deadline - now).total_seconds() / 3600
        urgency = max(0, min(1, 1 - hours_to_deadline / 168))  # 168 hours = 1 week
    
    # 2. Importance: normalize and apply client bias
    client_config = get_client_config(task.client)
    importance_bias = client_config.get("importance_bias", 1.0)
    importance = (task.importance / 5.0) * importance_bias
    importance = min(importance, 1.0)  # Cap at 1.0
    
    # 3. Effort factor: prefer smaller tasks (inverted)
    effort_hours = task.effort_hours or 1.0
    effort_factor = min(effort_hours / 8.0, 1.0)  # Normalize to 8-hour workday
    
    # 4. Freshness: newer tasks get higher scores
    if task.created_at.tzinfo is None:
        created_at = task.created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = task.created_at
    
    hours_since_created = (now - created_at).total_seconds() / 3600
    freshness = max(0, min(1, 1 - hours_since_created / 168))  # 168 hours = 1 week
    
    # 5. SLA pressure: higher score when approaching SLA
    sla_pressure = 0.0
    client_sla_hours = task.client_sla_hours or client_config.get("sla_hours", 72)
    if client_sla_hours:
        hours_to_sla = client_sla_hours - hours_since_created
        sla_pressure = max(0, min(1, 1 - hours_to_sla / 72))  # 72 hours warning window
    
    # 6. Recent progress: boost stalled tasks
    recent_progress_inverse = max(0, min(1, 1 - task.recent_progress))
    
    # Apply aging boost
    defaults = rules.get("defaults", {})
    aging_boost_per_day = defaults.get("aging_boost_per_day", 2)
    days_since_created = hours_since_created / 24
    aging_boost = min(days_since_created * aging_boost_per_day / 100, 0.5)  # Cap at 50% boost
    
    # Calculate weighted score
    score = (
        weights["urgency"] * urgency +
        weights["importance"] * importance +
        weights["effort"] * effort_factor +
        weights["freshness"] * freshness +
        weights["sla"] * sla_pressure +
        weights["progress"] * recent_progress_inverse +
        aging_boost
    )
    
    return min(score, 1.0)  # Cap at 1.0

def build_checklist_and_subtasks(task: Task, rules=None):
    """Generate checklist items and subtasks based on task type templates."""
    if rules is None:
        rules = load_rules()
    
    task_type_config = get_task_type_config(task.task_type)
    
    # Get checklist template
    checklist_template = task_type_config.get("checklist", [])
    checklist = checklist_template.copy()
    
    # Get subtasks template
    subtasks_template = task_type_config.get("subtasks", [])
    subtasks = []
    
    from app.models import Subtask
    for subtask_config in subtasks_template:
        subtask = Subtask(
            title=subtask_config["title"],
            effort_hours=subtask_config.get("effort_hours"),
            deadline=subtask_config.get("deadline"),
            assignee=subtask_config.get("assignee")
        )
        subtasks.append(subtask)
    
    return checklist, subtasks

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
    
    print(f"\n🎉 Demo complete! Processed {len(processed_tasks)} tasks successfully.")
    print("💡 In production, these would be automatically created in ClickUp/Trello/Todoist")

if __name__ == "__main__":
    demo_task_processing()