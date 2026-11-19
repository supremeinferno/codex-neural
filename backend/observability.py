import contextvars
import logging
import time
from contextlib import contextmanager


logger = logging.getLogger("backend.performance")
request_id_context = contextvars.ContextVar("request_id", default="-")


@contextmanager
def measure_stage(stage: str):
    started_at = time.perf_counter()
    outcome = "success"
    error_type = None

    try:
        yield
    except Exception as error:
        outcome = "error"
        error_type = type(error).__name__
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "event=stage_timing stage=%s outcome=%s duration_ms=%.2f "
            "request_id=%s error_type=%s",
            stage,
            outcome,
            elapsed_ms,
            request_id_context.get(),
            error_type or "-",
        )
