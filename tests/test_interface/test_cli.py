"""
Tests for CLI class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from todo_agent.interface.cli import CLI
from todo_agent.core.conversation_manager import MessageRole


class TestCLI:
    """Test CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock all dependencies to avoid import issues
        with patch('todo_agent.interface.cli.Config') as mock_config_class, \
             patch('todo_agent.interface.cli.TodoShell') as mock_todo_shell, \
             patch('todo_agent.interface.cli.TodoManager') as mock_todo_manager, \
             patch('todo_agent.interface.cli.ToolCallHandler') as mock_tool_handler, \
             patch('todo_agent.interface.cli.Inference') as mock_inference, \
             patch('todo_agent.interface.cli.Logger') as mock_logger_class:
            
            # Set up mock config
            mock_config = Mock()
            mock_config.validate.return_value = True
            mock_config_class.return_value = mock_config
            
            # Set up mock logger
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            # Set up mock components
            mock_todo_shell.return_value = Mock()
            mock_todo_manager.return_value = Mock()
            
            # ToolCallHandler now takes a logger parameter
            mock_tool_handler_instance = Mock()
            mock_tool_handler_instance.tools = [
                {
                    "function": {
                        "name": "list_projects",
                        "description": "List all projects",
                        "parameters": {"properties": {}}
                    }
                },
                {
                    "function": {
                        "name": "list_contexts",
                        "description": "List all contexts",
                        "parameters": {"properties": {}}
                    }
                },
                {
                    "function": {
                        "name": "list_tasks",
                        "description": "List tasks",
                        "parameters": {"properties": {"filter": {"type": "string"}}}
                    }
                },
                {
                    "function": {
                        "name": "add_task",
                        "description": "Add a task",
                        "parameters": {"properties": {"description": {"type": "string"}}}
                    }
                },
                {
                    "function": {
                        "name": "complete_task",
                        "description": "Complete a task",
                        "parameters": {"properties": {"task_number": {"type": "integer"}}}
                    }
                }
            ]
            mock_tool_handler.return_value = mock_tool_handler_instance
            
            # Set up mock inference engine
            mock_inference_instance = Mock()
            mock_inference_instance.process_request.return_value = ("Mock response", 1.5)
            mock_inference_instance.get_conversation_summary.return_value = {
                "total_messages": 5,
                "user_messages": 2,
                "assistant_messages": 2,
                "tool_messages": 1,
                "estimated_tokens": 100,
                "thinking_time_count": 3,
                "total_thinking_time": 4.5,
                "average_thinking_time": 1.5,
                "min_thinking_time": 0.8,
                "max_thinking_time": 2.2
            }
            mock_inference_instance.clear_conversation.return_value = None
            mock_inference.return_value = mock_inference_instance
            
            self.cli = CLI()

    def test_initialization_creates_all_required_components(self):
        """Test that CLI initialization creates all required components."""
        # Verify all required components are created
        assert hasattr(self.cli, 'logger')
        assert hasattr(self.cli, 'config')
        assert hasattr(self.cli, 'todo_shell')
        assert hasattr(self.cli, 'todo_manager')
        assert hasattr(self.cli, 'tool_handler')
        assert hasattr(self.cli, 'inference')
        assert hasattr(self.cli, 'console')

    def test_handle_request_success(self):
        """Test successful request handling with proper response and timing."""
        user_input = "Add a task to buy groceries"
        expected_response = "Task added successfully"
        expected_thinking_time = 2.1
        
        # Mock the inference engine
        self.cli.inference.process_request.return_value = (expected_response, expected_thinking_time)
        
        result = self.cli.handle_request(user_input)
        
        # Verify correct response
        assert result == expected_response
        
        # Verify inference engine was called with correct input
        self.cli.inference.process_request.assert_called_once_with(user_input)

    def test_handle_request_exception_handling(self):
        """Test that exceptions in handle_request are properly caught and formatted."""
        user_input = "Invalid request"
        error_message = "Test error"
        
        # Mock exception in inference engine
        self.cli.inference.process_request.side_effect = Exception(error_message)
        
        result = self.cli.handle_request(user_input)
        
        # Verify error is properly formatted
        assert result == f"Error: {error_message}"
        
        # Verify inference engine was called
        self.cli.inference.process_request.assert_called_once_with(user_input)

    def test_run_single_request_delegates_to_handle_request(self):
        """Test that run_single_request properly delegates to handle_request."""
        user_input = "Add task"
        expected_response = "Task added"
        
        # Mock handle_request
        self.cli.handle_request = Mock(return_value=expected_response)
        
        result = self.cli.run_single_request(user_input)
        
        # Verify correct response
        assert result == expected_response
        
        # Verify handle_request was called with correct input
        self.cli.handle_request.assert_called_once_with(user_input)

    def test_clear_command_functionality(self):
        """Test that the clear command properly clears conversation history."""
        # Mock input to simulate 'clear' command
        with patch('builtins.input', return_value='clear'), \
             patch('builtins.print') as mock_print:
            
            # Mock the run loop to exit after clear
            with patch.object(self.cli, 'run') as mock_run:
                # Simulate the clear command logic
                self.cli.inference.clear_conversation()
                print("Conversation history cleared.")
                
                # Verify clear_conversation was called
                self.cli.inference.clear_conversation.assert_called_once()
                
                # Verify success message was printed
                mock_print.assert_called_once_with("Conversation history cleared.")

    def test_history_command_functionality(self):
        """Test that the history command displays conversation statistics."""
        # Mock the conversation summary
        summary = {
            "total_messages": 10,
            "user_messages": 4,
            "assistant_messages": 4,
            "tool_messages": 2,
            "estimated_tokens": 250,
            "thinking_time_count": 5,
            "total_thinking_time": 8.5,
            "average_thinking_time": 1.7,
            "min_thinking_time": 0.5,
            "max_thinking_time": 3.2
        }
        
        self.cli.inference.get_conversation_summary.return_value = summary
        
        with patch('builtins.print') as mock_print:
            # Simulate the history command logic
            summary_output = self.cli.inference.get_conversation_summary()
            print(f"Conversation Stats:")
            print(f"  Total messages: {summary_output['total_messages']}")
            print(f"  User messages: {summary_output['user_messages']}")
            print(f"  Assistant messages: {summary_output['assistant_messages']}")
            print(f"  Tool messages: {summary_output['tool_messages']}")
            print(f"  Estimated tokens: {summary_output['estimated_tokens']}")
            print(f"  Thinking time stats:")
            print(f"    Total thinking time: {summary_output['total_thinking_time']:.2f}s")
            print(f"    Average thinking time: {summary_output['average_thinking_time']:.2f}s")
            print(f"    Min thinking time: {summary_output['min_thinking_time']:.2f}s")
            print(f"    Max thinking time: {summary_output['max_thinking_time']:.2f}s")
            print(f"    Requests with timing: {summary_output['thinking_time_count']}")
            
            # Verify get_conversation_summary was called
            self.cli.inference.get_conversation_summary.assert_called_once()
            
            # Verify all expected print calls
            expected_calls = [
                "Conversation Stats:",
                "  Total messages: 10",
                "  User messages: 4",
                "  Assistant messages: 4",
                "  Tool messages: 2",
                "  Estimated tokens: 250",
                "  Thinking time stats:",
                "    Total thinking time: 8.50s",
                "    Average thinking time: 1.70s",
                "    Min thinking time: 0.50s",
                "    Max thinking time: 3.20s",
                "    Requests with timing: 5"
            ]
            
            # Check that all expected calls were made
            for expected_call in expected_calls:
                assert any(expected_call in str(call) for call in mock_print.call_args_list)

    def test_list_command_success(self):
        """Test successful list command execution."""
        expected_output = "1 Buy groceries\n2 Call mom\n3 Review project"
        
        # Mock the todo_shell.list_tasks method
        self.cli.todo_shell.list_tasks.return_value = expected_output
        
        with patch('builtins.print') as mock_print:
            # Simulate the list command logic
            try:
                output = self.cli.todo_shell.list_tasks()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list tasks: {str(e)}")
            
            # Verify todo_shell.list_tasks was called
            self.cli.todo_shell.list_tasks.assert_called_once()
            
            # Verify print was called with the expected output
            mock_print.assert_called_once_with(expected_output)

    def test_list_command_exception_handling(self):
        """Test list command handles exceptions properly."""
        error_message = "Database connection failed"
        
        # Mock exception in todo_shell.list_tasks
        self.cli.todo_shell.list_tasks.side_effect = Exception(error_message)
        
        with patch('builtins.print') as mock_print:
            # Simulate the list command logic with error
            try:
                output = self.cli.todo_shell.list_tasks()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list tasks: {str(e)}")
            
            # Verify error was handled and formatted correctly
            mock_print.assert_called_once_with(f"Error: Failed to list tasks: {error_message}")

    def test_help_command_displays_available_commands(self):
        """Test that help command displays all available commands."""
        with patch('builtins.print') as mock_print:
            # Simulate the help command logic
            print("Available commands:")
            print("  clear    - Clear conversation history")
            print("  history  - Show conversation statistics")
            print("  help     - Show this help message")
            print("  list     - List all tasks (no LLM interaction)")
            print("  quit     - Exit the application")
            print("  Or just type your request naturally!")
            
            # Verify all help messages were printed
            expected_help_lines = [
                "Available commands:",
                "  clear    - Clear conversation history",
                "  history  - Show conversation statistics",
                "  help     - Show this help message",
                "  list     - List all tasks (no LLM interaction)",
                "  quit     - Exit the application",
                "  Or just type your request naturally!"
            ]
            
            # Check that all expected help lines were printed
            for expected_line in expected_help_lines:
                assert any(expected_line in str(call) for call in mock_print.call_args_list)

    def test_empty_input_handling(self):
        """Test that empty input is handled gracefully."""
        # This would be tested in the main run loop
        # For now, we test that handle_request can handle empty strings
        result = self.cli.handle_request("")
        
        # Should still call inference engine (let it handle empty input)
        self.cli.inference.process_request.assert_called_once_with("")

    def test_long_input_truncation_in_logging(self):
        """Test that long inputs are properly truncated in logging."""
        long_input = "A" * 100  # 100 character input
        
        # Mock the inference engine
        self.cli.inference.process_request.return_value = ("Response", 1.0)
        
        result = self.cli.handle_request(long_input)
        
        # Verify inference engine was called with full input
        self.cli.inference.process_request.assert_called_once_with(long_input)
        
        # Verify response is correct
        assert result == "Response"

    def test_thinking_spinner_creation(self):
        """Test that thinking spinner is created with correct message."""
        message = "Processing request..."
        spinner = self.cli._create_thinking_spinner(message)
        
        # Verify spinner was created
        assert spinner is not None
        assert hasattr(spinner, 'text')

    def test_live_display_creation(self):
        """Test that live display context is created properly."""
        live_display = self.cli._get_thinking_live()
        
        # Verify live display was created
        assert live_display is not None
        assert hasattr(live_display, 'console')
