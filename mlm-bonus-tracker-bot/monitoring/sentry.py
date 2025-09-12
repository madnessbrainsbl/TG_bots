
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

_SENTRY_AVAILABLE = False
try:
    import sentry_sdk  # type: ignore
    from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore
    _SENTRY_AVAILABLE = True
except Exception:
    sentry_sdk = None
    LoggingIntegration = None

def init_sentry(dsn: Optional[str] = None, environment: Optional[str] = None,
                release: Optional[str] = None, traces_sample_rate: float = 0.0) -> None:
    """Initialize Sentry if SDK available and DSN present."""
    if not _SENTRY_AVAILABLE:
        log.info("Sentry SDK not installed — skipping init")
        return
    dsn = dsn or os.getenv("SENTRY_DSN", "")
    if not dsn:
        log.info("SENTRY_DSN is empty — Sentry disabled")
        return
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(
        dsn=dsn,
        environment=environment or os.getenv("SENTRY_ENV", "production"),
        release=release or os.getenv("SENTRY_RELEASE", None),
        traces_sample_rate=traces_sample_rate,
        integrations=[sentry_logging],
    )
    log.info("Sentry initialized")

def capture_exception(exc: BaseException) -> None:
    if _SENTRY_AVAILABLE and sentry_sdk:
        sentry_sdk.capture_exception(exc)

# Optional: aiogram error handler wrapper
try:
    from aiogram import Dispatcher, F  # type: ignore
    from aiogram.types import ErrorEvent  # type: ignore

    def register_aiogram_error_handler(dp: "Dispatcher"):
        @dp.errors()
        async def on_error(event: "ErrorEvent"):
            try:
                exc = event.exception
            except Exception:
                exc = None
            if exc:
                capture_exception(exc)
except Exception:
    def register_aiogram_error_handler(dp):
        return
