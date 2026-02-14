"""Centralized logging configuration for the bot."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "personal_agent") -> logging.Logger:
    """Setup and return a configured logger.

    Args:
        name: Logger name (default: "personal_agent")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler - INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # File handler - DEBUG and above with rotation
    # Use absolute path to project root
    base_dir = Path(__file__).resolve().parent.parent.parent
    log_file = base_dir / "bot.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Default logger instance
logger = setup_logger()
