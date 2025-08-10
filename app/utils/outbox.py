"""
Outbox Pattern for reliable provider operations with idempotency
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OutboxStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OutboxOperation:
    """Represents an outbound operation to be performed"""
    
    def __init__(
        self,
        operation_type: str,
        provider: str,
        endpoint: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.operation_type = operation_type
        self.provider = provider
        self.endpoint = endpoint
        self.payload = payload
        self.idempotency_key = idempotency_key or self._generate_idempotency_key()
        self.status = OutboxStatus.PENDING
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.next_retry_at = None
        self.error_message = None
        self.metadata = metadata or {}
    
    def _generate_idempotency_key(self) -> str:
        """Generate idempotency key from provider, endpoint, and payload hash"""
        payload_str = json.dumps(self.payload, sort_keys=True)
        combined = f"{self.provider}|{self.endpoint}|{payload_str}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'provider': self.provider,
            'endpoint': self.endpoint,
            'payload': self.payload,
            'idempotency_key': self.idempotency_key,
            'status': self.status.value,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'error_message': self.error_message,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutboxOperation':
        """Create from dictionary"""
        op = cls(
            operation_type=data['operation_type'],
            provider=data['provider'],
            endpoint=data['endpoint'],
            payload=data['payload'],
            idempotency_key=data['idempotency_key'],
            retry_count=data['retry_count'],
            max_retries=data['max_retries'],
            metadata=data.get('metadata', {})
        )
        op.id = data['id']
        op.status = OutboxStatus(data['status'])
        op.created_at = datetime.fromisoformat(data['created_at'])
        op.updated_at = datetime.fromisoformat(data['updated_at'])
        op.next_retry_at = datetime.fromisoformat(data['next_retry_at']) if data['next_retry_at'] else None
        op.error_message = data.get('error_message')
        return op

class OutboxManager:
    """Manages outbox operations with database persistence"""
    
    def __init__(self, db_connection_func):
        self.get_db = db_connection_func
        self._init_schema()
    
    def _init_schema(self):
        """Initialize outbox table schema"""
        conn = self.get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outbox_operations (
                    id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 5,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    next_retry_at TIMESTAMPTZ,
                    error_message TEXT,
                    metadata JSONB,
                    UNIQUE(idempotency_key)
                );
                
                CREATE INDEX IF NOT EXISTS idx_outbox_status_retry 
                ON outbox_operations(status, next_retry_at);
                
                CREATE INDEX IF NOT EXISTS idx_outbox_provider 
                ON outbox_operations(provider);
                
                CREATE INDEX IF NOT EXISTS idx_outbox_created 
                ON outbox_operations(created_at);
            """)
            conn.commit()
        finally:
            cursor.close()
    
    def add_operation(
        self,
        operation_type: str,
        provider: str,
        endpoint: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        max_retries: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutboxOperation:
        """Add new operation to outbox"""
        
        operation = OutboxOperation(
            operation_type=operation_type,
            provider=provider,
            endpoint=endpoint,
            payload=payload,
            idempotency_key=idempotency_key,
            max_retries=max_retries,
            metadata=metadata
        )
        
        conn = self.get_db()
        cursor = conn.cursor()
        try:
            # Adapt SQL for SQLite vs PostgreSQL
            if hasattr(conn, 'row_factory'):  # SQLite
                cursor.execute("""
                    INSERT OR IGNORE INTO outbox_operations (
                        id, operation_type, provider, endpoint, payload,
                        idempotency_key, status, retry_count, max_retries,
                        created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation.id, operation.operation_type, operation.provider,
                    operation.endpoint, json.dumps(operation.payload),
                    operation.idempotency_key, operation.status.value,
                    operation.retry_count, operation.max_retries,
                    operation.created_at.isoformat(), operation.updated_at.isoformat(),
                    json.dumps(operation.metadata)
                ))
            else:  # PostgreSQL
                cursor.execute("""
                    INSERT INTO outbox_operations (
                        id, operation_type, provider, endpoint, payload,
                        idempotency_key, status, retry_count, max_retries,
                        created_at, updated_at, metadata
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING
                """, (
                    operation.id, operation.operation_type, operation.provider,
                    operation.endpoint, json.dumps(operation.payload),
                    operation.idempotency_key, operation.status.value,
                    operation.retry_count, operation.max_retries,
                    operation.created_at, operation.updated_at,
                    json.dumps(operation.metadata)
                ))
                
            # Check if operation was actually inserted (idempotency)
            if hasattr(conn, 'row_factory'):  # SQLite
                cursor.execute("SELECT id FROM outbox_operations WHERE idempotency_key = ?", (operation.idempotency_key,))
            else:  # PostgreSQL
                cursor.execute("SELECT id FROM outbox_operations WHERE idempotency_key = %s", (operation.idempotency_key,))
            
            result = cursor.fetchone()
            
            if result and result[0] != operation.id:
                # Operation already exists with this idempotency key
                logger.info(f"Operation with idempotency key {operation.idempotency_key} already exists")
                return self.get_operation_by_key(operation.idempotency_key)
            
            conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to add outbox operation: {e}")
            raise
        finally:
            cursor.close()
        
        return operation
    
    def get_operation_by_key(self, idempotency_key: str) -> Optional[OutboxOperation]:
        """Get operation by idempotency key"""
        conn = self.get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM outbox_operations WHERE idempotency_key = %s",
                (idempotency_key,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_operation(row)
        return None
    
    def get_pending_operations(self, limit: int = 100) -> List[OutboxOperation]:
        """Get pending operations ready for processing"""
        conn = self.get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM outbox_operations 
                WHERE status = 'pending' 
                   OR (status = 'failed' AND retry_count < max_retries 
                       AND (next_retry_at IS NULL OR next_retry_at <= %s))
                ORDER BY created_at
                LIMIT %s
            """, (datetime.now(timezone.utc), limit))
            
            return [self._row_to_operation(row) for row in cursor.fetchall()]
    
    def mark_processing(self, operation_id: str) -> bool:
        """Mark operation as processing"""
        return self._update_status(operation_id, OutboxStatus.PROCESSING)
    
    def mark_completed(self, operation_id: str) -> bool:
        """Mark operation as completed"""
        return self._update_status(operation_id, OutboxStatus.COMPLETED)
    
    def mark_failed(
        self,
        operation_id: str,
        error_message: str,
        retry_delay_seconds: int = 60
    ) -> bool:
        """Mark operation as failed and schedule retry"""
        conn = self.get_db()
        try:
            with conn.cursor() as cursor:
                # Get current retry count
                cursor.execute(
                    "SELECT retry_count, max_retries FROM outbox_operations WHERE id = %s",
                    (operation_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                
                retry_count, max_retries = row
                new_retry_count = retry_count + 1
                
                if new_retry_count >= max_retries:
                    # Max retries reached, mark as permanently failed
                    status = OutboxStatus.FAILED
                    next_retry_at = None
                else:
                    # Schedule retry
                    status = OutboxStatus.FAILED
                    next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay_seconds)
                
                cursor.execute("""
                    UPDATE outbox_operations 
                    SET status = %s, retry_count = %s, error_message = %s, 
                        next_retry_at = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    status.value, new_retry_count, error_message,
                    next_retry_at, datetime.now(timezone.utc), operation_id
                ))
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark operation as failed: {e}")
            return False
    
    def _update_status(self, operation_id: str, status: OutboxStatus) -> bool:
        """Update operation status"""
        conn = self.get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE outbox_operations 
                    SET status = %s, updated_at = %s
                    WHERE id = %s
                """, (status.value, datetime.now(timezone.utc), operation_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update operation status: {e}")
            return False
    
    def _row_to_operation(self, row) -> OutboxOperation:
        """Convert database row to OutboxOperation"""
        columns = [
            'id', 'operation_type', 'provider', 'endpoint', 'payload',
            'idempotency_key', 'status', 'retry_count', 'max_retries',
            'created_at', 'updated_at', 'next_retry_at', 'error_message', 'metadata'
        ]
        data = dict(zip(columns, row))
        return OutboxOperation.from_dict(data)
    
    def cleanup_completed(self, older_than_days: int = 7) -> int:
        """Clean up completed operations older than specified days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        conn = self.get_db()
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM outbox_operations 
                    WHERE status = 'completed' AND updated_at < %s
                """, (cutoff,))
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup completed operations: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get outbox statistics"""
        conn = self.get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM outbox_operations 
                GROUP BY status
            """)
            
            stats = {}
            for status, count in cursor.fetchall():
                stats[status] = count
            
            return stats

class OutboxProcessor:
    """Processes outbox operations"""
    
    def __init__(self, outbox_manager: OutboxManager, provider_registry: Dict[str, Any]):
        self.outbox = outbox_manager
        self.providers = provider_registry
        self.processing = False
    
    async def process_pending(self, batch_size: int = 50) -> Dict[str, int]:
        """Process pending outbox operations"""
        if self.processing:
            logger.warning("Outbox processing already in progress")
            return {"skipped": 1}
        
        self.processing = True
        stats = {"processed": 0, "completed": 0, "failed": 0, "skipped": 0}
        
        try:
            operations = self.outbox.get_pending_operations(limit=batch_size)
            
            for operation in operations:
                try:
                    await self._process_operation(operation)
                    stats["processed"] += 1
                    stats["completed"] += 1
                except Exception as e:
                    logger.error(f"Failed to process operation {operation.id}: {e}")
                    self.outbox.mark_failed(operation.id, str(e))
                    stats["processed"] += 1 
                    stats["failed"] += 1
        
        finally:
            self.processing = False
        
        return stats
    
    async def _process_operation(self, operation: OutboxOperation):
        """Process a single outbox operation"""
        # Mark as processing
        self.outbox.mark_processing(operation.id)
        
        # Get provider
        provider = self.providers.get(operation.provider)
        if not provider:
            raise ValueError(f"Unknown provider: {operation.provider}")
        
        # Execute operation based on type
        if operation.operation_type == "create_task":
            await provider.create_task_from_payload(operation.payload)
        elif operation.operation_type == "update_task":
            await provider.update_task_from_payload(operation.payload)
        elif operation.operation_type == "delete_task":
            await provider.delete_task_from_payload(operation.payload)
        else:
            raise ValueError(f"Unknown operation type: {operation.operation_type}")
        
        # Mark as completed
        self.outbox.mark_completed(operation.id)

# Helper functions for common operations
def create_task_operation(
    provider: str,
    task_data: Dict[str, Any],
    outbox: OutboxManager
) -> OutboxOperation:
    """Helper to create a task creation operation"""
    return outbox.add_operation(
        operation_type="create_task",
        provider=provider,
        endpoint="/tasks",
        payload=task_data,
        metadata={"task_id": task_data.get("id")}
    )

def update_task_operation(
    provider: str,
    task_id: str,
    updates: Dict[str, Any],
    outbox: OutboxManager
) -> OutboxOperation:
    """Helper to create a task update operation"""
    return outbox.add_operation(
        operation_type="update_task",
        provider=provider,
        endpoint=f"/tasks/{task_id}",
        payload={"task_id": task_id, "updates": updates},
        metadata={"task_id": task_id}
    )