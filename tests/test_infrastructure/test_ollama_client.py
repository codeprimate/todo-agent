"""
Tests for OllamaClient.
"""

import json
from unittest.mock import Mock, mock_open, patch

import pytest

from todo_agent.infrastructure.config import Config
from todo_agent.infrastructure.ollama_client import OllamaClient


class TestOllamaClient:
    """Test OllamaClient functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config.provider = "ollama"
        self.config.ollama_base_url = "http://localhost:11434"
        self.config.ollama_model = "llama3.2"

        # Patch the dependencies that are now initialized in the parent class
        with patch("todo_agent.infrastructure.llm_client.Logger") as mock_logger, patch(
            "todo_agent.infrastructure.llm_client.get_token_counter"
        ) as mock_token_counter:
            mock_logger.return_value = Mock()
            mock_token_counter.return_value = Mock()

            self.client = OllamaClient(self.config)

    def test_initialization(self):
        """Test client initialization."""
        assert self.client.config == self.config
        assert self.client.base_url == "http://localhost:11434"
        assert self.client.model == "llama3.2"
        assert self.client.logger is not None
        assert self.client.token_counter is not None

    def test_get_model_name(self):
        """Test getting model name."""
        assert self.client.get_model_name() == "llama3.2"

    def test_get_provider_name(self):
        """Test getting provider name."""
        assert self.client.get_provider_name() == "ollama"

    def test_get_request_timeout(self):
        """Test getting request timeout."""
        assert self.client.get_request_timeout() == 120  # 2 minutes for Ollama

    def test_get_request_headers(self):
        """Test request headers generation."""
        headers = self.client._get_request_headers()
        assert headers == {"Content-Type": "application/json"}

    def test_get_request_payload(self):
        """Test request payload generation."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]

        payload = self.client._get_request_payload(messages, tools)
        expected = {
            "model": "llama3.2",
            "messages": messages,
            "tools": tools,
            "stream": False,
            "reasoning_effort": "low",
        }
        assert payload == expected

    def test_get_api_endpoint(self):
        """Test API endpoint generation."""
        endpoint = self.client._get_api_endpoint()
        assert endpoint == "http://localhost:11434/api/chat"

    @patch("todo_agent.infrastructure.ollama_client.OllamaClient._make_http_request")
    def test_chat_with_tools_success(self, mock_make_request):
        """Test successful chat with tools."""
        # Mock the common HTTP request method
        expected_response = {
            "message": {"content": "Here are your tasks", "tool_calls": []}
        }
        mock_make_request.return_value = expected_response

        messages = [{"role": "user", "content": "List my tasks"}]
        tools = [{"function": {"name": "list_tasks", "description": "List tasks"}}]

        response = self.client.chat_with_tools(messages, tools)

        assert response == expected_response
        mock_make_request.assert_called_once_with(messages, tools, False)

    @patch("todo_agent.infrastructure.ollama_client.OllamaClient._make_http_request")
    def test_chat_with_tools_api_error(self, mock_make_request):
        """Test chat with tools when API returns error."""
        # Mock error response from the common method
        error_response = {
            "error": True,
            "error_type": "general_error",
            "provider": "ollama",
            "status_code": 500,
            "raw_error": "Internal Server Error",
        }
        mock_make_request.return_value = error_response

        messages = [{"role": "user", "content": "List my tasks"}]
        tools = [{"function": {"name": "list_tasks", "description": "List tasks"}}]

        response = self.client.chat_with_tools(messages, tools)
        assert response == error_response
        mock_make_request.assert_called_once_with(messages, tools, False)

    def test_extract_tool_calls_with_tools(self):
        """Test extracting tool calls from response with tools."""
        response = {
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

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["function"]["name"] == "list_tasks"

    def test_extract_tool_calls_without_tools(self):
        """Test extracting tool calls from response without tools."""
        response = {
            "message": {
                "content": "I'll help you with that",
            }
        }

        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 0

    def test_extract_tool_calls_with_error_response(self):
        """Test extracting tool calls from error response."""
        error_response = {"error": True, "error_type": "timeout", "provider": "ollama"}

        tool_calls = self.client.extract_tool_calls(error_response)
        assert len(tool_calls) == 0

    def test_extract_content_with_content(self):
        """Test extracting content from response with content."""
        response = {
            "message": {
                "content": "Here are your tasks",
            }
        }

        content = self.client.extract_content(response)
        assert content == "Here are your tasks"

    def test_extract_content_without_content(self):
        """Test extracting content from response without content."""
        response = {"message": {}}

        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_empty_response(self):
        """Test extracting content from empty response."""
        response = {}

        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_with_error_response(self):
        """Test extracting content from error response."""
        error_response = {"error": True, "error_type": "timeout", "provider": "ollama"}

        content = self.client.extract_content(error_response)
        assert content == ""

    def test_process_response(self):
        """Test response processing and logging."""
        response_data = {
            "message": {
                "content": "Hello",
                "tool_calls": [{"id": "call_1", "function": {"name": "test_tool"}}],
            }
        }

        with patch.object(self.client.logger, "info") as mock_info, patch.object(
            self.client.logger, "debug"
        ) as mock_debug:
            self.client._process_response(response_data, 0.0)

            # Should log response details
            assert mock_info.call_count >= 1
            assert mock_debug.call_count >= 1
