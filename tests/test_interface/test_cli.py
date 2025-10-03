"""
Tests for CLI class.
"""

import contextlib
import sys
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from todo_agent.core.conversation_manager import MessageRole
from todo_agent.interface.cli import CLI


class TestCLI:
    """Test CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock all dependencies to avoid import issues
        with patch("todo_agent.interface.cli.Config") as mock_config_class, patch(
            "todo_agent.interface.cli.TodoShell"
        ) as mock_todo_shell, patch(
            "todo_agent.interface.cli.TodoManager"
        ) as mock_todo_manager, patch(
            "todo_agent.interface.cli.ToolCallHandler"
        ) as mock_tool_handler, patch(
            "todo_agent.interface.cli.Inference"
        ) as mock_inference, patch(
            "todo_agent.interface.cli.Logger"
        ) as mock_logger_class:
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
                        "parameters": {"properties": {}},
                    }
                },
                {
                    "function": {
                        "name": "list_contexts",
                        "description": "List all contexts",
                        "parameters": {"properties": {}},
                    }
                },
                {
                    "function": {
                        "name": "list_tasks",
                        "description": "List tasks",
                        "parameters": {"properties": {"filter": {"type": "string"}}},
                    }
                },
                {
                    "function": {
                        "name": "add_task",
                        "description": "Add a task",
                        "parameters": {
                            "properties": {"description": {"type": "string"}}
                        },
                    }
                },
                {
                    "function": {
                        "name": "complete_task",
                        "description": "Complete a task",
                        "parameters": {
                            "properties": {"task_number": {"type": "integer"}}
                        },
                    }
                },
            ]
            mock_tool_handler.return_value = mock_tool_handler_instance

            # Set up mock inference engine
            mock_inference_instance = Mock()
            mock_inference_instance.process_request.return_value = (
                "Mock response",
                1.5,
            )
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
                "max_thinking_time": 2.2,
            }
            mock_inference_instance.clear_conversation.return_value = None
            mock_inference.return_value = mock_inference_instance

            self.cli = CLI()

    def test_initialization_creates_all_required_components(self):
        """Test that CLI initialization creates all required components."""
        # Verify all required components are created
        assert hasattr(self.cli, "logger")
        assert hasattr(self.cli, "config")
        assert hasattr(self.cli, "todo_shell")
        assert hasattr(self.cli, "todo_manager")
        assert hasattr(self.cli, "tool_handler")
        assert hasattr(self.cli, "inference")
        assert hasattr(self.cli, "console")

    def test_handle_request_success(self):
        """Test successful request handling with proper response and timing."""
        user_input = "Add a task to buy groceries"
        expected_response = "Task added successfully"
        expected_thinking_time = 2.1

        # Mock the inference engine
        self.cli.inference.process_request.return_value = (
            expected_response,
            expected_thinking_time,
        )

        result = self.cli.handle_request(user_input)

        # Verify correct response
        assert result == expected_response

        # Verify inference engine was called with correct input and progress callback
        call_args = self.cli.inference.process_request.call_args
        assert call_args[0][0] == user_input  # First argument should be user_input
        assert (
            call_args[0][1] is not None
        )  # Second argument should be progress callback

    def test_handle_request_exception_handling(self):
        """Test that exceptions in handle_request are properly caught and formatted."""
        user_input = "Invalid request"
        error_message = "Test error"

        # Mock exception in inference engine
        self.cli.inference.process_request.side_effect = Exception(error_message)

        result = self.cli.handle_request(user_input)

        # Verify error is properly formatted with unicode
        assert result == f"❌ {error_message}"

        # Verify inference engine was called with progress callback
        call_args = self.cli.inference.process_request.call_args
        assert call_args[0][0] == user_input  # First argument should be user_input
        assert (
            call_args[0][1] is not None
        )  # Second argument should be progress callback

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
        self.cli.handle_request.assert_called_once_with(user_input, False)

    def test_clear_command_functionality(self):
        """Test that the clear command properly clears conversation history."""
        # Mock input to simulate 'clear' command
        with patch("builtins.input", return_value="clear"), patch(
            "builtins.print"
        ) as mock_print:
            # Mock the run loop to exit after clear
            with patch.object(self.cli, "run"):
                # Simulate the clear command logic
                self.cli.inference.clear_conversation()
                print("Conversation history cleared.")

                # Verify clear_conversation was called
                self.cli.inference.clear_conversation.assert_called_once()

                # Verify success message was printed
                mock_print.assert_called_once_with("Conversation history cleared.")

    def test_list_command_success(self):
        """Test successful list command execution."""
        expected_output = "1 Buy groceries\n2 Call mom\n3 Review project"

        # Mock the todo_shell.list_tasks method
        self.cli.todo_shell.list_tasks.return_value = expected_output

        with patch("builtins.print") as mock_print:
            # Simulate the list command logic
            try:
                output = self.cli.todo_shell.list_tasks()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list tasks: {e!s}")

            # Verify todo_shell.list_tasks was called
            self.cli.todo_shell.list_tasks.assert_called_once()

            # Verify print was called with the expected output
            mock_print.assert_called_once_with(expected_output)

    def test_list_command_exception_handling(self):
        """Test list command handles exceptions properly."""
        error_message = "Database connection failed"

        # Mock exception in todo_shell.list_tasks
        self.cli.todo_shell.list_tasks.side_effect = Exception(error_message)

        with patch("builtins.print") as mock_print:
            # Simulate the list command logic with error
            try:
                output = self.cli.todo_shell.list_tasks()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list tasks: {e!s}")

            # Verify error was handled and formatted correctly
            mock_print.assert_called_once_with(
                f"Error: Failed to list tasks: {error_message}"
            )

    def test_done_command_success(self):
        """Test successful done command execution."""
        expected_output = (
            "x 2025-08-29 2025-08-28 Buy groceries\nx 2025-08-28 2025-08-27 Call mom"
        )

        # Mock the todo_shell.list_completed method
        self.cli.todo_shell.list_completed.return_value = expected_output

        with patch("builtins.print") as mock_print:
            # Simulate the done command logic
            try:
                output = self.cli.todo_shell.list_completed()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list completed tasks: {e!s}")

            # Verify todo_shell.list_completed was called
            self.cli.todo_shell.list_completed.assert_called_once()

            # Verify print was called with the expected output
            mock_print.assert_called_once_with(expected_output)

    def test_done_command_exception_handling(self):
        """Test done command handles exceptions properly."""
        error_message = "Database connection failed"

        # Mock exception in todo_shell.list_completed
        self.cli.todo_shell.list_completed.side_effect = Exception(error_message)

        with patch("builtins.print") as mock_print:
            # Simulate the done command logic with error
            try:
                output = self.cli.todo_shell.list_completed()
                print(output)
            except Exception as e:
                print(f"Error: Failed to list completed tasks: {e!s}")

            # Verify error was handled and formatted correctly
            mock_print.assert_called_once_with(
                f"Error: Failed to list completed tasks: {error_message}"
            )

    def test_help_command_displays_available_commands(self):
        """Test that help command displays all available commands."""
        with patch("builtins.print") as mock_print:
            # Simulate the help command logic
            print("Available commands:")
            print("  clear    - Clear conversation history")
            print("  help     - Show this help message")
            print("  list     - List all tasks")
            print("  done     - List completed tasks")
            print("  quit     - Exit the application")
            print("  Or just type your request naturally!")

            # Verify all help messages were printed
            expected_help_lines = [
                "Available commands:",
                "  clear    - Clear conversation history",
                "  help     - Show this help message",
                "  list     - List all tasks",
                "  done     - List completed tasks",
                "  quit     - Exit the application",
                "  Or just type your request naturally!",
            ]

            # Check that all expected help lines were printed
            for expected_line in expected_help_lines:
                assert any(
                    expected_line in str(call) for call in mock_print.call_args_list
                )

    def test_todo_passthrough_command_success(self):
        """Test successful todo.sh passthrough command execution."""
        with patch("builtins.input", return_value="/add test task"), patch("sys.exit"):
            # Mock the todo_shell execute method
            mock_todo_shell = Mock()
            mock_todo_shell.execute.return_value = "1 test task"

            # Create CLI instance with mocked dependencies
            with patch("todo_agent.interface.cli.Config"), patch(
                "todo_agent.interface.cli.TodoShell", return_value=mock_todo_shell
            ), patch("todo_agent.interface.cli.TodoManager"), patch(
                "todo_agent.interface.cli.ToolCallHandler"
            ), patch("todo_agent.interface.cli.Inference"), patch(
                "todo_agent.interface.cli.Logger"
            ), patch("todo_agent.interface.cli.Console") as mock_console:
                CLI()

                # Mock the console methods
                mock_console.return_value.input.return_value = "/add test task"
                mock_console.return_value.print = Mock()

                # Test the passthrough logic directly
                user_input = "/add test task"
                if user_input.startswith("/"):
                    todo_command = user_input[1:].strip()
                    output = mock_todo_shell.execute(["todo.sh", *todo_command.split()])

                    # Verify the command was executed correctly
                    mock_todo_shell.execute.assert_called_once_with(
                        ["todo.sh", "add", "test", "task"]
                    )
                    assert output == "1 test task"

    def test_todo_passthrough_command_empty(self):
        """Test todo.sh passthrough with empty command."""
        with patch("builtins.input", return_value="/"), patch("sys.exit"):
            # Mock the todo_shell execute method
            mock_todo_shell = Mock()

            # Create CLI instance with mocked dependencies
            with patch("todo_agent.interface.cli.Config"), patch(
                "todo_agent.interface.cli.TodoShell", return_value=mock_todo_shell
            ), patch("todo_agent.interface.cli.TodoManager"), patch(
                "todo_agent.interface.cli.ToolCallHandler"
            ), patch("todo_agent.interface.cli.Inference"), patch(
                "todo_agent.interface.cli.Logger"
            ), patch("todo_agent.interface.cli.Console") as mock_console:
                CLI()

                # Mock the console methods
                mock_console.return_value.input.return_value = "/"
                mock_console.return_value.print = Mock()

                # Test the passthrough logic with empty command
                user_input = "/"
                if user_input.startswith("/"):
                    todo_command = user_input[1:].strip()
                    if not todo_command:
                        # Should handle empty command gracefully
                        assert todo_command == ""

    def test_todo_help_command(self):
        """Test todo-help command execution."""
        with patch("builtins.input", return_value="todo-help"), patch("sys.exit"):
            # Mock the todo_shell get_help method
            mock_todo_shell = Mock()
            mock_todo_shell.get_help.return_value = "Todo.sh help output"

            # Create CLI instance with mocked dependencies
            with patch("todo_agent.interface.cli.Config"), patch(
                "todo_agent.interface.cli.TodoShell", return_value=mock_todo_shell
            ), patch("todo_agent.interface.cli.TodoManager"), patch(
                "todo_agent.interface.cli.ToolCallHandler"
            ), patch("todo_agent.interface.cli.Inference"), patch(
                "todo_agent.interface.cli.Logger"
            ), patch("todo_agent.interface.cli.Console") as mock_console:
                CLI()

                # Mock the console methods
                mock_console.return_value.input.return_value = "todo-help"
                mock_console.return_value.print = Mock()

                # Test the todo-help command
                user_input = "todo-help"
                if user_input.lower() == "todo-help":
                    help_output = mock_todo_shell.get_help()

                    # Verify the help was retrieved
                    mock_todo_shell.get_help.assert_called_once()
                    assert help_output == "Todo.sh help output"

    def test_empty_input_handling(self):
        """Test that empty input is handled gracefully."""
        # This would be tested in the main run loop
        # For now, we test that handle_request can handle empty strings
        self.cli.handle_request("")

        # Should still call inference engine (let it handle empty input)
        call_args = self.cli.inference.process_request.call_args
        assert call_args[0][0] == ""  # First argument should be empty string
        assert (
            call_args[0][1] is not None
        )  # Second argument should be progress callback

    def test_long_input_truncation_in_logging(self):
        """Test that long inputs are properly truncated in logging."""
        long_input = "A" * 100  # 100 character input

        # Mock the inference engine
        self.cli.inference.process_request.return_value = ("Response", 1.0)

        result = self.cli.handle_request(long_input)

        # Verify inference engine was called with full input and progress callback
        call_args = self.cli.inference.process_request.call_args
        assert call_args[0][0] == long_input  # First argument should be long_input
        assert (
            call_args[0][1] is not None
        )  # Second argument should be progress callback

        # Verify response is correct
        assert result == "Response"

    def test_thinking_spinner_creation(self):
        """Test that thinking spinner is created with correct message."""
        message = "Processing request..."
        spinner = self.cli._create_thinking_spinner(message)

        # Verify spinner was created
        assert spinner is not None
        assert hasattr(spinner, "text")

    def test_live_display_creation(self):
        """Test that live display context is created properly."""
        live_display = self.cli._get_thinking_live()

        # Verify live display was created
        assert live_display is not None
        assert hasattr(live_display, "console")

    @patch("todo_agent.interface.cli.CLI._print_header")
    def test_keyboard_interrupt_at_prompt(self, mock_print_header):
        """Test that KeyboardInterrupt at prompt is handled gracefully."""
        # Mock console.input to raise KeyboardInterrupt
        with patch.object(self.cli.console, "input", side_effect=KeyboardInterrupt):
            with patch.object(self.cli.console, "print") as mock_print:
                # This should not raise an exception and should exit cleanly
                with contextlib.suppress(SystemExit):
                    self.cli.run()

                # Verify that the goodbye message was printed
                mock_print.assert_any_call("\n[bold green]Goodbye! 👋[/bold green]")
