from __future__ import annotations

import json
import logging
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from uuid import uuid4

_operation_id: ContextVar[str] = ContextVar("minutas_operation_id", default="startup")


@dataclass(frozen=True)
class FailureRecord:
    timestamp: str
    operation_id: str
    origin: str
    exception_type: str
    message: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, sort_keys=True)


class OperationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.operation_id = _operation_id.get()
        return True


def configure_logger(log_directory: Path, *, level: int = logging.INFO) -> logging.Logger:
    """Build an idempotent rotating application logger."""

    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("minutas_ash")
    logger.setLevel(level)
    logger.propagate = False

    target = (log_directory / "MinutasASH.log").resolve()
    for existing in list(logger.handlers):
        if isinstance(existing, RotatingFileHandler):
            if Path(existing.baseFilename).resolve() == target:
                existing.setLevel(level)
                return logger
            logger.removeHandler(existing)
            existing.close()

    handler = RotatingFileHandler(
        target,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.addFilter(OperationFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | op=%(operation_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


@contextmanager
def operation(operation_id: str | None = None) -> Iterator[str]:
    """Correlate all records emitted inside one application operation."""

    current = operation_id or uuid4().hex[:12]
    token = _operation_id.set(current)
    try:
        yield current
    finally:
        _operation_id.reset(token)


def failure_record(exc: BaseException, *, origin: str) -> FailureRecord:
    return FailureRecord(
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        operation_id=_operation_id.get(),
        origin=origin,
        exception_type=type(exc).__name__,
        message=str(exc),
    )


def install_exception_hooks(
    logger: logging.Logger,
    notify_user: Callable[[str], None] | None = None,
) -> None:
    """Log uncaught main-thread and worker-thread failures with correlation."""

    def report(
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType | None,
        *,
        origin: str,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, traceback)
            return
        record = failure_record(exc_value, origin=origin)
        logger.critical(
            "unhandled_failure=%s", record.to_json(), exc_info=(exc_type, exc_value, traceback)
        )
        if notify_user is not None:
            try:
                notify_user("Ocurrió un error interno. Revise el registro de diagnóstico.")
            except Exception:
                logger.exception("No fue posible mostrar el aviso de error")

    def main_hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        report(exc_type, exc_value, traceback, origin="main_thread")

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        thread_name = args.thread.name if args.thread else "unknown"
        exc_value = args.exc_value or RuntimeError("Excepción de hilo sin detalle")
        report(
            args.exc_type,
            exc_value,
            args.exc_traceback,
            origin=f"thread:{thread_name}",
        )

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
