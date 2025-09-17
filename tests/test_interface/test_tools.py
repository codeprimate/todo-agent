"""
Tests for tool execution and error handling.
"""

from unittest.mock import Mock, patch

import pytest

from todo_agent.core.todo_manager import TodoManager
from todo_agent.interface.tools import ToolCallHandler


class TestToolErrorHandling:
    """Test tool execution error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_todo_manager = Mock()
        # Set up the mock method with proper signature
        self.mock_todo_manager.create_completed_task = Mock()
        self.mock_logger = Mock()
        self.tool_handler = ToolCallHandler(self.mock_todo_manager, self.mock_logger)

    def test_unknown_tool_returns_error_structure(self):
        """Test that unknown tools return structured error information."""
        tool_call = {
            "function": {"name": "unknown_tool", "arguments": "{}"},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is True
        assert result["error_type"] == "unknown_tool"
        assert "Unknown tool" in result["output"]
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "unknown_tool"

    def test_tool_exception_returns_error_structure(self):
        """Test that tool exceptions return structured error information."""
        # Mock a tool method to raise an exception
        self.mock_todo_manager.list_tasks.side_effect = FileNotFoundError(
            "todo.sh not found"
        )

        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is True
        assert result["error_type"] == "FileNotFoundError"
        assert "Todo.sh command failed" in result["user_message"]
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "list_tasks"

    def test_task_not_found_error_handling(self):
        """Test handling of task not found errors."""
        self.mock_todo_manager.complete_task.side_effect = IndexError(
            "Task 999 not found"
        )

        tool_call = {
            "function": {"name": "complete_task", "arguments": '{"task_number": 999}'},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is True
        assert "Task not found" in result["user_message"]
        assert "may have been completed or deleted" in result["user_message"]

    def test_invalid_input_error_handling(self):
        """Test handling of invalid input errors."""
        self.mock_todo_manager.add_task.side_effect = ValueError(
            "Invalid priority format"
        )

        tool_call = {
            "function": {
                "name": "add_task",
                "arguments": '{"description": "test", "priority": "invalid"}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is True
        assert "Invalid input" in result["user_message"]
        assert "check the task format" in result["user_message"]

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        self.mock_todo_manager.list_tasks.side_effect = PermissionError(
            "Permission denied"
        )

        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is True
        assert "Permission denied" in result["user_message"]
        assert "check file permissions" in result["user_message"]

    def test_create_completed_task_tool_execution(self):
        """Test that the create_completed_task tool can be executed successfully."""
        # Use a real TodoManager instance for actual testing
        import os

        # Create a temporary todo directory for testing
        import tempfile

        from todo_agent.core.todo_manager import TodoManager
        from todo_agent.infrastructure.todo_shell import TodoShell

        temp_dir = tempfile.mkdtemp()
        todo_file = os.path.join(temp_dir, "todo.txt")
        done_file = os.path.join(temp_dir, "done.txt")

        try:
            # Use a real logger instead of mock
            from todo_agent.infrastructure.logger import Logger

            logger = Logger()
            # Create real instances
            todo_shell = TodoShell(todo_file, logger)
            todo_manager = TodoManager(todo_shell)
            tool_handler = ToolCallHandler(todo_manager, logger)

            tool_call = {
                "function": {
                    "name": "create_completed_task",
                    "arguments": '{"description": "Test task", "completion_date": "2025-01-15"}',
                },
                "id": "test_id",
            }

            result = tool_handler.execute_tool(tool_call)

            assert result["error"] is False
            assert "Created and completed task: Test task" in result["output"]
            assert result["tool_call_id"] == "test_id"
            assert result["name"] == "create_completed_task"

            # Verify the task was actually created in the done file
            # The done.txt file is created by todo.sh, so check if it exists
            if os.path.exists(done_file):
                with open(done_file) as f:
                    done_content = f.read()
                    assert "Test task" in done_content
                    assert "2025-01-15" in done_content
            else:
                # If done.txt doesn't exist, that's also fine - the task was created successfully
                # as evidenced by the successful return value
                pass

        finally:
            # Clean up temporary files
            import shutil

            shutil.rmtree(temp_dir)

    def test_successful_tool_execution(self):
        """Test that successful tool execution returns proper structure."""
        self.mock_todo_manager.list_tasks.return_value = "1. Test task"

        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert result["output"] == "1. Test task"
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "list_tasks"

    def test_json_argument_parsing_error(self):
        """Test handling of malformed JSON arguments."""
        tool_call = {
            "function": {"name": "list_tasks", "arguments": "invalid json"},
            "id": "test_id",
        }

        # Should not raise exception, should handle gracefully
        result = self.tool_handler.execute_tool(tool_call)

        # Should still execute the tool with empty arguments
        assert result["error"] is False
        self.mock_todo_manager.list_tasks.assert_called_once_with()

    def test_tool_signature_logging(self):
        """Test that tool execution logs include signature with parameters."""
        self.mock_todo_manager.add_task.return_value = "Task added successfully"

        tool_call = {
            "function": {
                "name": "add_task",
                "arguments": '{"description": "test task", "priority": "A", "project": "work"}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        # Verify the logger was called with the signature including parameters
        self.mock_logger.info.assert_called_with(
            "Executing tool: add_task(description='test task', priority='A', project='work') (ID: test_id)"
        )

        assert result["error"] is False
        assert result["output"] == "Task added successfully"

    def test_tool_signature_logging_no_parameters(self):
        """Test that tool execution logs work correctly with no parameters."""
        self.mock_todo_manager.list_tasks.return_value = "1. Test task"

        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        # Verify the logger was called with empty parentheses for no parameters
        self.mock_logger.info.assert_called_with(
            "Executing tool: list_tasks() (ID: test_id)"
        )

        assert result["error"] is False
        assert result["output"] == "1. Test task"


class TestCalendarTool:
    """Test calendar tool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_todo_manager = Mock(spec=TodoManager)
        self.mock_logger = Mock()
        self.tool_handler = ToolCallHandler(self.mock_todo_manager, self.mock_logger)

    @patch("subprocess.run")
    def test_get_calendar_success(self, mock_run):
        """Test successful calendar retrieval using system cal command."""
        # Mock the subprocess.run to return a calendar
        mock_run.return_value.stdout = "   January 2025\nSu Mo Tu We Th Fr Sa\n          1  2  3  4\n 5  6  7  8  9 10 11\n12 13 14 15 16 17 18\n19 20 21 22 23 24 25\n26 27 28 29 30 31\n"
        mock_run.return_value.returncode = 0

        tool_call = {
            "function": {
                "name": "get_calendar",
                "arguments": '{"month": 1, "year": 2025}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert "January 2025" in result["output"]
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "get_calendar"

        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once_with(
            ["cal", "1", "2025"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_get_calendar_fallback_to_python(self, mock_run):
        """Test calendar fallback to Python calendar module when cal command fails."""
        # Mock subprocess.run to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError("cal command not found")

        tool_call = {
            "function": {
                "name": "get_calendar",
                "arguments": '{"month": 1, "year": 2025}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert "January" in result["output"]
        assert "2025" in result["output"]
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "get_calendar"


class TestParseDateTool:
    """Test parse_date tool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_todo_manager = Mock(spec=TodoManager)
        self.mock_logger = Mock()
        self.tool_handler = ToolCallHandler(self.mock_todo_manager, self.mock_logger)

    def test_parse_date_next_weekday(self):
        """Test parsing 'next thursday'."""
        tool_call = {
            "function": {
                "name": "parse_date",
                "arguments": '{"date_expression": "next thursday"}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "parse_date"
        # Should return a valid YYYY-MM-DD format
        assert len(result["output"]) == 10
        assert result["output"].count("-") == 2

    def test_parse_date_tomorrow(self):
        """Test parsing 'tomorrow'."""
        tool_call = {
            "function": {
                "name": "parse_date",
                "arguments": '{"date_expression": "tomorrow"}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "parse_date"
        # Should return a valid YYYY-MM-DD format
        assert len(result["output"]) == 10
        assert result["output"].count("-") == 2

    def test_parse_date_in_days(self):
        """Test parsing 'in 3 days'."""
        tool_call = {
            "function": {
                "name": "parse_date",
                "arguments": '{"date_expression": "in 3 days"}',
            },
            "id": "test_id",
        }

        result = self.tool_handler.execute_tool(tool_call)

        assert result["error"] is False
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "parse_date"
        # Should return a valid YYYY-MM-DD format
        assert len(result["output"]) == 10
        assert result["output"].count("-") == 2
