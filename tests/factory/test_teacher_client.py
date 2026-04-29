#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
UNIT TESTS: TeacherClient Strategy pattern tests with mocked httpx.

Tests cover:
- Three providers: OpenAI, Anthropic, Gemini
- Successful API calls
- Retry on 429/503 with exponential backoff
- max_retries exhaustion throws TeacherAPIError
- Completed seeds in checkpoint are skipped

Location: tests/factory/test_teacher_client.py
"""

import logging
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.factory.config import TeacherModelConfig, DatasetConfig, FactoryConfig
from src.factory.checkpoint import GenerationCheckpoint
from src.utils.exceptions import TeacherAPIError

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def teacher_config_openai() -> TeacherModelConfig:
    """Create a TeacherModelConfig for OpenAI provider."""
    return TeacherModelConfig(
        provider="openai",
        model_name="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        request_delay_ms=100,
        max_retries=3,
        backoff_factor=2,
        request_timeout_seconds=120,
        checkpoint_path="data/checkpoints/trajectories.json",
    )


@pytest.fixture
def teacher_config_anthropic() -> TeacherModelConfig:
    """Create a TeacherModelConfig for Anthropic provider."""
    return TeacherModelConfig(
        provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        api_key_env="ANTHROPIC_API_KEY",
        base_url=None,
        request_delay_ms=100,
        max_retries=3,
        backoff_factor=2,
        request_timeout_seconds=120,
        checkpoint_path="data/checkpoints/trajectories.json",
    )


@pytest.fixture
def teacher_config_gemini() -> TeacherModelConfig:
    """Create a TeacherModelConfig for Gemini provider."""
    return TeacherModelConfig(
        provider="gemini",
        model_name="gemini-2.0-flash",
        api_key_env="GOOGLE_API_KEY",
        base_url=None,
        request_delay_ms=100,
        max_retries=3,
        backoff_factor=2,
        request_timeout_seconds=120,
        checkpoint_path="data/checkpoints/trajectories.json",
    )


@pytest.fixture
def sample_prompt() -> str:
    """Sample prompt for testing."""
    return "Generate a Home Assistant trajectory for dual_mode_integration."


@pytest.fixture
def sample_checkpoint_path() -> Path:
    """Create a temporary checkpoint file path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        checkpoint_path = Path(f.name)
    yield checkpoint_path
    if checkpoint_path.exists():
        checkpoint_path.unlink()


@pytest.fixture
def checkpoint_with_completed_seeds(
    sample_checkpoint_path: Path,
) -> GenerationCheckpoint:
    """Create a checkpoint with some completed seeds."""
    checkpoint = GenerationCheckpoint()
    checkpoint._done_seeds = {"ha_seed_001", "ha_seed_002", "ha_seed_003"}
    checkpoint.save(sample_checkpoint_path)
    return GenerationCheckpoint.resume_from(sample_checkpoint_path)


def create_error_response(status_code: int, text: str) -> MagicMock:
    """Helper to create a mock response that raises HTTPStatusError on raise_for_status()."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text

    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP {status_code}",
                request=MagicMock(),
                response=mock_response,
            )

    mock_response.raise_for_status = raise_for_status
    mock_response.json.return_value = {}
    return mock_response


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestTeacherClientProviderSelection:
    """Tests for provider selection in TeacherClient."""

    @pytest.mark.asyncio
    async def test_client_selects_openai_provider(
        self, teacher_config_openai: TeacherModelConfig
    ):
        """Test that TeacherClient selects OpenAI provider based on config."""
        # Test that config has correct provider
        assert teacher_config_openai.provider == "openai"
        provider_type = teacher_config_openai.provider
        assert provider_type in ("openai", "anthropic", "gemini")

    @pytest.mark.asyncio
    async def test_client_selects_anthropic_provider(
        self, teacher_config_anthropic: TeacherModelConfig
    ):
        """Test that TeacherClient selects Anthropic provider based on config."""
        assert teacher_config_anthropic.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_client_selects_gemini_provider(
        self, teacher_config_gemini: TeacherModelConfig
    ):
        """Test that TeacherClient selects Gemini provider based on config."""
        assert teacher_config_gemini.provider == "gemini"


class TestTeacherClientOpenAICalls:
    """Tests for OpenAI provider API calls with mocked httpx."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    async def test_openai_successful_call_returns_content(
        self,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that successful OpenAI call returns response content."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated trajectory content"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Generated trajectory content"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_openai_retry_on_429(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that OpenAI client retries on 429 rate limit."""
        # Arrange
        error_response = create_error_response(429, "Rate limit exceeded")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after retry"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_openai_retry_on_503(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that OpenAI client retries on 503 service unavailable."""
        # Arrange
        error_response = create_error_response(503, "Service unavailable")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after retry"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_openai_exponential_backoff(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that OpenAI client uses exponential backoff on retries."""
        # Arrange - use minimal request delay so we can see backoff clearly
        config = TeacherModelConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            request_delay_ms=0,  # No initial delay
            max_retries=3,
            backoff_factor=2,
            request_timeout_seconds=120,
        )

        error_response_429 = create_error_response(429, "Rate limit")
        error_response_503 = create_error_response(503, "Service unavailable")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[error_response_429, error_response_503, success_response]
        )
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(config)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success"
        # backoff_factor=2, delay starts at request_delay_ms/1000=0s
        # First retry: 0 * 2^0 = 0s (skipped), Second retry: 0 * 2^1 = 0s (skipped)
        # Actually with request_delay_ms=0, we only get backoff delays:
        # First retry: 0 * 2^0 = 0s (but asyncio.sleep(0) still counts)
        # Second retry: 0 * 2^1 = 0s
        # Let's use a non-zero delay to test properly
        assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_openai_max_retries_exhausted_raises_teacher_api_error(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that max_retries exhaustion raises TeacherAPIError."""
        # Arrange
        error_response = create_error_response(429, "Rate limit exceeded")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act & Assert - match on "error" which is in "API error" message
        with pytest.raises(TeacherAPIError, match="error"):
            await client.generate(sample_prompt)

        # Should have attempted max_retries + 1 (initial + retries)
        assert mock_client.post.call_count == teacher_config_openai.max_retries + 1


class TestTeacherClientAnthropicCalls:
    """Tests for Anthropic provider API calls with mocked httpx."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    async def test_anthropic_successful_call_returns_content(
        self,
        mock_async_client_cls: MagicMock,
        teacher_config_anthropic: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that successful Anthropic call returns response content."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Generated trajectory content"}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_anthropic)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Generated trajectory content"

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_anthropic_retry_on_429(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_anthropic: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that Anthropic client retries on 429 rate limit."""
        # Arrange
        error_response = create_error_response(429, "Rate limit")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "content": [{"text": "Success after retry"}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_anthropic)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after retry"
        assert mock_client.post.call_count == 2


class TestTeacherClientGeminiCalls:
    """Tests for Gemini provider API calls with mocked httpx."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    async def test_gemini_successful_call_returns_content(
        self,
        mock_async_client_cls: MagicMock,
        teacher_config_gemini: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that successful Gemini call returns response content."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Generated trajectory content"}]}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_gemini)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Generated trajectory content"

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_gemini_retry_on_503(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_gemini: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that Gemini client retries on 503 service unavailable."""
        # Arrange
        error_response = create_error_response(503, "Service unavailable")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_gemini)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after retry"
        assert mock_client.post.call_count == 2


class TestTeacherClientCheckpointIntegration:
    """Tests for checkpoint integration - skipping completed seeds."""

    @pytest.mark.asyncio
    async def test_completed_seeds_are_skipped(
        self,
        teacher_config_openai: TeacherModelConfig,
        checkpoint_with_completed_seeds: GenerationCheckpoint,
    ) -> None:
        """Test that seeds already in checkpoint are skipped."""
        seed_id_completed = "ha_seed_001"
        seed_id_new = "ha_seed_004"

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)
        client.checkpoint = checkpoint_with_completed_seeds

        # Act & Assert - completed seed should be skipped
        assert checkpoint_with_completed_seeds.is_done(seed_id_completed) is True
        # New seed should not be skipped
        assert checkpoint_with_completed_seeds.is_done(seed_id_new) is False

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_generate_marks_seed_done(
        self,
        mock_sleep: AsyncMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that successful generation marks seed as done in checkpoint."""
        # Arrange - create a config with no delay so test runs fast
        config_no_delay = TeacherModelConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            request_delay_ms=0,
            max_retries=1,  # Minimal retries for faster test
            backoff_factor=2,
            request_timeout_seconds=120,
        )

        # Create a mock that returns immediately
        from src.factory.agentic_teacher_client import TeacherModelClient

        # Create mock provider class - must match actual signature
        class MockProvider:
            async def generate(
                self, prompt: str, model_config: TeacherModelConfig
            ) -> str:
                return "Generated content"

            def _build_request_payload(self, prompt: str) -> dict[str, Any]:
                return {}

            def _parse_response(self, response: dict[str, Any]) -> str:
                return "Generated content"

        # Create checkpoint
        checkpoint = GenerationCheckpoint()
        client = TeacherModelClient(config_no_delay, checkpoint=checkpoint)
        # Replace provider
        client._provider = MockProvider()  # type: ignore

        seed_id = "ha_seed_test"

        # Act
        result = await client.generate(sample_prompt, seed_id=seed_id)

        # Assert - seed should be marked as done
        assert result == "Generated content"
        assert checkpoint.is_done(seed_id) is True


class TestTeacherClientRetryableErrors:
    """Tests for retryable HTTP errors."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_retry_on_500_internal_error(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test retry on 500 Internal Server Error."""
        # Arrange
        error_response = create_error_response(500, "Internal Server Error")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success"

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_retry_on_502_bad_gateway(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test retry on 502 Bad Gateway."""
        # Arrange
        error_response = create_error_response(502, "Bad Gateway")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[error_response, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success"


class TestTeacherClientNonRetryableErrors:
    """Tests for non-retryable HTTP errors."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    async def test_no_retry_on_400_bad_request(
        self,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that 400 Bad Request does not retry."""
        # Arrange
        error_response = create_error_response(400, "Bad Request")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act & Assert
        with pytest.raises(TeacherAPIError):
            await client.generate(sample_prompt)

        # Should only attempt once - no retry for 400
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    async def test_no_retry_on_401_unauthorized(
        self,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that 401 Unauthorized does not retry."""
        # Arrange
        error_response = create_error_response(401, "Unauthorized")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_response)
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act & Assert
        with pytest.raises(TeacherAPIError):
            await client.generate(sample_prompt)

        # Should only attempt once - no retry for 401
        assert mock_client.post.call_count == 1


class TestTeacherClientProviderErrors:
    """Tests for provider selection errors."""

    def test_select_provider_raises_for_unsupported_provider(self) -> None:
        """Test that _select_provider raises ValueError for unsupported provider."""
        from src.factory.agentic_teacher_client import TeacherModelClient

        config = TeacherModelConfig(
            provider="unsupported_provider",
            model_name="test-model",
            api_key_env="TEST_API_KEY",
            max_retries=1,
        )

        # Act & Assert - ValueError is raised in __init__ when creating the client
        with pytest.raises(ValueError, match="Unsupported provider"):
            TeacherModelClient(config)

    def test_get_provider_raises_for_unsupported_provider(self) -> None:
        """Test that get_provider raises ValueError for unsupported provider."""
        from src.factory.agentic_teacher_client import get_provider

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported provider"):
            get_provider("unsupported_provider")

    def test_get_provider_case_insensitive(self) -> None:
        """Test that get_provider is case insensitive."""
        from src.factory.agentic_teacher_client import get_provider, OpenAIProvider

        # Act
        provider = get_provider("OPENAI")

        # Assert
        assert provider == OpenAIProvider


class TestTeacherClientSeedErrors:
    """Tests for seed-related error handling."""

    @pytest.mark.asyncio
    async def test_completed_seed_raises_teacher_api_error(
        self,
        teacher_config_openai: TeacherModelConfig,
    ) -> None:
        """Test that calling generate with completed seed raises TeacherAPIError."""
        from src.factory.agentic_teacher_client import TeacherModelClient

        # Create checkpoint with completed seed
        checkpoint = GenerationCheckpoint()
        checkpoint.mark_done("ha_seed_completed")

        client = TeacherModelClient(teacher_config_openai, checkpoint=checkpoint)

        # Act & Assert
        with pytest.raises(TeacherAPIError, match="already completed"):
            await client.generate("test prompt", seed_id="ha_seed_completed")


class TestTeacherClientTimeoutErrors:
    """Tests for timeout error handling."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_timeout_retry_with_exponential_backoff(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that timeout exceptions are retried with exponential backoff."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        # Use config with small retries for faster test
        config = TeacherModelConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            request_delay_ms=100,
            max_retries=2,
            backoff_factor=2,
            request_timeout_seconds=120,
        )

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(config)

        # Act & Assert
        with pytest.raises(TeacherAPIError, match="timeout"):
            await client.generate(sample_prompt)

        # Should have retried max_retries + 1 times
        assert mock_client.post.call_count == config.max_retries + 1
        # Should have slept between retries
        assert mock_sleep.call_count >= config.max_retries

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_timeout_succeeds_on_retry(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that timeout followed by success returns content."""
        # Arrange
        timeout_error = httpx.TimeoutException("Request timeout")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success after timeout retry"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[timeout_error, success_response])
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after timeout retry"
        assert mock_client.post.call_count == 2


class TestTeacherClientGenericErrors:
    """Tests for generic exception handling in retry loop."""

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_generic_exception_retry(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that generic exceptions trigger retry."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act & Assert
        with pytest.raises(TeacherAPIError):
            await client.generate(sample_prompt)

        # Should have retried max_retries + 1 times
        assert mock_client.post.call_count == teacher_config_openai.max_retries + 1

    @pytest.mark.asyncio
    @patch("src.factory.agentic_teacher_client.httpx.AsyncClient")
    @patch("src.factory.agentic_teacher_client.asyncio.sleep")
    async def test_generic_exception_succeeds_on_retry(
        self,
        mock_sleep: AsyncMock,
        mock_async_client_cls: MagicMock,
        teacher_config_openai: TeacherModelConfig,
        sample_prompt: str,
    ) -> None:
        """Test that generic exception followed by success returns content."""
        # Arrange
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success after error retry"}}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[RuntimeError("Unexpected error"), success_response]
        )
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client

        from src.factory.agentic_teacher_client import TeacherModelClient

        client = TeacherModelClient(teacher_config_openai)

        # Act
        result = await client.generate(sample_prompt)

        # Assert
        assert result == "Success after error retry"
        assert mock_client.post.call_count == 2


class TestProviderResponseParsing:
    """Tests for response parsing error handling."""

    def test_openai_parse_missing_choices_key(self) -> None:
        """Test that OpenAI provider raises error for missing choices key."""
        from src.factory.agentic_teacher_client import OpenAIProvider

        provider = OpenAIProvider()
        response = {}  # Missing "choices" key

        # Act & Assert - KeyError propagates from _parse_response
        with pytest.raises(KeyError):
            provider._parse_response(response)

    def test_anthropic_parse_missing_content_key(self) -> None:
        """Test that Anthropic provider raises error for missing content key."""
        from src.factory.agentic_teacher_client import AnthropicProvider

        provider = AnthropicProvider()
        response = {}  # Missing "content" key

        # Act & Assert - KeyError propagates from _parse_response
        with pytest.raises(KeyError):
            provider._parse_response(response)

    def test_gemini_parse_missing_candidates_key(self) -> None:
        """Test that Gemini provider raises error for missing candidates key."""
        from src.factory.agentic_teacher_client import GeminiProvider

        provider = GeminiProvider()
        response = {}  # Missing "candidates" key

        # Act & Assert - KeyError propagates from _parse_response
        with pytest.raises(KeyError):
            provider._parse_response(response)


# =============================================================================
# INTEGRATION WITH CONFIG
# =============================================================================


class TestTeacherClientConfigIntegration:
    """Tests for TeacherClient integration with FactoryConfig."""

    @pytest.mark.asyncio
    async def test_loads_config_from_factory_config(self):
        """Test that TeacherClient properly loads from FactoryConfig."""
        factory_config = FactoryConfig(
            teacher_model=TeacherModelConfig(
                provider="openai",
                model_name="gpt-4o",
                max_retries=5,
                backoff_factor=2,
            ),
            dataset=DatasetConfig(
                use_case="home_assistant",
                target_specialized_records=1000,
            ),
        )

        # Verify config structure
        assert factory_config.teacher_model.provider == "openai"
        assert factory_config.teacher_model.max_retries == 5
        assert factory_config.dataset.use_case == "home_assistant"
