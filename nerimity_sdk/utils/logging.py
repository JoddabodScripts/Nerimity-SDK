"""Structured logging with injectable logger interface."""
from __future__ import annotations
import logging
import json
from typing import Protocol, Any


class Logger(Protocol):
    def debug(self, msg: str, **kw: Any) -> None: ...
    def info(self, msg: str, **kw: Any) -> None: ...
    def warning(self, msg: str, **kw: Any) -> None: ...
    def error(self, msg: str, **kw: Any) -> None: ...


class _DefaultLogger:
    def __init__(self, name: str = "nerimity", level: int = logging.INFO, debug_payloads: bool = False):
        self._log = logging.getLogger(name)
        self._log.setLevel(level)
        if not self._log.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            self._log.addHandler(h)
        self.debug_payloads = debug_payloads

    def debug(self, msg: str, **kw: Any) -> None:
        self._log.debug(msg, extra=kw or None)

    def info(self, msg: str, **kw: Any) -> None:
        self._log.info(msg)

    def warning(self, msg: str, **kw: Any) -> None:
        self._log.warning(msg)

    def error(self, msg: str, **kw: Any) -> None:
        self._log.error(msg)

    def gateway(self, event: str, payload: Any) -> None:
        if self.debug_payloads:
            self._log.debug("[GATEWAY] %s\n%s", event, json.dumps(payload, indent=2, default=str))


_logger: _DefaultLogger = _DefaultLogger()


def get_logger() -> _DefaultLogger:
    return _logger


def configure_logger(name: str = "nerimity", level: int = logging.INFO, debug_payloads: bool = False) -> None:
    global _logger
    _logger = _DefaultLogger(name, level, debug_payloads)
