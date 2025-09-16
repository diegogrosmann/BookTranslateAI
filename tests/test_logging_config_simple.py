"""
Simple tests for the logging_config.py module
Testing only classes that actually exist.
"""

import logging
import os
import tempfile

from src.logging_config import CleanTerminalHandler, ColoredFormatter, setup_logging


class TestColoredFormatter:
    """Tests for the ColoredFormatter class."""

    def test_colored_formatter_creation(self):
        """Test creation of colored formatter."""
        formatter = ColoredFormatter(fmt="%(levelname)s - %(message)s")
        assert formatter is not None
        assert hasattr(formatter, "COLORS")

    def test_format_with_colors(self):
        """Test formatting with colors."""
        formatter = ColoredFormatter(fmt="%(levelname)s - %(message)s")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should contain ANSI color codes
        assert "\033[32m" in formatted  # Green for INFO
        assert "\033[0m" in formatted  # Reset
        assert "Test message" in formatted


class TestCleanTerminalHandler:
    """Tests for the CleanTerminalHandler class."""

    def test_clean_terminal_handler_creation(self):
        """Test creation of clean handler."""
        handler = CleanTerminalHandler(show_debug=True)
        assert handler.show_debug is True
        assert handler.last_message == ""

    def test_clean_terminal_handler_default(self):
        """Test creation with default configuration."""
        handler = CleanTerminalHandler()
        assert handler.show_debug is False


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")

    def teardown_method(self):
        """Cleanup after each test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        setup_logging(
            log_file=self.log_file, log_level="INFO", show_debug_in_terminal=False
        )

        # Verify root logger was configured
        root_logger = logging.getLogger()
        assert root_logger.level <= logging.INFO

        # Verify handlers were added
        assert len(root_logger.handlers) > 0


# Simple integration test
class TestIntegration:
    """Basic integration test."""

    def test_basic_logging_workflow(self):
        """Test basic logging workflow."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "integration.log")

        try:
            # Configure logging
            setup_logging(log_file=log_file, log_level="INFO")

            # Create logger and test
            logger = logging.getLogger("test.integration")
            logger.info("Test message")

            # Verify file was created
            assert os.path.exists(log_file)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

            # Clear handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
