"""
Conversation management for todo.sh LLM agent.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from todo_agent.infrastructure.token_counter import get_token_counter
except ImportError:
    from infrastructure.token_counter import get_token_counter  # type: ignore[no-redef]


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class ConversationMessage:
    role: MessageRole
    content: str
    tool_call_id: Optional[str] = None
    timestamp: Optional[float] = None
    tool_calls: Optional[List[Dict]] = None
    thinking_time: Optional[float] = None
    token_count: Optional[int] = None  # Cache token count for efficiency


class ConversationManager:
    """Manages conversation state and memory for LLM interactions."""

    def __init__(
        self, max_tokens: int = 64000, max_messages: int = 100, model: str = "gpt-4"
    ):
        self.history: List[ConversationMessage] = []
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.system_prompt: Optional[str] = None
        self.token_counter = get_token_counter(model)
        self._total_tokens: int = 0  # Running total of tokens in conversation
        self._tools_tokens: int = 0  # Cache for tools token count
        self._last_tools_hash: Optional[int] = None  # Track if tools have changed

    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_call_id: Optional[str] = None,
        thinking_time: Optional[float] = None,
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_call_id: Optional tool call identifier for tool messages
            thinking_time: Optional thinking time in seconds for assistant messages
        """
        # Calculate token count for this message
        token_count = self._estimate_tokens(content)

        message = ConversationMessage(
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            timestamp=time.time(),
            thinking_time=thinking_time,
            token_count=token_count,
        )

        self.history.append(message)
        self._total_tokens += token_count
        self._trim_if_needed()

    def get_messages(self, include_tool_calls: bool = True) -> List[Dict[str, Any]]:
        """
        Get conversation messages in OpenRouter API format.

        Args:
            include_tool_calls: Whether to include tool call messages

        Returns:
            List of message dictionaries for API consumption
        """
        messages: List[Dict[str, Any]] = []

        # Add conversation messages (system prompt is already in history)
        for msg in self.history:
            if msg.role == MessageRole.TOOL and not include_tool_calls:
                continue

            message_dict: Dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            # Handle tool calls in assistant messages
            if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls

            # Handle tool call IDs
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id

            messages.append(message_dict)

        return messages

    def _estimate_tokens(self, text: str) -> int:
        """
        Count tokens in text using accurate tokenization.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return self.token_counter.count_tokens(text)

    def _get_conversation_tokens(self) -> int:
        """Get total tokens in conversation using cached count."""
        return self._total_tokens

    def _remove_message_at_index(self, index: int) -> None:
        """
        Remove a message at the specified index and update token count.

        Args:
            index: Index of message to remove
        """
        if 0 <= index < len(self.history):
            message = self.history[index]
            # Decrement total token count by this message's token count
            if message.token_count is not None:
                self._total_tokens -= message.token_count
            self.history.pop(index)

    def get_request_tokens(self, tools: List[Dict[str, Any]]) -> int:
        """
        Get total request tokens (conversation + tools).

        Args:
            tools: Current tool definitions

        Returns:
            Total request tokens
        """
        # Check if tools have changed
        tools_hash = hash(str(tools))
        if tools_hash != self._last_tools_hash:
            self._tools_tokens = self.token_counter.count_tools_tokens(tools)
            self._last_tools_hash = tools_hash

        return self._total_tokens + self._tools_tokens

    def update_request_tokens(self, actual_prompt_tokens: int) -> None:
        """
        Update the conversation with actual token count from API response.

        Args:
            actual_prompt_tokens: Actual prompt tokens used by the API
        """
        # Calculate tools tokens by subtracting conversation tokens
        tools_tokens = actual_prompt_tokens - self._total_tokens
        if tools_tokens >= 0:
            self._tools_tokens = tools_tokens
        # Note: logger not available in this context, so we'll handle logging in the calling code

    def _trim_if_needed(self, tools: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Trim conversation history if it exceeds token or message limits.
        Preserves most recent messages and system prompt.

        Args:
            tools: Optional tools for request token calculation
        """
        # Check message count limit
        if len(self.history) > self.max_messages:
            # Keep system prompt and most recent messages
            system_messages = [
                msg for msg in self.history if msg.role == MessageRole.SYSTEM
            ]
            recent_messages = self.history[-self.max_messages :]
            self.history = (
                system_messages
                + recent_messages[-self.max_messages + len(system_messages) :]
            )

            # Recalculate total tokens after message count trimming
            self._recalculate_total_tokens()

        # Check token limit using request tokens if tools provided
        current_tokens = self.get_request_tokens(tools) if tools else self._total_tokens

        while current_tokens > self.max_tokens and len(self.history) > 2:
            # Find oldest non-system message to remove
            for i, msg in enumerate(self.history):
                if msg.role != MessageRole.SYSTEM:
                    self._remove_message_at_index(i)
                    break
            else:
                # No non-system messages found, break to avoid infinite loop
                break

            # Recalculate request tokens
            current_tokens = (
                self.get_request_tokens(tools) if tools else self._total_tokens
            )

    def _recalculate_total_tokens(self) -> None:
        """Recalculate total token count from scratch (used after major restructuring)."""
        self._total_tokens = 0
        for msg in self.history:
            if msg.token_count is not None:
                self._total_tokens += msg.token_count
            else:
                # Recalculate token count if not cached
                token_count = self._estimate_tokens(msg.content)
                msg.token_count = token_count
                self._total_tokens += token_count

    def clear_conversation(self, keep_system: bool = True) -> None:
        """
        Clear conversation history.

        Args:
            keep_system: Whether to preserve system prompt
        """
        if keep_system:
            system_messages = [
                msg for msg in self.history if msg.role == MessageRole.SYSTEM
            ]
            self.history = system_messages
            # Recalculate total tokens for remaining system messages
            self._recalculate_total_tokens()
        else:
            self.history = []
            self._total_tokens = 0

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt."""
        # Set the system prompt attribute
        self.system_prompt = prompt

        # Remove existing system messages and update token count
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].role == MessageRole.SYSTEM:
                self._remove_message_at_index(i)

        # Add new system prompt at beginning
        token_count = self._estimate_tokens(prompt)
        system_message = ConversationMessage(
            role=MessageRole.SYSTEM, content=prompt, token_count=token_count
        )
        self.history.insert(0, system_message)
        self._total_tokens += token_count

    def get_conversation_summary(
        self, tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Get conversation statistics and summary.

        Args:
            tools: Optional tools for request token calculation

        Returns:
            Dictionary with conversation metrics
        """
        # Filter out messages with None timestamps for min/max calculations
        messages_with_timestamps = [
            msg for msg in self.history if msg.timestamp is not None
        ]

        # Calculate thinking time statistics
        assistant_messages_with_time = [
            msg
            for msg in self.history
            if msg.role == MessageRole.ASSISTANT and msg.thinking_time is not None
        ]
        thinking_times = [msg.thinking_time for msg in assistant_messages_with_time]

        thinking_stats = {}
        if thinking_times:
            # Filter out None values for calculations
            valid_thinking_times = [t for t in thinking_times if t is not None]
            if valid_thinking_times:
                thinking_stats = {
                    "total_thinking_time": sum(valid_thinking_times),
                    "average_thinking_time": sum(valid_thinking_times)
                    / len(valid_thinking_times),
                    "min_thinking_time": min(valid_thinking_times),
                    "max_thinking_time": max(valid_thinking_times),
                    "thinking_time_count": len(valid_thinking_times),
                }

        return {
            "total_messages": len(self.history),
            "estimated_tokens": self._total_tokens,
            "request_tokens": self.get_request_tokens(tools)
            if tools
            else self._total_tokens,
            "user_messages": len(
                [msg for msg in self.history if msg.role == MessageRole.USER]
            ),
            "assistant_messages": len(
                [msg for msg in self.history if msg.role == MessageRole.ASSISTANT]
            ),
            "tool_messages": len(
                [msg for msg in self.history if msg.role == MessageRole.TOOL]
            ),
            "oldest_message": (
                min(
                    [
                        msg.timestamp
                        for msg in messages_with_timestamps
                        if msg.timestamp is not None
                    ]
                )
                if messages_with_timestamps
                else None
            ),
            "newest_message": (
                max(
                    [
                        msg.timestamp
                        for msg in messages_with_timestamps
                        if msg.timestamp is not None
                    ]
                )
                if messages_with_timestamps
                else None
            ),
            **thinking_stats,
        }

    def add_tool_call_sequence(
        self, tool_calls: List[Dict], tool_results: List[Dict]
    ) -> None:
        """
        Add a complete tool call sequence to conversation history.

        Args:
            tool_calls: List of tool call requests from LLM
            tool_results: List of tool execution results
        """
        # Add tool calls as assistant message with tool_calls field
        if tool_calls:
            # Create a single assistant message with all tool calls
            self.add_message(
                role=MessageRole.ASSISTANT,
                content="",  # Tool calls don't have content
                tool_call_id=None,  # This will be handled specially in get_messages
            )
            # Store tool calls for this assistant message
            self.history[-1].tool_calls = tool_calls

        # Add tool results
        for result in tool_results:
            self.add_message(
                role=MessageRole.TOOL,
                content=result.get("output", ""),
                tool_call_id=result.get("tool_call_id"),
            )

    def get_recent_context(self, num_messages: int = 5) -> List[ConversationMessage]:
        """
        Get recent conversation context for analysis.

        Args:
            num_messages: Number of recent messages to return

        Returns:
            List of recent conversation messages
        """
        return self.history[-num_messages:] if self.history else []
