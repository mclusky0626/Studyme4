from __future__ import annotations

import logging
import re

_SECRET_PATTERNS = (
    (
        re.compile(r"(?i)(authorization)(\s*[:=]\s*)(?:bearer\s+)?\S+"),
        r"\1\2[REDACTED]",
    ),
    (
        re.compile(r"(?i)(api[_-]?key|token|password)(\s*[:=]\s*)(\S+)"),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"(?i)bearer\s+[a-z0-9._-]+"), "Bearer [REDACTED]"),
)


def redact(value: str) -> str:
    clean = value
    for pattern, replacement in _SECRET_PATTERNS:
        clean = pattern.sub(replacement, clean)
    return clean


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg))
        if record.args:
            record.args = tuple(redact(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SecretRedactionFilter())
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[handler],
        force=True,
    )
