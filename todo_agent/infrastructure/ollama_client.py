"""
LLM client for Ollama API communication.
"""

from typing import Any, Dict, List

from todo_agent.infrastructure.llm_client import LLMClient


class OllamaClient(LLMClient):
    """Ollama API client implementation."""

    def __init__(self, config: Any) -> None:
        """
        Initialize Ollama client.

        Args:
            config: Configuration object
        """
        super().__init__(config, config.ollama_model, "ollama_client")
        self.base_url = config.ollama_base_url

    def _get_request_headers(self) -> Dict[str, str]:
        """Get request headers for Ollama API."""
        return {
            "Content-Type": "application/json",
        }

    def _get_request_payload(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get request payload for Ollama API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        # Add reasoning_effort parameter if configured
        # Note: Not all Ollama models support this parameter
        if hasattr(self.config, "reasoning_effort") and self.config.reasoning_effort:
            payload["reasoning_effort"] = self.config.reasoning_effort

        return payload

    def _get_api_endpoint(self) -> str:
        """Get Ollama API endpoint."""
        return f"{self.base_url}/api/chat"

    def _process_response(
        self, response_data: Dict[str, Any], start_time: float
    ) -> None:
        """Process and log Ollama response details."""
        import time

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        self.logger.info(f"Response received - Latency: {latency_ms:.2f}ms")

        # Log tool call details if present
        if "message" in response_data and "tool_calls" in response_data["message"]:
            tool_calls = response_data["message"]["tool_calls"]
            self.logger.info(f"Response contains {len(tool_calls)} tool calls")

            # Log thinking content (response body) if present
            content = response_data["message"].get("content", "")
            if content and content.strip():
                self.logger.info(f"LLM thinking before tool calls: {content}")

            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                self.logger.info(f"  Tool call {i + 1}: {tool_name}")
        elif "message" in response_data and "content" in response_data["message"]:
            content = response_data["message"]["content"]
            self.logger.debug(
                f"Response contains content: {content[:100]}{'...' if len(content) > 100 else ''}"
            )

        self.logger.debug(f"Raw response: {response_data}")

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        cancelled: bool = False,
    ) -> Dict[str, Any]:
        """
        Send chat message with function calling enabled.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions
            cancelled: Cancellation flag for user interruption

        Returns:
            API response dictionary
        """
        return self._make_http_request(messages, tools, cancelled)

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from API response."""
        # Check for provider errors first
        if response.get("error", False):
            self.logger.warning(
                f"Cannot extract tool calls from error response: {response.get('error_type')}"
            )
            return []

        tool_calls = []

        # Ollama response format is different from OpenRouter
        if "message" in response and "tool_calls" in response["message"]:
            raw_tool_calls = response["message"]["tool_calls"]

            # Process each tool call - validation now accepts both string and dict formats
            for i, tool_call in enumerate(raw_tool_calls):
                if self._validate_tool_call(tool_call, i):
                    tool_calls.append(tool_call)

            self.logger.debug(
                f"Extracted {len(tool_calls)} valid tool calls from {len(raw_tool_calls)} total"
            )
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
        # Check for provider errors first
        if response.get("error", False):
            self.logger.warning(
                f"Cannot extract content from error response: {response.get('error_type')}"
            )
            return ""

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

    def get_provider_name(self) -> str:
        """
        Get the provider name for this client.

        Returns:
            Provider name string
        """
        return "ollama"

    def get_request_timeout(self) -> int:
        """
        Get the request timeout in seconds for Ollama.

        Ollama can be slower than cloud providers, so we use a 2-minute timeout.

        Returns:
            Timeout value in seconds (120)
        """
        return 120
