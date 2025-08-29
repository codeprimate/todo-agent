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
                TodoShellError, match="Todo.sh command failed: Command not found"
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
            mock_execute.assert_called_once_with(["todo.sh", "ls"])
            assert result == "1. Task 1\n2. Task 2"

    def test_list_tasks_with_filter_appends_filter_to_command(self):
        """Test listing tasks with filter appends the filter to the ls command."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Work task"
        ) as mock_execute:
            result = self.todo_shell.list_tasks("+work")

            # Verify filter was appended to command
            mock_execute.assert_called_once_with(["todo.sh", "ls", "+work"])
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
        """Test setting task priority uses the priority command."""
        with patch.object(
            self.todo_shell, "execute", return_value="Priority set"
        ) as mock_execute:
            result = self.todo_shell.set_priority(1, "A")

            # Verify priority command
            mock_execute.assert_called_once_with(["todo.sh", "pri", "1", "A"])
            assert result == "Priority set"

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
            mock_execute.assert_called_once_with(["todo.sh", "lsp"])
            assert result == "+work\n+home\n+shopping"

    def test_list_contexts_uses_lsc_command(self):
        """Test listing contexts uses the lsc command."""
        with patch.object(
            self.todo_shell, "execute", return_value="@work\n@home\n@shopping"
        ) as mock_execute:
            result = self.todo_shell.list_contexts()

            # Verify lsc command
            mock_execute.assert_called_once_with(["todo.sh", "lsc"])
            assert result == "@work\n@home\n@shopping"

    def test_list_completed_uses_listfile_command(self):
        """Test listing completed tasks uses the listfile command with done.txt."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Completed task"
        ) as mock_execute:
            result = self.todo_shell.list_completed()

            # Verify listfile command with done.txt
            mock_execute.assert_called_once_with(["todo.sh", "listfile", "done.txt"])
            assert result == "1. Completed task"

    def test_list_completed_with_filter_appends_filter(self):
        """Test listing completed tasks with filter appends the filter to the command."""
        with patch.object(
            self.todo_shell, "execute", return_value="1. Work task completed"
        ) as mock_execute:
            result = self.todo_shell.list_completed("+work")

            # Verify filter was appended to command
            mock_execute.assert_called_once_with(
                ["todo.sh", "listfile", "done.txt", "+work"]
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
                TodoShellError, match="Todo.sh command failed: Command failed"
            ):
                self.todo_shell.execute(["todo.sh", "invalid"])

    def test_execute_with_file_not_found_error(self):
        """Test that FileNotFoundError is properly handled."""
        with patch(
            "subprocess.run", side_effect=FileNotFoundError("todo.sh not found")
        ):
            with pytest.raises(
                TodoShellError, match="Todo.sh command failed: todo.sh not found"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_permission_error(self):
        """Test that PermissionError is properly handled."""
        with patch("subprocess.run", side_effect=PermissionError("Permission denied")):
            with pytest.raises(
                TodoShellError, match="Todo.sh command failed: Permission denied"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_timeout_error(self):
        """Test that TimeoutError is properly handled."""
        with patch("subprocess.run", side_effect=TimeoutError("Command timed out")):
            with pytest.raises(
                TodoShellError, match="Todo.sh command failed: Command timed out"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])

    def test_execute_with_generic_exception(self):
        """Test that generic exceptions are properly handled."""
        with patch("subprocess.run", side_effect=Exception("Unknown error")):
            with pytest.raises(
                TodoShellError, match="Todo.sh command failed: Unknown error"
            ):
                self.todo_shell.execute(["todo.sh", "add", "test"])
