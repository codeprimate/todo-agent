"""
LLM client for Ollama API communication.
"""

import json
import time
from typing import Any, Dict, List

import requests

try:
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.llm_client import LLMClient
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.token_counter import get_token_counter
except ImportError:
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.llm_client import LLMClient  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from infrastructure.token_counter import get_token_counter  # type: ignore[no-redef]


class OllamaClient(LLMClient):
    """Ollama API client implementation."""

    def __init__(self, config: Config):
        """
        Initialize Ollama client.

        Args:
            config: Configuration object
        """
        self.config = config
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.logger = Logger("ollama_client")
        self.token_counter = get_token_counter(self.model)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using accurate tokenization.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return self.token_counter.count_tokens(text)

    def _log_request_details(self, payload: Dict[str, Any], start_time: float) -> None:
        """Log request details including accurate token count."""
        # Count tokens for messages
        messages = payload.get("messages", [])
        tools = payload.get("tools", [])

        total_tokens = self.token_counter.count_request_tokens(messages, tools)

        self.logger.info(f"Request sent - Token count: {total_tokens}")
        # self.logger.debug(f"Raw request payload: {json.dumps(payload, indent=2)}")

    def _log_response_details(
        self, response: Dict[str, Any], start_time: float
    ) -> None:
        """Log response details including latency."""
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        self.logger.info(f"Response received - Latency: {latency_ms:.2f}ms")

        # Log tool call details if present
        if "message" in response and "tool_calls" in response["message"]:
            tool_calls = response["message"]["tool_calls"]
            self.logger.info(f"Response contains {len(tool_calls)} tool calls")

            # Log thinking content (response body) if present
            content = response["message"].get("content", "")
            if content and content.strip():
                self.logger.info(f"LLM thinking before tool calls: {content}")

            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                self.logger.info(f"  Tool call {i + 1}: {tool_name}")
        elif "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
            self.logger.debug(
                f"Response contains content: {content[:100]}{'...' if len(content) > 100 else ''}"
            )

        self.logger.debug(f"Raw response: {json.dumps(response, indent=2)}")

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
        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        start_time = time.time()
        self._log_request_details(payload, start_time)

        response = requests.post(  # nosec B113
            f"{self.base_url}/api/chat", headers=headers, json=payload
        )

        if response.status_code != 200:
            self.logger.error(f"Ollama API error: {response.text}")
            raise Exception(f"Ollama API error: {response.text}")

        response_data: Dict[str, Any] = response.json()
        self._log_response_details(response_data, start_time)

        return response_data

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from API response."""
        tool_calls = []

        # Ollama response format is different from OpenRouter
        if "message" in response and "tool_calls" in response["message"]:
            tool_calls = response["message"]["tool_calls"]
            self.logger.debug(f"Extracted {len(tool_calls)} tool calls from response")
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                tool_call_id = tool_call.get("id", "unknown")
                self.logger.debug(
                    f"Tool call {i + 1}: {tool_name} (ID: {tool_call_id})"
                )
        else:
            self.logger.debug("No tool calls found in response")

        return tool_calls

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from API response."""
        if "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
            return content if isinstance(content, str) else str(content)
        return ""

    def get_model_name(self) -> str:
        """
        Get the model name being used by this client.

        Returns:
            Model name string
        """
        return self.model
