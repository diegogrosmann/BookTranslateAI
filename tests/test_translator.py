"""
Tests for the translator.py module
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.translator import TranslationClient, TranslationConfig


class TestTranslationConfig:
    """Tests for the TranslationConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = TranslationConfig(model="gpt-4")

        assert config.model == "gpt-4"
        assert config.target_language == "pt-BR"
        assert config.context == ""
        assert config.custom_instructions == ""

    def test_custom_config(self):
        """Test custom configuration."""
        config = TranslationConfig(
            model="claude-3.5-sonnet",
            target_language="es-ES",
            context="Specific context",
            custom_instructions="Custom instructions",
        )

        assert config.model == "claude-3.5-sonnet"
        assert config.target_language == "es-ES"
        assert config.context == "Specific context"
        assert config.custom_instructions == "Custom instructions"


class TestTranslationClient:
    """Tests for the TranslationClient class."""

    def setup_method(self):
        """Setup for each test."""
        self.config = TranslationConfig(model="gpt-4")
        self.client = TranslationClient(self.config)

    def test_client_initialization(self):
        """Test client initialization."""
        assert self.client.config == self.config
        assert self.client.api_key is None

    def test_client_with_api_key(self):
        """Test initialization with API key."""
        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(self.config, api_key="test-key")

            assert client.api_key == "test-key"
            # Should configure the appropriate environment variable
            assert os.environ.get("OPENAI_API_KEY") == "test-key"

    def test_set_api_key_openai(self):
        """Test API key configuration for OpenAI."""
        config = TranslationConfig(model="openai/gpt-4")

        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="openai-key")
            assert os.environ.get("OPENAI_API_KEY") == "openai-key"

    def test_set_api_key_anthropic(self):
        """Test API key configuration for Anthropic."""
        config = TranslationConfig(model="anthropic/claude-3.5-sonnet")

        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="anthropic-key")
            assert os.environ.get("ANTHROPIC_API_KEY") == "anthropic-key"

    def test_set_api_key_google(self):
        """Test API key configuration for Google."""
        config = TranslationConfig(model="google/gemini-pro")

        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="google-key")
            assert os.environ.get("GOOGLE_API_KEY") == "google-key"

    def test_set_api_key_unknown_provider(self):
        """Test API key configuration for unknown provider."""
        config = TranslationConfig(model="unknown/model")

        with patch.dict(os.environ, {}, clear=True):
            client = TranslationClient(config, api_key="unknown-key")
            assert os.environ.get("API_KEY") == "unknown-key"
            assert os.environ.get("LITELLM_API_KEY") == "unknown-key"

    @pytest.mark.asyncio
    @patch("src.translator.litellm.acompletion")
    async def test_translate_text_success(self, mock_completion):
        """Test successful translation."""
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Text translated to Portuguese"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 30
        mock_response.usage.total_tokens = 80

        mock_completion.return_value = mock_response

        result = await self.client.translate_text("Text to translate")

        assert result == "Text translated to Portuguese"

        # Verify it was called
        mock_completion.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.translator.litellm.acompletion")
    async def test_translate_text_with_context(self, mock_completion):
        """Test translation with context."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Translation with context"

        mock_completion.return_value = mock_response

        config = TranslationConfig(
            model="gpt-4",
            context="Specific context",
            custom_instructions="Custom instructions",
        )
        client = TranslationClient(config)

        result = await client.translate_text("Text with context")

        assert result == "Translation with context"
        mock_completion.assert_called_once()

    def test_build_system_prompt_default(self):
        """Test construction of default system prompt."""
        prompt = self.client._build_system_prompt()

        assert "professional translator" in prompt.lower()
        assert "pt-br" in prompt.lower()
        assert "translate the following text" in prompt.lower()

    def test_build_system_prompt_with_context(self):
        """Test construction of prompt with custom context."""
        config = TranslationConfig(
            model="gpt-4",
            target_language="es-ES",
            context="Specific context",
            custom_instructions="Special instructions",
        )
        client = TranslationClient(config)

        prompt = client._build_system_prompt()

        assert "es-es" in prompt.lower()
        assert "specific context" in prompt.lower()
        assert "special instructions" in prompt.lower()

    def test_get_model_info(self):
        """Test getting model information."""
        info = self.client.get_model_info()

        assert "model" in info
        assert "target_language" in info
        assert info["model"] == "gpt-4"
        assert info["target_language"] == "pt-BR"
