import logging

from src.config import LOG_LEVEL


def configure_logging() -> None:
    """Configure console logging for command-line agent runs."""
    level_name = LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
