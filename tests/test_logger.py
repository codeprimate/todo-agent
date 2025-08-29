"""
Tests for the Logger class.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from todo_agent.infrastructure.logger import Logger


class TestLogger:
    """Test cases for the Logger class."""

    def test_logger_initialization(self):
        """Test that logger initializes correctly."""
        logger = Logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.logger is not None

    def test_log_level_environment_variable_detection(self):
        """Test that LOG_LEVEL environment variable is detected correctly."""
        logger = Logger("test_logger")

        # Test with LOG_LEVEL not set (should default to INFO)
        with patch.dict(os.environ, {}, clear=True):
            assert logger._get_log_level() == logging.INFO

        # Test with various log level values
        level_tests = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("debug", logging.DEBUG),  # Test case insensitivity
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ]

        for log_level_str, expected_level in level_tests:
            with patch.dict(os.environ, {"LOG_LEVEL": log_level_str}, clear=True):
                assert logger._get_log_level() == expected_level

        # Test with invalid log level (should default to INFO)
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=True):
            assert logger._get_log_level() == logging.INFO

    def test_logs_directory_creation(self):
        """Test that logs directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Test without TODO_DIR (should create local logs directory)
                with patch.dict(os.environ, {}, clear=True):
                    # Remove logs directory if it exists
                    if Path("logs").exists():
                        import shutil

                        shutil.rmtree("logs")

                    logger = Logger("test_logger")
                    logger._ensure_logs_directory()

                    # Verify the directory was created locally
                    assert Path("logs").exists()

                # Test with TODO_DIR (should create logs directory in TODO_DIR)
                with patch.dict(os.environ, {"TODO_DIR": temp_dir}, clear=True):
                    # Remove logs directory if it exists
                    logs_in_todo_dir = Path(temp_dir) / "logs"
                    if logs_in_todo_dir.exists():
                        import shutil

                        shutil.rmtree(logs_in_todo_dir)

                    logger = Logger("test_logger")
                    logger._ensure_logs_directory()

                    # Verify the directory was created in TODO_DIR
                    assert logs_in_todo_dir.exists()
            finally:
                os.chdir(original_cwd)

    def test_file_handler_setup(self):
        """Test that file handler is set up correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                logger = Logger("test_logger")
                logger._setup_file_handler()

                # Verify file handler was added
                assert len(logger.logger.handlers) > 0

                # Verify at least one handler is a FileHandler
                file_handlers = [
                    h
                    for h in logger.logger.handlers
                    if isinstance(h, logging.FileHandler)
                ]
                assert len(file_handlers) > 0
            finally:
                os.chdir(original_cwd)

    def test_console_handler_setup_with_log_level(self):
        """Test that console handler is set up correctly with appropriate log level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                logger = Logger("test_logger")

                # Test with different log levels
                level_tests = [
                    ("DEBUG", logging.DEBUG),
                    ("INFO", logging.INFO),
                    ("WARNING", logging.WARNING),
                    ("ERROR", logging.ERROR),
                ]

                for log_level_str, expected_level in level_tests:
                    with patch.dict(
                        os.environ,
                        {"DEBUG": "1", "LOG_LEVEL": log_level_str},
                        clear=True,
                    ):
                        # Clear existing handlers
                        logger.logger.handlers.clear()

                        # Set up console handler
                        logger._setup_console_handler()

                        # Verify console handler was added with correct level
                        console_handlers = [
                            h
                            for h in logger.logger.handlers
                            if isinstance(h, logging.StreamHandler)
                            and not isinstance(h, logging.FileHandler)
                        ]
                        assert len(console_handlers) > 0
                        assert console_handlers[0].level == expected_level
            finally:
                os.chdir(original_cwd)

    def test_logging_methods(self):
        """Test that all logging methods work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                logger = Logger("test_logger")

                # Test all logging methods
                logger.debug("Debug message")
                logger.info("Info message")
                logger.warning("Warning message")
                logger.error("Error message")
                logger.critical("Critical message")

                # Verify no exceptions were raised
                assert True
            finally:
                os.chdir(original_cwd)

    def test_logger_with_debug_level(self):
        """Test logger behavior when LOG_LEVEL is set to DEBUG."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                with patch.dict(
                    os.environ, {"DEBUG": "1", "LOG_LEVEL": "DEBUG"}, clear=True
                ):
                    logger = Logger("test_logger")

                    # Should have both file and console handlers
                    assert len(logger.logger.handlers) >= 2

                    # Console handler should be set to DEBUG level
                    console_handlers = [
                        h
                        for h in logger.logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)
                    ]
                    assert len(console_handlers) > 0
                    assert console_handlers[0].level == logging.DEBUG
            finally:
                os.chdir(original_cwd)

    def test_logger_with_info_level(self):
        """Test logger behavior when LOG_LEVEL is set to INFO."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                with patch.dict(
                    os.environ, {"DEBUG": "1", "LOG_LEVEL": "INFO"}, clear=True
                ):
                    logger = Logger("test_logger")

                    # Should have both file and console handlers
                    assert len(logger.logger.handlers) >= 2

                    # Console handler should be set to INFO level
                    console_handlers = [
                        h
                        for h in logger.logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)
                    ]
                    assert len(console_handlers) > 0
                    assert console_handlers[0].level == logging.INFO
            finally:
                os.chdir(original_cwd)

    def test_logger_with_warning_level(self):
        """Test logger behavior when LOG_LEVEL is set to WARNING."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                with patch.dict(
                    os.environ, {"DEBUG": "1", "LOG_LEVEL": "WARNING"}, clear=True
                ):
                    logger = Logger("test_logger")

                    # Should have both file and console handlers
                    assert len(logger.logger.handlers) >= 2

                    # Console handler should be set to WARNING level
                    console_handlers = [
                        h
                        for h in logger.logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)
                    ]
                    assert len(console_handlers) > 0
                    assert console_handlers[0].level == logging.WARNING
            finally:
                os.chdir(original_cwd)

    def test_logger_with_error_level(self):
        """Test logger behavior when LOG_LEVEL is set to ERROR."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                with patch.dict(
                    os.environ, {"DEBUG": "1", "LOG_LEVEL": "ERROR"}, clear=True
                ):
                    logger = Logger("test_logger")

                    # Should have both file and console handlers
                    assert len(logger.logger.handlers) >= 2

                    # Console handler should be set to ERROR level
                    console_handlers = [
                        h
                        for h in logger.logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)
                    ]
                    assert len(console_handlers) > 0
                    assert console_handlers[0].level == logging.ERROR
            finally:
                os.chdir(original_cwd)

    def test_logger_without_log_level_set(self):
        """Test logger behavior when LOG_LEVEL environment variable is not set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                with patch.dict(os.environ, {"DEBUG": "1"}, clear=True):
                    logger = Logger("test_logger")

                    # Should have both file and console handlers (console defaults to INFO)
                    assert len(logger.logger.handlers) >= 2

                    # Console handler should default to INFO level
                    console_handlers = [
                        h
                        for h in logger.logger.handlers
                        if isinstance(h, logging.StreamHandler)
                        and not isinstance(h, logging.FileHandler)
                    ]
                    assert len(console_handlers) > 0
                    assert console_handlers[0].level == logging.INFO
            finally:
                os.chdir(original_cwd)
