"""
Tests for Inference class.
"""

import signal
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from todo_agent.infrastructure.inference import Inference


class TestInference:
    """Test Inference functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock all dependencies
        with patch(
            "todo_agent.infrastructure.inference.Config"
        ) as mock_config_class, patch(
            "todo_agent.infrastructure.inference.LLMClientFactory"
        ) as mock_factory, patch(
            "todo_agent.infrastructure.inference.Logger"
        ) as mock_logger, patch(
            "todo_agent.infrastructure.inference.ConversationManager"
        ) as mock_conversation_manager, patch(
            "todo_agent.infrastructure.inference.ToolCallHandler"
        ) as mock_tool_handler:
            # Set up mock config
            mock_config = Mock()
            mock_config.validate.return_value = True
            mock_config_class.return_value = mock_config

            # Set up mock components
            mock_llm_client = Mock()
            mock_llm_client.get_model_name.return_value = "test-model"
            mock_factory.create_client.return_value = mock_llm_client
            mock_logger.return_value = Mock()
            mock_conversation_manager.return_value = Mock()

            # Set up mock tool handler
            mock_tool_handler_instance = Mock()
            mock_tool_handler_instance.tools = [
                {
                    "function": {
                        "name": "list_tasks",
                        "description": "List tasks",
                        "parameters": {"properties": {}},
                    }
                }
            ]
            mock_tool_handler.return_value = mock_tool_handler_instance

            # Create inference instance
            self.inference = Inference(mock_config, mock_tool_handler_instance)

    def test_initialization_creates_required_components(self):
        """Test that Inference initialization creates all required components with correct configuration."""
        # Verify all required components are created
        assert hasattr(self.inference, "config")
        assert hasattr(self.inference, "tool_handler")
        assert hasattr(self.inference, "logger")
        assert hasattr(self.inference, "llm_client")
        assert hasattr(self.inference, "conversation_manager")

        # Verify components are properly configured
        assert self.inference.config is not None
        assert self.inference.tool_handler is not None
        assert self.inference.logger is not None
        assert self.inference.llm_client is not None
        assert self.inference.conversation_manager is not None

        # Verify the tool handler has the expected tools
        assert hasattr(self.inference.tool_handler, "tools")
        assert len(self.inference.tool_handler.tools) > 0

    def test_process_request_success(self):
        """Test successful request processing."""
        user_input = "List my tasks"

        # Mock the conversation flow
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )
        self.inference.conversation_manager.add_tool_call_sequence = Mock()
        self.inference.conversation_manager.add_message = Mock()

        # Mock LLM response
        mock_response = {"choices": [{"message": {"content": "Here are your tasks"}}]}
        self.inference.llm_client.chat_with_tools = Mock(return_value=mock_response)
        self.inference.llm_client.extract_tool_calls = Mock(return_value=[])
        self.inference.llm_client.extract_content = Mock(
            return_value="Here are your tasks"
        )

        result, thinking_time = self.inference.process_request(user_input)

        assert result == "Here are your tasks"
        assert isinstance(thinking_time, float)
        assert thinking_time >= 0
        self.inference.conversation_manager.add_message.assert_called()

    def test_system_prompt_datetime_interpolation(self):
        """Test that current datetime is properly interpolated into system prompt."""
        # Mock the file reading
        mock_prompt_content = (
            "CURRENT DATE/TIME: {current_datetime}\nCALENDAR: {calendar_output}"
        )

        with patch("builtins.open", mock_open(read_data=mock_prompt_content)):
            # Call the method that loads the system prompt
            result = self.inference._load_system_prompt()

            # Verify that the datetime placeholder is replaced with actual datetime
            assert "{current_datetime}" not in result
            assert "CURRENT DATE/TIME:" in result

            # Verify that the datetime format is correct (YYYY-MM-DD HH:MM:SS)
            import re

            datetime_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
            assert re.search(datetime_pattern, result), (
                "System prompt should contain properly formatted datetime"
            )

            # Verify that calendar_output is also interpolated
            assert "{calendar_output}" not in result
            # Should contain calendar month information (could be any month)
            import re

            month_pattern = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            assert re.search(month_pattern, result), (
                "Should contain calendar month information"
            )

    def test_process_request_with_tool_calls(self):
        """Test request processing with tool calls."""
        user_input = "List my tasks"

        # Mock conversation flow
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )
        self.inference.conversation_manager.add_tool_call_sequence = Mock()
        self.inference.conversation_manager.add_message = Mock()

        # Mock tool calls
        tool_calls = [
            {"id": "call_1", "function": {"name": "list_tasks", "arguments": "{}"}}
        ]
        tool_results = [{"tool_call_id": "call_1", "output": "1. Task 1\n2. Task 2"}]

        # Mock LLM responses
        self.inference.llm_client.chat_with_tools = Mock(
            side_effect=[
                {"choices": [{"message": {"tool_calls": tool_calls}}]},
                {"choices": [{"message": {"content": "Here are your tasks"}}]},
            ]
        )
        self.inference.llm_client.extract_tool_calls = Mock(
            side_effect=[tool_calls, []]
        )
        self.inference.llm_client.extract_content = Mock(
            return_value="Here are your tasks"
        )

        # Mock tool execution
        self.inference.tool_handler.execute_tool = Mock(return_value=tool_results[0])

        result, thinking_time = self.inference.process_request(user_input)

        assert result == "Here are your tasks"
        assert isinstance(thinking_time, float)
        assert thinking_time >= 0
        self.inference.tool_handler.execute_tool.assert_called_once()

    def test_process_request_exception(self):
        """Test request processing with exception."""
        user_input = "Invalid request"

        # Mock exception
        self.inference.conversation_manager.add_message = Mock(
            side_effect=Exception("Test error")
        )

        result, thinking_time = self.inference.process_request(user_input)

        assert result == "Error: Test error"
        assert isinstance(thinking_time, float)
        assert thinking_time >= 0

    def test_get_conversation_summary(self):
        """Test getting conversation summary."""
        mock_summary = {
            "total_messages": 5,
            "user_messages": 2,
            "assistant_messages": 2,
            "tool_messages": 1,
            "estimated_tokens": 100,
        }
        self.inference.conversation_manager.get_conversation_summary = Mock(
            return_value=mock_summary
        )

        result = self.inference.get_conversation_summary()

        assert result == mock_summary
        self.inference.conversation_manager.get_conversation_summary.assert_called_once()

    def test_clear_conversation(self):
        """Test clearing conversation."""
        self.inference.conversation_manager.clear_conversation = Mock()

        self.inference.clear_conversation()

        self.inference.conversation_manager.clear_conversation.assert_called_once()

    def test_get_conversation_manager(self):
        """Test getting conversation manager."""
        result = self.inference.get_conversation_manager()

        assert result == self.inference.conversation_manager

    def test_signal_handler_setup(self):
        """Test that signal handler is properly set up during initialization."""
        # Verify cancellation flag is initialized
        assert hasattr(self.inference, "_cancelled")
        assert self.inference._cancelled is False

        # Verify signal handler method exists
        assert hasattr(self.inference, "_handle_interrupt")
        assert callable(self.inference._handle_interrupt)

        # Verify cancellation handler method exists
        assert hasattr(self.inference, "_handle_cancellation")
        assert callable(self.inference._handle_cancellation)

    def test_handle_interrupt_sets_cancellation_flag(self):
        """Test that signal handler sets the cancellation flag."""
        # Initially not cancelled
        assert self.inference._cancelled is False

        # Simulate signal handler call
        self.inference._handle_interrupt(signal.SIGINT, None)

        # Should now be cancelled
        assert self.inference._cancelled is True

    def test_handle_cancellation_adds_message_and_resets_flag(self):
        """Test that cancellation handler adds message and resets flag."""
        # Set up cancellation flag
        self.inference._cancelled = True

        # Mock conversation manager
        self.inference.conversation_manager.add_message = Mock()

        # Call cancellation handler with a start time
        import time

        start_time = time.time() - 1.5  # Simulate 1.5 seconds elapsed
        result, thinking_time = self.inference._handle_cancellation(start_time)

        # Verify response
        assert result == "I stopped."
        assert thinking_time >= 1.4  # Should be approximately 1.5 seconds
        assert thinking_time <= 1.6  # Allow some tolerance for test execution time

        # Verify message was added to conversation
        self.inference.conversation_manager.add_message.assert_called_once()
        call_args = self.inference.conversation_manager.add_message.call_args[0]
        assert call_args[0].value == "assistant"  # MessageRole.ASSISTANT
        assert call_args[1] == "I stopped."

        # Verify flag was reset
        assert self.inference._cancelled is False

    def test_process_request_cancellation_before_llm_call(self):
        """Test cancellation check before LLM API call."""
        user_input = "List my tasks"

        # Set up cancellation flag
        self.inference._cancelled = True

        # Mock conversation manager
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )

        # Call process_request
        result, thinking_time = self.inference.process_request(user_input)

        # Should return cancellation response
        assert result == "I stopped."
        assert thinking_time >= 0.0  # Should be actual elapsed time

        # Should not have called LLM client
        self.inference.llm_client.chat_with_tools.assert_not_called()

    def test_process_request_cancellation_after_llm_call(self):
        """Test cancellation check after LLM response received."""
        user_input = "List my tasks"

        # Mock conversation manager
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )

        # Mock LLM response
        mock_response = {"choices": [{"message": {"content": "Here are your tasks"}}]}
        self.inference.llm_client.chat_with_tools = Mock(return_value=mock_response)
        self.inference.llm_client.extract_tool_calls = Mock(return_value=[])
        self.inference.llm_client.extract_content = Mock(
            return_value="Here are your tasks"
        )

        # Set up cancellation flag after LLM call would be made
        def mock_chat_with_tools(*_args, **_kwargs):
            self.inference._cancelled = True
            return mock_response

        self.inference.llm_client.chat_with_tools = Mock(
            side_effect=mock_chat_with_tools
        )

        # Call process_request
        result, thinking_time = self.inference.process_request(user_input)

        # Should return cancellation response
        assert result == "I stopped."
        assert thinking_time >= 0.0  # Should be actual elapsed time

        # Should have called LLM client once
        self.inference.llm_client.chat_with_tools.assert_called_once()

    def test_process_request_cancellation_between_tool_executions(self):
        """Test cancellation between tool executions."""
        user_input = "List my tasks"

        # Mock conversation flow
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )
        self.inference.conversation_manager.add_tool_call_sequence = Mock()

        # Mock tool calls
        tool_calls = [
            {"id": "call_1", "function": {"name": "list_tasks", "arguments": "{}"}},
            {"id": "call_2", "function": {"name": "add_task", "arguments": "{}"}},
        ]

        # Mock LLM responses
        self.inference.llm_client.chat_with_tools = Mock(
            return_value={"choices": [{"message": {"tool_calls": tool_calls}}]}
        )
        self.inference.llm_client.extract_tool_calls = Mock(return_value=tool_calls)

        # Mock tool execution to set cancellation flag after first tool
        def mock_execute_tool(tool_call):
            if tool_call["id"] == "call_1":
                self.inference._cancelled = True
            return {"tool_call_id": tool_call["id"], "output": "success"}

        self.inference.tool_handler.execute_tool = Mock(side_effect=mock_execute_tool)

        # Call process_request
        result, thinking_time = self.inference.process_request(user_input)

        # Should return cancellation response
        assert result == "I stopped."
        assert thinking_time >= 0.0  # Should be actual elapsed time

        # Should have executed first tool but not second
        assert self.inference.tool_handler.execute_tool.call_count == 1

    def test_process_request_cancellation_before_tool_execution(self):
        """Test cancellation before any tool execution."""
        user_input = "List my tasks"

        # Mock conversation flow
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )

        # Mock tool calls
        tool_calls = [
            {"id": "call_1", "function": {"name": "list_tasks", "arguments": "{}"}}
        ]

        # Mock LLM responses
        self.inference.llm_client.chat_with_tools = Mock(
            return_value={"choices": [{"message": {"tool_calls": tool_calls}}]}
        )
        self.inference.llm_client.extract_tool_calls = Mock(return_value=tool_calls)

        # Set cancellation flag before tool execution
        self.inference._cancelled = True

        # Call process_request
        result, thinking_time = self.inference.process_request(user_input)

        # Should return cancellation response
        assert result == "I stopped."
        assert thinking_time >= 0.0  # Should be actual elapsed time

        # Should not have executed any tools
        self.inference.tool_handler.execute_tool.assert_not_called()

    def test_process_request_cancellation_after_tool_execution(self):
        """Test cancellation after tool execution but before adding to conversation."""
        user_input = "List my tasks"

        # Mock conversation flow
        self.inference.conversation_manager.add_message = Mock()
        self.inference.conversation_manager.get_messages = Mock(
            return_value=[{"role": "user", "content": user_input}]
        )
        self.inference.conversation_manager.add_tool_call_sequence = Mock()

        # Mock tool calls
        tool_calls = [
            {"id": "call_1", "function": {"name": "list_tasks", "arguments": "{}"}}
        ]

        # Mock LLM responses
        self.inference.llm_client.chat_with_tools = Mock(
            return_value={"choices": [{"message": {"tool_calls": tool_calls}}]}
        )
        self.inference.llm_client.extract_tool_calls = Mock(return_value=tool_calls)

        # Mock tool execution to set cancellation flag after execution
        def mock_execute_tool(tool_call):
            self.inference._cancelled = True
            return {"tool_call_id": tool_call["id"], "output": "success"}

        self.inference.tool_handler.execute_tool = Mock(side_effect=mock_execute_tool)

        # Call process_request
        result, thinking_time = self.inference.process_request(user_input)

        # Should return cancellation response
        assert result == "I stopped."
        assert thinking_time >= 0.0  # Should be actual elapsed time

        # Should have executed the tool
        self.inference.tool_handler.execute_tool.assert_called_once()

        # Should not have added tool results to conversation
        self.inference.conversation_manager.add_tool_call_sequence.assert_not_called()
