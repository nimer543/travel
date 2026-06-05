import time
from threading import Lock
from typing import Any, Dict, Optional


# Time To Live for optimisation 
class TTLInMemoryCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                # Check if item is still valid
                if time.time() - entry["timestamp"] < self.ttl:
                    return entry["value"]
                # Expired item, clean it up
                del self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            self.cache[key] = {
                "value": value,
                "timestamp": time.time()
            }

    def delete(self, key: str) -> None:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    def clear(self) -> None:
        with self.lock:
            self.cache.clear()
