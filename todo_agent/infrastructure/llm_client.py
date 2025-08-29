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
