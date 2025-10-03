"""
Abstract LLM client interface for todo.sh agent.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import requests

from todo_agent.infrastructure.logger import Logger
from todo_agent.infrastructure.token_counter import get_token_counter


class LLMClient(ABC):
    """Abstract interface for LLM clients with common functionality."""

    def __init__(self, config: Any, model: str, logger_name: str = "llm_client"):
        """
        Initialize common LLM client functionality.

        Args:
            config: Configuration object
            model: Model name for token counting
            logger_name: Logger name for this client
        """
        self.config = config
        self.model = model
        self.logger = Logger(logger_name)
        self.token_counter = get_token_counter(model)

    @abstractmethod
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

    @abstractmethod
    def _get_request_headers(self) -> Dict[str, str]:
        """
        Get request headers for the API call.

        Returns:
            Dictionary of headers
        """
        pass

    @abstractmethod
    def _get_request_payload(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get request payload for the API call.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions

        Returns:
            Request payload dictionary
        """
        pass

    @abstractmethod
    def _get_api_endpoint(self) -> str:
        """
        Get the API endpoint for requests.

        Returns:
            API endpoint URL
        """
        pass

    @abstractmethod
    def _process_response(
        self, response_data: Dict[str, Any], start_time: float
    ) -> None:
        """
        Process and log response details.

        Args:
            response_data: Response data from API
            start_time: Request start time for latency calculation
        """
        pass

    def _log_request_details(self, payload: Dict[str, Any], start_time: float) -> None:
        """Log request details including accurate token count."""
        messages = payload.get("messages", [])
        tools = payload.get("tools", [])

        total_tokens = self.token_counter.count_request_tokens(messages, tools)
        self.logger.info(f"Request sent - Token count: {total_tokens}")

    def _make_http_request(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        cancelled: bool = False,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the LLM API with common error handling and cancellation support.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions
            cancelled: Cancellation flag for user interruption

        Returns:
            API response dictionary
        """
        # Check for cancellation before making request
        if cancelled:
            self.logger.info(
                f"{self.get_provider_name()} request cancelled before HTTP call"
            )
            return self._create_cancelled_response()

        headers = self._get_request_headers()
        payload = self._get_request_payload(messages, tools)
        endpoint = self._get_api_endpoint()

        start_time = time.time()
        self._log_request_details(payload, start_time)

        # Use reasonable timeout values for LLM requests
        overall_timeout = 120  # 2 minutes overall timeout
        individual_timeout = 30  # 30 seconds per individual request

        while time.time() - start_time < overall_timeout:
            # Check cancellation flag during polling
            if cancelled:
                self.logger.info(  # type: ignore
                    f"{self.get_provider_name()} request cancelled during HTTP polling"
                )
                return self._create_cancelled_response()

            try:
                response = requests.post(  # nosec B113
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=individual_timeout,
                )

                # If we get a response, process it
                if response.status_code == 200:
                    try:
                        response_data: Dict[str, Any] = response.json()
                        self._process_response(response_data, start_time)
                        return response_data
                    except Exception as e:
                        self.logger.error(
                            f"Failed to parse {self.get_provider_name()} response JSON: {e}"
                        )
                        return self._create_error_response(
                            "malformed_response",
                            f"JSON parsing failed: {e}",
                            response.status_code,
                        )
                else:
                    # Non-200 status code - return error
                    self.logger.error(
                        f"{self.get_provider_name()} API error: {response.text}"
                    )
                    error_type = self.classify_error(
                        Exception(response.text), self.get_provider_name()
                    )
                    return self._create_error_response(
                        error_type, response.text, response.status_code
                    )

            except requests.exceptions.Timeout:
                # Individual request timeout - continue polling
                continue
            except requests.exceptions.ConnectionError as e:
                self.logger.error(
                    f"{self.get_provider_name()} API connection error: {e}"
                )
                return self._create_error_response("timeout", f"Connection error: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"{self.get_provider_name()} API request error: {e}")
                return self._create_error_response(
                    "general_error", f"Request error: {e}"
                )

        # If we get here, we've hit the overall timeout
        self.logger.error(
            f"{self.get_provider_name()} API request timed out after {overall_timeout}s"
        )
        return self._create_error_response("timeout", "Request timed out")

    def _create_cancelled_response(self) -> Dict[str, Any]:
        """
        Create standardized cancelled response.

        Returns:
            Standardized cancelled response dictionary
        """
        return {
            "error": True,
            "error_type": "cancelled",
            "provider": self.get_provider_name(),
            "status_code": 0,
            "raw_error": "Request cancelled by user",
        }

    def _create_error_response(
        self, error_type: str, raw_error: str, status_code: int = 0
    ) -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            error_type: Type of error
            raw_error: Raw error message
            status_code: HTTP status code if available

        Returns:
            Standardized error response dictionary
        """
        return {
            "error": True,
            "error_type": error_type,
            "provider": self.get_provider_name(),
            "status_code": status_code,
            "raw_error": raw_error,
        }

    def _validate_tool_call(self, tool_call: Any, index: int) -> bool:
        """
        Validate a tool call structure.

        Args:
            tool_call: Tool call to validate
            index: Index of the tool call for logging

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(tool_call, dict):
                self.logger.warning(
                    f"Tool call {index + 1} is not a dictionary: {tool_call}"
                )
                return False

            function = tool_call.get("function", {})
            if not isinstance(function, dict):
                self.logger.warning(
                    f"Tool call {index + 1} function is not a dictionary: {function}"
                )
                return False

            tool_name = function.get("name")
            if not tool_name:
                self.logger.warning(
                    f"Tool call {index + 1} missing function name: {tool_call}"
                )
                return False

            arguments = function.get("arguments", "{}")
            # Accept both string (JSON) and dict formats for arguments
            if arguments and not isinstance(arguments, (str, dict)):
                self.logger.warning(
                    f"Tool call {index + 1} arguments not a string or dict: {arguments}"
                )
                return False

            return True
        except Exception as e:
            self.logger.warning(f"Error validating tool call {index + 1}: {e}")
            return False

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
        elif (
            "rate limit" in error_str
            or "429" in error_str
            or "too many requests" in error_str
        ):
            return "rate_limit"
        elif (
            "unauthorized" in error_str
            or "401" in error_str
            or "authentication" in error_str
        ):
            return "auth_error"
        elif "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif "connection" in error_str or "network" in error_str or "dns" in error_str:
            return "timeout"  # Treat connection issues as timeouts for user messaging
        elif "refused" in error_str or "unreachable" in error_str:
            return "timeout"  # Connection refused is similar to timeout for users
        else:
            return "general_error"

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the provider name for this client.

        Returns:
            Provider name string
        """
        pass

    def get_request_timeout(self) -> int:
        """
        Get the request timeout in seconds for this provider.

        Returns:
            Timeout value in seconds (default: 30)
        """
        return 30
