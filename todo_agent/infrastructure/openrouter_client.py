"""
LLM client for OpenRouter API communication.
"""

from typing import Any, Dict, List

from todo_agent.infrastructure.llm_client import LLMClient


class OpenRouterClient(LLMClient):
    """LLM API communication and response handling."""

    def __init__(self, config: Any) -> None:
        """
        Initialize OpenRouter client.

        Args:
            config: Configuration object
        """
        super().__init__(config, config.model, "openrouter_client")
        self.api_key = config.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"

    def _get_request_headers(self) -> Dict[str, str]:
        """Get request headers for OpenRouter API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_request_payload(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get request payload for OpenRouter API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }

        # Add reasoning_effort parameter if configured
        if hasattr(self.config, "reasoning_effort") and self.config.reasoning_effort:
            payload["reasoning_effort"] = self.config.reasoning_effort

        return payload

    def _get_api_endpoint(self) -> str:
        """Get OpenRouter API endpoint."""
        return f"{self.base_url}/chat/completions"

    def _process_response(
        self, response_data: Dict[str, Any], start_time: float
    ) -> None:
        """Process and log OpenRouter response details."""
        import time

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Extract token usage from response if available
        usage = response_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", "unknown")
        completion_tokens = usage.get("completion_tokens", "unknown")
        total_tokens = usage.get("total_tokens", "unknown")

        self.logger.info(f"Response received - Latency: {latency_ms:.2f}ms")
        self.logger.info(
            f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}"
        )

        # Extract and log choice details
        choices = response_data.get("choices", [])
        if not choices:
            return

        choice = choices[0]
        message = choice.get("message", {})

        # Always log reasoning and content if present
        reasoning = message.get("reasoning", "")
        if reasoning:
            self.logger.info(f"LLM reasoning: {reasoning}")

        content = message.get("content", "")
        if content:
            self.logger.info(f"LLM content: {content}")

        # Handle tool calls
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            self.logger.info(f"Response contains {len(tool_calls)} tool calls")

            # Log each tool call
            for i, tool_call in enumerate(tool_calls, 1):
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                self.logger.info(f"  Tool call {i}: {tool_name}")

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

    def continue_with_tool_result(self, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continue conversation with tool execution result.

        Args:
            tool_result: Tool execution result

        Returns:
            API response dictionary
        """
        # TODO: Implement continuation logic
        return {}

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from API response."""
        # Check for provider errors first
        if response.get("error", False):
            self.logger.warning(
                f"Cannot extract tool calls from error response: {response.get('error_type')}"
            )
            return []

        tool_calls = []
        if response.get("choices"):
            choice = response["choices"][0]
            if "message" in choice and "tool_calls" in choice["message"]:
                raw_tool_calls = choice["message"]["tool_calls"]

                # Validate each tool call using common validation
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
        else:
            self.logger.debug("No choices found in response")
        return tool_calls

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from API response."""
        # Check for provider errors first
        if response.get("error", False):
            self.logger.warning(
                f"Cannot extract content from error response: {response.get('error_type')}"
            )
            return ""

        if response.get("choices"):
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
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
        return "openrouter"

    def get_request_timeout(self) -> int:
        """
        Get the request timeout in seconds for OpenRouter.

        Cloud APIs typically respond quickly, so we use a 30-second timeout.

        Returns:
            Timeout value in seconds (30)
        """
        return 30
