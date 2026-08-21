"""Structured, secret-safe logging for SourceLens."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class RedactingFilter(logging.Filter):
    """Removes values that look like secrets from log records."""

    _SECRET_KEYS = (
        "api_key",
        "apikey",
        "api-key",
        "key",
        "token",
        "secret",
        "password",
        "authorization",
        "bearer",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            redacted = {
                k: ("***" if any(s in k.lower() for s in self._SECRET_KEYS) else v)
                for k, v in record.args.items()
            }
            record.args = redacted
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.getLogger("sourcelens").level)
    logger.propagate = False
    return logger


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger("sourcelens")
    root.setLevel(level.upper())
    # Re-apply level to existing child loggers.
    for child in logging.Logger.manager.loggerDict.values():
        if isinstance(child, logging.Logger) and child.name.startswith("sourcelens"):
            child.setLevel(level.upper())


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("sl_"):
                payload[key[3:]] = value
        return json.dumps(payload, default=str)
