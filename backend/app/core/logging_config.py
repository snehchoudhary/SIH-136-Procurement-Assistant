import logging
import sys
from typing import Any


def configure_logging() -> logging.Logger:
    logger = logging.getLogger('pilotproof')
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    ))
    logger.addHandler(handler)
    return logger


logger = configure_logging()
