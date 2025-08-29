"""
Logging infrastructure for todo.sh LLM agent.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """Custom logger that respects LOG_LEVEL environment variable and logs to screen and file."""

    def __init__(self, name: str = "todo_agent"):
        """
        Initialize the logger.

        Args:
            name: Logger name, defaults to "todo_agent"
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create logs directory if it doesn't exist
        self._ensure_logs_directory()

        # Set up file handler (always active)
        self._setup_file_handler()

        # Set up console handler with appropriate log level
        self._setup_console_handler()

    def _ensure_logs_directory(self) -> None:
        """Ensure the logs directory exists in TODO_DIR."""
        logs_dir = self._get_logs_directory()
        logs_dir.mkdir(exist_ok=True)

    def _get_logs_directory(self) -> Path:
        """Get the logs directory path from TODO_DIR environment variable."""
        todo_dir = os.getenv("TODO_DIR")
        if todo_dir:
            return Path(todo_dir) / "logs"
        else:
            # Fallback to local logs directory if TODO_DIR is not set
            return Path("logs")

    def _get_log_level(self) -> int:
        """Get log level from LOG_LEVEL environment variable."""
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Map string values to logging constants
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        return level_map.get(log_level_str, logging.INFO)

    def _should_log_to_console(self) -> bool:
        """Check if we should log to console based on DEBUG environment variable."""
        return os.getenv("DEBUG") is not None

    def _setup_file_handler(self) -> None:
        """Set up file handler for logging to file."""
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        logs_dir = self._get_logs_directory()
        log_file = logs_dir / f"todo_agent_{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create formatter for file logging
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(file_handler)

    def _setup_console_handler(self) -> None:
        """Set up console handler for logging to screen with appropriate log level."""
        # Only add console handler if DEBUG environment variable is set
        if not self._should_log_to_console():
            return

        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._get_log_level())

        # Create formatter for console logging (more concise)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(console_handler)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log a critical message."""
        self.logger.critical(message)

    def exception(self, message: str) -> None:
        """Log an exception message with traceback."""
        self.logger.exception(message)
