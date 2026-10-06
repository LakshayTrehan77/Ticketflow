import json
import logging
import time
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


class Cache:
    """Small cache wrapper. Uses Redis if it is reachable, otherwise a plain dict."""

    def __init__(self, redis_url: str | None = None):
        self._redis = None
        self._local: dict[str, tuple[float, str]] = {}

        if redis_url:
            try:
                import redis

                client = redis.Redis.from_url(
                    redis_url, decode_responses=True, socket_connect_timeout=2
                )
                client.ping()
                self._redis = client
                logger.info("cache: connected to redis")
            except Exception as exc:
                logger.warning("cache: redis not reachable (%s), using in-memory cache", exc)

    def get(self, key: str):
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
            except Exception:
                return None
            return json.loads(raw) if raw else None

        item = self._local.get(key)
        if item and item[0] > time.time():
            return json.loads(item[1])
        return None

    def set(self, key: str, value, ttl: int = 30) -> None:
        raw = json.dumps(value)
        if self._redis is not None:
            try:
                self._redis.set(key, raw, ex=ttl)
            except Exception:
                logger.warning("cache: could not write key %s", key)
            return
        self._local[key] = (time.time() + ttl, raw)

    def delete(self, key: str) -> None:
        if self._redis is not None:
            try:
                self._redis.delete(key)
            except Exception:
                logger.warning("cache: could not delete key %s", key)
            return
        self._local.pop(key, None)

    def clear(self) -> None:
        self._local.clear()


@lru_cache
def get_cache() -> Cache:
    return Cache(get_settings().redis_url)
