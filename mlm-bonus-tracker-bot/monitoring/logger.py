
import logging
import os
from logging.handlers import RotatingFileHandler
import json
from typing import Optional

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "name": record.name,
            "time": self.formatTime(record, self.datefmt),
            "message": record.getMessage(),
        }
        # Inject extras if any
        for key, value in record.__dict__.items():
            if key not in ("levelname","name","asctime","msg","args","created","msecs",
                           "relativeCreated","exc_info","exc_text","stack_info","stacklevel",
                           "filename","funcName","levelno","lineno","module","pathname","process",
                           "processName","thread","threadName"):
                try:
                    json.dumps({key: value})
                    payload[key] = value
                except Exception:
                    payload[key] = str(value)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_logging(app_name: str = "mlm_bot",
                  log_level: Optional[str] = None,
                  json_format: bool = True,
                  log_file: Optional[str] = "logs/app.log",
                  max_bytes: int = 5 * 1024 * 1024,
                  backup_count: int = 5) -> None:
    """
    Configure root logger: console + rotating file, optional JSON.
    Safe to call multiple times.
    """
    level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    if getattr(root, "_mlm_logging_configured", False):
        root.setLevel(level)
        return

    root.setLevel(level)

    # Ensure logs dir
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Formatters
    if json_format:
        formatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s :: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    root.addHandler(sh)

    # File
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # Quiet noisy libs (optional)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    root._mlm_logging_configured = True

    logging.getLogger(__name__).info("Logging configured", extra={"app": app_name, "level": level})
