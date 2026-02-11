import time
import threading

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: Maximum number of tokens in the bucket.
        refill_rate: Tokens added per second.
        """
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = float(refill_rate)
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def _refill(self):
        now = time.time()
        delta = now - self.last_refill
        
        # Refill tokens
        new_tokens = delta * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def take(self, cost: int = 1) -> bool:
        """
        Attempts to take 'cost' tokens from the bucket.
        Returns True if successful, False if insufficient tokens.
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False

    def current_tokens(self) -> float:
        with self.lock:
            self._refill()
            return self.tokens
