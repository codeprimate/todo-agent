"""
Factory for creating LLM clients based on configuration.
"""

# mypy: disable-error-code="no-redef"

from typing import Optional

try:
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.llm_client import LLMClient
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.ollama_client import OllamaClient
    from todo_agent.infrastructure.openrouter_client import OpenRouterClient
except ImportError:
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.llm_client import LLMClient  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from infrastructure.ollama_client import OllamaClient  # type: ignore[no-redef]
    from infrastructure.openrouter_client import (
        OpenRouterClient,  # type: ignore[no-redef, misc]
    )


class LLMClientFactory:
    """Factory for creating LLM clients based on configuration."""

    @staticmethod
    def create_client(config: Config, logger: Optional[Logger] = None) -> LLMClient:
        """
        Create appropriate LLM client based on configuration.

        Args:
            config: Configuration object
            logger: Optional logger instance

        Returns:
            LLM client instance

        Raises:
            ValueError: If provider is not supported
        """
        logger = logger or Logger("llm_client_factory")

        if config.provider == "openrouter":
            logger.info(
                f"Creating OpenRouter client with model: {config.openrouter_model}"
            )
            return OpenRouterClient(config)
        elif config.provider == "ollama":
            logger.info(f"Creating Ollama client with model: {config.ollama_model}")
            return OllamaClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
