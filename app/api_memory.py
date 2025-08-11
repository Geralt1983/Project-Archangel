from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db_pg import get_conn

router = APIRouter(prefix="/memory", tags=["memory"])

@router.get("/recent")
def recent(session: str = Query("default"), limit: int = Query(50, ge=1, le=200)):
    """Get recent coordination events for a session."""
    try:
        conn = get_conn()
        with conn.cursor() as c:
            c.execute("""
                select kind, payload, created_at 
                from swarm_memory 
                where session=%s 
                order by id desc 
                limit %s
            """, (session, limit))
            rows = [
                {
                    "kind": r[0], 
                    "payload": r[1], 
                    "created_at": r[2].isoformat()
                } 
                for r in c.fetchall()
            ]
        return {"session": session, "items": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
def list_sessions(limit: int = Query(20, ge=1, le=100)):
    """List active sessions with event counts."""
    try:
        conn = get_conn()
        with conn.cursor() as c:
            c.execute("""
                select session, count(*) as event_count, 
                       min(created_at) as first_event,
                       max(created_at) as last_event
                from swarm_memory
                group by session
                order by max(created_at) desc
                limit %s
            """, (limit,))
            sessions = [
                {
                    "session": r[0],
                    "event_count": r[1],
                    "first_event": r[2].isoformat(),
                    "last_event": r[3].isoformat()
                }
                for r in c.fetchall()
            ]
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/traces")
def decision_traces(
    session: str = Query("default"), 
    limit: int = Query(20, ge=1, le=100)
):
    """Get decision traces for a session."""
    try:
        conn = get_conn()
        with conn.cursor() as c:
            c.execute("""
                select payload, created_at
                from swarm_memory
                where session=%s and kind='decision_trace'
                order by id desc
                limit %s
            """, (session, limit))
            traces = [
                {
                    "trace": r[0].get("trace", ""),
                    "moved_task": r[0].get("moved_task"),
                    "target_task": r[0].get("target_task"),
                    "total_delta": r[0].get("total_delta"),
                    "old_rank": r[0].get("old_rank"),
                    "new_rank": r[0].get("new_rank"),
                    "created_at": r[1].isoformat()
                }
                for r in c.fetchall()
            ]
        return {"session": session, "traces": traces, "count": len(traces)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session}")
def clear_session(session: str):
    """Clear all events for a session."""
    try:
        conn = get_conn()
        with conn.cursor() as c:
            c.execute("delete from swarm_memory where session=%s", (session,))
            deleted = c.rowcount
        return {"session": session, "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def memory_stats():
    """Get overall memory statistics."""
    try:
        conn = get_conn()
        with conn.cursor() as c:
            # Total events
            c.execute("select count(*) from swarm_memory")
            total_events = c.fetchone()[0]
            
            # Events by kind
            c.execute("""
                select kind, count(*) 
                from swarm_memory 
                group by kind 
                order by count(*) desc
            """)
            events_by_kind = dict(c.fetchall())
            
            # Recent activity (last 24h)
            c.execute("""
                select count(*) 
                from swarm_memory 
                where created_at > now() - interval '24 hours'
            """)
            recent_24h = c.fetchone()[0]
            
        return {
            "total_events": total_events,
            "events_by_kind": events_by_kind,
            "recent_24h": recent_24h
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))