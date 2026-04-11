"""Circuit breaker for REST calls.

Wraps any async callable and trips open after *failure_threshold* consecutive
failures, preventing further calls until *recovery_timeout* seconds have
elapsed (half-open probe).

States
------
CLOSED  — normal operation; failures are counted.
OPEN    — calls are rejected immediately with ``CircuitOpenError``.
HALF_OPEN — one probe call is allowed; success → CLOSED, failure → OPEN.

Usage::

    from nerimity_sdk.transport.circuit_breaker import CircuitBreaker, CircuitOpenError

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

    try:
        result = await cb.call(bot.rest.create_message, channel_id, "hello")
    except CircuitOpenError:
        print("REST is unavailable, circuit is open")
"""
from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Coroutine


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Async circuit breaker.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in OPEN state before allowing a probe call.
    expected_exceptions:
        Exception types that count as failures.  Defaults to ``(Exception,)``.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._state = State.CLOSED
        self._failures = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    async def call(
        self,
        fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute *fn* through the circuit breaker."""
        async with self._lock:
            if self._state is State.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._state = State.HALF_OPEN
                else:
                    raise CircuitOpenError(
                        f"Circuit is OPEN (resets in "
                        f"{self.recovery_timeout - (time.monotonic() - self._opened_at):.1f}s)"
                    )

        try:
            result = await fn(*args, **kwargs)
        except self.expected_exceptions as exc:
            async with self._lock:
                self._failures += 1
                if self._state is State.HALF_OPEN or self._failures >= self.failure_threshold:
                    self._state = State.OPEN
                    self._opened_at = time.monotonic()
            raise exc
        else:
            async with self._lock:
                self._failures = 0
                self._state = State.CLOSED
            return result

    def reset(self) -> None:
        """Manually close the circuit and reset failure count."""
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def __repr__(self) -> str:
        return (
            f"<CircuitBreaker state={self._state.value} "
            f"failures={self._failures}/{self.failure_threshold}>"
        )
