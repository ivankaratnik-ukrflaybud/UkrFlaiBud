import logging
from logging.config import dictConfig
from pathlib import Path

import yaml

from app.core.config import settings


def configure_logging() -> None:
    config_path = Path(settings.logging_config_path)
    if config_path.exists():
        with config_path.open(encoding="utf-8") as config_file:
            dictConfig(yaml.safe_load(config_file))
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
