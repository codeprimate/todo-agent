"""
Tests for TodoShell class.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

try:
    from todo_agent.core.exceptions import TodoShellError
    from todo_agent.infrastructure.todo_shell import TodoShell
except ImportError:
    from core.exceptions import TodoShellError
    from infrastructure.todo_shell import TodoShell


class TestTodoShell:
    """Test TodoShell functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.todo_shell = TodoShell("/path/to/todo.txt")

    def test_initialization_sets_correct_paths(self):
        """Test TodoShell initialization sets correct file and directory paths."""
        assert self.todo_shell.todo_file_path == "/path/to/todo.txt"
        assert self.todo_shell.todo_dir == "/path/to"

    def test_execute_success_returns_stdout(self):
        """Test successful command execution returns stdout content."""
        mock_result = Mock()
        mock_result.stdout = "Task added successfully\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = self.todo_shell.execute(["todo.sh", "add", "test task"])

            # Verify subprocess was called with correct parameters
            mock_run.assert_called_once_with(
                ["todo.sh", "add", "test task"],
                cwd="/path/to",
                capture_output=True,
                text=True,
                check=True,
            )
            # Verify the actual output is returned
            assert result == "Task added successfully"

    def test_execute_with_custom_cwd_uses_specified_directory(self):
        """Test command execution uses custom working directory when specified."""
        mock_result = Mock()
        mock_result.stdout = "Custom output\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = self.todo_shell.execute(["todo.sh", "ls"], cwd="/custom/path")

            # Verify subprocess was called with custom cwd
            mock_run.assert_called_once_with(
                ["todo.sh", "ls"],
                cwd="/custom/path",
                capture_output=True,
                text=True,
                check=True,
            )
            assert result == "Custom output"

    def test_execute_failure_raises_todo_shell_error(self):
        """Test command execution failure raises TodoShellError with stderr message."""
        error = subprocess.CalledProcessError(
            1, ["todo.sh", "invalid"], stderr="Command not found"
        )

        with patch("subprocess.run", side_effect=error):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: Command not found"
            ):
                self.todo_shell.execute(["todo.sh", "invalid"])

    def test_add_task_constructs_correct_command(self):
        """Test adding a task constructs the correct todo.sh command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Task added"
        ) as mock_execute:
            result = self.todo_shell.add("Buy groceries")

            # Verify the correct command was constructed
            mock_execute.assert_called_once_with(["todo.sh", "add", "Buy groceries"])
            assert result == "Task added"

    def test_list_tasks_no_filter_uses_ls_command(self):
        """Test listing tasks without filter uses the ls command."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Task 1\n2. Task 2"
        ) as mock_execute:
            result = self.todo_shell.list_tasks()

            # Verify the correct command was used
            mock_execute.assert_called_once_with(["todo.sh", "ls"], suppress_color=True)
            assert result == "1. Task 1\n2. Task 2"

    def test_list_tasks_with_filter_appends_filter_to_command(self):
        """Test listing tasks with filter appends the filter to the ls command."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Work task"
        ) as mock_execute:
            result = self.todo_shell.list_tasks("+work")

            # Verify filter was appended to command
            mock_execute.assert_called_once_with(
                ["todo.sh", "ls", "+work"], suppress_color=True
            )
            assert result == "1. Work task"

    def test_complete_task_uses_do_command_with_task_number(self):
        """Test completing a task uses the do command with the correct task number."""
        with patch.object(
            self.todo_shell, "execute", return_value="Task 1 completed"
        ) as mock_execute:
            result = self.todo_shell.complete(1)

            # Verify correct command with task number
            mock_execute.assert_called_once_with(["todo.sh", "do", "1"])
            assert result == "Task 1 completed"

    def test_replace_task_constructs_replace_command(self):
        """Test replacing task content constructs the correct replace command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Task replaced"
        ) as mock_execute:
            result = self.todo_shell.replace(1, "New task description")

            # Verify replace command with task number and new description
            mock_execute.assert_called_once_with(
                ["todo.sh", "replace", "1", "New task description"]
            )
            assert result == "Task replaced"

    def test_append_to_task_uses_append_command(self):
        """Test appending text to task uses the append command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Text appended"
        ) as mock_execute:
            result = self.todo_shell.append(1, "additional info")

            # Verify append command
            mock_execute.assert_called_once_with(
                ["todo.sh", "append", "1", "additional info"]
            )
            assert result == "Text appended"

    def test_prepend_to_task_uses_prepend_command(self):
        """Test prepending text to task uses the prepend command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Text prepended"
        ) as mock_execute:
            result = self.todo_shell.prepend(1, "urgent")

            # Verify prepend command
            mock_execute.assert_called_once_with(["todo.sh", "prepend", "1", "urgent"])
            assert result == "Text prepended"

    def test_delete_task_uses_force_delete_command(self):
        """Test deleting entire task uses the force delete command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Task deleted"
        ) as mock_execute:
            result = self.todo_shell.delete(1)

            # Verify force delete command
            mock_execute.assert_called_once_with(["todo.sh", "-f", "del", "1"])
            assert result == "Task deleted"

    def test_delete_task_term_uses_force_delete_with_term(self):
        """Test deleting specific term from task uses force delete with term."""
        with patch.object(
            self.todo_shell, "execute", return_value="Term deleted"
        ) as mock_execute:
            result = self.todo_shell.delete(1, "old")

            # Verify force delete with term
            mock_execute.assert_called_once_with(["todo.sh", "-f", "del", "1", "old"])
            assert result == "Term deleted"

    def test_set_priority_uses_priority_command(self):
        """Test that set_priority uses the correct todo.sh command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Priority set"
        ) as mock_execute:
            result = self.todo_shell.set_priority(1, "A")

            mock_execute.assert_called_once_with(["todo.sh", "pri", "1", "A"])
            assert result == "Priority set"

    def test_set_due_date_parses_and_reconstructs_task(self):
        """Test that set_due_date intelligently rewrites a task with new due date."""
        # Mock the list_tasks to return a sample task
        sample_task = "1 (A) Buy groceries +shopping @home due:2025-01-10"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ) as mock_list, patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "2025-01-15")

            # Should call list_tasks to get current task
            mock_list.assert_called_once()
            # Should call replace with updated task
            mock_replace.assert_called_once_with(
                1, "(A) Buy groceries +shopping @home due:2025-01-15"
            )
            assert result == "Task updated"

    def test_set_due_date_adds_due_date_to_task_without_one(self):
        """Test that set_due_date adds due date to task that doesn't have one."""
        # Mock the list_tasks to return a task without due date
        sample_task = "1 (B) Call dentist +health @phone"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "2025-01-20")

            # Should call replace with due date added
            mock_replace.assert_called_once_with(
                1, "(B) Call dentist +health @phone due:2025-01-20"
            )
            assert result == "Task updated"

    def test_set_due_date_preserves_all_components(self):
        """Test that set_due_date preserves all task components."""
        # Mock the list_tasks to return a complex task
        sample_task = (
            "1 (C) Review quarterly report +work @office due:2025-01-10 custom:tag"
        )
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "2025-01-25")

            # Should preserve all components and update due date
            expected = (
                "(C) Review quarterly report +work @office due:2025-01-25 custom:tag"
            )
            mock_replace.assert_called_once_with(1, expected)
            assert result == "Task updated"

    def test_set_due_date_handles_task_without_priority(self):
        """Test that set_due_date handles tasks without priority."""
        # Mock the list_tasks to return a task without priority
        sample_task = "1 Buy milk +shopping @grocery"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "2025-01-30")

            # Should preserve task without priority and add due date
            mock_replace.assert_called_once_with(
                1, "Buy milk +shopping @grocery due:2025-01-30"
            )
            assert result == "Task updated"

    def test_set_due_date_raises_error_for_invalid_task_number(self):
        """Test that set_due_date raises error for invalid task number."""
        # Mock the list_tasks to return only one task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Task number 5 not found"):
                self.todo_shell.set_due_date(5, "2025-01-15")

    def test_set_due_date_removes_due_date_with_empty_string(self):
        """Test that set_due_date removes due date when empty string is provided."""
        # Mock the list_tasks to return a task with due date
        sample_task = "1 (A) Buy groceries +shopping @home due:2025-01-10"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "")

            # Should remove due date from task
            mock_replace.assert_called_once_with(1, "(A) Buy groceries +shopping @home")
            assert result == "Task updated"

    def test_set_due_date_removes_due_date_with_whitespace_only(self):
        """Test that set_due_date removes due date when only whitespace is provided."""
        # Mock the list_tasks to return a task with due date
        sample_task = "1 (B) Call dentist +health @phone due:2025-01-15"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "   ")

            # Should remove due date from task
            mock_replace.assert_called_once_with(1, "(B) Call dentist +health @phone")
            assert result == "Task updated"

    def test_set_due_date_removes_due_date_from_task_without_priority(self):
        """Test that set_due_date removes due date from task without priority."""
        # Mock the list_tasks to return a task without priority but with due date
        sample_task = "1 Buy milk +shopping @grocery due:2025-01-20"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_due_date(1, "")

            # Should remove due date from task
            mock_replace.assert_called_once_with(1, "Buy milk +shopping @grocery")
            assert result == "Task updated"

    def test_set_context_parses_and_reconstructs_task(self):
        """Test that set_context intelligently rewrites a task with new context."""
        # Mock the list_tasks to return a sample task
        sample_task = "1 (A) Buy groceries +shopping @home due:2025-01-10"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ) as mock_list, patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "office")

            # Should call list_tasks to get current task
            mock_list.assert_called_once()
            # Should call replace with updated task
            mock_replace.assert_called_once_with(
                1, "(A) Buy groceries +shopping @office due:2025-01-10"
            )
            assert result == "Task updated"

    def test_set_context_adds_context_to_task_without_one(self):
        """Test that set_context adds context to task that doesn't have one."""
        # Mock the list_tasks to return a task without context
        sample_task = "1 (B) Call dentist +health"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "phone")

            # Should call replace with context added
            mock_replace.assert_called_once_with(1, "(B) Call dentist +health @phone")
            assert result == "Task updated"

    def test_set_context_preserves_all_components(self):
        """Test that set_context preserves all task components."""
        # Mock the list_tasks to return a complex task
        sample_task = (
            "1 (C) Review quarterly report +work @office due:2025-01-10 custom:tag"
        )
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "home")

            # Should preserve all components and update context
            expected = (
                "(C) Review quarterly report +work @home due:2025-01-10 custom:tag"
            )
            mock_replace.assert_called_once_with(1, expected)
            assert result == "Task updated"

    def test_set_context_handles_task_without_priority(self):
        """Test that set_context handles tasks without priority."""
        # Mock the list_tasks to return a task without priority
        sample_task = "1 Buy milk +shopping @grocery"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "store")

            # Should preserve task without priority and update context
            mock_replace.assert_called_once_with(1, "Buy milk +shopping @store")
            assert result == "Task updated"

    def test_set_context_removes_context_with_empty_string(self):
        """Test that set_context removes context when empty string is provided."""
        # Mock the list_tasks to return a task with context
        sample_task = "1 (A) Buy groceries +shopping @home due:2025-01-10"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "")

            # Should remove context from task
            mock_replace.assert_called_once_with(
                1, "(A) Buy groceries +shopping due:2025-01-10"
            )
            assert result == "Task updated"

    def test_set_context_removes_context_with_whitespace_only(self):
        """Test that set_context removes context when only whitespace is provided."""
        # Mock the list_tasks to return a task with context
        sample_task = "1 (B) Call dentist +health @phone"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "   ")

            # Should remove context from task
            mock_replace.assert_called_once_with(1, "(B) Call dentist +health")
            assert result == "Task updated"

    def test_set_context_handles_context_with_at_symbol(self):
        """Test that set_context handles context names that already have @ symbol."""
        # Mock the list_tasks to return a task
        sample_task = "1 Test task +project"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_context(1, "@office")

            # Should handle @ symbol correctly
            mock_replace.assert_called_once_with(1, "Test task +project @office")
            assert result == "Task updated"

    def test_set_context_raises_error_for_empty_context_after_cleaning(self):
        """Test that set_context raises error for context that becomes empty after cleaning."""
        # Mock the list_tasks to return a task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Context name cannot be empty"):
                self.todo_shell.set_context(1, "@")

    def test_set_context_raises_error_for_invalid_task_number(self):
        """Test that set_context raises error for invalid task number."""
        # Mock the list_tasks to return only one task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Task number 5 not found"):
                self.todo_shell.set_context(5, "office")

    def test_parse_task_components_handles_various_formats(self):
        """Test that _parse_task_components correctly parses different task formats."""
        # Test task with all components
        task = "(A) Buy groceries +shopping @home due:2025-01-10 custom:tag"
        components = self.todo_shell._parse_task_components(task)

        assert components["priority"] == "A"
        assert components["description"] == "Buy groceries"
        assert components["projects"] == ["+shopping"]
        assert components["contexts"] == ["@home"]
        assert components["due"] == "2025-01-10"

        assert components["other_tags"] == ["custom:tag"]

    def test_reconstruct_task_preserves_order(self):
        """Test that _reconstruct_task preserves the correct order of components."""
        components = {
            "priority": "B",
            "description": "Test task",
            "projects": ["+work"],
            "contexts": ["@office"],
            "due": "2025-01-15",
            "other_tags": ["custom:tag"],
        }

        result = self.todo_shell._reconstruct_task(components)
        expected = "(B) Test task +work @office due:2025-01-15 custom:tag"
        assert result == expected

    def test_remove_priority_uses_depriority_command(self):
        """Test removing task priority uses the depriority command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Priority removed"
        ) as mock_execute:
            result = self.todo_shell.remove_priority(1)

            # Verify depriority command
            mock_execute.assert_called_once_with(["todo.sh", "depri", "1"])
            assert result == "Priority removed"

    def test_list_projects_uses_lsp_command(self):
        """Test listing projects uses the lsp command."""
        with patch.object(
            self.todo_shell, "execute", return_value="+work\n+home\n+shopping"
        ) as mock_execute:
            result = self.todo_shell.list_projects()

            # Verify lsp command
            mock_execute.assert_called_once_with(
                ["todo.sh", "lsp"], suppress_color=True
            )
            assert result == "+work\n+home\n+shopping"

    def test_list_contexts_uses_lsc_command(self):
        """Test listing contexts uses the lsc command."""
        with patch.object(
            self.todo_shell, "execute", return_value="@work\n@home\n@shopping"
        ) as mock_execute:
            result = self.todo_shell.list_contexts()

            # Verify lsc command
            mock_execute.assert_called_once_with(
                ["todo.sh", "lsc"], suppress_color=True
            )
            assert result == "@work\n@home\n@shopping"

    def test_list_completed_uses_listfile_command(self):
        """Test listing completed tasks uses the listfile command with done.txt."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Completed task"
        ) as mock_execute:
            result = self.todo_shell.list_completed()

            # Verify listfile command with done.txt
            mock_execute.assert_called_once_with(
                ["todo.sh", "listfile", "done.txt"], suppress_color=True
            )
            assert result == "1. Completed task"

    def test_list_completed_with_filter_appends_filter(self):
        """Test listing completed tasks with filter appends the filter to the command."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Work task completed"
        ) as mock_execute:
            result = self.todo_shell.list_completed("+work")

            # Verify filter was appended to command
            mock_execute.assert_called_once_with(
                ["todo.sh", "listfile", "done.txt", "+work"], suppress_color=True
            )
            assert result == "1. Work task completed"

    def test_execute_with_subprocess_error_handling(self):
        """Test that subprocess errors are properly handled and converted to TodoShellError."""
        # Test with CalledProcessError
        error = subprocess.CalledProcessError(
            1, ["todo.sh", "invalid"], stderr="Command failed"
        )
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: Command failed"
            ):
                self.todo_shell.execute(["todo.sh", "invalid"])

    def test_execute_with_file_not_found_error(self):
        """Test that FileNotFoundError is properly handled."""
        with patch(
            "subprocess.run", side_effect=FileNotFoundError("todo.sh not found")
        ):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: todo.sh not found"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_permission_error(self):
        """Test that PermissionError is properly handled."""
        with patch("subprocess.run", side_effect=PermissionError("Permission denied")):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: Permission denied"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_timeout_error(self):
        """Test that TimeoutError is properly handled."""
        with patch("subprocess.run", side_effect=TimeoutError("Command timed out")):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: Command timed out"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_generic_exception(self):
        """Test that generic exceptions are properly handled."""
        with patch("subprocess.run", side_effect=Exception("Unknown error")):
            with pytest.raises(
                TodoShellError, match=r"Todo.sh command failed: Unknown error"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_suppresses_color_codes_when_requested(self):
        """Test that execute method strips ANSI color codes when suppress_color=True."""
        # Mock subprocess to return output with ANSI color codes
        mock_result = type(
            "MockResult",
            (),
            {
                "stdout": "\033[1;33m1\033[0m (A) \033[1;32m2025-08-29\033[0m Clean cat box \033[1;34m@home\033[0m \033[1;35m+chores\033[0m \033[1;31mdue:2025-08-29\033[0m",
                "stderr": "",
                "returncode": 0,
            },
        )()

        with patch("subprocess.run", return_value=mock_result):
            # Test with suppress_color=True (default for LLM consumption)
            result = self.todo_shell.execute(["todo.sh", "ls"], suppress_color=True)

            # Should return clean text without ANSI codes
            assert (
                result == "1 (A) 2025-08-29 Clean cat box @home +chores due:2025-08-29"
            )
            assert "\033[" not in result  # No ANSI escape sequences

            # Test with suppress_color=False (for interactive display)
            result_with_color = self.todo_shell.execute(
                ["todo.sh", "ls"], suppress_color=False
            )

            # Should preserve ANSI codes
            assert "\033[" in result_with_color  # ANSI escape sequences preserved
            assert (
                result_with_color
                == "\033[1;33m1\033[0m (A) \033[1;32m2025-08-29\033[0m Clean cat box \033[1;34m@home\033[0m \033[1;35m+chores\033[0m \033[1;31mdue:2025-08-29\033[0m"
            )

    def test_set_project_adds_projects_to_task_without_projects(self):
        """Test that set_project adds projects to task that doesn't have any."""
        # Mock the list_tasks to return a task without projects
        sample_task = "1 (A) Buy groceries @home due:2025-01-10"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["shopping", "errands"])

            # Should add both projects
            mock_replace.assert_called_once_with(
                1, "(A) Buy groceries +shopping +errands @home due:2025-01-10"
            )
            assert result == "Task updated"

    def test_set_project_adds_projects_to_task_with_existing_projects(self):
        """Test that set_project adds projects to task that already has projects."""
        # Mock the list_tasks to return a task with existing projects
        sample_task = "1 (B) Call dentist +health @phone"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["appointment", "personal"])

            # Should add new projects while preserving existing ones
            mock_replace.assert_called_once_with(
                1, "(B) Call dentist +health +appointment +personal @phone"
            )
            assert result == "Task updated"

    def test_set_project_removes_specific_projects(self):
        """Test that set_project removes specific projects using - prefix."""
        # Mock the list_tasks to return a task with multiple projects
        sample_task = "1 (C) Review report +work +urgent +review @office"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["-urgent", "-review"])

            # Should remove specified projects while keeping others
            mock_replace.assert_called_once_with(1, "(C) Review report +work @office")
            assert result == "Task updated"

    def test_set_project_mixed_add_and_remove_operations(self):
        """Test that set_project handles mixed add and remove operations."""
        # Mock the list_tasks to return a task with existing projects
        sample_task = "1 (A) Task with projects +old +keep @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["-old", "new", "another"])

            # Should remove 'old', add 'new' and 'another', keep 'keep'
            mock_replace.assert_called_once_with(
                1, "(A) Task with projects +keep +new +another @context"
            )
            assert result == "Task updated"

    def test_set_project_handles_empty_projects_list_as_noop(self):
        """Test that set_project does nothing when projects list is empty."""
        # Mock the list_tasks to return a task
        sample_task = "1 (B) Test task +existing @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, [])

            # Should not call replace since it's a NOOP
            mock_replace.assert_not_called()
            # Should return the original task unchanged
            assert result == "(B) Test task +existing @context"

    def test_set_project_handles_empty_strings_as_noop(self):
        """Test that set_project skips empty strings in projects list."""
        # Mock the list_tasks to return a task
        sample_task = "1 (C) Test task +existing @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["", "valid", "  ", "another"])

            # Should only process "valid" and "another", skip empty strings
            mock_replace.assert_called_once_with(
                1, "(C) Test task +existing +valid +another @context"
            )
            assert result == "Task updated"

    def test_set_project_handles_projects_with_plus_prefix(self):
        """Test that set_project handles projects that already have + prefix."""
        # Mock the list_tasks to return a task
        sample_task = "1 Test task @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["+work", "+home"])

            # Should handle + prefix correctly
            mock_replace.assert_called_once_with(1, "Test task +work +home @context")
            assert result == "Task updated"

    def test_set_project_handles_remove_operations_with_plus_prefix(self):
        """Test that set_project handles remove operations with + prefix."""
        # Mock the list_tasks to return a task with projects
        sample_task = "1 Test task +work +home +shopping @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["-+work", "-+shopping"])

            # Should remove projects even if they have + prefix in the remove operation
            mock_replace.assert_called_once_with(1, "Test task +home @context")
            assert result == "Task updated"

    def test_set_project_preserves_all_other_components(self):
        """Test that set_project preserves all task components when modifying projects."""
        # Mock the list_tasks to return a complex task
        sample_task = "1 (A) Complex task +old +keep @office due:2025-01-15 custom:tag"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["-old", "new"])

            # Should preserve all components and update projects
            expected = "(A) Complex task +keep +new @office due:2025-01-15 custom:tag"
            mock_replace.assert_called_once_with(1, expected)
            assert result == "Task updated"

    def test_set_project_raises_error_for_empty_project_after_cleaning(self):
        """Test that set_project raises error for project that becomes empty after cleaning."""
        # Mock the list_tasks to return a task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Project name cannot be empty"):
                self.todo_shell.set_project(1, ["+"])

    def test_set_project_raises_error_for_empty_remove_project_after_cleaning(self):
        """Test that set_project raises error for remove project that becomes empty after cleaning."""
        # Mock the list_tasks to return a task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Project name cannot be empty"):
                self.todo_shell.set_project(1, ["-+"])

    def test_set_project_raises_error_for_invalid_task_number(self):
        """Test that set_project raises error for invalid task number."""
        # Mock the list_tasks to return only one task
        sample_task = "1 Test task"
        with patch.object(self.todo_shell, "list_tasks", return_value=sample_task):
            with pytest.raises(TodoShellError, match="Task number 5 not found"):
                self.todo_shell.set_project(5, ["work"])

    def test_set_project_prevents_duplicate_projects(self):
        """Test that set_project doesn't add duplicate projects."""
        # Mock the list_tasks to return a task with existing project
        sample_task = "1 Test task +work @context"
        with patch.object(
            self.todo_shell, "list_tasks", return_value=sample_task
        ), patch.object(
            self.todo_shell, "replace", return_value="Task updated"
        ) as mock_replace:
            result = self.todo_shell.set_project(1, ["work", "new"])

            # Should not duplicate +work, only add +new
            mock_replace.assert_called_once_with(1, "Test task +work +new @context")
            assert result == "Task updated"

    def test_get_help_constructs_correct_command(self):
        """Test getting help constructs the correct todo.sh command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Todo.sh help output"
        ) as mock_execute:
            result = self.todo_shell.get_help()

            # Verify the correct command was constructed
            mock_execute.assert_called_once_with(
                ["todo.sh", "help"], suppress_color=False
            )
            assert result == "Todo.sh help output"
