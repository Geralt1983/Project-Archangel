"""
Redis Cache Client - High-Performance Caching Layer
Implements intelligent caching for AI responses, task scoring, and provider operations.
"""

import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import structlog
import os

logger = structlog.get_logger(__name__)

class RedisCacheClient:
    """
    Production-ready Redis cache client with connection pooling,
    automatic serialization, and intelligent TTL management.
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.pool = None
        self.client = None
        self._connected = False
        
        # Cache TTL configuration (seconds)
        self.ttl_config = {
            'ai_response': int(os.getenv("CACHE_TTL_AI_RESPONSE", "3600")),     # 1 hour
            'task_score': int(os.getenv("CACHE_TTL_TASK_SCORE", "1800")),      # 30 minutes
            'provider_api': int(os.getenv("CACHE_TTL_PROVIDER_API", "300")),   # 5 minutes
            'user_session': int(os.getenv("CACHE_TTL_USER_SESSION", "86400")), # 24 hours
            'webhook_dedupe': int(os.getenv("CACHE_TTL_WEBHOOK_DEDUPE", "604800")), # 7 days
            'default': int(os.getenv("CACHE_TTL_DEFAULT", "1800"))             # 30 minutes
        }
        
        # Key prefixes for namespace isolation
        self.prefixes = {
            'ai': 'archangel:ai:',
            'score': 'archangel:score:',
            'provider': 'archangel:provider:',
            'session': 'archangel:session:',
            'webhook': 'archangel:webhook:',
            'config': 'archangel:config:',
            'metrics': 'archangel:metrics:'
        }
    
    async def connect(self) -> bool:
        """Initialize Redis connection with retry logic"""
        try:
            self.pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
            self._connected = True
            
            await logger.ainfo("Redis cache connected", url=self.redis_url)
            return True
            
        except Exception as e:
            await logger.aerror("Redis connection failed", error=str(e))
            self._connected = False
            return False
    
    async def disconnect(self):
        """Clean shutdown of Redis connections"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        self._connected = False
        await logger.ainfo("Redis cache disconnected")
    
    def _generate_key(self, prefix: str, key: str) -> str:
        """Generate namespaced cache key"""
        base_prefix = self.prefixes.get(prefix, f"archangel:{prefix}:")
        return f"{base_prefix}{key}"
    
    def _hash_complex_key(self, data: Union[Dict, List, str]) -> str:
        """Generate consistent hash for complex keys"""
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        else:
            serialized = str(data)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with automatic serialization and TTL"""
        if not self._connected:
            return False
        
        try:
            cache_key = self._generate_key(namespace, key)
            ttl = ttl or self.ttl_config.get(namespace, self.ttl_config['default'])
            
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            await self.client.setex(cache_key, ttl, serialized_value)
            
            await logger.adebug("Cache set", key=cache_key, ttl=ttl)
            return True
            
        except Exception as e:
            await logger.aerror("Cache set failed", key=key, error=str(e))
            return False
    
    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get cache value with automatic deserialization"""
        if not self._connected:
            return None
        
        try:
            cache_key = self._generate_key(namespace, key)
            value = await self.client.get(cache_key)
            
            if value is None:
                return None
            
            # Try to deserialize as JSON, fallback to string
            try:
                return json.loads(value.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return value.decode()
                
        except Exception as e:
            await logger.aerror("Cache get failed", key=key, error=str(e))
            return None
    
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete cache entry"""
        if not self._connected:
            return False
        
        try:
            cache_key = self._generate_key(namespace, key)
            result = await self.client.delete(cache_key)
            
            await logger.adebug("Cache delete", key=cache_key, found=bool(result))
            return bool(result)
            
        except Exception as e:
            await logger.aerror("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, namespace: str, key: str) -> bool:
        """Check if cache key exists"""
        if not self._connected:
            return False
        
        try:
            cache_key = self._generate_key(namespace, key)
            return bool(await self.client.exists(cache_key))
            
        except Exception as e:
            await logger.aerror("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def increment(self, namespace: str, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Atomic increment operation"""
        if not self._connected:
            return None
        
        try:
            cache_key = self._generate_key(namespace, key)
            value = await self.client.incrby(cache_key, amount)
            
            # Set TTL on first increment
            if value == amount and ttl:
                await self.client.expire(cache_key, ttl)
            
            return value
            
        except Exception as e:
            await logger.aerror("Cache increment failed", key=key, error=str(e))
            return None
    
    async def set_if_not_exists(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value only if key doesn't exist (atomic)"""
        if not self._connected:
            return False
        
        try:
            cache_key = self._generate_key(namespace, key)
            ttl = ttl or self.ttl_config.get(namespace, self.ttl_config['default'])
            
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            result = await self.client.set(cache_key, serialized_value, ex=ttl, nx=True)
            return bool(result)
            
        except Exception as e:
            await logger.aerror("Cache set_if_not_exists failed", key=key, error=str(e))
            return False

# Cache-specific helper methods

class CacheManager:
    """High-level cache management with domain-specific methods"""
    
    def __init__(self, redis_client: RedisCacheClient):
        self.redis = redis_client
    
    async def cache_ai_response(self, task_data: Dict, response: Dict, provider: str) -> bool:
        """Cache AI enhancement response for similar tasks"""
        key_data = {
            'title': task_data.get('title', ''),
            'description': task_data.get('description', ''),
            'client': task_data.get('client', ''),
            'task_type': task_data.get('task_type', ''),
            'provider': provider
        }
        cache_key = self.redis._hash_complex_key(key_data)
        
        cache_value = {
            'response': response,
            'cached_at': datetime.utcnow().isoformat(),
            'task_hash': self.redis._hash_complex_key(task_data)
        }
        
        return await self.redis.set('ai', cache_key, cache_value)
    
    async def get_cached_ai_response(self, task_data: Dict, provider: str) -> Optional[Dict]:
        """Retrieve cached AI response for similar tasks"""
        key_data = {
            'title': task_data.get('title', ''),
            'description': task_data.get('description', ''),
            'client': task_data.get('client', ''),
            'task_type': task_data.get('task_type', ''),
            'provider': provider
        }
        cache_key = self.redis._hash_complex_key(key_data)
        
        cached_data = await self.redis.get('ai', cache_key)
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('response')
        return None
    
    async def cache_task_score(self, task_id: str, score_data: Dict) -> bool:
        """Cache task scoring results"""
        cache_value = {
            'score': score_data.get('score'),
            'components': score_data.get('components', {}),
            'calculated_at': datetime.utcnow().isoformat()
        }
        return await self.redis.set('score', task_id, cache_value)
    
    async def get_cached_task_score(self, task_id: str) -> Optional[Dict]:
        """Retrieve cached task score"""
        return await self.redis.get('score', task_id)
    
    async def cache_provider_response(self, provider: str, endpoint: str, params_hash: str, response: Dict) -> bool:
        """Cache provider API responses"""
        cache_key = f"{provider}:{endpoint}:{params_hash}"
        cache_value = {
            'response': response,
            'cached_at': datetime.utcnow().isoformat()
        }
        return await self.redis.set('provider', cache_key, cache_value)
    
    async def get_cached_provider_response(self, provider: str, endpoint: str, params_hash: str) -> Optional[Dict]:
        """Retrieve cached provider response"""
        cache_key = f"{provider}:{endpoint}:{params_hash}"
        cached_data = await self.redis.get('provider', cache_key)
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('response')
        return None
    
    async def track_webhook_delivery(self, delivery_id: str) -> bool:
        """Track webhook delivery for deduplication"""
        return await self.redis.set_if_not_exists(
            'webhook', 
            delivery_id, 
            {'received_at': datetime.utcnow().isoformat()}, 
            ttl=self.redis.ttl_config['webhook_dedupe']
        )
    
    async def is_webhook_duplicate(self, delivery_id: str) -> bool:
        """Check if webhook was already processed"""
        return await self.redis.exists('webhook', delivery_id)

# Global cache instance
_cache_client = None
_cache_manager = None

async def get_cache_client() -> RedisCacheClient:
    """Get global cache client instance"""
    global _cache_client
    if _cache_client is None:
        _cache_client = RedisCacheClient()
        await _cache_client.connect()
    return _cache_client

async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        client = await get_cache_client()
        _cache_manager = CacheManager(client)
    return _cache_manager

async def shutdown_cache():
    """Shutdown cache connections"""
    global _cache_client, _cache_manager
    if _cache_client:
        await _cache_client.disconnect()
        _cache_client = None
        _cache_manager = None