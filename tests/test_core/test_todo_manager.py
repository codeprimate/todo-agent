"""
Tests for TodoManager.
"""

import unittest
from unittest.mock import Mock, patch

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
        with patch.object(self.todo_shell, "add", return_value="Task added"):
            result = self.todo_manager.add_task("Test task", due="2025-01-15")
            self.assertIn("due:2025-01-15", result)

    def test_set_due_date_with_valid_date(self):
        """Test setting due date with valid date format."""
        with patch.object(self.todo_shell, "set_due_date", return_value="Task updated"):
            result = self.todo_manager.set_due_date(1, "2025-01-15")
            self.assertIn("Set due date 2025-01-15 for task 1", result)

    def test_set_due_date_removes_due_date_with_empty_string(self):
        """Test that set_due_date removes due date when empty string is provided."""
        with patch.object(self.todo_shell, "set_due_date", return_value="Task updated"):
            result = self.todo_manager.set_due_date(1, "")
            self.assertIn("Removed due date from task 1", result)

    def test_set_due_date_removes_due_date_with_whitespace_only(self):
        """Test that set_due_date removes due date when only whitespace is provided."""
        with patch.object(self.todo_shell, "set_due_date", return_value="Task updated"):
            result = self.todo_manager.set_due_date(1, "   ")
            self.assertIn("Removed due date from task 1", result)

    def test_set_context_with_valid_context(self):
        """Test setting context with valid context name."""
        with patch.object(self.todo_shell, "set_context", return_value="Task updated"):
            result = self.todo_manager.set_context(1, "office")
            self.assertIn("Set context @office for task 1", result)

    def test_set_context_removes_context_with_empty_string(self):
        """Test that set_context removes context when empty string is provided."""
        with patch.object(self.todo_shell, "set_context", return_value="Task updated"):
            result = self.todo_manager.set_context(1, "")
            self.assertIn("Removed context from task 1", result)

    def test_set_context_removes_context_with_whitespace_only(self):
        """Test that set_context removes context when only whitespace is provided."""
        with patch.object(self.todo_shell, "set_context", return_value="Task updated"):
            result = self.todo_manager.set_context(1, "   ")
            self.assertIn("Removed context from task 1", result)

    def test_set_context_handles_context_with_at_symbol(self):
        """Test that set_context handles context names that already have @ symbol."""
        with patch.object(self.todo_shell, "set_context", return_value="Task updated"):
            result = self.todo_manager.set_context(1, "@office")
            self.assertIn("Set context @office for task 1", result)

    def test_set_context_raises_error_for_empty_context_after_cleaning(self):
        """Test that set_context raises error for context that becomes empty after cleaning."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.set_context(1, "@")
        self.assertIn("Context name cannot be empty", str(context.exception))

    def test_set_due_date_with_invalid_date_format(self):
        """Test setting due date with invalid date format raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.set_due_date(1, "invalid-date")
        self.assertIn("Invalid due date format", str(context.exception))

    def test_set_due_date_with_invalid_date_format_short(self):
        """Test setting due date with short date format raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.set_due_date(1, "2025/1/5")
        self.assertIn("Invalid due date format", str(context.exception))

    def test_add_task_with_invalid_duration_format(self):
        """Test adding a task with invalid duration format raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", duration="30s")
        self.assertIn("Invalid duration format", str(context.exception))

    def test_add_task_with_invalid_duration_unit(self):
        """Test adding a task with invalid duration unit raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", duration="30s")
        self.assertIn("Invalid duration format", str(context.exception))

    def test_add_task_with_invalid_duration_value(self):
        """Test adding a task with invalid duration value raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", duration="0m")
        self.assertIn("Must be a positive number", str(context.exception))

    def test_add_task_with_negative_duration(self):
        """Test adding a task with negative duration raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", duration="-30m")
        self.assertIn("Must be a positive number", str(context.exception))

    def test_add_task_with_empty_duration(self):
        """Test adding a task with empty duration raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.add_task("Test task", duration="")
        self.assertIn("Duration must be a non-empty string", str(context.exception))

    def test_add_task_with_duration(self):
        """Test adding a task with duration parameter."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task(
            "Test task",
            duration="30m",
        )
        self.assertEqual(result, "Added task: Test task duration:30m")
        self.todo_shell.add.assert_called_once_with("Test task duration:30m")

    def test_add_task_with_all_parameters_including_duration(self):
        """Test adding a task with all parameters including duration."""
        self.todo_shell.add.return_value = "Test task"
        result = self.todo_manager.add_task(
            "Test task",
            priority="A",
            project="work",
            context="office",
            due="2024-01-15",
            duration="2h",
        )
        self.assertEqual(
            result,
            "Added task: (A) Test task +work @office due:2024-01-15 duration:2h",
        )
        self.todo_shell.add.assert_called_once_with(
            "(A) Test task +work @office due:2024-01-15 duration:2h"
        )

    def test_list_tasks(self):
        """Test listing tasks."""
        self.todo_shell.list_tasks.return_value = "1. Task 1\n2. Task 2"
        result = self.todo_manager.list_tasks()
        self.assertEqual(result, "1. Task 1\n2. Task 2")
        self.todo_shell.list_tasks.assert_called_once_with(None, suppress_color=True)

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
        self.todo_shell.list_completed.assert_called_once_with(
            None, suppress_color=True
        )

    def test_list_completed_tasks_with_project_filter(self):
        """Test listing completed tasks with project filter."""
        self.todo_shell.list_completed.return_value = "1. Work task completed"
        result = self.todo_manager.list_completed_tasks(project="work")
        self.assertEqual(result, "1. Work task completed")
        self.todo_shell.list_completed.assert_called_once_with(
            "+work", suppress_color=True
        )

    def test_list_completed_tasks_with_context_filter(self):
        """Test listing completed tasks with context filter."""
        self.todo_shell.list_completed.return_value = "1. Office task completed"
        result = self.todo_manager.list_completed_tasks(context="office")
        self.assertEqual(result, "1. Office task completed")
        self.todo_shell.list_completed.assert_called_once_with(
            "@office", suppress_color=True
        )

    def test_list_completed_tasks_with_text_search(self):
        """Test listing completed tasks with text search."""
        self.todo_shell.list_completed.return_value = "1. Review task completed"
        result = self.todo_manager.list_completed_tasks(text_search="review")
        self.assertEqual(result, "1. Review task completed")
        self.todo_shell.list_completed.assert_called_once_with(
            "review", suppress_color=True
        )

    def test_list_completed_tasks_with_date_filters(self):
        """Test listing completed tasks with date filters."""
        self.todo_shell.list_completed.return_value = "1. Task completed in date range"
        result = self.todo_manager.list_completed_tasks(
            date_from="2025-08-01", date_to="2025-08-31"
        )
        self.assertEqual(result, "1. Task completed in date range")
        # With both date_from and date_to, we use the year-month pattern from date_from
        self.todo_shell.list_completed.assert_called_once_with(
            "2025-08", suppress_color=True
        )

    def test_list_completed_tasks_with_date_from_only(self):
        """Test listing completed tasks with only date_from filter."""
        self.todo_shell.list_completed.return_value = "1. Task completed from date"
        result = self.todo_manager.list_completed_tasks(date_from="2025-08-01")
        self.assertEqual(result, "1. Task completed from date")
        self.todo_shell.list_completed.assert_called_once_with(
            "2025-08-01", suppress_color=True
        )

    def test_list_completed_tasks_with_date_to_only(self):
        """Test listing completed tasks with only date_to filter."""
        self.todo_shell.list_completed.return_value = "1. Task completed in month"
        result = self.todo_manager.list_completed_tasks(date_to="2025-08-31")
        self.assertEqual(result, "1. Task completed in month")
        # With only date_to, we use the year-month pattern
        self.todo_shell.list_completed.assert_called_once_with(
            "2025-08", suppress_color=True
        )

    def test_list_completed_tasks_with_multiple_filters(self):
        """Test listing completed tasks with multiple filters."""
        self.todo_shell.list_completed.return_value = (
            "1. Work task from office completed"
        )
        result = self.todo_manager.list_completed_tasks(
            project="work", context="office", text_search="review"
        )
        self.assertEqual(result, "1. Work task from office completed")
        self.todo_shell.list_completed.assert_called_once_with(
            "+work @office review", suppress_color=True
        )

    def test_list_completed_tasks_with_raw_filter(self):
        """Test listing completed tasks with raw filter string."""
        self.todo_shell.list_completed.return_value = "1. Custom filtered task"
        result = self.todo_manager.list_completed_tasks(filter="+urgent @home")
        self.assertEqual(result, "1. Custom filtered task")
        self.todo_shell.list_completed.assert_called_once_with(
            "+urgent @home", suppress_color=True
        )

    def test_list_completed_tasks_no_results(self):
        """Test listing completed tasks when no results found."""
        self.todo_shell.list_completed.return_value = ""
        result = self.todo_manager.list_completed_tasks(project="nonexistent")
        self.assertEqual(result, "No completed tasks found matching the criteria.")
        self.todo_shell.list_completed.assert_called_once_with(
            "+nonexistent", suppress_color=True
        )

    def test_add_task_sanitizes_inputs(self):
        """Test that add_task sanitizes inputs to prevent duplicates."""
        # Mock the todo_shell
        mock_shell = Mock()
        mock_shell.add.return_value = "1 Test task +project1 @context1"

        manager = TodoManager(mock_shell)

        # Test with inputs that already have + and @ symbols
        result = manager.add_task(
            description="Test task",
            project="+project1",  # Already has + symbol
            context="@context1",  # Already has @ symbol
        )

        # Verify the task was added with properly formatted projects and contexts
        mock_shell.add.assert_called_once()
        call_args = mock_shell.add.call_args[0][0]

        # Should have exactly one instance of each (sanitization prevents duplicates)
        assert call_args.count("+project1") == 1
        assert call_args.count("@context1") == 1

        # Verify the result message
        assert "Added task:" in result

    def test_parse_task_components_deduplicates(self):
        """Test that _parse_task_components deduplicates projects and contexts."""
        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Test with duplicate projects and contexts in the task line
        task_line = "1 (A) Task description +project1 +project1 +project2 @context1 @context1 @context2"
        components = shell._parse_task_components(task_line)

        # Verify deduplication
        assert components["projects"] == [
            "+project1",
            "+project2",
        ]  # Sorted and deduplicated
        assert components["contexts"] == [
            "@context1",
            "@context2",
        ]  # Sorted and deduplicated
        assert components["priority"] == "A"
        assert components["description"] == "Task description"

    def test_reconstruct_task_maintains_deduplication(self):
        """Test that _reconstruct_task maintains deduplication."""
        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Create components with potential duplicates
        components = {
            "priority": "A",
            "description": "Test task",
            "projects": ["+project1", "+project1", "+project2"],  # Duplicate project1
            "contexts": ["@context1", "@context1", "@context2"],  # Duplicate context1
            "due": "2024-01-01",
            "other_tags": [],
        }

        # Reconstruct the task
        reconstructed = shell._reconstruct_task(components)

        # Verify that duplicates are preserved in reconstruction (since we handle deduplication in parsing)
        # This is expected behavior - reconstruction should preserve the exact components given
        assert reconstructed.count("+project1") == 2
        assert reconstructed.count("+project2") == 1
        assert reconstructed.count("@context1") == 2
        assert reconstructed.count("@context2") == 1

    def test_todo_shell_set_project_actually_prevents_duplicates(self):
        """Test that the todo_shell set_project method actually prevents duplicates."""
        from unittest.mock import patch

        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Mock the list_tasks method to return a task with existing projects
        with patch.object(shell, "list_tasks") as mock_list_tasks:
            mock_list_tasks.return_value = (
                "1 (A) Existing task +existing_project @existing_context"
            )

            # Mock the replace method to capture what gets called
            with patch.object(shell, "replace") as mock_replace:
                mock_replace.return_value = (
                    "1 (A) Existing task +existing_project @existing_context"
                )

                # Try to add a project that already exists
                result = shell.set_project(1, ["existing_project"])

                # Since the project already exists, replace should NOT be called
                # (our deduplication logic prevents unnecessary updates)
                mock_replace.assert_not_called()

                # The result should be the reconstructed task without duplicates
                assert "+existing_project" in result
                assert result.count("+existing_project") == 1  # Only one instance

    def test_todo_shell_set_context_actually_prevents_duplicates(self):
        """Test that the todo_shell set_context method actually prevents duplicates."""
        from unittest.mock import patch

        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Mock the list_tasks method to return a task with existing context
        with patch.object(shell, "list_tasks") as mock_list_tasks:
            mock_list_tasks.return_value = (
                "1 (A) Existing task +existing_project @existing_context"
            )

            # Mock the replace method to capture what gets called
            with patch.object(shell, "replace") as mock_replace:
                mock_replace.return_value = (
                    "1 (A) Existing task +existing_project @existing_context"
                )

                # Try to set a context that already exists
                result = shell.set_context(1, "existing_context")

                # Since the context already exists, replace should NOT be called
                # (our deduplication logic prevents unnecessary updates)
                mock_replace.assert_not_called()

                # The result should be the reconstructed task without duplicates
                assert "@existing_context" in result
                assert result.count("@existing_context") == 1  # Only one instance

    def test_todo_shell_set_project_adds_new_projects(self):
        """Test that the todo_shell set_project method adds new projects and prevents duplicates."""
        from unittest.mock import patch

        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Mock the list_tasks method to return a task with existing projects
        with patch.object(shell, "list_tasks") as mock_list_tasks:
            mock_list_tasks.return_value = (
                "1 (A) Existing task +existing_project @existing_context"
            )

            # Mock the replace method to capture what gets called
            with patch.object(shell, "replace") as mock_replace:
                mock_replace.return_value = "1 (A) Existing task +existing_project +new_project @existing_context"

                # Try to add a new project
                shell.set_project(1, ["new_project"])

                # Since we're adding a new project, replace should be called
                mock_replace.assert_called_once()

                # Get the actual task description that was passed to replace
                actual_task_description = mock_replace.call_args[0][1]

                # Verify that the new project was added and no duplicates exist
                assert "+new_project" in actual_task_description
                assert actual_task_description.count("+existing_project") == 1
                assert actual_task_description.count("+new_project") == 1

    def test_todo_shell_set_context_adds_new_contexts(self):
        """Test that the todo_shell set_context method adds new contexts and prevents duplicates."""
        from unittest.mock import patch

        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Mock the list_tasks method to return a task with existing context
        with patch.object(shell, "list_tasks") as mock_list_tasks:
            mock_list_tasks.return_value = (
                "1 (A) Existing task +existing_project @existing_context"
            )

            # Mock the replace method to capture what gets called
            with patch.object(shell, "replace") as mock_replace:
                mock_replace.return_value = (
                    "1 (A) Existing task +existing_project @new_context"
                )

                # Try to set a new context
                shell.set_context(1, "new_context")

                # Since we're adding a new context, replace should be called
                mock_replace.assert_called_once()

                # Get the actual task description that was passed to replace
                actual_task_description = mock_replace.call_args[0][1]

                # Verify that the new context was added and the old context was replaced
                # (set_context replaces all contexts with the new one)
                assert "@new_context" in actual_task_description
                assert (
                    "@existing_context" not in actual_task_description
                )  # Old context replaced
                assert (
                    actual_task_description.count("@new_context") == 1
                )  # Only one instance

    def test_parse_task_components_actually_deduplicates(self):
        """Test that _parse_task_components actually removes duplicates from input."""
        from todo_agent.infrastructure.todo_shell import TodoShell

        # Create a TodoShell instance
        shell = TodoShell("/tmp/todo.txt")

        # Test with a task line that has multiple duplicates
        task_line = "1 (A) Task description +project1 +project1 +project1 +project2 @context1 @context1 @context2"
        components = shell._parse_task_components(task_line)

        # Verify that duplicates were actually removed
        assert len(components["projects"]) == 2  # Should only have 2 unique projects
        assert len(components["contexts"]) == 2  # Should only have 2 unique contexts

        # Verify the specific projects and contexts
        assert "+project1" in components["projects"]
        assert "+project2" in components["projects"]
        assert "@context1" in components["contexts"]
        assert "@context2" in components["contexts"]

        # Verify no duplicates exist in the lists
        assert components["projects"].count("+project1") == 1
        assert components["projects"].count("+project2") == 1
        assert components["contexts"].count("@context1") == 1
        assert components["contexts"].count("@context2") == 1

    def test_get_current_datetime(self):
        """Test getting current date and time."""
        with patch("todo_agent.core.todo_manager.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.side_effect = lambda fmt: {
                "%Y-%m-%d %H:%M:%S": "2025-01-15 10:30:00",
                "%A, %B %d, %Y at %I:%M %p": "Wednesday, January 15, 2025 at 10:30 AM",
            }[fmt]
            mock_now.isocalendar.return_value = (2025, 3, 3)
            mock_now.astimezone.return_value.tzinfo = Mock()
            mock_datetime.now.return_value = mock_now

            result = self.todo_manager.get_current_datetime()
            self.assertIn("2025-01-15 10:30:00", result)
            self.assertIn("Week 3", result)

    def test_create_completed_task_basic(self):
        """Test creating and immediately completing a task."""
        # Mock the todo_shell methods
        self.todo_shell.add.return_value = "Task added"
        self.todo_shell.list_tasks.return_value = "1 Test task\n2 Another task"
        self.todo_shell.complete.return_value = "Task completed"

        result = self.todo_manager.create_completed_task("Test task")

        # Verify the task was added
        self.todo_shell.add.assert_called_once_with("Test task")
        # Verify the task was completed (should find task number 1 since it contains "Test task")
        self.todo_shell.complete.assert_called_once_with(1)
        # Verify the result message
        self.assertIn("Created and completed task: Test task", result)

    def test_create_completed_task_with_project_and_context(self):
        """Test creating and completing a task with project and context."""
        self.todo_shell.add.return_value = "Task added"
        self.todo_shell.list_tasks.return_value = "1 Test task\n2 Another task"
        self.todo_shell.complete.return_value = "Task completed"

        result = self.todo_manager.create_completed_task(
            "Test task", project="work", context="office"
        )

        # Verify the task was added with project and context
        self.todo_shell.add.assert_called_once_with("Test task +work @office")
        # Verify the task was completed (should find task number 1 since it contains "Test task")
        self.todo_shell.complete.assert_called_once_with(1)
        self.assertIn("+work @office", result)

    def test_create_completed_task_with_custom_date(self):
        """Test creating and completing a task with a custom completion date."""
        self.todo_shell.addto.return_value = "Task added to done.txt"

        result = self.todo_manager.create_completed_task(
            "Test task", completion_date="2025-01-10"
        )

        # Verify the task was added directly to done.txt with the custom date
        self.todo_shell.addto.assert_called_once_with(
            "done.txt", "x 2025-01-10 Test task"
        )
        # Verify add and complete were NOT called when using custom date
        self.todo_shell.add.assert_not_called()
        self.todo_shell.complete.assert_not_called()
        self.assertIn("completed on 2025-01-10", result)

    def test_create_completed_task_with_invalid_date(self):
        """Test that invalid completion date raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.create_completed_task(
                "Test task", completion_date="invalid-date"
            )
        self.assertIn("Invalid completion date format", str(context.exception))

    def test_create_completed_task_sanitizes_project_and_context(self):
        """Test that project and context with existing symbols are properly sanitized."""
        self.todo_shell.add.return_value = "Task added"
        self.todo_shell.list_tasks.return_value = "1 Test task"
        self.todo_shell.complete.return_value = "Task completed"

        result = self.todo_manager.create_completed_task(
            "Test task", project="+work", context="@office"
        )

        # Verify the task was added with properly sanitized project and context
        self.todo_shell.add.assert_called_once_with("Test task +work @office")
        self.assertIn("+work @office", result)

    def test_create_completed_task_with_empty_project_after_sanitization(self):
        """Test that empty project after sanitization raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.create_completed_task("Test task", project="+")
        self.assertIn("Project name cannot be empty", str(context.exception))

    def test_create_completed_task_with_empty_context_after_sanitization(self):
        """Test that empty context after sanitization raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.todo_manager.create_completed_task("Test task", context="@")
        self.assertIn("Context name cannot be empty", str(context.exception))

    def test_create_completed_task_no_tasks_after_addition(self):
        """Test that RuntimeError is raised when no tasks are found after addition."""
        self.todo_shell.add.return_value = "Task added"
        self.todo_shell.list_tasks.return_value = ""  # No tasks found

        with self.assertRaises(RuntimeError) as context:
            self.todo_manager.create_completed_task("Test task")
        self.assertIn("Failed to add task", str(context.exception))


if __name__ == "__main__":
    unittest.main()
