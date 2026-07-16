import logging
from logging.config import dictConfig
from pathlib import Path

import yaml

from app.core.config import settings
from app.core.request_context import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


def configure_logging() -> None:
    config_path = Path(settings.logging_config_path)
    if config_path.exists():
        with config_path.open(encoding="utf-8") as config_file:
            dictConfig(yaml.safe_load(config_file))
        _attach_correlation_filter()
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] [%(correlation_id)s] %(message)s",
    )
    _attach_correlation_filter()


def _attach_correlation_filter() -> None:
    correlation_filter = CorrelationIdFilter()
    for logger_name in ("", "uvicorn.access", "uvicorn.error", "app"):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            handler.addFilter(correlation_filter)
