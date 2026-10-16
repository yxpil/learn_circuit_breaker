"""Circuit Breaker: closed (allow) -> open (fail fast) -> half-open (probe) -> closed."""
import time
from collections import deque


class CircuitOpen(Exception):
    """Raised when the circuit is open and calls are blocked."""
    def __init__(self, waited):
        self.waited = waited
        super().__init__(f"circuit open for {waited:.1f}s")


class CircuitBreaker:
    def __init__(self, fail_threshold=3, reset_timeout=2.0, half_open_calls=1):
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.half_open_calls = half_open_calls
        self.state = "closed"          # closed | open | half-open
        self.failures = 0
        self.opened_at = None
        self.half_open_remaining = 0

    def call(self, fn, *args, **kwargs):
        if self.state == "open":
            if time.monotonic() - self.opened_at >= self.reset_timeout:
                self._to_half_open()
            else:
                raise CircuitOpen(time.monotonic() - self.opened_at)

        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            self._record_failure()
            raise e

        self._record_success()
        return result

    def _to_half_open(self):
        self.state = "half-open"
        self.half_open_remaining = self.half_open_calls

    def _record_failure(self):
        if self.state == "half-open":
            # probe failed -> back to open
            self.state = "open"
            self.opened_at = time.monotonic()
            self.failures = self.fail_threshold
        else:
            self.failures += 1
            if self.failures >= self.fail_threshold:
                self.state = "open"
                self.opened_at = time.monotonic()

    def _record_success(self):
        if self.state == "half-open":
            self.half_open_remaining -= 1
            if self.half_open_remaining <= 0:
                self.state = "closed"
                self.failures = 0
        else:
            self.failures = 0
