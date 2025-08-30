"""
LLM inference engine for todo.sh agent.
"""

import os
import time
from typing import Any, Dict, Optional

try:
    from todo_agent.core.conversation_manager import ConversationManager, MessageRole
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.llm_client_factory import LLMClientFactory
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.interface.tools import ToolCallHandler
except ImportError:
    from core.conversation_manager import (  # type: ignore[no-redef]
        ConversationManager,
        MessageRole,
    )
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.llm_client_factory import (  # type: ignore[no-redef]
        LLMClientFactory,
    )
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from interface.tools import ToolCallHandler  # type: ignore[no-redef]


class Inference:
    """LLM inference engine that orchestrates tool calling and conversation management."""

    def __init__(
        self,
        config: Config,
        tool_handler: ToolCallHandler,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the inference engine.

        Args:
            config: Configuration object
            tool_handler: Tool call handler for executing tools
            logger: Optional logger instance
        """
        self.config = config
        self.tool_handler = tool_handler
        self.logger = logger or Logger("inference")

        # Initialize LLM client using factory
        self.llm_client = LLMClientFactory.create_client(config, self.logger)

        # Initialize conversation manager
        self.conversation_manager = ConversationManager()

        # Set up system prompt
        self._setup_system_prompt()

        self.logger.info(
            f"Inference engine initialized with {config.provider} provider using model: {self.llm_client.get_model_name()}"
        )

    def _setup_system_prompt(self) -> None:
        """Set up the system prompt for the LLM."""
        system_prompt = self._load_system_prompt()
        self.conversation_manager.set_system_prompt(system_prompt)
        self.logger.debug("System prompt loaded and set")

    def _load_system_prompt(self) -> str:
        """Load and format the system prompt from file."""
        # Generate tools section programmatically
        tools_section = self._generate_tools_section()

        # Get current datetime for interpolation
        from datetime import datetime

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get calendar output
        from .calendar_utils import get_calendar_output
        
        try:
            calendar_output = get_calendar_output()
        except Exception as e:
            self.logger.warning(f"Failed to get calendar output: {e!s}")
            calendar_output = "Calendar unavailable"

        # Load system prompt from file
        prompt_file_path = os.path.join(
            os.path.dirname(__file__), "prompts", "system_prompt.txt"
        )

        try:
            with open(prompt_file_path, encoding="utf-8") as f:
                system_prompt_template = f.read()

            # Format the template with the tools section, current datetime, and calendar
            return system_prompt_template.format(
                tools_section=tools_section, 
                current_datetime=current_datetime,
                calendar_output=calendar_output
            )

        except FileNotFoundError:
            self.logger.error(f"System prompt file not found: {prompt_file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e!s}")
            raise

    def _generate_tools_section(self) -> str:
        """Generate the AVAILABLE TOOLS section with strategic categorization."""
        tool_categories = {
            "Discovery Tools": [
                "list_projects",
                "list_contexts",
                "list_tasks",
                "list_completed_tasks",
            ],
            "Modification Tools": [
                "add_task",
                "complete_task",
                "replace_task",
                "append_to_task",
                "prepend_to_task",
            ],
            "Management Tools": [
                "delete_task",
                "set_priority",
                "remove_priority",
                "move_task",
            ],
            "Maintenance Tools": ["archive_tasks", "deduplicate_tasks", "get_overview"],
        }

        tools_section = []
        for category, tool_names in tool_categories.items():
            tools_section.append(f"\n**{category}:**")
            for tool_name in tool_names:
                tool_info = next(
                    (
                        t
                        for t in self.tool_handler.tools
                        if t["function"]["name"] == tool_name
                    ),
                    None,
                )
                if tool_info:
                    # Get first sentence of description for concise overview
                    first_sentence = (
                        tool_info["function"]["description"].split(".")[0] + "."
                    )
                    tools_section.append(f"- {tool_name}(): {first_sentence}")

        return "\n".join(tools_section)

    def process_request(self, user_input: str) -> tuple[str, float]:
        """
        Process a user request through the LLM with tool orchestration.

        Args:
            user_input: Natural language user request

        Returns:
            Tuple of (formatted response for user, thinking time in seconds)
        """
        # Start timing the request
        start_time = time.time()

        try:
            self.logger.debug(
                f"Starting request processing for: {user_input[:30]}{'...' if len(user_input) > 30 else ''}"
            )

            # Add user message to conversation
            self.conversation_manager.add_message(MessageRole.USER, user_input)
            self.logger.debug("Added user message to conversation")

            # Get conversation history for LLM
            messages = self.conversation_manager.get_messages()
            self.logger.debug(
                f"Retrieved {len(messages)} messages from conversation history"
            )

            # Send to LLM with function calling enabled
            self.logger.debug("Sending request to LLM with tools")
            response = self.llm_client.chat_with_tools(
                messages=messages, tools=self.tool_handler.tools
            )

            # Handle multiple tool calls in sequence
            tool_call_count = 0
            while True:
                tool_calls = self.llm_client.extract_tool_calls(response)

                if not tool_calls:
                    break

                tool_call_count += 1
                self.logger.debug(
                    f"Executing tool call sequence #{tool_call_count} with {len(tool_calls)} tools"
                )

                # Execute all tool calls and collect results
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    tool_call_id = tool_call.get("id", "unknown")
                    self.logger.debug(
                        f"=== TOOL EXECUTION #{i + 1}/{len(tool_calls)} ==="
                    )
                    self.logger.debug(f"Tool: {tool_name}")
                    self.logger.debug(f"Tool Call ID: {tool_call_id}")
                    self.logger.debug(f"Raw tool call: {tool_call}")

                    result = self.tool_handler.execute_tool(tool_call)

                    # Log tool execution result (success or error)
                    if result.get("error", False):
                        self.logger.warning(
                            f"Tool {tool_name} failed: {result.get('user_message', result.get('output', 'Unknown error'))}"
                        )
                    else:
                        self.logger.debug(f"Tool {tool_name} succeeded")

                    self.logger.debug(f"Tool result: {result}")
                    tool_results.append(result)

                # Add tool call sequence to conversation
                self.conversation_manager.add_tool_call_sequence(
                    tool_calls, tool_results
                )
                self.logger.debug("Added tool call sequence to conversation")

                # Continue conversation with tool results
                messages = self.conversation_manager.get_messages()
                response = self.llm_client.chat_with_tools(
                    messages=messages, tools=self.tool_handler.tools
                )

            # Calculate and log total thinking time
            end_time = time.time()
            thinking_time = end_time - start_time

            # Add final assistant response to conversation with thinking time
            final_content = self.llm_client.extract_content(response)
            self.conversation_manager.add_message(
                MessageRole.ASSISTANT, final_content, thinking_time=thinking_time
            )

            self.logger.info(
                f"Request completed successfully with {tool_call_count} tool call sequences in {thinking_time:.2f}s"
            )

            # Return final user-facing response and thinking time
            return final_content, thinking_time

        except Exception as e:
            # Calculate and log thinking time even for failed requests
            end_time = time.time()
            thinking_time = end_time - start_time
            self.logger.error(
                f"Error processing request after {thinking_time:.2f}s: {e!s}"
            )
            return f"Error: {e!s}", thinking_time

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get conversation statistics and summary.

        Returns:
            Dictionary with conversation metrics
        """
        return self.conversation_manager.get_conversation_summary()

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_manager.clear_conversation()
        self.logger.info("Conversation history cleared")

    def get_conversation_manager(self) -> ConversationManager:
        """
        Get the conversation manager instance.

        Returns:
            Conversation manager instance
        """
        return self.conversation_manager
