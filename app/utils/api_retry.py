"""
API Retry Handler with Exponential Backoff and Circuit Breaker

Provides resilient API call handling with:
- Exponential backoff for transient failures
- Circuit breaker to prevent cascading failures
- Configurable timeouts and retry attempts
"""
import asyncio
import time
import logging
from typing import Optional, Callable, Any
import aiohttp

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open"""
    pass


class APIRetryHandler:
    """
    Retry handler with exponential backoff and circuit breaker pattern.

    Circuit Breaker States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, all requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout_base: float = 15.0,
        circuit_failure_threshold: int = 5,
        circuit_timeout: float = 60.0
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay between retries
            timeout_base: Base timeout for API calls (increases with retries)
            circuit_failure_threshold: Failures needed to open circuit
            circuit_timeout: Time to wait before attempting recovery (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout_base = timeout_base
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_timeout = circuit_timeout

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_time = 0
        self._lock = asyncio.Lock()

    async def _check_circuit(self):
        """Check circuit breaker state and update if needed"""
        async with self._lock:
            if self._circuit_open:
                elapsed = time.time() - self._circuit_open_time
                if elapsed >= self.circuit_timeout:
                    # Attempt recovery - move to HALF_OPEN
                    logger.info("Circuit breaker attempting recovery (HALF_OPEN)")
                    self._circuit_open = False
                    # Don't reset failure count yet - next success will do that
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker open - API temporarily unavailable. "
                        f"Retry in {self.circuit_timeout - elapsed:.1f}s"
                    )

    async def _record_success(self):
        """Record successful API call"""
        async with self._lock:
            if self._failure_count > 0:
                logger.info(f"API recovered - resetting failure count from {self._failure_count}")
            self._failure_count = 0
            self._circuit_open = False

    async def _record_failure(self):
        """Record failed API call and potentially open circuit"""
        async with self._lock:
            self._failure_count += 1
            logger.warning(f"API failure count: {self._failure_count}/{self.circuit_failure_threshold}")

            if self._failure_count >= self.circuit_failure_threshold:
                self._circuit_open = True
                self._circuit_open_time = time.time()
                logger.error(
                    f"Circuit breaker OPENED due to {self._failure_count} consecutive failures. "
                    f"Will retry after {self.circuit_timeout}s"
                )

    async def execute_with_retry(
        self,
        api_call: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute API call with retry logic and circuit breaker.

        Args:
            api_call: Async function to execute
            *args, **kwargs: Arguments to pass to api_call

        Returns:
            Result from api_call

        Raises:
            CircuitBreakerOpen: If circuit breaker is open
            Exception: If all retries exhausted
        """
        # Check circuit breaker
        await self._check_circuit()

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Calculate timeout for this attempt (increases with retries)
                timeout_seconds = self.timeout_base + (attempt * 5)

                logger.info(
                    f"API call attempt {attempt + 1}/{self.max_retries} "
                    f"(timeout: {timeout_seconds}s)"
                )

                # Execute with timeout
                result = await asyncio.wait_for(
                    api_call(*args, **kwargs),
                    timeout=timeout_seconds
                )

                # Success - reset failure tracking
                await self._record_success()
                return result

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    f"API timeout on attempt {attempt + 1}/{self.max_retries} "
                    f"(timeout was {timeout_seconds}s)"
                )

                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                continue

            except (aiohttp.ClientError, aiohttp.ServerTimeoutError) as e:
                last_exception = e
                logger.warning(
                    f"API error on attempt {attempt + 1}/{self.max_retries}: {type(e).__name__}"
                )

                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                continue

            except Exception as e:
                # Unexpected error - don't retry
                last_exception = e
                logger.error(f"Unexpected error in API call: {e}", exc_info=True)
                break

        # All retries failed
        await self._record_failure()

        logger.error(
            f"All {self.max_retries} retry attempts exhausted. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )

        raise last_exception


# Global retry handlers for different services
# Different services may need different retry configurations
prompt_api_retry = APIRetryHandler(
    max_retries=2,
    base_delay=2.0,
    timeout_base=15.0,
    circuit_failure_threshold=5,
    circuit_timeout=60.0
)

image_api_retry = APIRetryHandler(
    max_retries=2,
    base_delay=2.0,
    timeout_base=20.0,  # Image generation takes longer
    circuit_failure_threshold=5,
    circuit_timeout=60.0
)

vision_api_retry = APIRetryHandler(
    max_retries=2,
    base_delay=1.5,
    timeout_base=15.0,
    circuit_failure_threshold=5,
    circuit_timeout=60.0
)
