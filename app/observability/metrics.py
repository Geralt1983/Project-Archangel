"""
Prometheus Metrics Collection
Production-ready metrics for monitoring performance, health, and business KPIs.
"""

import time
import os
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    start_http_server, generate_latest, CONTENT_TYPE_LATEST
)
import structlog

logger = structlog.get_logger(__name__)

# Business Metrics
TASKS_CREATED_TOTAL = Counter(
    'archangel_tasks_created_total',
    'Total tasks created',
    ['client', 'provider', 'task_type']
)

TASKS_COMPLETED_TOTAL = Counter(
    'archangel_tasks_completed_total', 
    'Total tasks completed',
    ['client', 'provider', 'outcome']
)

TASK_SCORE_HISTOGRAM = Histogram(
    'archangel_task_score',
    'Distribution of task scores',
    ['client', 'provider'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

WORKLOAD_BALANCE_GAUGE = Gauge(
    'archangel_workload_balance',
    'Current workload balance score (0-1, higher is better)',
    ['client']
)

AI_ENHANCEMENT_RATE = Gauge(
    'archangel_ai_enhancement_rate',
    'Percentage of tasks enhanced by AI',
    ['provider']
)

# Performance Metrics
REQUEST_DURATION = Histogram(
    'archangel_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_COUNT = Counter(
    'archangel_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

EXTERNAL_API_DURATION = Histogram(
    'archangel_external_api_duration_seconds',
    'External API call duration',
    ['provider', 'endpoint', 'status_code'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

DATABASE_OPERATION_DURATION = Histogram(
    'archangel_database_operation_duration_seconds',
    'Database operation duration',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Cache Metrics
CACHE_OPERATIONS_TOTAL = Counter(
    'archangel_cache_operations_total',
    'Total cache operations',
    ['operation', 'namespace', 'result']
)

CACHE_HIT_RATE = Gauge(
    'archangel_cache_hit_rate',
    'Cache hit rate by namespace',
    ['namespace']
)

CACHE_OPERATION_DURATION = Histogram(
    'archangel_cache_operation_duration_seconds',
    'Cache operation duration',
    ['operation', 'namespace'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# System Health Metrics
ACTIVE_CONNECTIONS = Gauge(
    'archangel_active_connections',
    'Number of active connections',
    ['type']
)

ERROR_RATE = Counter(
    'archangel_errors_total',
    'Total errors by type',
    ['error_type', 'component']
)

AI_SERVICE_HEALTH = Gauge(
    'archangel_ai_service_health',
    'AI service health status (1=healthy, 0=unhealthy)',
    ['service']
)

WEBHOOK_VERIFICATION_TOTAL = Counter(
    'archangel_webhook_verification_total',
    'Webhook verification attempts',
    ['provider', 'result']
)

# Worker Metrics
OUTBOX_QUEUE_SIZE = Gauge(
    'archangel_outbox_queue_size',
    'Number of items in outbox queue',
    ['status']
)

WORKER_PROCESSING_DURATION = Histogram(
    'archangel_worker_processing_duration_seconds',
    'Worker task processing duration',
    ['worker_type', 'outcome'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]
)

# Application Info
APP_INFO = Info(
    'archangel_app_info',
    'Application information'
)

class MetricsCollector:
    """High-level metrics collection interface"""
    
    def __init__(self):
        self.start_time = time.time()
        self._cache_stats = {}
        
        # Set application info
        APP_INFO.info({
            'version': os.getenv('APP_VERSION', 'dev'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'build_date': os.getenv('BUILD_DATE', 'unknown'),
            'commit_sha': os.getenv('COMMIT_SHA', 'unknown')
        })
    
    # Business Metrics
    def record_task_created(self, client: str, provider: str, task_type: str, score: float):
        """Record task creation event"""
        TASKS_CREATED_TOTAL.labels(
            client=client,
            provider=provider, 
            task_type=task_type
        ).inc()
        
        TASK_SCORE_HISTOGRAM.labels(
            client=client,
            provider=provider
        ).observe(score)
    
    def record_task_completed(self, client: str, provider: str, outcome: str):
        """Record task completion event"""
        TASKS_COMPLETED_TOTAL.labels(
            client=client,
            provider=provider,
            outcome=outcome
        ).inc()
    
    def update_workload_balance(self, client: str, balance_score: float):
        """Update workload balance gauge"""
        WORKLOAD_BALANCE_GAUGE.labels(client=client).set(balance_score)
    
    def update_ai_enhancement_rate(self, provider: str, rate: float):
        """Update AI enhancement rate"""
        AI_ENHANCEMENT_RATE.labels(provider=provider).set(rate)
    
    # Performance Metrics
    @asynccontextmanager
    async def time_request(self, method: str, endpoint: str, status_code: int):
        """Context manager for timing HTTP requests"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).observe(duration)
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
    
    @asynccontextmanager
    async def time_external_api(self, provider: str, endpoint: str, status_code: int):
        """Context manager for timing external API calls"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            EXTERNAL_API_DURATION.labels(
                provider=provider,
                endpoint=endpoint,
                status_code=status_code
            ).observe(duration)
    
    @asynccontextmanager
    async def time_database_operation(self, operation: str, table: str):
        """Context manager for timing database operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            DATABASE_OPERATION_DURATION.labels(
                operation=operation,
                table=table
            ).observe(duration)
    
    # Cache Metrics
    def record_cache_operation(self, operation: str, namespace: str, hit: bool, duration: float):
        """Record cache operation metrics"""
        result = 'hit' if hit else 'miss'
        
        CACHE_OPERATIONS_TOTAL.labels(
            operation=operation,
            namespace=namespace,
            result=result
        ).inc()
        
        CACHE_OPERATION_DURATION.labels(
            operation=operation,
            namespace=namespace
        ).observe(duration)
        
        # Update hit rate statistics
        key = f"{namespace}_{operation}"
        if key not in self._cache_stats:
            self._cache_stats[key] = {'hits': 0, 'total': 0}
        
        self._cache_stats[key]['total'] += 1
        if hit:
            self._cache_stats[key]['hits'] += 1
        
        hit_rate = self._cache_stats[key]['hits'] / self._cache_stats[key]['total']
        CACHE_HIT_RATE.labels(namespace=namespace).set(hit_rate)
    
    # System Health Metrics
    def update_active_connections(self, connection_type: str, count: int):
        """Update active connections gauge"""
        ACTIVE_CONNECTIONS.labels(type=connection_type).set(count)
    
    def record_error(self, error_type: str, component: str):
        """Record error occurrence"""
        ERROR_RATE.labels(
            error_type=error_type,
            component=component
        ).inc()
    
    def update_ai_service_health(self, service: str, healthy: bool):
        """Update AI service health status"""
        AI_SERVICE_HEALTH.labels(service=service).set(1 if healthy else 0)
    
    def record_webhook_verification(self, provider: str, success: bool):
        """Record webhook verification attempt"""
        result = 'success' if success else 'failure'
        WEBHOOK_VERIFICATION_TOTAL.labels(
            provider=provider,
            result=result
        ).inc()
    
    # Worker Metrics
    def update_outbox_queue_size(self, status: str, size: int):
        """Update outbox queue size"""
        OUTBOX_QUEUE_SIZE.labels(status=status).set(size)
    
    @asynccontextmanager
    async def time_worker_processing(self, worker_type: str, outcome: str):
        """Context manager for timing worker processing"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            WORKER_PROCESSING_DURATION.labels(
                worker_type=worker_type,
                outcome=outcome
            ).observe(duration)

# Global metrics instance
metrics = MetricsCollector()

def start_metrics_server(port: int = 8090):
    """Start Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info("Metrics server started", port=port)
    except Exception as e:
        logger.error("Failed to start metrics server", error=str(e))

async def get_metrics() -> str:
    """Get metrics in Prometheus format"""
    return generate_latest()

def get_metrics_content_type() -> str:
    """Get Prometheus metrics content type"""
    return CONTENT_TYPE_LATEST