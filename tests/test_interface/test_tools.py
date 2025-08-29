"""
Tests for tool execution and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from todo_agent.interface.tools import ToolCallHandler
from todo_agent.core.todo_manager import TodoManager


class TestToolErrorHandling:
    """Test tool execution error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_todo_manager = Mock(spec=TodoManager)
        self.mock_logger = Mock()
        self.tool_handler = ToolCallHandler(self.mock_todo_manager, self.mock_logger)

    def test_unknown_tool_returns_error_structure(self):
        """Test that unknown tools return structured error information."""
        tool_call = {
            "function": {"name": "unknown_tool", "arguments": "{}"},
            "id": "test_id"
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
        self.mock_todo_manager.list_tasks.side_effect = FileNotFoundError("todo.sh not found")
        
        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id"
        }
        
        result = self.tool_handler.execute_tool(tool_call)
        
        assert result["error"] is True
        assert result["error_type"] == "FileNotFoundError"
        assert "Todo.sh command failed" in result["user_message"]
        assert result["tool_call_id"] == "test_id"
        assert result["name"] == "list_tasks"

    def test_task_not_found_error_handling(self):
        """Test handling of task not found errors."""
        self.mock_todo_manager.complete_task.side_effect = IndexError("Task 999 not found")
        
        tool_call = {
            "function": {"name": "complete_task", "arguments": '{"task_number": 999}'},
            "id": "test_id"
        }
        
        result = self.tool_handler.execute_tool(tool_call)
        
        assert result["error"] is True
        assert "Task not found" in result["user_message"]
        assert "may have been completed or deleted" in result["user_message"]

    def test_invalid_input_error_handling(self):
        """Test handling of invalid input errors."""
        self.mock_todo_manager.add_task.side_effect = ValueError("Invalid priority format")
        
        tool_call = {
            "function": {"name": "add_task", "arguments": '{"description": "test", "priority": "invalid"}'},
            "id": "test_id"
        }
        
        result = self.tool_handler.execute_tool(tool_call)
        
        assert result["error"] is True
        assert "Invalid input" in result["user_message"]
        assert "check the task format" in result["user_message"]

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        self.mock_todo_manager.list_tasks.side_effect = PermissionError("Permission denied")
        
        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id"
        }
        
        result = self.tool_handler.execute_tool(tool_call)
        
        assert result["error"] is True
        assert "Permission denied" in result["user_message"]
        assert "check file permissions" in result["user_message"]

    def test_successful_tool_execution(self):
        """Test that successful tool execution returns proper structure."""
        self.mock_todo_manager.list_tasks.return_value = "1. Test task"
        
        tool_call = {
            "function": {"name": "list_tasks", "arguments": "{}"},
            "id": "test_id"
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
            "id": "test_id"
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
                "arguments": '{"description": "test task", "priority": "A", "project": "work"}'
            },
            "id": "test_id"
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
            "id": "test_id"
        }
        
        result = self.tool_handler.execute_tool(tool_call)
        
        # Verify the logger was called with empty parentheses for no parameters
        self.mock_logger.info.assert_called_with(
            "Executing tool: list_tasks() (ID: test_id)"
        )
        
        assert result["error"] is False
        assert result["output"] == "1. Test task"
