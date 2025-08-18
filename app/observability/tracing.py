"""
Distributed Tracing Configuration
OpenTelemetry integration for end-to-end request tracing across services.
"""

import os
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import structlog

logger = structlog.get_logger(__name__)

class TracingConfig:
    """OpenTelemetry tracing configuration and management"""
    
    def __init__(self):
        self.service_name = "project-archangel"
        self.service_version = os.getenv('APP_VERSION', 'dev')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.jaeger_endpoint = os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces')
        self.tracing_enabled = os.getenv('TRACING_ENABLED', 'true').lower() == 'true'
        
        self.tracer_provider = None
        self.tracer = None
    
    def setup_tracing(self) -> bool:
        """Initialize OpenTelemetry tracing"""
        if not self.tracing_enabled:
            logger.info("Tracing disabled")
            return False
        
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": self.service_version,
                "deployment.environment": self.environment,
                "service.instance.id": os.getenv('INSTANCE_ID', 'local')
            })
            
            # Set up tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                endpoint=self.jaeger_endpoint,
                collector_endpoint=None  # Use HTTP endpoint
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)
            
            # Get tracer instance
            self.tracer = trace.get_tracer(__name__)
            
            logger.info("Tracing initialized", 
                       service=self.service_name,
                       endpoint=self.jaeger_endpoint)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize tracing", error=str(e))
            return False
    
    def instrument_app(self, app):
        """Instrument FastAPI application"""
        if not self.tracing_enabled:
            return
        
        try:
            # Instrument FastAPI
            FastAPIInstrumentor.instrument_app(app)
            
            # Instrument Redis (if available)
            try:
                RedisInstrumentor().instrument()
            except Exception as e:
                logger.warning("Redis instrumentation failed", error=str(e))
            
            # Instrument PostgreSQL
            try:
                Psycopg2Instrumentor().instrument()
            except Exception as e:
                logger.warning("PostgreSQL instrumentation failed", error=str(e))
            
            # Instrument HTTP client
            try:
                HTTPXClientInstrumentor().instrument()
            except Exception as e:
                logger.warning("HTTPX instrumentation failed", error=str(e))
            
            logger.info("Application instrumentation completed")
            
        except Exception as e:
            logger.error("Application instrumentation failed", error=str(e))
    
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a new span with optional attributes"""
        if not self.tracer:
            return trace.INVALID_SPAN
        
        span = self.tracer.start_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        return span
    
    def add_span_attributes(self, span, attributes: Dict[str, Any]):
        """Add attributes to existing span"""
        if span and span.is_recording():
            for key, value in attributes.items():
                span.set_attribute(key, value)
    
    def record_exception(self, span, exception: Exception):
        """Record exception in span"""
        if span and span.is_recording():
            span.record_exception(exception)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))

class BusinessTracing:
    """Business-specific tracing for task orchestration flows"""
    
    def __init__(self, tracing_config: TracingConfig):
        self.tracing = tracing_config
    
    def trace_task_intake(self, task_data: Dict[str, Any]):
        """Create span for task intake process"""
        attributes = {
            "task.client": task_data.get('client', ''),
            "task.type": task_data.get('task_type', ''),
            "task.provider": task_data.get('provider', ''),
            "task.importance": task_data.get('importance', 0)
        }
        return self.tracing.create_span("task.intake", attributes)
    
    def trace_ai_enhancement(self, task_id: str, provider: str):
        """Create span for AI enhancement process"""
        attributes = {
            "ai.provider": provider,
            "task.id": task_id,
            "operation.type": "ai_enhancement"
        }
        return self.tracing.create_span("ai.enhance_task", attributes)
    
    def trace_scoring(self, task_id: str, algorithm: str):
        """Create span for task scoring"""
        attributes = {
            "task.id": task_id,
            "scoring.algorithm": algorithm,
            "operation.type": "scoring"
        }
        return self.tracing.create_span("task.scoring", attributes)
    
    def trace_provider_operation(self, provider: str, operation: str, task_id: str = None):
        """Create span for provider operations"""
        attributes = {
            "provider.name": provider,
            "provider.operation": operation,
            "operation.type": "provider_api"
        }
        if task_id:
            attributes["task.id"] = task_id
        
        return self.tracing.create_span(f"provider.{operation}", attributes)
    
    def trace_workload_rebalance(self, trigger: str):
        """Create span for workload rebalancing"""
        attributes = {
            "rebalance.trigger": trigger,
            "operation.type": "workload_management"
        }
        return self.tracing.create_span("workload.rebalance", attributes)

class CacheTracing:
    """Cache operation tracing"""
    
    def __init__(self, tracing_config: TracingConfig):
        self.tracing = tracing_config
    
    def trace_cache_operation(self, operation: str, namespace: str, key: str = None):
        """Create span for cache operations"""
        attributes = {
            "cache.operation": operation,
            "cache.namespace": namespace,
            "operation.type": "cache"
        }
        if key:
            attributes["cache.key"] = key[:50]  # Truncate long keys
        
        return self.tracing.create_span(f"cache.{operation}", attributes)

class DatabaseTracing:
    """Database operation tracing"""
    
    def __init__(self, tracing_config: TracingConfig):
        self.tracing = tracing_config
    
    def trace_db_operation(self, operation: str, table: str, query_type: str = None):
        """Create span for database operations"""
        attributes = {
            "db.operation": operation,
            "db.table": table,
            "operation.type": "database"
        }
        if query_type:
            attributes["db.query_type"] = query_type
        
        return self.tracing.create_span(f"db.{operation}", attributes)

# Global tracing instances
tracing_config = TracingConfig()
business_tracing = BusinessTracing(tracing_config)
cache_tracing = CacheTracing(tracing_config)
database_tracing = DatabaseTracing(tracing_config)

def setup_tracing(app) -> bool:
    """Setup tracing for the application"""
    success = tracing_config.setup_tracing()
    if success:
        tracing_config.instrument_app(app)
    return success

def get_current_span():
    """Get the current active span"""
    return trace.get_current_span()

def set_span_attribute(key: str, value: Any):
    """Set attribute on current span"""
    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)

def record_span_exception(exception: Exception):
    """Record exception on current span"""
    span = get_current_span()
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))