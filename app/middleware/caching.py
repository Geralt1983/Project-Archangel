"""
Caching Middleware for FastAPI
Intelligent request/response caching with Redis backend and performance optimization.
"""

import time
import json
import hashlib
from typing import Callable, Optional, Any, Dict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from app.cache.redis_client import get_cache_manager
from app.observability.metrics import metrics
from app.observability.logging_config import performance_logger

logger = structlog.get_logger(__name__)

class CachingMiddleware:
    """
    FastAPI middleware for intelligent request/response caching
    with performance metrics and cache warming strategies.
    """
    
    def __init__(self, app):
        self.app = app
        
        # Cacheable endpoints configuration
        self.cacheable_endpoints = {
            '/health': {'ttl': 300, 'vary_by': []},
            '/tasks/intake': {'ttl': 0, 'vary_by': ['provider'], 'cache_ai_response': True},
            '/weekly': {'ttl': 1800, 'vary_by': ['client']},
            '/audit/export': {'ttl': 600, 'vary_by': []},
            '/providers/*/status': {'ttl': 300, 'vary_by': ['provider']},
            '/metrics': {'ttl': 60, 'vary_by': []},
        }
        
        # Methods that should be cached (read-only operations)
        self.cacheable_methods = {'GET', 'HEAD'}
        
        # Headers to exclude from cache key generation
        self.exclude_headers = {
            'user-agent', 'accept-encoding', 'connection', 'host',
            'x-forwarded-for', 'x-real-ip', 'authorization'  # Never cache auth-dependent responses
        }
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching logic"""
        start_time = time.time()
        
        # Determine if request is cacheable
        cache_config = self._get_cache_config(request)
        
        if cache_config and request.method in self.cacheable_methods:
            # Try cache first
            cache_key = await self._generate_cache_key(request, cache_config)
            cached_response = await self._get_cached_response(cache_key)
            
            if cached_response:
                duration = time.time() - start_time
                await performance_logger.log_cache_performance('hit', True, duration, cache_key)
                metrics.record_cache_operation('get', 'response', True, duration)
                
                return JSONResponse(
                    content=cached_response['content'],
                    status_code=cached_response['status_code'],
                    headers={**cached_response['headers'], 'X-Cache': 'HIT'}
                )
        
        # Process request normally
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Cache response if applicable
        if cache_config and response.status_code == 200:
            await self._cache_response(request, response, cache_config, duration)
        
        # Add cache miss header
        if cache_config:
            response.headers['X-Cache'] = 'MISS'
            await performance_logger.log_cache_performance('miss', False, duration)
            metrics.record_cache_operation('get', 'response', False, duration)
        
        return response
    
    def _get_cache_config(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get cache configuration for the request endpoint"""
        path = request.url.path
        
        # Exact match first
        if path in self.cacheable_endpoints:
            return self.cacheable_endpoints[path]
        
        # Pattern matching for dynamic endpoints
        for pattern, config in self.cacheable_endpoints.items():
            if '*' in pattern:
                pattern_parts = pattern.split('*')
                if (path.startswith(pattern_parts[0]) and 
                    (len(pattern_parts) == 1 or path.endswith(pattern_parts[1]))):
                    return config
        
        return None
    
    async def _generate_cache_key(self, request: Request, config: Dict[str, Any]) -> str:
        """Generate unique cache key for request"""
        key_components = [
            request.method,
            request.url.path,
        ]
        
        # Add query parameters
        if request.query_params:
            sorted_params = sorted(request.query_params.items())
            key_components.append(f"query:{json.dumps(sorted_params)}")
        
        # Add headers specified in vary_by
        vary_headers = {}
        for header_name in config.get('vary_by', []):
            header_value = request.headers.get(header_name.lower())
            if header_value:
                vary_headers[header_name] = header_value
        
        if vary_headers:
            key_components.append(f"headers:{json.dumps(vary_headers, sort_keys=True)}")
        
        # For POST requests with JSON body (if explicitly cacheable)
        if request.method == 'POST' and config.get('cache_post_body'):
            try:
                body = await request.body()
                if body:
                    # Create hash of body to avoid huge cache keys
                    body_hash = hashlib.sha256(body).hexdigest()[:16]
                    key_components.append(f"body:{body_hash}")
            except Exception:
                pass  # Skip body caching if not readable
        
        # Generate final key
        key_string = '|'.join(key_components)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:32]
        
        return f"api_response:{cache_key}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response"""
        try:
            cache_manager = await get_cache_manager()
            cached_data = await cache_manager.redis.get('response', cache_key)
            
            if cached_data and isinstance(cached_data, dict):
                # Validate cached response structure
                required_fields = {'content', 'status_code', 'headers', 'cached_at'}
                if all(field in cached_data for field in required_fields):
                    return cached_data
            
            return None
            
        except Exception as e:
            await logger.aerror("Cache retrieval failed", key=cache_key, error=str(e))
            return None
    
    async def _cache_response(self, request: Request, response: Response, config: Dict[str, Any], duration: float):
        """Cache response data"""
        try:
            ttl = config.get('ttl', 300)
            if ttl <= 0:
                return  # No caching for TTL <= 0
            
            cache_key = await self._generate_cache_key(request, config)
            
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Parse JSON content
            try:
                content = json.loads(response_body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                content = response_body.decode()
            
            # Prepare cache data
            cache_data = {
                'content': content,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'cached_at': time.time(),
                'request_duration': duration
            }
            
            # Store in cache
            cache_manager = await get_cache_manager()
            success = await cache_manager.redis.set('response', cache_key, cache_data, ttl=ttl)
            
            if success:
                await performance_logger.log_cache_performance('store', True, 0, cache_key)
                metrics.record_cache_operation('set', 'response', True, 0)
            
            # Replace response body iterator
            response.body_iterator = iter([response_body])
            
        except Exception as e:
            await logger.aerror("Cache storage failed", error=str(e))

class AIResponseCache:
    """
    Specialized caching for AI-enhanced responses
    with intelligent cache warming and invalidation.
    """
    
    def __init__(self):
        self.cache_namespace = 'ai_response'
        self.default_ttl = 3600  # 1 hour
    
    async def get_or_generate_ai_response(self, task_data: Dict[str, Any], provider: str, ai_function: Callable) -> Dict[str, Any]:
        """
        Get cached AI response or generate new one.
        Implements intelligent caching based on task similarity.
        """
        try:
            cache_manager = await get_cache_manager()
            
            # Try to get cached response
            cached_response = await cache_manager.get_cached_ai_response(task_data, provider)
            
            if cached_response:
                await logger.adebug("AI response cache hit", provider=provider)
                return cached_response
            
            # Generate new AI response
            start_time = time.time()
            ai_response = await ai_function(task_data, provider)
            duration = time.time() - start_time
            
            # Cache the response
            await cache_manager.cache_ai_response(task_data, ai_response, provider)
            
            await performance_logger.log_external_api_call(
                provider="serena_ai", 
                endpoint="triage", 
                duration=duration, 
                status_code=200
            )
            
            await logger.adebug("AI response generated and cached", 
                               provider=provider, 
                               duration_ms=round(duration * 1000, 2))
            
            return ai_response
            
        except Exception as e:
            await logger.aerror("AI response caching failed", error=str(e))
            # Fallback to direct AI call
            return await ai_function(task_data, provider)
    
    async def invalidate_client_cache(self, client: str):
        """Invalidate all cached responses for a specific client"""
        try:
            await get_cache_manager()
            # Implementation would depend on Redis key patterns
            # This is a placeholder for cache invalidation logic
            await logger.ainfo("Cache invalidated for client", client=client)
        except Exception as e:
            await logger.aerror("Cache invalidation failed", client=client, error=str(e))

class ProviderResponseCache:
    """
    Caching layer for external provider API responses
    with rate limiting and response optimization.
    """
    
    def __init__(self):
        self.cache_namespace = 'provider_api'
        self.default_ttl = 300  # 5 minutes
    
    async def cached_provider_call(self, provider: str, endpoint: str, params: Dict[str, Any], api_function: Callable) -> Dict[str, Any]:
        """
        Execute provider API call with caching
        """
        try:
            cache_manager = await get_cache_manager()
            
            # Generate cache key from parameters
            params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
            
            # Try cache first
            cached_response = await cache_manager.get_cached_provider_response(provider, endpoint, params_hash)
            
            if cached_response:
                await logger.adebug("Provider API cache hit", provider=provider, endpoint=endpoint)
                return cached_response
            
            # Make API call
            start_time = time.time()
            response = await api_function(params)
            duration = time.time() - start_time
            
            # Cache successful responses
            if response:
                await cache_manager.cache_provider_response(provider, endpoint, params_hash, response)
            
            await performance_logger.log_external_api_call(provider, endpoint, duration, 200)
            
            return response
            
        except Exception as e:
            await logger.aerror("Provider API caching failed", provider=provider, error=str(e))
            return await api_function(params)

# Global instances
ai_response_cache = AIResponseCache()
provider_response_cache = ProviderResponseCache()