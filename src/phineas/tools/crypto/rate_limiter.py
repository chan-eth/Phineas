"""
Rate limiting implementation for cryptocurrency API calls.

Uses token bucket algorithm for smooth rate limiting with burst capacity.
Thread-safe for concurrent requests.
"""

import time
import threading
from typing import Dict, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket algorithm implementation for rate limiting.

    Allows burst traffic while maintaining average rate over time.
    Thread-safe for concurrent access.
    """

    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second (e.g., 0.5 = 30 per minute)
            capacity: Maximum tokens that can accumulate (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            bool: True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.rate)
            )
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def wait_time(self) -> float:
        """
        Calculate time to wait until next token is available.

        Returns:
            float: Seconds to wait, 0 if tokens available
        """
        with self.lock:
            if self.tokens >= 1:
                return 0.0

            # Time needed to accumulate 1 token
            return (1.0 - self.tokens) / self.rate


class RateLimiter:
    """
    Multi-API rate limiter with configurable limits per API.

    Implements exponential backoff for 429 responses.
    Thread-safe and production-ready.
    """

    # API rate limits (requests per minute)
    API_LIMITS = {
        "coingecko": 30,  # Free tier: ~30/min conservative estimate
        "coindesk": 50,  # Data API: ~50/min conservative estimate
        "kraken": 15,  # Kraken: ~15-20 calls per minute for most endpoints
        "coinbase": 10,  # Coinbase Advanced: 10 requests per second = 600/min, but conservative
    }

    # Maximum concurrent waiters per API to prevent resource exhaustion
    MAX_WAITERS_PER_API = 100

    def __init__(self, limits: Optional[Dict[str, int]] = None):
        """
        Initialize rate limiter.

        Args:
            limits: Optional custom limits dict {api_name: requests_per_minute}

        Raises:
            ValueError: If limits are invalid
        """
        self.limits = limits or self.API_LIMITS
        self.buckets: Dict[str, TokenBucket] = {}
        self.backoff_until: Dict[str, float] = {}
        self.waiters: Dict[str, threading.Semaphore] = {}
        self.lock = threading.Lock()

        # Validate limits
        for api_name, rpm in self.limits.items():
            if not isinstance(rpm, (int, float)):
                raise ValueError(f"Rate limit for {api_name} must be numeric, got {type(rpm)}")
            if rpm <= 0:
                raise ValueError(f"Rate limit for {api_name} must be positive, got {rpm}")
            if rpm > 10000:
                raise ValueError(f"Rate limit for {api_name} unreasonably high: {rpm}")

        # Create token buckets for each API
        for api_name, rpm in self.limits.items():
            # Convert requests per minute to tokens per second
            rate = rpm / 60.0
            # Allow burst of 5 requests
            capacity = min(5.0, rpm / 12.0)
            self.buckets[api_name] = TokenBucket(rate, capacity)
            self.backoff_until[api_name] = 0.0
            # Limit concurrent waiters to prevent resource exhaustion
            self.waiters[api_name] = threading.Semaphore(self.MAX_WAITERS_PER_API)

        logger.info(f"Rate limiter initialized with limits: {self.limits}")

    # Minimum sleep duration to prevent CPU thrashing
    MIN_SLEEP = 0.01  # 10ms

    # Maximum timeout to prevent indefinite blocking
    MAX_TIMEOUT = 300  # 5 minutes

    def acquire(self, api_name: str, timeout: float = 60.0) -> bool:
        """
        Acquire permission to make an API call.

        Blocks until permission is granted or timeout is reached.
        Respects exponential backoff for 429 responses.
        Limits concurrent waiters to prevent resource exhaustion.

        Args:
            api_name: Name of the API (e.g., "coingecko")
            timeout: Maximum seconds to wait

        Returns:
            bool: True if permission granted, False if timeout

        Raises:
            ValueError: If api_name is unknown or timeout is invalid
        """
        if api_name not in self.buckets:
            raise ValueError(f"Unknown API: {api_name}. Known APIs: {list(self.buckets.keys())}")

        # Validate timeout
        if timeout < 0:
            raise ValueError(f"Timeout must be non-negative, got {timeout}")
        if timeout > self.MAX_TIMEOUT:
            logger.warning(f"Timeout {timeout}s exceeds maximum {self.MAX_TIMEOUT}s, capping")
            timeout = self.MAX_TIMEOUT

        # Try to acquire waiter slot - fail fast if too many waiters
        if not self.waiters[api_name].acquire(blocking=False):
            logger.warning(f"Too many concurrent waiters for {api_name} (max {self.MAX_WAITERS_PER_API})")
            return False

        try:
            bucket = self.buckets[api_name]
            start_time = time.time()

            # Check exponential backoff
            backoff_time = self.backoff_until.get(api_name, 0.0)
            if backoff_time > time.time():
                wait_time = backoff_time - time.time()
                logger.warning(
                    f"API {api_name} in backoff period, waiting {wait_time:.1f}s"
                )
                if wait_time > timeout:
                    return False
                time.sleep(wait_time)

            # Wait for token availability with minimum sleep to prevent CPU thrashing
            while True:
                if bucket.consume():
                    logger.debug(f"Rate limit token acquired for {api_name}")
                    return True

                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit timeout for {api_name}")
                    return False

                # Enforce minimum sleep to prevent busy-wait CPU thrashing
                wait_time = max(self.MIN_SLEEP, min(bucket.wait_time(), timeout - elapsed))
                if wait_time > 0:
                    time.sleep(wait_time)
        finally:
            # Always release waiter slot
            self.waiters[api_name].release()

    def report_rate_limit_error(self, api_name: str, retry_after: Optional[int] = None):
        """
        Report that a 429 rate limit error occurred.

        Implements exponential backoff for subsequent requests.

        Args:
            api_name: Name of the API that returned 429
            retry_after: Optional retry-after header value in seconds
        """
        with self.lock:
            # Use retry-after if provided, otherwise exponential backoff
            if retry_after:
                backoff_seconds = retry_after
            else:
                # Exponential backoff: start at 60s, max 300s (5 min)
                current_backoff = self.backoff_until.get(api_name, 0.0)
                if current_backoff > time.time():
                    # Double the backoff
                    remaining = current_backoff - time.time()
                    backoff_seconds = min(remaining * 2, 300)
                else:
                    # Start with 60 second backoff
                    backoff_seconds = 60

            self.backoff_until[api_name] = time.time() + backoff_seconds
            logger.warning(
                f"Rate limit hit for {api_name}, backing off for {backoff_seconds}s"
            )

    def reset_backoff(self, api_name: str):
        """
        Reset exponential backoff for an API.

        Call this after successful requests to clear backoff state.

        Args:
            api_name: Name of the API to reset
        """
        with self.lock:
            self.backoff_until[api_name] = 0.0

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get current rate limiter statistics.

        Acquires locks in consistent order to prevent deadlocks.

        Returns:
            dict: Statistics for each API including available tokens and wait times
        """
        stats = {}

        # Acquire self.lock first to get backoff data (consistent lock order)
        with self.lock:
            backoff_data = dict(self.backoff_until)

        # Then acquire individual bucket locks
        for api_name, bucket in self.buckets.items():
            with bucket.lock:
                stats[api_name] = {
                    "available_tokens": bucket.tokens,
                    "capacity": bucket.capacity,
                    "rate_per_second": bucket.rate,
                    "wait_time_seconds": bucket.wait_time(),
                    "backoff_until": backoff_data.get(api_name, 0.0),
                }
        return stats


# Global rate limiter instance with thread-safe initialization
_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """
    Get or create the global rate limiter instance.

    Thread-safe singleton pattern with double-checked locking.

    Returns:
        RateLimiter: The global rate limiter
    """
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            # Double-check pattern to prevent race condition
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    return _rate_limiter
