import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, DateTime, Float, Integer, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .models import Task, AuditEvent, WebhookEvent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    external_id = Column(String, index=True)
    provider = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    client = Column(String, index=True)
    project = Column(String)
    task_type = Column(String, index=True)
    labels = Column(JSON)
    status = Column(String, index=True)
    deadline = Column(DateTime)
    effort_hours = Column(Float)
    importance = Column(Integer)
    client_sla_hours = Column(Float)
    freshness_score = Column(Float)
    recent_progress = Column(Float)
    score = Column(Float, index=True)
    checklist = Column(JSON)
    subtasks = Column(JSON)
    source = Column(String)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    idempotency_key = Column(String, unique=True, index=True)

class AuditEventDB(Base):
    __tablename__ = "audit_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False, index=True)
    task_id = Column(String, index=True)
    external_id = Column(String, index=True)
    provider = Column(String, index=True)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    request_id = Column(String, index=True)

class WebhookEventDB(Base):
    __tablename__ = "webhook_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False, index=True)
    event_id = Column(String, index=True)
    delivery_id = Column(String, unique=True, index=True)
    task_id = Column(String, index=True)
    external_id = Column(String, index=True)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class DeliveryTrackingDB(Base):
    __tablename__ = "delivery_tracking"
    
    delivery_id = Column(String, primary_key=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_task(task: Task) -> TaskDB:
    """Save task to database."""
    db = next(get_db())
    
    # Convert Pydantic model to dict for storage
    task_dict = task.dict()
    
    # Check if task already exists
    existing = db.query(TaskDB).filter(TaskDB.id == task.id).first()
    
    if existing:
        # Update existing task
        for key, value in task_dict.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        # Create new task
        db_task = TaskDB(**task_dict)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

def get_task(task_id: str) -> Optional[Task]:
    """Get task by ID."""
    db = next(get_db())
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    
    if not db_task:
        return None
    
    # Convert DB model back to Pydantic model
    task_dict = {
        column.name: getattr(db_task, column.name)
        for column in db_task.__table__.columns
    }
    return Task(**task_dict)

def get_task_by_external_id(external_id: str) -> Optional[Task]:
    """Get task by external provider ID."""
    db = next(get_db())
    db_task = db.query(TaskDB).filter(TaskDB.external_id == external_id).first()
    
    if not db_task:
        return None
    
    task_dict = {
        column.name: getattr(db_task, column.name)
        for column in db_task.__table__.columns
    }
    return Task(**task_dict)

def fetch_open_tasks() -> List[Task]:
    """Get all tasks that are not done."""
    db = next(get_db())
    db_tasks = db.query(TaskDB).filter(TaskDB.status != "done").all()
    
    tasks = []
    for db_task in db_tasks:
        task_dict = {
            column.name: getattr(db_task, column.name)
            for column in db_task.__table__.columns
        }
        tasks.append(Task(**task_dict))
    
    return tasks

def fetch_tasks_by_client(client: str) -> List[Task]:
    """Get all tasks for a specific client."""
    db = next(get_db())
    db_tasks = db.query(TaskDB).filter(TaskDB.client == client).all()
    
    tasks = []
    for db_task in db_tasks:
        task_dict = {
            column.name: getattr(db_task, column.name)
            for column in db_task.__table__.columns
        }
        tasks.append(Task(**task_dict))
    
    return tasks

def seen_delivery(delivery_id: str) -> bool:
    """Check if webhook delivery has been processed."""
    if not delivery_id:
        return False
        
    db = next(get_db())
    existing = db.query(DeliveryTrackingDB).filter(
        DeliveryTrackingDB.delivery_id == delivery_id
    ).first()
    
    return existing is not None

def upsert_event(delivery_id: str, event_data: Dict[str, Any]) -> WebhookEventDB:
    """Store webhook event with idempotency."""
    db = next(get_db())
    
    # Mark delivery as seen
    if delivery_id and not seen_delivery(delivery_id):
        tracking = DeliveryTrackingDB(delivery_id=delivery_id)
        db.add(tracking)
    
    # Store the event
    webhook_event = WebhookEventDB(
        event_type=event_data.get("event", "unknown"),
        event_id=event_data.get("event_id"),
        delivery_id=delivery_id,
        task_id=event_data.get("task_id"),
        external_id=event_data.get("task", {}).get("id") if event_data.get("task") else None,
        data=event_data
    )
    
    db.add(webhook_event)
    db.commit()
    db.refresh(webhook_event)
    
    return webhook_event

def log_audit_event(event_type: str, task_id: Optional[str] = None, 
                   external_id: Optional[str] = None, provider: Optional[str] = None,
                   data: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> AuditEventDB:
    """Log an audit event."""
    db = next(get_db())
    
    audit_event = AuditEventDB(
        event_type=event_type,
        task_id=task_id,
        external_id=external_id,
        provider=provider,
        data=data or {},
        request_id=request_id
    )
    
    db.add(audit_event)
    db.commit()
    db.refresh(audit_event)
    
    return audit_event