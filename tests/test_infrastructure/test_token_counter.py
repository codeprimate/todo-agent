"""
Tests for TokenCounter class.
"""

from unittest.mock import Mock, patch

import pytest

try:
    from todo_agent.infrastructure.token_counter import TokenCounter, get_token_counter
except ImportError:
    from infrastructure.token_counter import TokenCounter, get_token_counter


class TestTokenCounter:
    """Test TokenCounter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter("gpt-4")

    def test_initialization(self):
        """Test TokenCounter initialization."""
        counter = TokenCounter("gpt-4")
        assert counter.model == "gpt-4"
        assert counter._encoder is not None

    def test_count_tokens_basic(self):
        """Test basic token counting with meaningful assertions."""
        # Test simple text
        text = "Hello world"
        tokens = self.token_counter.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

        # Test empty string
        assert self.token_counter.count_tokens("") == 0

        # Test None
        assert self.token_counter.count_tokens(None) == 0

    def test_count_tokens_accuracy_vs_character_estimation(self):
        """Test that token counting is more accurate than character-based estimation."""
        test_cases = [
            ("Hello world", 2),  # Simple text
            (
                "This is a longer sentence with more words and complexity.",
                11,
            ),  # Longer text
            ("Special characters: @#$%^&*() and punctuation!", 12),  # Special chars
            ("Numbers: 1234567890 and text mixed together", 11),  # Numbers
            ("你好世界", 5),  # CJK characters
            ("Mixed: Hello 123 @#$% world! 你好", 13),  # Mixed content
        ]

        for text, expected_min_tokens in test_cases:
            actual_tokens = self.token_counter.count_tokens(text)
            char_estimate = len(text) // 4

            # Token count should be reasonable
            assert actual_tokens >= expected_min_tokens

            # For longer texts, token count should be different from character estimate
            # (shorter texts might coincidentally match)
            if len(text) > 15:
                assert actual_tokens != char_estimate, (
                    f"Token count {actual_tokens} equals char estimate {char_estimate} for longer text '{text}'"
                )

            # Token count should be within reasonable bounds of character estimate
            # (not too far off, but more accurate)
            ratio = actual_tokens / max(char_estimate, 1)
            # CJK characters typically have higher token ratios
            max_ratio = 6.0 if any(ord(c) > 127 for c in text) else 3.0
            assert 0.3 <= ratio <= max_ratio, (
                f"Token count ratio {ratio} for '{text}' is unreasonable"
            )

    def test_count_tokens_consistency(self):
        """Test that token counting is consistent for same input."""
        text = "This is a test sentence with some complexity."

        # Same text should give same token count
        tokens1 = self.token_counter.count_tokens(text)
        tokens2 = self.token_counter.count_tokens(text)
        assert tokens1 == tokens2

        # Different text should give different token count
        different_text = "This is a different test sentence."
        different_tokens = self.token_counter.count_tokens(different_text)
        assert different_tokens != tokens1

    def test_count_message_tokens_structure(self):
        """Test that message token counting includes all message components."""
        message = {"role": "user", "content": "Hello, how are you?"}
        tokens = self.token_counter.count_message_tokens(message)

        # Should be more than just content tokens
        content_tokens = self.token_counter.count_tokens("Hello, how are you?")
        role_tokens = self.token_counter.count_tokens("user")
        expected_min = content_tokens + role_tokens

        assert tokens >= expected_min

    def test_count_message_tokens_with_tool_calls(self):
        """Test that tool calls add to message token count."""
        message_with_tools = {
            "role": "assistant",
            "content": "I'll help you with that.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "list_tasks",
                        "arguments": '{"project": "work"}',
                    },
                }
            ],
        }

        message_without_tools = {
            "role": "assistant",
            "content": "I'll help you with that.",
        }

        tokens_with_tools = self.token_counter.count_message_tokens(message_with_tools)
        tokens_without_tools = self.token_counter.count_message_tokens(
            message_without_tools
        )

        # Tool calls should add tokens
        assert tokens_with_tools > tokens_without_tools

    def test_count_tool_call_tokens_structure(self):
        """Test that tool call token counting includes all components."""
        tool_call = {
            "id": "call_1",
            "function": {"name": "add_task", "arguments": '{"text": "New task"}'},
        }
        tokens = self.token_counter.count_tool_call_tokens(tool_call)

        # Should include id, name, and arguments
        id_tokens = self.token_counter.count_tokens("call_1")
        name_tokens = self.token_counter.count_tokens("add_task")
        args_tokens = self.token_counter.count_tokens('{"text": "New task"}')
        expected_min = id_tokens + name_tokens + args_tokens

        assert tokens >= expected_min

    def test_count_messages_tokens_accumulation(self):
        """Test that multiple messages accumulate tokens correctly."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        total_tokens = self.token_counter.count_messages_tokens(messages)

        # Should equal sum of individual message tokens
        individual_sum = sum(
            self.token_counter.count_message_tokens(msg) for msg in messages
        )
        assert total_tokens == individual_sum

        # Should be more than single message
        single_tokens = self.token_counter.count_message_tokens(messages[0])
        assert total_tokens > single_tokens

    def test_count_messages_tokens_empty(self):
        """Test counting tokens in empty message list."""
        tokens = self.token_counter.count_messages_tokens([])
        assert tokens == 0

    def test_count_tools_tokens_structure(self):
        """Test that tools token counting works with tool definitions."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "List all tasks",
                    "parameters": {
                        "type": "object",
                        "properties": {"project": {"type": "string"}},
                    },
                },
            }
        ]
        tokens = self.token_counter.count_tools_tokens(tools)
        assert tokens > 0

    def test_count_tools_tokens_empty(self):
        """Test counting tokens in empty tools list."""
        tokens = self.token_counter.count_tools_tokens([])
        assert tokens == 0

    def test_count_request_tokens_complete(self):
        """Test counting tokens in a complete request."""
        messages = [{"role": "user", "content": "List my tasks"}]
        tools = [
            {
                "type": "function",
                "function": {"name": "list_tasks", "description": "List all tasks"},
            }
        ]

        request_tokens = self.token_counter.count_request_tokens(messages, tools)
        messages_tokens = self.token_counter.count_messages_tokens(messages)
        tools_tokens = self.token_counter.count_tools_tokens(tools)

        # Should equal sum of messages and tools tokens
        assert request_tokens == messages_tokens + tools_tokens

    def test_count_request_tokens_no_tools(self):
        """Test counting tokens in a request without tools."""
        messages = [{"role": "user", "content": "Hello"}]
        tokens = self.token_counter.count_request_tokens(messages)

        # Should equal just messages tokens
        messages_tokens = self.token_counter.count_messages_tokens(messages)
        assert tokens == messages_tokens

    def test_get_token_counter(self):
        """Test get_token_counter function."""
        counter = get_token_counter("gpt-4")
        assert isinstance(counter, TokenCounter)
        assert counter.model == "gpt-4"

    @patch("tiktoken.get_encoding")
    def test_initialization_fallback(self, mock_get_encoding):
        """Test initialization with fallback to cl100k_base."""
        # Mock to succeed with cl100k_base
        mock_get_encoding.return_value = Mock()

        counter = TokenCounter("unknown-model")
        assert counter.model == "unknown-model"
        assert counter._encoder is not None

    @patch("tiktoken.get_encoding")
    def test_initialization_complete_failure(self, mock_get_encoding):
        """Test initialization when tiktoken.get_encoding fails."""
        mock_get_encoding.side_effect = Exception("All encodings failed")

        with pytest.raises(Exception, match="All encodings failed"):
            TokenCounter("unknown-model")

    def test_token_counting_edge_cases(self):
        """Test token counting with edge cases and special characters."""
        edge_cases = [
            ("", 0),  # Empty string
            (" ", 1),  # Single space
            ("\n", 1),  # Newline
            ("\t", 1),  # Tab
            ("a", 1),  # Single character
            ("aa", 1),  # Two characters (might be one token)
            ("aaa", 1),  # Three characters (might be one token)
            ("aaaa", 2),  # Four characters (likely two tokens)
        ]

        for text, expected_max in edge_cases:
            tokens = self.token_counter.count_tokens(text)
            assert tokens <= expected_max, (
                f"Token count {tokens} for '{text}' exceeds expected maximum {expected_max}"
            )

    def test_token_counting_unicode_handling(self):
        """Test that Unicode characters are handled correctly."""
        unicode_texts = [
            "Hello 世界",  # Mixed ASCII and CJK
            "Привет мир",  # Cyrillic
            "مرحبا بالعالم",  # Arabic
            "नमस्ते दुनिया",  # Devanagari
            "🌍 Hello World 🌎",  # Emojis
        ]

        for text in unicode_texts:
            tokens = self.token_counter.count_tokens(text)
            assert tokens > 0
            assert isinstance(tokens, int)

            # Unicode text should have reasonable token count
            # (not too many tokens for the character count)
            char_count = len(text)
            assert tokens <= char_count * 2, (
                f"Token count {tokens} for '{text}' is unreasonably high"
            )
