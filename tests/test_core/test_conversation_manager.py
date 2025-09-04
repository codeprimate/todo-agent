"""
Tests for ConversationManager.
"""

import pytest

from todo_agent.core.conversation_manager import ConversationManager, MessageRole


class TestConversationManager:
    """Test ConversationManager functionality."""

    def test_initialization(self):
        """Test ConversationManager initialization."""
        manager = ConversationManager()
        assert len(manager.history) == 0
        assert manager.max_tokens == 64000
        assert manager.max_messages == 100
        assert manager.system_prompt is None

    def test_add_message(self):
        """Test adding messages to conversation."""
        manager = ConversationManager()

        manager.add_message(MessageRole.USER, "Hello")
        assert len(manager.history) == 1
        assert manager.history[0].role == MessageRole.USER
        assert manager.history[0].content == "Hello"
        assert manager.history[0].timestamp is not None

    def test_get_messages(self):
        """Test getting messages in API format."""
        manager = ConversationManager()

        manager.add_message(MessageRole.USER, "Hello")
        manager.add_message(MessageRole.ASSISTANT, "Hi there!")

        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    def test_system_prompt(self):
        """Test system prompt handling."""
        manager = ConversationManager()
        prompt = "You are a helpful assistant."

        manager.set_system_prompt(prompt)
        assert manager.system_prompt == prompt

        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == prompt

    def test_clear_conversation(self):
        """Test clearing conversation history."""
        manager = ConversationManager()

        manager.add_message(MessageRole.USER, "Hello")
        manager.add_message(MessageRole.ASSISTANT, "Hi!")
        manager.set_system_prompt("System prompt")

        # Clear but keep system
        manager.clear_conversation(keep_system=True)
        assert len(manager.history) == 1
        assert manager.history[0].role == MessageRole.SYSTEM

        # Clear everything
        manager.clear_conversation(keep_system=False)
        assert len(manager.history) == 0

    def test_conversation_summary(self):
        """Test conversation summary generation."""
        manager = ConversationManager()

        manager.add_message(MessageRole.USER, "Hello")
        manager.add_message(MessageRole.ASSISTANT, "Hi!")
        manager.add_message(MessageRole.TOOL, "Tool result")

        summary = manager.get_conversation_summary()
        assert summary["total_messages"] == 3
        assert summary["user_messages"] == 1
        assert summary["assistant_messages"] == 1
        assert summary["tool_messages"] == 1
        assert summary["estimated_tokens"] > 0

    def test_tool_call_sequence(self):
        """Test adding tool call sequences."""
        manager = ConversationManager()

        tool_calls = [
            {"id": "call_1", "function": {"name": "test_tool"}},
            {"id": "call_2", "function": {"name": "test_tool2"}},
        ]

        tool_results = [
            {"tool_call_id": "call_1", "output": "Result 1"},
            {"tool_call_id": "call_2", "output": "Result 2"},
        ]

        manager.add_tool_call_sequence(tool_calls, tool_results)

        messages = manager.get_messages()
        assert (
            len(messages) == 3
        )  # 1 assistant message with tool calls + 2 tool results

        # Check assistant message with tool calls
        assert messages[0]["role"] == "assistant"
        assert "tool_calls" in messages[0]
        assert len(messages[0]["tool_calls"]) == 2
        assert messages[0]["tool_calls"][0]["id"] == "call_1"
        assert messages[0]["tool_calls"][1]["id"] == "call_2"

        # Check tool results
        assert messages[1]["role"] == "tool"
        assert messages[1]["tool_call_id"] == "call_1"
        assert messages[1]["content"] == "Result 1"
        assert messages[2]["role"] == "tool"
        assert messages[2]["tool_call_id"] == "call_2"
        assert messages[2]["content"] == "Result 2"

    def test_recent_context(self):
        """Test getting recent conversation context."""
        manager = ConversationManager()

        for i in range(10):
            manager.add_message(MessageRole.USER, f"Message {i}")

        recent = manager.get_recent_context(num_messages=5)
        assert len(recent) == 5
        assert recent[-1].content == "Message 9"

    def test_message_limit_trimming(self):
        """Test trimming when message limit is exceeded."""
        manager = ConversationManager(max_messages=3)

        manager.set_system_prompt("System prompt")
        manager.add_message(MessageRole.USER, "Message 1")
        manager.add_message(MessageRole.ASSISTANT, "Response 1")
        manager.add_message(MessageRole.USER, "Message 2")
        manager.add_message(MessageRole.ASSISTANT, "Response 2")

        # Should trim to keep system prompt and most recent messages
        assert len(manager.history) <= 3
        assert manager.history[0].role == MessageRole.SYSTEM  # System prompt preserved

    def test_token_estimation(self):
        """Test token estimation functionality."""
        manager = ConversationManager()

        # Test basic token counting
        test_text = "Hello, world!"
        tokens = manager._estimate_tokens(test_text)
        assert tokens > 0

        # Test that token count is consistent
        tokens2 = manager._estimate_tokens(test_text)
        assert tokens == tokens2

    def test_efficient_token_tracking(self):
        """Test that token counting is efficient with running total."""
        manager = ConversationManager(max_tokens=1000, max_messages=10)

        # Add several messages and verify running total
        messages = [
            ("Hello, this is a test message.", 0),
            ("Another message with some content.", 0),
            ("Third message for testing purposes.", 0),
        ]

        for content, _ in messages:
            manager.add_message(MessageRole.USER, content)

        # Verify running total is accurate
        expected_total = sum(
            manager._estimate_tokens(content) for content, _ in messages
        )
        assert manager._total_tokens == expected_total

        # Test that removing messages decrements the count correctly
        initial_count = manager._total_tokens
        if len(manager.history) > 1:
            # Remove the first non-system message
            for i, msg in enumerate(manager.history):
                if msg.role != MessageRole.SYSTEM:
                    removed_tokens = msg.token_count
                    manager._remove_message_at_index(i)
                    assert manager._total_tokens == initial_count - removed_tokens
                    break
