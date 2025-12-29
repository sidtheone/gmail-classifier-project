"""
Logging configuration for Gmail Email Classifier
Supports both file and console logging with different levels
"""

import logging
import os
from datetime import datetime
from colorama import Fore, Style


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"

        return super().format(record)


def setup_logger(name: str, log_level: str = "INFO", log_to_file: bool = True):
    """
    Setup logger with console and file handlers.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    logger.handlers = []

    # Set level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed logs)
    if log_to_file:
        os.makedirs('logs', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f'logs/classifier_{timestamp}.log'

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG level in file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str):
    """Get existing logger or create new one"""
    return logging.getLogger(name)
