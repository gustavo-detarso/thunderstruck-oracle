import time
import hashlib

class CacheManager:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.cache = {}

    def _generate_key(self, query, tags):
        key_string = f"{query.lower().strip()}|{','.join(sorted(tags))}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def set(self, query, tags, response):
        key = self._generate_key(query, tags)
        self.cache[key] = {
            "response": response,
            "timestamp": time.time()
        }

    def get(self, query, tags):
        key = self._generate_key(query, tags)
        item = self.cache.get(key)
        if item:
            if time.time() - item["timestamp"] < self.ttl:
                return item["response"]
            else:
                del self.cache[key]
        return None

    def clean(self):
        now = time.time()
        keys_to_delete = [k for k, v in self.cache.items() if now - v["timestamp"] >= self.ttl]
        for k in keys_to_delete:
            del self.cache[k]
