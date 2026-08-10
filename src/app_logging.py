from __future__ import annotations

import logging

from src.observability import configure_logger
from src.runtime_paths import logs_dir

LOGGER_NAME = "minutas_ash"


def setup_logging() -> logging.Logger:
    return configure_logger(logs_dir())


def get_logger() -> logging.Logger:
    return setup_logging()