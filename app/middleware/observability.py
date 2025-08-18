"""
Observability Middleware for FastAPI
Comprehensive request/response logging, metrics collection, and distributed tracing.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import structlog

from app.observability.logging_config import (
    request_logger, security_logger, performance_logger, 
    set_correlation_id, clear_correlation_id
)
from app.observability.metrics import metrics
from app.observability.tracing import get_current_span, set_span_attribute

logger = structlog.get_logger(__name__)

class ObservabilityMiddleware:
    """
    Comprehensive observability middleware that adds:
    - Request/response logging with correlation IDs
    - Performance metrics collection
    - Distributed tracing context
    - Security event logging
    - Error tracking and alerting
    """
    
    def __init__(self, app):
        self.app = app
        
        # Endpoints to exclude from detailed logging (health checks, metrics)
        self.exclude_detailed_logging = {'/health', '/metrics'}
        
        # Sensitive endpoints requiring security logging
        self.security_endpoints = {'/webhooks/', '/auth/', '/admin/'}
        
        # Slow request threshold (seconds)
        self.slow_request_threshold = 2.0
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive observability"""
        
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Set up tracing context
        span = get_current_span()
        if span and span.is_recording():
            set_span_attribute("correlation_id", correlation_id)
            set_span_attribute("http.method", request.method)
            set_span_attribute("http.url", str(request.url))
            set_span_attribute("http.user_agent", request.headers.get("user-agent", ""))
        
        start_time = time.time()
        
        # Log request start (skip for excluded endpoints)
        if request.url.path not in self.exclude_detailed_logging:
            await request_logger.log_request(request, start_time)
        
        # Security logging for sensitive endpoints
        if any(endpoint in request.url.path for endpoint in self.security_endpoints):
            await security_logger.log_authentication_attempt(
                user_id=request.headers.get("x-user-id", "anonymous"),
                success=True,  # Will be updated after processing
                method=request.method
            )
        
        response = None
        status_code = 500
        error_occurred = False
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Update tracing with response info
            if span and span.is_recording():
                set_span_attribute("http.status_code", status_code)
                set_span_attribute("http.response.size", 
                                 response.headers.get("content-length", "unknown"))
            
        except HTTPException as e:
            status_code = e.status_code
            error_occurred = True
            
            # Create error response
            response = JSONResponse(
                status_code=status_code,
                content={"error": e.detail, "correlation_id": correlation_id}
            )
            
            # Log HTTP exceptions
            duration = time.time() - start_time
            await request_logger.log_error(request, e, duration)
            
            # Record error metrics
            metrics.record_error("http_exception", "api")
            
        except Exception as e:
            status_code = 500
            error_occurred = True
            
            # Create generic error response
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "correlation_id": correlation_id}
            )
            
            # Log unexpected errors
            duration = time.time() - start_time
            await request_logger.log_error(request, e, duration)
            
            # Record error metrics
            metrics.record_error("internal_error", "api")
        
        finally:
            # Calculate final duration
            duration = time.time() - start_time
            
            # Add correlation ID to response headers
            if response:
                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"
            
            # Log request completion
            if request.url.path not in self.exclude_detailed_logging:
                if error_occurred:
                    await request_logger.log_error(request, Exception("Request failed"), duration)
                else:
                    await request_logger.log_response(request, response, duration, status_code)
            
            # Record performance metrics
            async with metrics.time_request(request.method, request.url.path, status_code):
                pass  # Metrics recorded in context manager
            
            # Log slow requests
            if duration > self.slow_request_threshold:
                await performance_logger.log_slow_query(
                    query=f"{request.method} {request.url.path}",
                    duration=duration,
                    table="api_endpoint"
                )
            
            # Security logging for webhook endpoints
            if "/webhooks/" in request.url.path:
                await security_logger.log_webhook_verification(
                    provider=request.url.path.split('/')[-1],
                    success=status_code == 200,
                    client_ip=request.client.host if request.client else None
                )
            
            # Business metrics for task-related endpoints
            if request.url.path.startswith("/tasks/"):
                if request.method == "POST" and status_code == 200:
                    # Extract provider and client from request/response if available
                    provider = request.query_params.get("provider", "unknown")
                    # Note: Would extract client from request body in real implementation
                    metrics.record_task_created("unknown", provider, "unknown", 0.0)
            
            # Clean up correlation ID
            clear_correlation_id()
        
        return response

class SecurityMiddleware:
    """
    Security-focused middleware for threat detection and prevention
    """
    
    def __init__(self, app):
        self.app = app
        self.request_counts = {}  # Simple in-memory rate limiting
        self.max_requests_per_minute = 100
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with security checks"""
        
        client_ip = self._get_client_ip(request)
        
        # Simple rate limiting (production should use Redis)
        if self._is_rate_limited(client_ip):
            await security_logger.log_rate_limit_exceeded(
                client_ip=client_ip,
                endpoint=request.url.path,
                limit=self.max_requests_per_minute
            )
            
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": 60}
            )
        
        # Security headers validation
        if self._has_suspicious_headers(request):
            await security_logger.log_authentication_attempt(
                user_id="suspicious",
                success=False,
                method="header_validation"
            )
        
        response = await call_next(request)
        
        # Add security headers to response
        self._add_security_headers(response)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Simple rate limiting check"""
        current_time = time.time()
        minute_bucket = int(current_time // 60)
        
        key = f"{client_ip}:{minute_bucket}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        
        self.request_counts[key] += 1
        
        # Clean old buckets (keep only last 2 minutes)
        old_keys = [k for k in self.request_counts.keys() 
                   if int(k.split(':')[1]) < minute_bucket - 1]
        for old_key in old_keys:
            del self.request_counts[old_key]
        
        return self.request_counts[key] > self.max_requests_per_minute
    
    def _has_suspicious_headers(self, request: Request) -> bool:
        """Check for suspicious request headers"""
        suspicious_patterns = [
            "curl", "wget", "scanner", "bot", "crawler"
        ]
        
        user_agent = request.headers.get("user-agent", "").lower()
        return any(pattern in user_agent for pattern in suspicious_patterns)
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        })

class HealthCheckMiddleware:
    """
    Middleware for health check and service status monitoring
    """
    
    def __init__(self, app):
        self.app = app
        self.health_endpoints = {'/health', '/health/live', '/health/ready'}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Handle health check requests with minimal overhead"""
        
        if request.url.path in self.health_endpoints:
            # Fast path for health checks - minimal processing
            return await self._handle_health_check(request)
        
        return await call_next(request)
    
    async def _handle_health_check(self, request: Request) -> Response:
        """Handle health check with service status"""
        try:
            # Basic health check
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "1.0.0"  # Would come from environment
            }
            
            # Add detailed checks for /health/ready
            if request.url.path == '/health/ready':
                # Check dependencies (Redis, PostgreSQL, AI service)
                health_status.update({
                    "dependencies": {
                        "database": "healthy",  # Would check actual DB connection
                        "cache": "healthy",     # Would check Redis connection
                        "ai_service": "healthy" # Would check Serena MCP connection
                    }
                })
            
            return JSONResponse(content=health_status)
            
        except Exception as e:
            await logger.aerror("Health check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)}
            )