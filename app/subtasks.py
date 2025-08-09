from typing import List, Tuple, Dict, Any
from .models import Task, Subtask
from .config import load_rules, get_task_type_config

def build_checklist_and_subtasks(task: Task, rules: Dict[str, Any] = None) -> Tuple[List[str], List[Subtask]]:
    """
    Generate checklist items and subtasks based on task type templates.
    
    Returns:
        Tuple of (checklist_items, subtasks)
    """
    if rules is None:
        rules = load_rules()
    
    task_type_config = get_task_type_config(task.task_type)
    
    # Get checklist template
    checklist_template = task_type_config.get("checklist", [])
    checklist = expand_template_strings(checklist_template, task)
    
    # Get subtasks template
    subtasks_template = task_type_config.get("subtasks", [])
    subtasks = []
    
    for subtask_config in subtasks_template:
        subtask_title = expand_template_string(subtask_config["title"], task)
        
        subtask = Subtask(
            title=subtask_title,
            effort_hours=subtask_config.get("effort_hours"),
            deadline=subtask_config.get("deadline"),
            assignee=subtask_config.get("assignee")
        )
        
        subtasks.append(subtask)
    
    return checklist, subtasks

def expand_template_strings(templates: List[str], task: Task) -> List[str]:
    """Expand template strings with task context."""
    expanded = []
    for template in templates:
        expanded.append(expand_template_string(template, task))
    return expanded

def expand_template_string(template: str, task: Task) -> str:
    """
    Expand a template string with task variables.
    
    Available variables:
    - {client}: Client name
    - {task_type}: Task type
    - {title}: Task title
    - {project}: Project name (if available)
    """
    variables = {
        "client": task.client,
        "task_type": task.task_type or "general",
        "title": task.title,
        "project": task.project or "Default",
    }
    
    try:
        return template.format(**variables)
    except KeyError:
        # If template has variables we don't support, return as-is
        return template

def generate_context_aware_subtasks(task: Task) -> List[Subtask]:
    """
    Generate subtasks with context-aware naming and effort estimation.
    This is a more advanced version that could use ML or complex rules.
    """
    base_checklist, base_subtasks = build_checklist_and_subtasks(task)
    
    # Add context-specific adjustments
    if task.task_type == "bugfix":
        # For bugs, add urgency-based subtasks
        if task.importance >= 4:
            urgent_subtask = Subtask(
                title=f"Urgent: Hotfix for {task.title}",
                effort_hours=0.5
            )
            base_subtasks.insert(0, urgent_subtask)
    
    elif task.task_type == "report":
        # For reports, add client-specific review
        if task.client != "unknown":
            review_subtask = Subtask(
                title=f"Client review with {task.client}",
                effort_hours=0.25
            )
            base_subtasks.append(review_subtask)
    
    return base_subtasks

def estimate_subtask_effort(task: Task, subtask: Subtask) -> float:
    """
    Estimate effort for a subtask based on task context.
    This could be enhanced with ML models trained on historical data.
    """
    base_effort = subtask.effort_hours or 1.0
    
    # Adjust based on task complexity
    complexity_multiplier = 1.0
    
    if task.task_type == "bugfix" and task.importance >= 4:
        complexity_multiplier = 1.5  # Urgent bugs take longer
    elif task.task_type == "report" and task.effort_hours and task.effort_hours > 4:
        complexity_multiplier = 1.2  # Large reports need more review
    
    # Adjust based on client
    if task.client in ["acme", "meridian"]:  # High-touch clients
        complexity_multiplier *= 1.1
    
    return base_effort * complexity_multiplier