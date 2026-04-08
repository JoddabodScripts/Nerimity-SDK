"""Lightweight cron scheduler backed by croniter.

Usage::

    @bot.cron("0 9 * * *")   # every day at 09:00 UTC
    async def morning_report():
        await bot.rest.create_message(CHANNEL_ID, "Good morning!")
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional


class CronJob:
    def __init__(self, expr: str, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self.expr = expr
        self.fn = fn
        self._task: Optional[asyncio.Task] = None

    def _next_delay(self) -> float:
        try:
            from croniter import croniter
        except ImportError:
            raise ImportError("Install croniter: pip install croniter")
        now = datetime.now(timezone.utc)
        nxt = croniter(self.expr, now).get_next(datetime)
        return (nxt - now).total_seconds()

    async def _loop(self) -> None:
        from nerimity_sdk.utils.logging import get_logger
        while True:
            delay = self._next_delay()
            await asyncio.sleep(delay)
            try:
                await self.fn()
            except Exception as exc:
                get_logger().error(f"[Cron] {self.expr} error: {exc}")

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def cancel(self) -> None:
        if self._task:
            self._task.cancel()


class Scheduler:
    def __init__(self) -> None:
        self._jobs: list[CronJob] = []

    def cron(self, expr: str):
        """Decorator: @scheduler.cron("*/5 * * * *")"""
        def decorator(fn: Callable[[], Coroutine[Any, Any, None]]) -> Callable:
            job = CronJob(expr, fn)
            self._jobs.append(job)
            return fn
        return decorator

    def start_all(self) -> None:
        for job in self._jobs:
            job.start()

    def stop_all(self) -> None:
        for job in self._jobs:
            job.cancel()
