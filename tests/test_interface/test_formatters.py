"""
Tests for formatters module.
"""

import pytest
from rich.text import Text

from todo_agent.interface.formatters import TaskFormatter


class TestTaskFormatter:
    """Test TaskFormatter functionality."""

    def test_format_task_list_preserves_ansi_codes(self):
        """Test that format_task_list preserves ANSI color codes."""
        # Sample output with ANSI color codes (simulating todo.sh output)
        raw_tasks = "\033[1;33m1\033[0m (A) \033[1;32m2025-08-29\033[0m Clean cat box \033[1;34m@home\033[0m \033[1;35m+chores\033[0m \033[1;31mdue:2025-08-29\033[0m"

        result = TaskFormatter.format_task_list(raw_tasks)

        # The result should be a Rich Text object
        assert isinstance(result, Text)

        # Check that the Rich Text object contains the original ANSI codes
        # We can check this by looking at the raw text content
        result_str = result.plain
        assert "1" in result_str  # Task number should be present
        assert "(A)" in result_str  # Priority should be present
        assert "2025-08-29" in result_str  # Date should be present
        assert "@home" in result_str  # Context should be present
        assert "+chores" in result_str  # Project should be present
        assert "due:2025-08-29" in result_str  # Due date should be present

    def test_format_completed_tasks_preserves_ansi_codes(self):
        """Test that format_completed_tasks preserves ANSI color codes."""
        # Sample completed task output with ANSI color codes
        raw_tasks = "\033[1;32mx\033[0m \033[1;32m2025-08-29\033[0m \033[1;32m2025-08-28\033[0m Clean cat box \033[1;34m@home\033[0m \033[1;35m+chores\033[0m"

        result = TaskFormatter.format_completed_tasks(raw_tasks)

        # The result should be a Rich Text object
        assert isinstance(result, Text)

        # Check that the Rich Text object contains the original content
        # We can check this by looking at the raw text content
        result_str = result.plain
        assert "x" in result_str  # Completion marker should be present
        assert "2025-08-29" in result_str  # Completion date should be present
        assert "2025-08-28" in result_str  # Creation date should be present
        assert "@home" in result_str  # Context should be present
        assert "+chores" in result_str  # Project should be present

    def test_format_task_list_handles_empty_input(self):
        """Test that format_task_list handles empty input gracefully."""
        result = TaskFormatter.format_task_list("")
        assert isinstance(result, Text)
        assert "No tasks found" in str(result)

    def test_format_completed_tasks_handles_empty_input(self):
        """Test that format_completed_tasks handles empty input gracefully."""
        result = TaskFormatter.format_completed_tasks("")
        assert isinstance(result, Text)
        assert "No completed tasks found" in str(result)

    def test_format_task_list_handles_whitespace_only(self):
        """Test that format_task_list handles whitespace-only input."""
        result = TaskFormatter.format_task_list("   \n  \t  ")
        assert isinstance(result, Text)
        assert "No tasks found" in str(result)

    def test_format_completed_tasks_handles_whitespace_only(self):
        """Test that format_completed_tasks handles whitespace-only input."""
        result = TaskFormatter.format_completed_tasks("   \n  \t  ")
        assert isinstance(result, Text)
        assert "No completed tasks found" in str(result)
