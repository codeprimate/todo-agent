"""
LLM client for OpenRouter API communication.
"""

import json
import time
from typing import Any, Dict, List

import requests

try:
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.token_counter import get_token_counter
    from todo_agent.infrastructure.llm_client import LLMClient
except ImportError:
    from infrastructure.config import Config
    from infrastructure.logger import Logger
    from infrastructure.token_counter import get_token_counter
    from infrastructure.llm_client import LLMClient


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

    def _log_request_details(self, payload: Dict[str, Any], start_time: float):
        """Log request details including accurate token count."""
        # Count tokens for messages
        messages = payload.get("messages", [])
        tools = payload.get("tools", [])
        
        total_tokens = self.token_counter.count_request_tokens(messages, tools)
        
        self.logger.info(f"Request sent - Token count: {total_tokens}")
        # self.logger.debug(f"Raw request payload: {json.dumps(payload, indent=2)}")

    def _log_response_details(self, response: Dict[str, Any], start_time: float):
        """Log response details including token count and latency."""
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Extract token usage from response if available
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", "unknown")
        completion_tokens = usage.get("completion_tokens", "unknown")
        total_tokens = usage.get("total_tokens", "unknown")
        
        self.logger.info(f"Response received - Latency: {latency_ms:.2f}ms")
        self.logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        # Log tool call details if present
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice and "tool_calls" in choice["message"]:
                tool_calls = choice["message"]["tool_calls"]
                self.logger.info(f"Response contains {len(tool_calls)} tool calls")
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    self.logger.info(f"  Tool call {i+1}: {tool_name}")
            elif "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                self.logger.debug(f"Response contains content: {content[:100]}{'...' if len(content) > 100 else ''}")
        
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

        response = requests.post(
            f"{self.base_url}/chat/completions", headers=headers, json=payload
        )

        if response.status_code != 200:
            self.logger.error(f"OpenRouter API error: {response.text}")
            raise Exception(f"OpenRouter API error: {response.text}")

        response_data = response.json()
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
        tool_calls = []
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice and "tool_calls" in choice["message"]:
                tool_calls = choice["message"]["tool_calls"]
                self.logger.debug(f"Extracted {len(tool_calls)} tool calls from response")
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    tool_call_id = tool_call.get("id", "unknown")
                    self.logger.debug(f"Tool call {i+1}: {tool_name} (ID: {tool_call_id})")
            else:
                self.logger.debug("No tool calls found in response")
        else:
            self.logger.debug("No choices found in response")
        return tool_calls

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from API response."""
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
        return ""

    def get_model_name(self) -> str:
        """
        Get the model name being used by this client.

        Returns:
            Model name string
        """
        return self.model
