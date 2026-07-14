import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from app.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        for key, value in record.__dict__.items():
            if key in ("args", "msg", "levelname", "levelno", "name", "pathname", "filename", "module",
                        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                        "relativeCreated", "thread", "threadName", "processName", "process", "message"):
                continue
            payload[key] = value
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    logging.getLogger("uvicorn.access").handlers = [handler]


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def now_ms() -> float:
    return time.perf_counter() * 1000
