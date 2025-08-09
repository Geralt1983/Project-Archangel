import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .models import Task
from .db import fetch_open_tasks, fetch_tasks_by_client, save_task, log_audit_event
from .providers.clickup import ClickUpAdapter
from .providers.base import ProviderAdapter
from .scoring import compute_score, is_task_stale, is_sla_at_risk
from .config import load_rules, get_client_config

def get_provider_adapter() -> ProviderAdapter:
    """Get the configured provider adapter."""
    return ClickUpAdapter(
        token=os.getenv("CLICKUP_TOKEN", ""),
        team_id=os.getenv("CLICKUP_TEAM_ID", ""),
        list_id=os.getenv("CLICKUP_LIST_ID", ""),
        webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET", "")
    )

def daily_reevaluation():
    """
    Daily job to re-evaluate all open tasks:
    - Recalculate scores
    - Check for stale tasks
    - Check SLA at-risk tasks
    - Send notifications
    """
    print(f"[{datetime.now()}] Starting daily reevaluation...")
    
    rules = load_rules()
    adapter = get_provider_adapter()
    
    try:
        open_tasks = fetch_open_tasks()
        stale_tasks = []
        sla_risk_tasks = []
        updated_count = 0
        
        for task in open_tasks:
            # Recalculate score
            old_score = task.score
            task.score = compute_score(task, rules)
            
            # Check if task is stale
            if is_task_stale(task, rules):
                stale_tasks.append(task)
            
            # Check SLA risk
            if is_sla_at_risk(task, rules):
                sla_risk_tasks.append(task)
                # Update status to at-risk if not already done
                if task.status.value not in ["blocked", "done"]:
                    try:
                        adapter.update_status(task.external_id, "blocked")  # Use blocked as "at-risk"
                        task.status = "blocked"
                    except Exception as e:
                        print(f"Failed to update task {task.id} status: {e}")
            
            # Save if score changed significantly
            if abs((task.score or 0) - (old_score or 0)) > 0.05:
                save_task(task)
                updated_count += 1
        
        # Log the reevaluation
        log_audit_event(
            event_type="daily_reevaluation",
            data={
                "tasks_processed": len(open_tasks),
                "tasks_updated": updated_count,
                "stale_tasks": len(stale_tasks),
                "sla_risk_tasks": len(sla_risk_tasks)
            }
        )
        
        # Send notifications for stale and at-risk tasks
        if stale_tasks or sla_risk_tasks:
            send_task_notifications(stale_tasks, sla_risk_tasks)
        
        print(f"Daily reevaluation complete: {updated_count} tasks updated, "
              f"{len(stale_tasks)} stale, {len(sla_risk_tasks)} at SLA risk")
        
    except Exception as e:
        print(f"Daily reevaluation failed: {e}")
        log_audit_event(
            event_type="daily_reevaluation_failed",
            data={"error": str(e)}
        )

def weekly_checkin():
    """
    Weekly job to generate summary reports:
    - Tasks completed per client
    - Average completion time
    - Upcoming deadlines
    - Capacity utilization
    """
    print(f"[{datetime.now()}] Starting weekly check-in...")
    
    try:
        # Get date range for the past week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        rules = load_rules()
        clients = rules.get("clients", {})
        
        weekly_report = {
            "week_ending": end_date.isoformat(),
            "clients": {}
        }
        
        for client_name in clients.keys():
            if client_name == "unknown":
                continue
                
            tasks = fetch_tasks_by_client(client_name)
            
            # Filter to tasks from this week
            week_tasks = [
                t for t in tasks 
                if t.created_at >= start_date or t.updated_at >= start_date
            ]
            
            completed_tasks = [t for t in week_tasks if t.status.value == "done"]
            open_tasks = [t for t in week_tasks if t.status.value != "done"]
            
            # Calculate metrics
            client_config = get_client_config(client_name)
            daily_cap = client_config.get("daily_cap_hours", 4)
            
            total_effort_completed = sum(t.effort_hours or 0 for t in completed_tasks)
            total_effort_planned = sum(t.effort_hours or 0 for t in week_tasks)
            
            weekly_report["clients"][client_name] = {
                "tasks_completed": len(completed_tasks),
                "tasks_in_progress": len(open_tasks),
                "effort_hours_completed": total_effort_completed,
                "effort_hours_planned": total_effort_planned,
                "daily_capacity_hours": daily_cap,
                "utilization_pct": (total_effort_completed / (daily_cap * 7)) * 100 if daily_cap > 0 else 0,
                "upcoming_deadlines": [
                    {"title": t.title, "deadline": t.deadline.isoformat()}
                    for t in open_tasks 
                    if t.deadline and t.deadline <= end_date + timedelta(days=7)
                ]
            }
        
        # Log the weekly report
        log_audit_event(
            event_type="weekly_checkin",
            data=weekly_report
        )
        
        # Send report (could be email, Slack, etc.)
        send_weekly_report(weekly_report)
        
        print("Weekly check-in complete")
        
    except Exception as e:
        print(f"Weekly check-in failed: {e}")
        log_audit_event(
            event_type="weekly_checkin_failed",
            data={"error": str(e)}
        )

def rebalance_tasks(dry_run: bool = False, client_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Load balancing algorithm:
    1. Get daily capacity per client
    2. Sort tasks by score
    3. Distribute fairly while respecting caps
    4. Handle urgent tasks that exceed caps
    """
    print(f"[{datetime.now()}] Starting task rebalancing (dry_run={dry_run})")
    
    rules = load_rules()
    clients_config = rules.get("clients", {})
    
    # Get all open tasks
    open_tasks = fetch_open_tasks()
    
    if client_filter:
        open_tasks = [t for t in open_tasks if t.client == client_filter]
    
    # Sort by score (higher scores = higher priority)
    open_tasks.sort(key=lambda t: t.score or 0, reverse=True)
    
    # Initialize client allocations
    client_allocations = {}
    for client_name, config in clients_config.items():
        if client_name == "unknown":
            continue
        client_allocations[client_name] = {
            "daily_cap": config.get("daily_cap_hours", 4),
            "allocated": 0.0,
            "tasks": []
        }
    
    # Distribute tasks
    planned_tasks = []
    overflowed_tasks = []
    
    for task in open_tasks:
        client = task.client
        effort = task.effort_hours or 1.0
        
        # Check for urgent override (SLA risk or close deadline)
        is_urgent = (
            is_sla_at_risk(task, rules) or
            (task.deadline and task.deadline <= datetime.now() + timedelta(hours=24))
        )
        
        # Allocate to client if within capacity or urgent
        if client in client_allocations:
            allocation = client_allocations[client]
            
            if allocation["allocated"] + effort <= allocation["daily_cap"] or is_urgent:
                allocation["allocated"] += effort
                allocation["tasks"].append(task)
                planned_tasks.append(task)
                
                if is_urgent:
                    task.meta["urgent_override"] = True
            else:
                overflowed_tasks.append(task)
        else:
            # Unknown client - add to overflow
            overflowed_tasks.append(task)
    
    # Update task metadata with planning info
    if not dry_run:
        for task in planned_tasks:
            task.meta["planned_today"] = datetime.now().isoformat()
            save_task(task)
    
    # Create result summary
    result = {
        "dry_run": dry_run,
        "total_tasks": len(open_tasks),
        "planned_tasks": len(planned_tasks),
        "overflow_tasks": len(overflowed_tasks),
        "client_allocations": {
            name: {
                "tasks_count": len(alloc["tasks"]),
                "effort_allocated": alloc["allocated"],
                "daily_cap": alloc["daily_cap"],
                "utilization_pct": (alloc["allocated"] / alloc["daily_cap"]) * 100 if alloc["daily_cap"] > 0 else 0
            }
            for name, alloc in client_allocations.items()
        }
    }
    
    # Log the rebalancing
    log_audit_event(
        event_type="task_rebalancing",
        data=result
    )
    
    print(f"Rebalancing complete: {len(planned_tasks)} planned, {len(overflowed_tasks)} overflow")
    
    return result

def send_task_notifications(stale_tasks: List[Task], sla_risk_tasks: List[Task]):
    """Send notifications for stale and at-risk tasks."""
    # This is a placeholder - implement actual notification logic
    # Could send to Slack, email, etc.
    
    if stale_tasks:
        print(f"NOTIFICATION: {len(stale_tasks)} stale tasks need attention")
        for task in stale_tasks[:5]:  # Show first 5
            print(f"  - {task.title} (client: {task.client}, age: {task.created_at})")
    
    if sla_risk_tasks:
        print(f"ALERT: {len(sla_risk_tasks)} tasks at SLA risk!")
        for task in sla_risk_tasks:
            print(f"  - {task.title} (client: {task.client}, SLA: {task.client_sla_hours}h)")

def send_weekly_report(report: Dict[str, Any]):
    """Send weekly report summary."""
    # This is a placeholder - implement actual report sending
    print("WEEKLY REPORT:")
    print(f"Week ending: {report['week_ending']}")
    
    for client, metrics in report["clients"].items():
        print(f"\n{client.upper()}:")
        print(f"  Completed: {metrics['tasks_completed']} tasks")
        print(f"  Effort: {metrics['effort_hours_completed']:.1f}h")
        print(f"  Utilization: {metrics['utilization_pct']:.1f}%")
        
        if metrics["upcoming_deadlines"]:
            print("  Upcoming deadlines:")
            for deadline in metrics["upcoming_deadlines"][:3]:
                print(f"    - {deadline['title']} ({deadline['deadline']})")

def main():
    """Main scheduler entry point."""
    scheduler = BlockingScheduler()
    
    # Daily reevaluation at 9 AM
    scheduler.add_job(
        daily_reevaluation,
        CronTrigger(hour=9, minute=0),
        id="daily_reevaluation"
    )
    
    # Weekly check-in on Mondays at 10 AM
    scheduler.add_job(
        weekly_checkin,
        CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="weekly_checkin"
    )
    
    print("Scheduler starting...")
    print("Jobs scheduled:")
    print("  - Daily reevaluation: 9:00 AM")
    print("  - Weekly check-in: Monday 10:00 AM")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("Scheduler stopped.")

if __name__ == "__main__":
    main()