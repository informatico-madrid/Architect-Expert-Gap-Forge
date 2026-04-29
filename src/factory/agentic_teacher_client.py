#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Teacher Model Client — Strategy Pattern Implementation
======================================================
Provides async API clients for external teacher models (OpenAI, Anthropic, Gemini)
with retry logic, exponential backoff, and checkpoint integration.

This module implements the Strategy pattern as specified in plan.md,
aligned with src/audit/inference.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

from src.factory.config import TeacherModelConfig
from src.factory.checkpoint import GenerationCheckpoint
from src.utils.exceptions import TeacherAPIError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Retryable HTTP status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


# ==============================================================================
# PROVIDER PROTOCOL
# ==============================================================================


class TeacherProvider(ABC):
    """Abstract base class for teacher model providers.

    Each provider (OpenAI, Anthropic, Gemini) implements this interface
    to make API calls with provider-specific request/response handling.
    """

    @abstractmethod
    async def generate(self, prompt: str, model_config: TeacherModelConfig) -> str:
        """Generate a response from the teacher model.

        Args:
            prompt: The input prompt for the model.
            model_config: Configuration for the teacher model.

        Returns:
            The generated text response.

        Raises:
            TeacherAPIError: If the API call fails.
        """

    @abstractmethod
    def _build_request_payload(self, prompt: str) -> dict[str, Any]:
        """Build the request payload for the provider.

        Args:
            prompt: The input prompt.

        Returns:
            The request payload dictionary.
        """

    @abstractmethod
    def _parse_response(self, response: dict[str, Any]) -> str:
        """Parse the API response to extract content.

        Args:
            response: The API response dictionary.

        Returns:
            The extracted content string.
        """


# ==============================================================================
# OPENAI PROVIDER
# ==============================================================================


class OpenAIProvider(TeacherProvider):
    """OpenAI-compatible API provider."""

    async def generate(self, prompt: str, model_config: TeacherModelConfig) -> str:
        """Generate using OpenAI-compatible API."""
        payload = self._build_request_payload(prompt)
        base_url = model_config.base_url or "https://api.openai.com/v1"
        headers = {
            "Authorization": f"Bearer {os.getenv(model_config.api_key_env, 'dummy-key')}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=model_config.request_timeout_seconds
        ) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data)

    def _build_request_payload(self, prompt: str) -> dict[str, Any]:
        """Build OpenAI-compatible request payload."""
        return {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

    def _parse_response(self, response: dict[str, Any]) -> str:
        """Parse OpenAI response."""
        return response["choices"][0]["message"]["content"]


# ==============================================================================
# ANTHROPIC PROVIDER
# ==============================================================================


class AnthropicProvider(TeacherProvider):
    """Anthropic Claude API provider."""

    async def generate(self, prompt: str, model_config: TeacherModelConfig) -> str:
        """Generate using Anthropic Claude API."""
        payload = self._build_request_payload(prompt)
        headers = {
            "x-api-key": os.getenv(model_config.api_key_env, "dummy-key"),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=model_config.request_timeout_seconds
        ) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data)

    def _build_request_payload(self, prompt: str) -> dict[str, Any]:
        """Build Anthropic request payload."""
        return {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

    def _parse_response(self, response: dict[str, Any]) -> str:
        """Parse Anthropic response."""
        return response["content"][0]["text"]


# ==============================================================================
# GEMINI PROVIDER
# ==============================================================================


class GeminiProvider(TeacherProvider):
    """Google Gemini API provider."""

    async def generate(self, prompt: str, model_config: TeacherModelConfig) -> str:
        """Generate using Google Gemini API."""
        payload = self._build_request_payload(prompt)
        api_key = os.getenv(model_config.api_key_env, "dummy-key")

        async with httpx.AsyncClient(
            timeout=model_config.request_timeout_seconds
        ) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_config.model_name}:generateContent?key={api_key}",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data)

    def _build_request_payload(self, prompt: str) -> dict[str, Any]:
        """Build Gemini request payload."""
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            },
        }

    def _parse_response(self, response: dict[str, Any]) -> str:
        """Parse Gemini response."""
        return response["candidates"][0]["content"]["parts"][0]["text"]


# ==============================================================================
# TEACHER MODEL CLIENT (ROUTER)
# ==============================================================================


class TeacherModelClient:
    """Router class that selects provider based on configuration.

    Provides async generation with retry logic, exponential backoff,
    and checkpoint integration for resume capability.
    """

    def __init__(
        self,
        config: TeacherModelConfig,
        checkpoint: GenerationCheckpoint | None = None,
    ) -> None:
        """Initialize the TeacherModelClient.

        Args:
            config: Teacher model configuration.
            checkpoint: Optional checkpoint for tracking completed seeds.
        """
        self.config = config
        self.checkpoint = (
            checkpoint if checkpoint is not None else GenerationCheckpoint()
        )
        self._provider = self._select_provider()

    def _select_provider(self) -> TeacherProvider:
        """Select the appropriate provider based on config.

        Returns:
            The selected provider instance.

        Raises:
            ValueError: If provider is not supported.
        """
        provider = self.config.provider.lower()
        if provider == "openai":
            return OpenAIProvider()
        elif provider == "anthropic":
            return AnthropicProvider()
        elif provider == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def generate(self, prompt: str, seed_id: str | None = None) -> str:
        """Generate a response with retry logic and exponential backoff.

        Args:
            prompt: The input prompt for the model.
            seed_id: Optional seed ID for checkpoint tracking.

        Returns:
            The generated text response.

        Raises:
            TeacherAPIError: If all retries are exhausted.
        """
        # Check if seed is already completed in checkpoint
        if seed_id and self.checkpoint.is_done(seed_id):
            logger.info("Seed %s already completed, skipping", seed_id)
            raise TeacherAPIError(f"Seed {seed_id} already completed")

        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_retries + 2):  # +1 for initial attempt
            try:
                # Apply request delay
                if self.config.request_delay_ms > 0:
                    await asyncio.sleep(self.config.request_delay_ms / 1000.0)

                result = await self._provider.generate(prompt, self.config)

                # Mark seed as done if checkpoint provided
                if seed_id:
                    self.checkpoint.mark_done(seed_id)

                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if (
                    status_code in RETRYABLE_STATUS_CODES
                    and attempt <= self.config.max_retries
                ):
                    # Calculate exponential backoff
                    delay = (self.config.request_delay_ms / 1000.0) * (
                        self.config.backoff_factor ** (attempt - 1)
                    )
                    logger.warning(
                        "Attempt %d/%d failed with %d, retrying in %.2fs",
                        attempt,
                        self.config.max_retries,
                        status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error or max retries exhausted
                    raise TeacherAPIError(f"API error {status_code}: {e}") from e

            except httpx.TimeoutException as e:
                if attempt <= self.config.max_retries:
                    delay = (self.config.request_delay_ms / 1000.0) * (
                        self.config.backoff_factor ** (attempt - 1)
                    )
                    logger.warning(
                        "Attempt %d/%d timed out, retrying in %.2fs",
                        attempt,
                        self.config.max_retries,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise TeacherAPIError(
                        f"Request timeout after {attempt} attempts"
                    ) from e

            except Exception as e:
                last_exception = e
                if attempt <= self.config.max_retries:
                    delay = (self.config.request_delay_ms / 1000.0) * (
                        self.config.backoff_factor ** (attempt - 1)
                    )
                    logger.warning(
                        "Attempt %d/%d failed with %s, retrying in %.2fs",
                        attempt,
                        self.config.max_retries,
                        type(e).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        # All retries exhausted
        error_msg = f"Generation failed after {self.config.max_retries + 1} attempts"
        if last_exception:
            error_msg = f"{error_msg}: {last_exception}"
        raise TeacherAPIError(error_msg)


# ==============================================================================
# PROVIDER FACTORY
# ==============================================================================


def get_provider(provider_name: str) -> type[TeacherProvider]:
    """Get the provider class by name.

    Args:
        provider_name: Name of the provider (openai, anthropic, gemini).

    Returns:
        The provider class.

    Raises:
        ValueError: If provider is not supported.
    """
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    provider_lower = provider_name.lower()
    if provider_lower not in providers:
        raise ValueError(
            f"Unsupported provider: {provider_name}. "
            f"Supported providers: {', '.join(providers.keys())}"
        )
    return providers[provider_lower]
