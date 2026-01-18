"""Service de cache pour optimiser les performances."""

import asyncio
import hashlib
import json
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis

from ..core.logger import get_logger


class CacheService:
    """Service de cache pour les données de trading."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.logger = get_logger(__name__)
        self.redis_client = None
        self.memory_cache = {}  # Cache local en cas d'échec Redis
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
    
    async def initialize(self) -> None:
        """Initialise la connexion Redis."""
        try:
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            self.logger.info("Cache Redis connected")
        except Exception as e:
            self.logger.warning(f"Redis connection failed, using memory cache: {e}")
            self.redis_client = None
    
    def _generate_key(self, namespace: str, data: Any) -> str:
        """Génère une clé de cache."""
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{namespace}:{hash_obj.hexdigest()}"
    
    async def get(self, namespace: str, data: Any) -> Optional[Any]:
        """Récupère une valeur du cache."""
        key = self._generate_key(namespace, data)
        
        try:
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    self.cache_stats["hits"] += 1
                    return json.loads(value)
            else:
                # Cache mémoire
                if key in self.memory_cache:
                    cache_entry = self.memory_cache[key]
                    if cache_entry["expires"] > datetime.utcnow():
                        self.cache_stats["hits"] += 1
                        return cache_entry["value"]
                    else:
                        del self.memory_cache[key]
        except Exception as e:
            self.logger.warning(f"Cache get error: {e}")
            self.cache_stats["errors"] += 1
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(self, namespace: str, data: Any, value: Any, ttl_seconds: int = 300) -> None:
        """Stocke une valeur dans le cache."""
        key = self._generate_key(namespace, data)
        
        try:
            if self.redis_client:
                await self.redis_client.setex(key, ttl_seconds, json.dumps(value))
            else:
                # Cache mémoire
                self.memory_cache[key] = {
                    "value": value,
                    "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds)
                }
        except Exception as e:
            self.logger.warning(f"Cache set error: {e}")
            self.cache_stats["errors"] += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache."""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / max(1, total) * 100
        
        return {
            **self.cache_stats,
            "hit_rate_percent": round(hit_rate, 1),
            "total_requests": total
        }


# Instance globale du service de cache
cache_service = CacheService()
