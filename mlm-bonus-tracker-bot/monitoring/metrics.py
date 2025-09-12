
import os
import time
from typing import Optional

_PROM_AVAILABLE = False
try:
    from prometheus_client import Counter, Summary, start_http_server  # type: ignore
    _PROM_AVAILABLE = True
except Exception:
    # Soft dependency: no-op metrics
    Counter = Summary = None
    def start_http_server(*args, **kwargs):
        return None

# Define metrics if available
if _PROM_AVAILABLE:
    METRICS_UPDATES = Counter("bot_updates_total", "Total updates received")
    METRICS_ERRORS = Counter("bot_errors_total", "Total handler errors")
    METRICS_HANDLER_LAT = Summary("bot_handler_latency_seconds", "Handler latency in seconds")
else:
    METRICS_UPDATES = METRICS_ERRORS = METRICS_HANDLER_LAT = None

def start_metrics_server(port: Optional[int] = None):
    """
    Start Prometheus metrics HTTP server on given port (default from env METRICS_PORT=9000).
    If prometheus_client is not installed, does nothing.
    """
    if not _PROM_AVAILABLE:
        return
    port = port or int(os.getenv("METRICS_PORT", "9000"))
    start_http_server(port)

def inc_updates():
    if METRICS_UPDATES:
        METRICS_UPDATES.inc()

def inc_errors():
    if METRICS_ERRORS:
        METRICS_ERRORS.inc()

class track_latency:
    """Context manager/decorator to observe handler latency."""
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self
    def __exit__(self, exc_type, exc, tb):
        if METRICS_HANDLER_LAT:
            METRICS_HANDLER_LAT.observe(time.perf_counter() - self.t0)
        return False  # don't suppress

# Optional: aiogram middleware to count updates and measure latency
try:
    from aiogram import BaseMiddleware
    from aiogram.types import Message, CallbackQuery
    from typing import Callable, Dict, Any, Awaitable

    class MetricsMiddleware(BaseMiddleware):
        async def __call__(self, handler: Callable, event, data: Dict[str, Any]):
            inc_updates()
            with track_latency():
                try:
                    return await handler(event, data)
                except Exception:
                    inc_errors()
                    raise
except Exception:
    BaseMiddleware = None
    class MetricsMiddleware:  # type: ignore
        pass
