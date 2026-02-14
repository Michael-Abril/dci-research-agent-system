"""
Logging configuration for DCI Research Agent System.
"""

import logging
import os
import sys


def setup_logging(name: str = "dci_agent") -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name (typically module name).

    Returns:
        Configured logger instance.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level, logging.INFO))
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level, logging.INFO))

    return logger
