"""
Structured Logging Configuration
Production-ready logging with correlation IDs, performance metrics, and security audit trails.
"""

import os
import sys
import json
import time
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar
import structlog
from structlog.stdlib import LoggerFactory
import logging.config

# Correlation ID context variable for request tracing
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to all log entries"""
    cid = correlation_id.get()
    if cid:
        event_dict['correlation_id'] = cid
    return event_dict

def add_timestamp(logger, method_name, event_dict):
    """Add precise timestamp to log entries"""
    event_dict['timestamp'] = time.time()
    return event_dict

def add_service_context(logger, method_name, event_dict):
    """Add service context information"""
    event_dict.update({
        'service': 'project-archangel',
        'version': os.getenv('APP_VERSION', 'dev'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'instance_id': os.getenv('INSTANCE_ID', 'local')
    })
    return event_dict

def filter_sensitive_data(logger, method_name, event_dict):
    """Remove sensitive data from logs"""
    sensitive_keys = {
        'password', 'token', 'secret', 'key', 'authorization', 
        'webhook_secret', 'api_key', 'clickup_token', 'trello_token',
        'todoist_token', 'serena_api_key'
    }
    
    def clean_dict(d):
        if isinstance(d, dict):
            return {
                k: '***REDACTED***' if any(sens in k.lower() for sens in sensitive_keys)
                else clean_dict(v) for k, v in d.items()
            }
        elif isinstance(d, list):
            return [clean_dict(item) for item in d]
        else:
            return d
    
    return clean_dict(event_dict)

def setup_logging():
    """Configure structured logging for production use"""
    
    # Log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Console output format
    console_format = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'console'
    
    processors = [
        add_correlation_id,
        add_timestamp,
        add_service_context,
        filter_sensitive_data,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if console_format == 'json':
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
    
    # Set uvicorn logging level
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

class RequestLogger:
    """Request/response logging middleware with performance metrics"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def log_request(self, request, start_time: float = None):
        """Log incoming request details"""
        cid = str(uuid.uuid4())
        correlation_id.set(cid)
        
        await self.logger.ainfo(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length"),
            start_time=start_time or time.time()
        )
    
    async def log_response(self, request, response, duration: float, status_code: int):
        """Log response details with performance metrics"""
        await self.logger.ainfo(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            response_size=response.headers.get("content-length") if hasattr(response, 'headers') else None
        )
    
    async def log_error(self, request, error: Exception, duration: float):
        """Log request errors with context"""
        await self.logger.aerror(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=round(duration * 1000, 2),
            exc_info=True
        )

class SecurityLogger:
    """Security-focused logging for audit trails"""
    
    def __init__(self):
        self.logger = structlog.get_logger("security")
    
    async def log_webhook_verification(self, provider: str, success: bool, client_ip: str = None):
        """Log webhook signature verification attempts"""
        await self.logger.ainfo(
            "Webhook verification",
            provider=provider,
            verification_success=success,
            client_ip=client_ip,
            severity="medium" if not success else "low"
        )
    
    async def log_rate_limit_exceeded(self, client_ip: str, endpoint: str, limit: int):
        """Log rate limiting violations"""
        await self.logger.awarning(
            "Rate limit exceeded",
            client_ip=client_ip,
            endpoint=endpoint,
            rate_limit=limit,
            severity="medium"
        )
    
    async def log_authentication_attempt(self, user_id: str, success: bool, method: str):
        """Log authentication attempts"""
        await self.logger.ainfo(
            "Authentication attempt",
            user_id=user_id,
            success=success,
            auth_method=method,
            severity="high" if not success else "low"
        )

class PerformanceLogger:
    """Performance monitoring and metrics logging"""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    async def log_slow_query(self, query: str, duration: float, table: str = None):
        """Log slow database queries"""
        await self.logger.awarning(
            "Slow database query",
            query_duration_ms=round(duration * 1000, 2),
            table=table,
            query_preview=query[:100] + "..." if len(query) > 100 else query
        )
    
    async def log_cache_performance(self, operation: str, hit: bool, duration: float, key: str = None):
        """Log cache performance metrics"""
        await self.logger.adebug(
            "Cache operation",
            operation=operation,
            cache_hit=hit,
            duration_ms=round(duration * 1000, 2),
            cache_key=key
        )
    
    async def log_external_api_call(self, provider: str, endpoint: str, duration: float, status_code: int):
        """Log external API call performance"""
        await self.logger.ainfo(
            "External API call",
            provider=provider,
            endpoint=endpoint,
            duration_ms=round(duration * 1000, 2),
            status_code=status_code,
            success=200 <= status_code < 300
        )

class BusinessLogger:
    """Business event logging for analytics and monitoring"""
    
    def __init__(self):
        self.logger = structlog.get_logger("business")
    
    async def log_task_created(self, task_id: str, client: str, provider: str, score: float):
        """Log task creation events"""
        await self.logger.ainfo(
            "Task created",
            task_id=task_id,
            client=client,
            provider=provider,
            initial_score=score,
            event_type="task_lifecycle"
        )
    
    async def log_ai_enhancement(self, task_id: str, provider: str, enhanced: bool, duration: float):
        """Log AI enhancement events"""
        await self.logger.ainfo(
            "AI enhancement",
            task_id=task_id,
            provider=provider,
            ai_enhanced=enhanced,
            duration_ms=round(duration * 1000, 2),
            event_type="ai_operation"
        )
    
    async def log_workload_rebalance(self, tasks_moved: int, duration: float, trigger: str):
        """Log workload rebalancing events"""
        await self.logger.ainfo(
            "Workload rebalanced",
            tasks_moved=tasks_moved,
            duration_ms=round(duration * 1000, 2),
            trigger=trigger,
            event_type="system_optimization"
        )

# Global logger instances
request_logger = RequestLogger()
security_logger = SecurityLogger()
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()

# Utility functions
def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()

def set_correlation_id(cid: str):
    """Set correlation ID for current context"""
    correlation_id.set(cid)

def clear_correlation_id():
    """Clear correlation ID"""
    correlation_id.set(None)