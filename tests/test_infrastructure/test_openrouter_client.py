"""
Tests for OpenRouterClient class.
"""

from unittest.mock import Mock, patch

import pytest
import requests

try:
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.openrouter_client import OpenRouterClient
except ImportError:
    from infrastructure.config import Config
    from infrastructure.openrouter_client import OpenRouterClient


class TestOpenRouterClient:
    """Test OpenRouterClient functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Patch the dependencies that are now initialized in the parent class
        with patch("todo_agent.infrastructure.llm_client.Logger") as mock_logger, patch(
            "todo_agent.infrastructure.llm_client.get_token_counter"
        ) as mock_token_counter:
            mock_logger.return_value = Mock()
            mock_token_counter.return_value = Mock()

            self.config = Mock(spec=Config)
            self.config.openrouter_api_key = "test_api_key"
            self.config.model = "test-model"
            self.client = OpenRouterClient(self.config)

    def test_initialization(self):
        """Test OpenRouterClient initialization."""
        assert self.client.api_key == "test_api_key"
        assert self.client.model == "test-model"
        assert self.client.base_url == "https://openrouter.ai/api/v1"
        assert self.client.logger is not None

    def test_get_provider_name(self):
        """Test getting provider name."""
        assert self.client.get_provider_name() == "openrouter"

    def test_get_request_timeout(self):
        """Test getting request timeout."""
        assert self.client.get_request_timeout() == 30  # 30 seconds for cloud APIs

    def test_get_request_headers(self):
        """Test request headers generation."""
        headers = self.client._get_request_headers()
        expected = {
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json",
        }
        assert headers == expected

    def test_get_request_payload(self):
        """Test request payload generation."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]

        payload = self.client._get_request_payload(messages, tools)
        expected = {
            "model": "test-model",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        assert payload == expected

    def test_get_api_endpoint(self):
        """Test API endpoint generation."""
        endpoint = self.client._get_api_endpoint()
        assert endpoint == "https://openrouter.ai/api/v1/chat/completions"

    @patch(
        "todo_agent.infrastructure.openrouter_client.OpenRouterClient._make_http_request"
    )
    def test_chat_with_tools_success(self, mock_make_request):
        """Test successful chat with tools."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]

        expected_response = {
            "choices": [
                {
                    "message": {
                        "content": "Hello there!",
                        "tool_calls": [
                            {"id": "call_1", "function": {"name": "test_tool"}}
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

        mock_make_request.return_value = expected_response

        result = self.client.chat_with_tools(messages, tools)

        assert result == expected_response
        mock_make_request.assert_called_once_with(messages, tools, False)

    @patch(
        "todo_agent.infrastructure.openrouter_client.OpenRouterClient._make_http_request"
    )
    def test_chat_with_tools_api_error(self, mock_make_request):
        """Test API error handling."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = []

        error_response = {
            "error": True,
            "error_type": "auth_error",
            "provider": "openrouter",
            "status_code": 401,
            "raw_error": "Unauthorized",
        }
        mock_make_request.return_value = error_response

        result = self.client.chat_with_tools(messages, tools)
        assert result == error_response
        mock_make_request.assert_called_once_with(messages, tools, False)

    @patch(
        "todo_agent.infrastructure.openrouter_client.OpenRouterClient._make_http_request"
    )
    def test_chat_with_tools_cancellation(self, mock_make_request):
        """Test chat with tools cancellation."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = []

        cancelled_response = {
            "error": True,
            "error_type": "cancelled",
            "provider": "openrouter",
            "status_code": 0,
            "raw_error": "Request cancelled by user",
        }
        mock_make_request.return_value = cancelled_response

        result = self.client.chat_with_tools(messages, tools, cancelled=True)
        assert result == cancelled_response
        mock_make_request.assert_called_once_with(messages, tools, True)

    def test_create_cancelled_response(self):
        """Test creating cancelled response."""
        cancelled_response = self.client._create_cancelled_response()

        expected = {
            "error": True,
            "error_type": "cancelled",
            "provider": "openrouter",
            "status_code": 0,
            "raw_error": "Request cancelled by user",
        }
        assert cancelled_response == expected

    def test_extract_tool_calls_with_tool_calls(self):
        """Test extracting tool calls from response with tool calls."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "I'll help you with that",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {"name": "list_tasks", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ]
        }

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["function"]["name"] == "list_tasks"

    def test_extract_tool_calls_no_tool_calls(self):
        """Test extracting tool calls from response without tool calls."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "I'll help you with that",
                    }
                }
            ]
        }

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 0

    def test_extract_tool_calls_empty_choices(self):
        """Test extracting tool calls from response with empty choices."""
        response = {"choices": []}

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 0

    def test_extract_tool_calls_no_choices(self):
        """Test extracting tool calls from response without choices."""
        response = {}

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 0

    def test_extract_tool_calls_with_error_response(self):
        """Test extracting tool calls from error response."""
        error_response = {
            "error": True,
            "error_type": "timeout",
            "provider": "openrouter",
        }

        tool_calls = self.client.extract_tool_calls(error_response)
        assert len(tool_calls) == 0

    def test_extract_content_success(self):
        """Test extracting content from successful response."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "Here are your tasks",
                    }
                }
            ]
        }

        content = self.client.extract_content(response)
        assert content == "Here are your tasks"

    def test_extract_content_no_content(self):
        """Test extracting content from response without content."""
        response = {"choices": [{"message": {}}]}

        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_empty_choices(self):
        """Test extracting content from response with empty choices."""
        response = {"choices": []}

        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_no_choices(self):
        """Test extracting content from response without choices."""
        response = {}

        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_with_error_response(self):
        """Test extracting content from error response."""
        error_response = {
            "error": True,
            "error_type": "timeout",
            "provider": "openrouter",
        }

        content = self.client.extract_content(error_response)
        assert content == ""

    def test_continue_with_tool_result(self):
        """Test continue with tool result method."""
        tool_result = {"result": "test"}
        result = self.client.continue_with_tool_result(tool_result)
        assert result == {}

    def test_process_response(self):
        """Test response processing and logging."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Hello",
                        "tool_calls": [
                            {"id": "call_1", "function": {"name": "test_tool"}}
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch.object(self.client.logger, "info") as mock_info, patch.object(
            self.client.logger, "debug"
        ) as mock_debug:
            self.client._process_response(response_data, 0.0)

            # Should log response details
            assert mock_info.call_count >= 2  # Latency and token usage
            assert mock_debug.call_count >= 1  # Raw response
