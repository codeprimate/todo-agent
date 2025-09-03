"""
LLM client for OpenRouter API communication.
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


class OpenRouterClient(LLMClient):
    """LLM API communication and response handling."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.openrouter_api_key
        self.model = config.model
        self.base_url = "https://openrouter.ai/api/v1"
        self.logger = Logger("openrouter_client")
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
        """Log response details including token count and latency."""
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Extract token usage from response if available
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", "unknown")
        completion_tokens = usage.get("completion_tokens", "unknown")
        total_tokens = usage.get("total_tokens", "unknown")

        self.logger.info(f"Response received - Latency: {latency_ms:.2f}ms")
        self.logger.info(
            f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}"
        )

        # Extract and log choice details
        choices = response.get("choices", [])
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
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }

        start_time = time.time()
        self._log_request_details(payload, start_time)

        try:
            response = requests.post(  # nosec B113
                f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30
            )
        except requests.exceptions.Timeout:
            self.logger.error("OpenRouter API request timed out")
            return {
                "error": True,
                "error_type": "timeout",
                "provider": "openrouter",
                "status_code": 0,
                "raw_error": "Request timed out"
            }
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"OpenRouter API connection error: {e}")
            return {
                "error": True,
                "error_type": "timeout",
                "provider": "openrouter",
                "status_code": 0,
                "raw_error": f"Connection error: {e}"
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenRouter API request error: {e}")
            return {
                "error": True,
                "error_type": "general_error",
                "provider": "openrouter",
                "status_code": 0,
                "raw_error": f"Request error: {e}"
            }

        if response.status_code != 200:
            self.logger.error(f"OpenRouter API error: {response.text}")
            error_type = self.classify_error(Exception(response.text), "openrouter")
            return {
                "error": True,
                "error_type": error_type,
                "provider": "openrouter",
                "status_code": response.status_code,
                "raw_error": response.text
            }

        try:
            response_data: Dict[str, Any] = response.json()
        except Exception as e:
            self.logger.error(f"Failed to parse OpenRouter response JSON: {e}")
            return {
                "error": True,
                "error_type": "malformed_response",
                "provider": "openrouter",
                "status_code": response.status_code,
                "raw_error": f"JSON parsing failed: {e}"
            }
            
        self._log_response_details(response_data, start_time)

        return response_data

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
            self.logger.warning(f"Cannot extract tool calls from error response: {response.get('error_type')}")
            return []
            
        tool_calls = []
        if response.get("choices"):
            choice = response["choices"][0]
            if "message" in choice and "tool_calls" in choice["message"]:
                raw_tool_calls = choice["message"]["tool_calls"]
                
                # Validate each tool call
                for i, tool_call in enumerate(raw_tool_calls):
                    try:
                        # Check if tool call has required structure
                        if not isinstance(tool_call, dict):
                            self.logger.warning(f"Tool call {i+1} is not a dictionary: {tool_call}")
                            continue
                            
                        function = tool_call.get("function", {})
                        if not isinstance(function, dict):
                            self.logger.warning(f"Tool call {i+1} function is not a dictionary: {function}")
                            continue
                            
                        tool_name = function.get("name")
                        if not tool_name:
                            self.logger.warning(f"Tool call {i+1} missing function name: {tool_call}")
                            continue
                            
                        # Validate arguments if present
                        arguments = function.get("arguments", "{}")
                        if arguments and not isinstance(arguments, str):
                            self.logger.warning(f"Tool call {i+1} arguments not a string: {arguments}")
                            continue
                            
                        # If we get here, the tool call is valid
                        tool_calls.append(tool_call)
                        
                    except Exception as e:
                        self.logger.warning(f"Error validating tool call {i+1}: {e}")
                        continue
                
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
            self.logger.warning(f"Cannot extract content from error response: {response.get('error_type')}")
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
