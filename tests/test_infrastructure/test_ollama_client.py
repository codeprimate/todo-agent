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

        with patch(
            "todo_agent.infrastructure.ollama_client.Logger"
        ) as mock_logger, patch(
            "todo_agent.infrastructure.ollama_client.get_token_counter"
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

    @patch("requests.post")
    def test_chat_with_tools_success(self, mock_post):
        """Test successful chat with tools."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Here are your tasks", "tool_calls": []}
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "List my tasks"}]
        tools = [{"function": {"name": "list_tasks", "description": "List tasks"}}]

        response = self.client.chat_with_tools(messages, tools)

        assert response == mock_response.json.return_value
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/chat",
            headers={"Content-Type": "application/json"},
            json={
                "model": "llama3.2",
                "messages": messages,
                "tools": tools,
                "stream": False,
            },
        )

    @patch("requests.post")
    def test_chat_with_tools_api_error(self, mock_post):
        """Test chat with tools when API returns error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "List my tasks"}]
        tools = [{"function": {"name": "list_tasks", "description": "List tasks"}}]

        with pytest.raises(Exception, match="Ollama API error: Internal Server Error"):
            self.client.chat_with_tools(messages, tools)

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
        response = {"message": {"content": "Here are your tasks"}}

        tool_calls = self.client.extract_tool_calls(response)

        assert len(tool_calls) == 0

    def test_extract_content_with_content(self):
        """Test extracting content from response with content."""
        response = {"message": {"content": "Here are your tasks"}}

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
