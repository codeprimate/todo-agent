"""
Tests for TodoManager.
"""

import unittest
import pytest
from unittest.mock import Mock

try:
    from todo_agent.core.todo_manager import TodoManager
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.todo_manager import TodoManager


class TestTodoManager(unittest.TestCase):
    """Test cases for TodoManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.todo_shell = Mock()
        self.todo_manager = TodoManager(self.todo_shell)

    def test_add_task(self):
        """Test adding a task."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task")
        self.assertEqual(result, "Added task: Test task")
        self.todo_shell.add.assert_called_once_with("Test task")

    def test_list_tasks(self):
        """Test listing tasks."""
        self.todo_shell.list_tasks.return_value = "1. Task 1\n2. Task 2"
        result = self.todo_manager.list_tasks()
        self.assertEqual(result, "1. Task 1\n2. Task 2")
        self.todo_shell.list_tasks.assert_called_once_with(None)

    def test_complete_task(self):
        """Test completing a task."""
        self.todo_shell.complete.return_value = "Task 1"
        result = self.todo_manager.complete_task(1)
        self.assertEqual(result, "Completed task 1: Task 1")
        self.todo_shell.complete.assert_called_once_with(1)

    def test_list_completed_tasks_no_filter(self):
        """Test listing completed tasks without filter."""
        self.todo_shell.list_completed.return_value = "1. Completed task 1\n2. Completed task 2"
        result = self.todo_manager.list_completed_tasks()
        self.assertEqual(result, "1. Completed task 1\n2. Completed task 2")
        self.todo_shell.list_completed.assert_called_once_with(None)

    def test_list_completed_tasks_with_project_filter(self):
        """Test listing completed tasks with project filter."""
        self.todo_shell.list_completed.return_value = "1. Work task completed"
        result = self.todo_manager.list_completed_tasks(project="work")
        self.assertEqual(result, "1. Work task completed")
        self.todo_shell.list_completed.assert_called_once_with("+work")

    def test_list_completed_tasks_with_context_filter(self):
        """Test listing completed tasks with context filter."""
        self.todo_shell.list_completed.return_value = "1. Office task completed"
        result = self.todo_manager.list_completed_tasks(context="office")
        self.assertEqual(result, "1. Office task completed")
        self.todo_shell.list_completed.assert_called_once_with("@office")

    def test_list_completed_tasks_with_text_search(self):
        """Test listing completed tasks with text search."""
        self.todo_shell.list_completed.return_value = "1. Review task completed"
        result = self.todo_manager.list_completed_tasks(text_search="review")
        self.assertEqual(result, "1. Review task completed")
        self.todo_shell.list_completed.assert_called_once_with("review")

    def test_list_completed_tasks_with_date_filters(self):
        """Test listing completed tasks with date filters."""
        self.todo_shell.list_completed.return_value = "1. Task completed in date range"
        result = self.todo_manager.list_completed_tasks(date_from="2025-08-01", date_to="2025-08-31")
        self.assertEqual(result, "1. Task completed in date range")
        # With both date_from and date_to, we use the year-month pattern from date_from
        self.todo_shell.list_completed.assert_called_once_with("2025-08")

    def test_list_completed_tasks_with_date_from_only(self):
        """Test listing completed tasks with only date_from filter."""
        self.todo_shell.list_completed.return_value = "1. Task completed from date"
        result = self.todo_manager.list_completed_tasks(date_from="2025-08-01")
        self.assertEqual(result, "1. Task completed from date")
        self.todo_shell.list_completed.assert_called_once_with("2025-08-01")

    def test_list_completed_tasks_with_date_to_only(self):
        """Test listing completed tasks with only date_to filter."""
        self.todo_shell.list_completed.return_value = "1. Task completed in month"
        result = self.todo_manager.list_completed_tasks(date_to="2025-08-31")
        self.assertEqual(result, "1. Task completed in month")
        # With only date_to, we use the year-month pattern
        self.todo_shell.list_completed.assert_called_once_with("2025-08")

    def test_list_completed_tasks_with_multiple_filters(self):
        """Test listing completed tasks with multiple filters."""
        self.todo_shell.list_completed.return_value = "1. Work task from office completed"
        result = self.todo_manager.list_completed_tasks(project="work", context="office", text_search="review")
        self.assertEqual(result, "1. Work task from office completed")
        self.todo_shell.list_completed.assert_called_once_with("+work @office review")

    def test_list_completed_tasks_with_raw_filter(self):
        """Test listing completed tasks with raw filter string."""
        self.todo_shell.list_completed.return_value = "1. Custom filtered task"
        result = self.todo_manager.list_completed_tasks(filter="+urgent @home")
        self.assertEqual(result, "1. Custom filtered task")
        self.todo_shell.list_completed.assert_called_once_with("+urgent @home")

    def test_list_completed_tasks_no_results(self):
        """Test listing completed tasks when no results found."""
        self.todo_shell.list_completed.return_value = ""
        result = self.todo_manager.list_completed_tasks(project="nonexistent")
        self.assertEqual(result, "No completed tasks found matching the criteria.")
        self.todo_shell.list_completed.assert_called_once_with("+nonexistent")

if __name__ == "__main__":
    unittest.main()
