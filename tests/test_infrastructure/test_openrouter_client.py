"""
Tests for OpenRouterClient class.
"""

import pytest
from unittest.mock import Mock, patch
import requests

try:
    from todo_agent.infrastructure.openrouter_client import OpenRouterClient
    from todo_agent.infrastructure.config import Config
except ImportError:
    from infrastructure.openrouter_client import OpenRouterClient
    from infrastructure.config import Config


class TestOpenRouterClient:
    """Test OpenRouterClient functionality."""

    def setup_method(self):
        """Set up test fixtures."""
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

    def test_estimate_tokens(self):
        """Test token estimation method."""
        # Test with typical text
        text = "Hello world, this is a test message."
        estimated = self.client._estimate_tokens(text)
        # Should be more accurate than character-based estimation
        assert estimated > 0
        
        # Test with longer text that should show difference
        longer_text = "This is a much longer sentence that contains many more words and should demonstrate the difference between character-based estimation and actual tokenization."
        longer_estimated = self.client._estimate_tokens(longer_text)
        char_estimate = len(longer_text) // 4
        assert longer_estimated != char_estimate  # Should be different for longer text
        
        # Test with empty string
        assert self.client._estimate_tokens("") == 0

    def test_chat_with_tools_success(self):
        """Test successful chat with tools."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]
        
        expected_response = {
            "choices": [{
                "message": {
                    "content": "Hello there!",
                    "tool_calls": [{"id": "call_1", "function": {"name": "test_tool"}}]
                }
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 20,
                "total_tokens": 70
            }
        }
        
        with patch('requests.post') as mock_post, \
             patch.object(self.client.logger, 'info') as mock_info, \
             patch.object(self.client.logger, 'debug') as mock_debug:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_post.return_value = mock_response
            
            result = self.client.chat_with_tools(messages, tools)
            
            # Verify request was made correctly
            mock_post.assert_called_once_with(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer test_api_key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "test-model",
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
            )
            
            # Verify logging calls
            assert mock_info.call_count >= 2  # Request and response logs
            assert mock_debug.call_count >= 1  # Raw response log (request debug is commented out)
            
            assert result == expected_response

    def test_chat_with_tools_api_error(self):
        """Test API error handling."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = []
        
        with patch('requests.post') as mock_post, \
             patch.object(self.client.logger, 'error') as mock_error:
            
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception, match="OpenRouter API error: Unauthorized"):
                self.client.chat_with_tools(messages, tools)
            
            # Verify error was logged
            mock_error.assert_called_once_with("OpenRouter API error: Unauthorized")

    def test_extract_tool_calls_with_tool_calls(self):
        """Test extracting tool calls from response."""
        response = {
            "choices": [{
                "message": {
                    "content": "I'll help you",
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "list_tasks"}},
                        {"id": "call_2", "function": {"name": "add_task"}}
                    ]
                }
            }]
        }
        
        tool_calls = self.client.extract_tool_calls(response)
        assert len(tool_calls) == 2
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["function"]["name"] == "list_tasks"
        assert tool_calls[1]["id"] == "call_2"
        assert tool_calls[1]["function"]["name"] == "add_task"

    def test_extract_tool_calls_no_tool_calls(self):
        """Test extracting tool calls when none exist."""
        response = {
            "choices": [{
                "message": {
                    "content": "Just a regular response"
                }
            }]
        }
        
        tool_calls = self.client.extract_tool_calls(response)
        assert tool_calls == []

    def test_extract_tool_calls_empty_choices(self):
        """Test extracting tool calls with empty choices."""
        response = {"choices": []}
        
        tool_calls = self.client.extract_tool_calls(response)
        assert tool_calls == []

    def test_extract_tool_calls_no_choices(self):
        """Test extracting tool calls with no choices key."""
        response = {"some_other_key": "value"}
        
        tool_calls = self.client.extract_tool_calls(response)
        assert tool_calls == []

    def test_extract_content_success(self):
        """Test extracting content from response."""
        response = {
            "choices": [{
                "message": {
                    "content": "Here's your task list"
                }
            }]
        }
        
        content = self.client.extract_content(response)
        assert content == "Here's your task list"

    def test_extract_content_no_content(self):
        """Test extracting content when no content exists."""
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [{"id": "call_1"}]
                }
            }]
        }
        
        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_empty_choices(self):
        """Test extracting content with empty choices."""
        response = {"choices": []}
        
        content = self.client.extract_content(response)
        assert content == ""

    def test_extract_content_no_choices(self):
        """Test extracting content with no choices key."""
        response = {"some_other_key": "value"}
        
        content = self.client.extract_content(response)
        assert content == ""

    def test_continue_with_tool_result(self):
        """Test continue_with_tool_result method (currently returns empty dict)."""
        tool_result = {"tool_call_id": "call_1", "output": "Task added"}
        
        result = self.client.continue_with_tool_result(tool_result)
        assert result == {}

    def test_request_headers(self):
        """Test that request headers are properly set."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
            mock_post.return_value = mock_response
            
            self.client.chat_with_tools([], [])
            
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            
            assert headers["Authorization"] == "Bearer test_api_key"
            assert headers["Content-Type"] == "application/json"

    def test_request_payload_structure(self):
        """Test that request payload has correct structure."""
        messages = [{"role": "user", "content": "test"}]
        tools = [{"name": "test_tool"}]
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
            mock_post.return_value = mock_response
            
            self.client.chat_with_tools(messages, tools)
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload["model"] == "test-model"
            assert payload["messages"] == messages
            assert payload["tools"] == tools
            assert payload["tool_choice"] == "auto"

    def test_logging_functionality(self):
        """Test that logging methods work correctly."""
        messages = [{"role": "user", "content": "Test message"}]
        tools = [{"name": "test_tool", "description": "A test tool"}]
        
        expected_response = {
            "choices": [{
                "message": {
                    "content": "Test response"
                }
            }],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 10,
                "total_tokens": 35
            }
        }
        
        with patch('requests.post') as mock_post, \
             patch.object(self.client.logger, 'info') as mock_info, \
             patch.object(self.client.logger, 'debug') as mock_debug:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_post.return_value = mock_response
            
            result = self.client.chat_with_tools(messages, tools)
            
            # Verify logging calls were made
            info_calls = [call[0][0] for call in mock_info.call_args_list]
            debug_calls = [call[0][0] for call in mock_debug.call_args_list]
            
            # Check that request logging occurred
            request_logs = [log for log in info_calls if "Request sent" in log]
            assert len(request_logs) == 1
            assert "Token count:" in request_logs[0]
            
            # Check that response logging occurred
            response_logs = [log for log in info_calls if "Response received" in log]
            assert len(response_logs) == 1
            assert "Latency:" in response_logs[0]
            
            # Check that token usage was logged
            token_logs = [log for log in info_calls if "Token usage" in log]
            assert len(token_logs) == 1
            assert "Prompt: 25" in token_logs[0]
            assert "Completion: 10" in token_logs[0]
            assert "Total: 35" in token_logs[0]
            
            # Check that raw response was logged at debug level (request debug is commented out)
            raw_request_logs = [log for log in debug_calls if "Raw request payload" in log]
            raw_response_logs = [log for log in debug_calls if "Raw response" in log]
            assert len(raw_request_logs) == 0  # Request debug logging is commented out
            assert len(raw_response_logs) == 1
            
            assert result == expected_response
