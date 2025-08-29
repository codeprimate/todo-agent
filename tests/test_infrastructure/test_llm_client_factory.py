"""
Tests for LLMClientFactory.
"""

from unittest.mock import Mock, patch

import pytest

from todo_agent.infrastructure.config import Config
from todo_agent.infrastructure.llm_client_factory import LLMClientFactory


class TestLLMClientFactory:
    """Test LLMClientFactory functionality."""

    def test_create_openrouter_client(self):
        """Test creating OpenRouter client."""
        config = Config()
        config.provider = "openrouter"
        config.openrouter_model = "openai/gpt-4o-mini"

        with patch(
            "todo_agent.infrastructure.llm_client_factory.OpenRouterClient"
        ) as mock_openrouter:
            mock_client = Mock()
            mock_openrouter.return_value = mock_client

            client = LLMClientFactory.create_client(config)

            assert client == mock_client
            mock_openrouter.assert_called_once_with(config)

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        config = Config()
        config.provider = "ollama"
        config.ollama_model = "llama3.2"

        with patch(
            "todo_agent.infrastructure.llm_client_factory.OllamaClient"
        ) as mock_ollama:
            mock_client = Mock()
            mock_ollama.return_value = mock_client

            client = LLMClientFactory.create_client(config)

            assert client == mock_client
            mock_ollama.assert_called_once_with(config)

    def test_create_unsupported_provider(self):
        """Test creating client with unsupported provider."""
        config = Config()
        config.provider = "unsupported"

        with pytest.raises(ValueError, match="Unsupported LLM provider: unsupported"):
            LLMClientFactory.create_client(config)

    def test_create_client_with_logger(self):
        """Test creating client with custom logger."""
        config = Config()
        config.provider = "openrouter"
        config.openrouter_model = "openai/gpt-4o-mini"

        mock_logger = Mock()

        with patch(
            "todo_agent.infrastructure.llm_client_factory.OpenRouterClient"
        ) as mock_openrouter:
            mock_client = Mock()
            mock_openrouter.return_value = mock_client

            client = LLMClientFactory.create_client(config, mock_logger)

            assert client == mock_client
            mock_openrouter.assert_called_once_with(config)
