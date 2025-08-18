import logging
import os
import re
import structlog

REDACT_KEYS = {"authorization", "token", "api_key", "apikey", "secret", "password", "x-signature", "x-trello-webhook", "x-todoist-hmac-sha256"}
REDACT_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.IGNORECASE)


def _redact_value(key: str, value: object) -> object:
    if isinstance(value, str):
        if key.lower() in REDACT_KEYS:
            return "***"
        return REDACT_PATTERN.sub(r"\1***", value)
    return value


def _processor(logger, method_name, event_dict):  # type: ignore
    # Redact sensitive keys
    for k in list(event_dict.keys()):
        event_dict[k] = _redact_value(k, event_dict[k])
    return event_dict


def setup_logging(level: str | int = None) -> None:
    lvl = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, lvl, logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _processor,
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, lvl, logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
