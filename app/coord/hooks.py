from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping
from app.db_pg import get_conn

def _now(): 
    return datetime.now(timezone.utc)

def _insert(kind: str, payload: Mapping[str, Any]):
    """Insert a coordination event into swarm_memory table."""
    conn = get_conn()
    with conn.cursor() as c:
        # Create table if not exists (idempotent)
        c.execute("""
        create table if not exists swarm_memory (
          id bigserial primary key,
          session text not null,
          kind text not null,
          payload jsonb not null,
          created_at timestamptz not null default now()
        )""")
        
        # Create index for efficient queries
        c.execute("""
        create index if not exists idx_swarm_memory_session_created 
        on swarm_memory(session, created_at desc)
        """)
        
        # Insert the event
        c.execute("""
        insert into swarm_memory(session, kind, payload)
        values(%s,%s,%s::jsonb)
        """, (payload.get("session", "default"), kind, json.dumps(payload)))

def pre_task(session: str, description: str, **kw):
    """Log the start of a task with inputs and assumptions."""
    _insert("pre_task", {
        "session": session, 
        "description": description, 
        "meta": kw, 
        "ts": _now().isoformat()
    })
    # Also print for immediate visibility
    print(f"[coord] pre_task: {description}")

def post_edit(session: str, file: str, reason: str, **kw):
    """Record file modifications with reasoning."""
    _insert("post_edit", {
        "session": session, 
        "file": file, 
        "reason": reason, 
        "meta": kw, 
        "ts": _now().isoformat()
    })
    print(f"[coord] post_edit: {file} - {reason}")

def notify(session: str, message: str, **kw):
    """Add decision trace entries."""
    _insert("notify", {
        "session": session, 
        "message": message, 
        "meta": kw, 
        "ts": _now().isoformat()
    })
    print(f"[coord] notify: {message}")

def post_task(session: str, task_id: str, summary: str, **kw):
    """Summarize task completion with deltas and resulting state."""
    _insert("post_task", {
        "session": session, 
        "task_id": task_id, 
        "summary": summary, 
        "meta": kw, 
        "ts": _now().isoformat()
    })
    print(f"[coord] post_task: {task_id} - {summary}")

def decision_trace(session: str, moved_task: str, target_task: str, 
                   urgency_delta: float, sla_delta: float, 
                   staleness_delta: float, total_delta: float,
                   old_rank: int, new_rank: int):
    """Record task rebalancing decisions in standard format."""
    trace = f"""* moved {moved_task} above {target_task}:
  * urgency {urgency_delta:+.3f}
  * SLA {sla_delta:+.3f}
  * staleness {staleness_delta:+.3f}
  = Δscore {total_delta:+.3f} → rank #{old_rank} → #{new_rank}"""
    
    _insert("decision_trace", {
        "session": session,
        "moved_task": moved_task,
        "target_task": target_task,
        "urgency_delta": urgency_delta,
        "sla_delta": sla_delta,
        "staleness_delta": staleness_delta,
        "total_delta": total_delta,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "trace": trace,
        "ts": _now().isoformat()
    })
    print(f"[coord] decision_trace: {trace}")
    return trace

def batch_operation(session: str, operation: str, items: list, **kw):
    """Log batched operations (following claude-flow batching principle)."""
    _insert("batch_operation", {
        "session": session,
        "operation": operation,
        "item_count": len(items),
        "items": items[:10],  # Store first 10 for reference
        "meta": kw,
        "ts": _now().isoformat()
    })
    print(f"[coord] batch_operation: {operation} ({len(items)} items)")