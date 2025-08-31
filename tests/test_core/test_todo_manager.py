"""
Tests for TodoManager.
"""

import unittest
from unittest.mock import Mock

import pytest

try:
    from todo_agent.core.todo_manager import TodoManager
except ImportError:
    import os
    import sys

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

    def test_add_task_with_invalid_priority(self):
        """Test adding a task with invalid priority raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", priority="invalid")
        self.assertIn("Invalid priority", str(context.exception))

    def test_add_task_with_invalid_priority_lowercase(self):
        """Test adding a task with lowercase priority raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", priority="a")
        self.assertIn("Invalid priority", str(context.exception))

    def test_add_task_with_invalid_priority_multiple_chars(self):
        """Test adding a task with multiple character priority raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", priority="AB")
        self.assertIn("Invalid priority", str(context.exception))

    def test_add_task_sanitizes_project_with_plus(self):
        """Test that project with existing + symbol is properly sanitized."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task", project="+work")
        self.assertEqual(result, "Added task: Test task +work")
        self.todo_shell.add.assert_called_once_with("Test task +work")

    def test_add_task_sanitizes_context_with_at(self):
        """Test that context with existing @ symbol is properly sanitized."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task", context="@office")
        self.assertEqual(result, "Added task: Test task @office")
        self.todo_shell.add.assert_called_once_with("Test task @office")

    def test_add_task_with_empty_project_after_sanitization(self):
        """Test adding a task with empty project after removing + raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", project="+")
        self.assertIn("Project name cannot be empty", str(context.exception))

    def test_add_task_with_empty_context_after_sanitization(self):
        """Test adding a task with empty context after removing @ raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", context="@")
        self.assertIn("Context name cannot be empty", str(context.exception))

    def test_add_task_with_invalid_due_date(self):
        """Test adding a task with invalid due date format raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", due="invalid-date")
        self.assertIn("Invalid due date format", str(context.exception))

    def test_add_task_with_valid_due_date(self):
        """Test adding a task with valid due date format."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task", due="2024-01-15")
        self.assertEqual(result, "Added task: Test task due:2024-01-15")
        self.todo_shell.add.assert_called_once_with("Test task due:2024-01-15")

    def test_add_task_with_valid_recurring_daily(self):
        """Test adding a task with valid daily recurring format."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task", recurring="rec:daily")
        self.assertEqual(result, "Added task: Test task rec:daily")
        self.todo_shell.add.assert_called_once_with("Test task rec:daily")

    def test_add_task_with_valid_recurring_weekly_interval(self):
        """Test adding a task with valid weekly recurring format with interval."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task("Test task", recurring="rec:weekly:2")
        self.assertEqual(result, "Added task: Test task rec:weekly:2")
        self.todo_shell.add.assert_called_once_with("Test task rec:weekly:2")

    def test_add_task_with_invalid_recurring_format(self):
        """Test adding a task with invalid recurring format raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", recurring="invalid")
        self.assertIn("Invalid recurring format", str(context.exception))

    def test_add_task_with_invalid_recurring_frequency(self):
        """Test adding a task with invalid recurring frequency raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", recurring="rec:invalid")
        self.assertIn("Invalid frequency", str(context.exception))

    def test_add_task_with_invalid_recurring_interval(self):
        """Test adding a task with invalid recurring interval raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", recurring="rec:weekly:invalid")
        self.assertIn("Invalid interval", str(context.exception))

    def test_add_task_with_zero_recurring_interval(self):
        """Test adding a task with zero recurring interval raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", recurring="rec:weekly:0")
        self.assertIn("Must be a positive integer", str(context.exception))

    def test_add_task_with_all_parameters_including_recurring(self):
        """Test adding a task with all parameters including recurring."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task(
            "Test task", 
            priority="A", 
            project="work", 
            context="office", 
            due="2024-01-15",
            recurring="rec:daily"
        )
        self.assertEqual(result, "Added task: (A) Test task +work @office due:2024-01-15 rec:daily")
        self.todo_shell.add.assert_called_once_with("(A) Test task +work @office due:2024-01-15 rec:daily")

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
        self.todo_shell.list_completed.return_value = (
            "1. Completed task 1\n2. Completed task 2"
        )
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
        result = self.todo_manager.list_completed_tasks(
            date_from="2025-08-01", date_to="2025-08-31"
        )
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
        self.todo_shell.list_completed.return_value = (
            "1. Work task from office completed"
        )
        result = self.todo_manager.list_completed_tasks(
            project="work", context="office", text_search="review"
        )
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
