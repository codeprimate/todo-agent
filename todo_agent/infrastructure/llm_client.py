"""
Abstract LLM client interface for todo.sh agent.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMClient(ABC):
    """Abstract interface for LLM clients."""

    @abstractmethod
    def chat_with_tools(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send chat message with function calling enabled.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions

        Returns:
            API response dictionary
        """
        pass

    @abstractmethod
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from API response.

        Args:
            response: API response dictionary

        Returns:
            List of tool call dictionaries
        """
        pass

    @abstractmethod
    def extract_content(self, response: Dict[str, Any]) -> str:
        """
        Extract content from API response.

        Args:
            response: API response dictionary

        Returns:
            Extracted content string
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name being used by this client.

        Returns:
            Model name string
        """
        pass

    def classify_error(self, error: Exception, provider: str) -> str:
        """
        Classify provider errors using simple string matching.
        
        Args:
            error: The exception that occurred
            provider: The provider name (e.g., 'openrouter', 'ollama')
            
        Returns:
            Error type string for message lookup
        """
        error_str = str(error).lower()
        
        if "malformed" in error_str or "invalid" in error_str or "parse" in error_str:
            return "malformed_response"
        elif "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            return "rate_limit"
        elif "unauthorized" in error_str or "401" in error_str or "authentication" in error_str:
            return "auth_error"
        elif "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif "connection" in error_str or "network" in error_str or "dns" in error_str:
            return "timeout"  # Treat connection issues as timeouts for user messaging
        elif "refused" in error_str or "unreachable" in error_str:
            return "timeout"  # Connection refused is similar to timeout for users
        else:
            return "general_error"
