"""
Cache LRU avec TTL — Évite les appels LLM redondants.

Design :
- LRU (Least Recently Used) : éviction des entrées les moins récentes
- TTL (Time To Live) : expiration automatique après N secondes
- Thread-safe via threading.Lock
- Statistiques (hits, misses, évictions)
"""

import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """Entrée du cache avec valeur et timestamp d'expiration."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl_seconds: float):
        self.value      = value
        self.expires_at = time.monotonic() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class LRUCache:
    """
    Cache LRU avec TTL thread-safe.

    Utilisation :
        cache = LRUCache(max_size=100, ttl_seconds=300)
        cache.set("key", {"data": "value"})
        result = cache.get("key")  # None si absent ou expiré
        print(cache.stats)
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300.0):
        self.max_size    = max_size
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock       = threading.Lock()
        self._hits       = 0
        self._misses     = 0
        self._evictions  = 0

    # ── Opérations principales ────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Retourne la valeur si présente et non expirée, None sinon."""
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None

            entry = self._store[key]

            if entry.is_expired:
                del self._store[key]
                self._misses += 1
                logger.debug("Cache EXPIRED: %s", key[:60])
                return None

            # Mettre à jour l'ordre LRU (déplacer en fin)
            self._store.move_to_end(key)
            self._hits += 1
            logger.debug("Cache HIT: %s", key[:60])
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Insère ou met à jour une entrée. Éviction LRU si nécessaire."""
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds

        with self._lock:
            if key in self._store:
                # Mise à jour — déplacer en fin (most recently used)
                self._store.move_to_end(key)
                self._store[key] = CacheEntry(value, ttl)
                return

            # Éviction LRU si plein
            while len(self._store) >= self.max_size:
                evicted_key, _ = self._store.popitem(last=False)
                self._evictions += 1
                logger.debug("Cache EVICT: %s", evicted_key[:60])

            self._store[key] = CacheEntry(value, ttl)
            logger.debug("Cache SET: %s (ttl=%.0fs)", key[:60], ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
        logger.info("Cache vidé")

    def invalidate_pattern(self, prefix: str) -> int:
        """Invalide toutes les entrées dont la clé commence par prefix."""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
        logger.info("Cache invalidé: %d entrées (prefix=%s)", len(keys), prefix)
        return len(keys)

    # ── Nettoyage des entrées expirées ────────────────────────────────────────

    def purge_expired(self) -> int:
        """Supprime les entrées expirées. Retourne le nombre supprimé."""
        with self._lock:
            expired = [k for k, v in self._store.items() if v.is_expired]
            for k in expired:
                del self._store[k]
        if expired:
            logger.debug("Cache purge: %d entrées expirées supprimées", len(expired))
        return len(expired)

    # ── Statistiques ──────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        with self._lock:
            total   = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size":       len(self._store),
                "max_size":   self.max_size,
                "hits":       self._hits,
                "misses":     self._misses,
                "evictions":  self._evictions,
                "hit_rate":   round(hit_rate, 1),
                "ttl_seconds": self.ttl_seconds,
            }

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __repr__(self) -> str:
        s = self.stats
        return f"<LRUCache size={s['size']}/{s['max_size']} hit_rate={s['hit_rate']}%>"
