"""Structured logging utility for autocopy_tool."""
import logging
import sys
from pathlib import Path


def get_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger.

    Args:
        name: Logger name (typically ``__name__`` of the calling module).
        log_file: Optional path to write log output to a file.
        level: Logging level (default: INFO).

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
