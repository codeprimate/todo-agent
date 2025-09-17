"""
Token counting utilities for accurate LLM token estimation.
"""

import json
from typing import Any, Dict, List, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore


class TokenCounter:
    """Accurate token counting using tiktoken library."""

    def __init__(self, model: str = "gpt-4"):
        """
        Initialize token counter for a specific model.

        Args:
            model: Model name to use for tokenization (default: gpt-4)
        """
        self.model = model
        self._encoder: Optional[Any] = None
        self._initialize_encoder()

    def _initialize_encoder(self) -> None:
        """Initialize the tiktoken encoder for the specified model."""
        if tiktoken is None:
            raise ImportError(
                "tiktoken library is required for accurate token counting. "
                "Install it with: pip install tiktoken"
            )

        self._encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using accurate tokenization.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self._encoder is None:
            raise RuntimeError("Encoder not initialized")
        return len(self._encoder.encode(text))

    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """
        Count tokens in a single message (including role, content, and tool calls).

        Args:
            message: Message dictionary with role, content, etc.

        Returns:
            Number of tokens
        """
        tokens = 0

        # Count role tokens (typically 1-2 tokens)
        role = message.get("role", "")
        if role:
            tokens += self.count_tokens(str(role))

        # Count content tokens
        content = message.get("content", "")
        if content:
            tokens += self.count_tokens(str(content))

        # Count tool calls tokens
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            for tool_call in tool_calls:
                tokens += self.count_tool_call_tokens(tool_call)

        # Count tool call ID if present
        tool_call_id = message.get("tool_call_id", "")
        if tool_call_id:
            tokens += self.count_tokens(str(tool_call_id))

        return tokens

    def count_tool_call_tokens(self, tool_call: Dict[str, Any]) -> int:
        """
        Count tokens in a tool call.

        Args:
            tool_call: Tool call dictionary

        Returns:
            Number of tokens
        """
        tokens = 0

        # Count tool call ID
        tool_call_id = tool_call.get("id", "")
        if tool_call_id:
            tokens += self.count_tokens(str(tool_call_id))

        # Count function call
        function = tool_call.get("function", {})
        if function:
            # Count function name
            function_name = function.get("name", "")
            if function_name:
                tokens += self.count_tokens(str(function_name))

            # Count function arguments
            arguments = function.get("arguments", "")
            if arguments:
                # Arguments could be a string or dict, handle both
                if isinstance(arguments, str):
                    tokens += self.count_tokens(arguments)
                else:
                    tokens += self.count_tokens(str(arguments))

        return tokens

    def count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Total number of tokens
        """
        total_tokens = 0

        for message in messages:
            total_tokens += self.count_message_tokens(message)

        return total_tokens

    def count_tools_tokens(self, tools: List[Dict[str, Any]]) -> int:
        """
        Count tokens in tool definitions.

        Args:
            tools: List of tool definition dictionaries

        Returns:
            Number of tokens
        """
        if not tools:
            return 0

        try:
            # Convert tools to JSON string and count tokens
            tools_json = json.dumps(tools, separators=(",", ":"))
            return self.count_tokens(tools_json)
        except (TypeError, ValueError) as e:
            # If JSON serialization fails, fall back to a rough estimate
            # This could happen if tools contain non-serializable objects
            print(f"Warning: Failed to serialize tools for token counting: {e}")
            # Return a rough estimate based on string representation
            tools_str = str(tools)
            return self.count_tokens(tools_str)

    def count_request_tokens(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Count total tokens in a complete request (messages + tools).

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Total number of tokens
        """
        total_tokens = self.count_messages_tokens(messages)

        if tools:
            total_tokens += self.count_tools_tokens(tools)

        return total_tokens


def get_token_counter(model: str = "gpt-4") -> TokenCounter:
    """
    Get a token counter instance for the specified model.

    Args:
        model: Model name to use for tokenization

    Returns:
        TokenCounter instance
    """
    return TokenCounter(model)
