#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Inference Client Mock Utilities

Mock utilities for testing code that interacts with inference backends.
Provides fake implementations for:
- GeminiClient (Google GenAI SDK)
- VLLMClient (OpenAI-compatible HTTP API)
- ClaudeClient (Claude Code CLI wrapper)
- InferenceRouter (client resolution)

Location: tests/fixtures/inference_mocks.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import os
import types
from typing import Any


# =============================================================================
# REGISTRY FOR MOCK RESPONSES
# =============================================================================

# Registry to store mock responses per client
_MOCK_RESPONSES: dict[str, str] = {}
_MOCK_REGISTRY: list[str] = []


def register_mock_response(client_type: str, response: str) -> None:
    """Register a mock response for a specific client type.

    Args:
        client_type: The client type identifier ("gemini", "vllm", "claude")
        response: The mock response string to return
    """
    _MOCK_RESPONSES[client_type] = response


def clear_mock_responses() -> None:
    """Clear all registered mock responses."""
    global _MOCK_RESPONSES
    _MOCK_RESPONSES = {}


# =============================================================================
# MOCK CLASSES
# =============================================================================


class MockBaseInferenceClient:
    """Mock base inference client for testing.

    Provides a simple implementation that returns configurable responses
    without making any actual API calls.
    """

    _backend_name: str = "Mock"

    def __init__(self, mock_response: str = "mock response") -> None:
        self._mock_response = mock_response

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 65536,
        temperature: float = 0.6,
        top_k: int | None = None,
        min_p: float | None = None,
        repetition_penalty: float | None = None,
        presence_penalty: float | None = None,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Return the configured mock response."""
        return self._mock_response

    def generate_with_retry(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 65536,
        temperature: float = 0.6,
        top_k: int | None = None,
        min_p: float | None = None,
        repetition_penalty: float | None = None,
        presence_penalty: float | None = None,
        retries: int = 3,
        retry_delay: float = 5.0,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Return the configured mock response (retry logic not needed in mock)."""
        return self._mock_response


class MockGeminiClient(MockBaseInferenceClient):
    """Mock Gemini client for testing.

    Simulates the GeminiClient behavior without making actual API calls
    to Google GenAI.
    """

    _backend_name = "Gemini"

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        mock_response: str = "gemini mock response",
    ) -> None:
        super().__init__(mock_response)
        self._model = model
        self._api_key = os.getenv("GOOGLE_API_KEY", "")

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 65536,
        temperature: float = 0.3,
        top_k: int | None = None,
        min_p: float | None = None,
        repetition_penalty: float | None = None,
        presence_penalty: float | None = None,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Return mock response, simulating Gemini API behavior."""
        # Store last request for verification
        self._last_prompt = prompt
        self._last_system_prompt = system_prompt
        self._last_max_tokens = max_tokens
        self._last_temperature = temperature
        self._last_json_mode = json_mode
        return self._mock_response


class MockVLLMClient(MockBaseInferenceClient):
    """Mock vLLM client for testing.

    Simulates the VLLMClient behavior without making HTTP requests
    to an OpenAI-compatible endpoint.
    """

    _backend_name = "vLLM"

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
<<<<<<< Updated upstream
        model: str = "qwen3-5-35b-a3b-nvfp4",
=======
        model: str = "qwen3-30b-a3b-thinking-fp8",
>>>>>>> Stashed changes
        mock_response: str = "vllm mock response",
    ) -> None:
        super().__init__(mock_response)
        self._api_url = api_url.rstrip("/")
        self._model = model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 65536,
        temperature: float = 0.6,
        top_k: int | None = None,
        min_p: float | None = None,
        repetition_penalty: float | None = None,
        presence_penalty: float | None = None,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Return mock response, simulating vLLM HTTP API behavior."""
        # Store last request for verification
        self._last_prompt = prompt
        self._last_system_prompt = system_prompt
        self._last_max_tokens = max_tokens
        self._last_temperature = temperature
        self._last_top_k = top_k
        self._last_min_p = min_p
        self._last_repetition_penalty = repetition_penalty
        self._last_presence_penalty = presence_penalty
        self._last_json_mode = json_mode
        return self._mock_response


class MockClaudeClient(MockBaseInferenceClient):
    """Mock Claude client for testing.

    Simulates the ClaudeClient behavior without calling the Claude CLI.
    """

    _backend_name = "Claude"

    def __init__(
        self,
        model: str = "MiniMax-M2.5",
        mock_response: str = "claude mock response",
    ) -> None:
        super().__init__(mock_response)
        self._model = model
        self._cli_path = "mock_claude"

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 65536,
        temperature: float = 0.6,
        top_k: int | None = None,
        min_p: float | None = None,
        repetition_penalty: float | None = None,
        presence_penalty: float | None = None,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Return mock response, simulating Claude CLI behavior."""
        # Store last request for verification
        self._last_prompt = prompt
        self._last_system_prompt = system_prompt
        self._last_max_tokens = max_tokens
        return self._mock_response


class MockInferenceRouter:
    """Mock InferenceRouter for testing.

    Returns mock clients without creating real inference backends.
    """

    def __init__(self) -> None:
        self._cache: dict[str, MockBaseInferenceClient] = {}

    def professor(
        self,
        backend: str = "auto",
        gemini_model: str = "gemini-2.5-flash",
<<<<<<< Updated upstream
        vllm_model: str = "qwen3-5-35b-a3b-nvfp4",
=======
        vllm_model: str = "qwen3-30b-a3b-thinking-fp8",
>>>>>>> Stashed changes
        api_url: str = "http://localhost:8000/v1",
        claude_model: str = "MiniMax-M2.5",
    ) -> MockBaseInferenceClient:
        """Return a mock professor client."""
        key = f"professor:{backend}:{gemini_model}:{vllm_model}:{claude_model}"
        if key not in self._cache:
            if backend == "gemini" or (backend == "auto" and os.getenv("GOOGLE_API_KEY")):
                self._cache[key] = MockGeminiClient(model=gemini_model)
            elif backend == "claude":
                self._cache[key] = MockClaudeClient(model=claude_model)
            else:
                self._cache[key] = MockVLLMClient(api_url=api_url, model=vllm_model)
        return self._cache[key]

    def student(
        self,
        backend: str = "vllm",
        gemini_model: str = "gemini-2.5-flash",
<<<<<<< Updated upstream
        model: str = "qwen3-5-35b-a3b-nvfp4",
=======
        model: str = "qwen3-30b-a3b-thinking-fp8",
>>>>>>> Stashed changes
        api_url: str = "http://localhost:8000/v1",
        claude_model: str = "MiniMax-M2.5",
    ) -> MockBaseInferenceClient:
        """Return a mock student client."""
        key = f"student:{backend}:{model}:{gemini_model}:{claude_model}"
        if key not in self._cache:
            if backend == "gemini":
                self._cache[key] = MockGeminiClient(model=gemini_model)
            elif backend == "claude":
                self._cache[key] = MockClaudeClient(model=claude_model)
            else:
                self._cache[key] = MockVLLMClient(api_url=api_url, model=model)
        return self._cache[key]


# =============================================================================
# PYTEST FIXTURES
# =============================================================================


def create_gemini_fixture(response: str = "gemini response") -> MockGeminiClient:
    """Create a Gemini client mock fixture.

    Args:
        response: The response the mock should return

    Returns:
        A configured MockGeminiClient instance
    """
    return MockGeminiClient(mock_response=response)


def create_vllm_fixture(
    response: str = "vllm response",
    api_url: str = "http://localhost:8000/v1",
<<<<<<< Updated upstream
    model: str = "qwen3-5-35b-a3b-nvfp4",
=======
    model: str = "qwen3-30b-a3b-thinking-fp8",
>>>>>>> Stashed changes
) -> MockVLLMClient:
    """Create a vLLM client mock fixture.

    Args:
        response: The response the mock should return
        api_url: The API URL (stored but not used)
        model: The model name (stored but not used)

    Returns:
        A configured MockVLLMClient instance
    """
    return MockVLLMClient(mock_response=response, api_url=api_url, model=model)


def create_claude_fixture(
    response: str = "claude response",
    model: str = "MiniMax-M2.5",
) -> MockClaudeClient:
    """Create a Claude client mock fixture.

    Args:
        response: The response the mock should return
        model: The model name (stored but not used)

    Returns:
        A configured MockClaudeClient instance
    """
    return MockClaudeClient(mock_response=response, model=model)


def create_router_fixture() -> MockInferenceRouter:
    """Create an inference router mock fixture.

    Returns:
        A configured MockInferenceRouter instance
    """
    return MockInferenceRouter()


def create_judge_response_fixture() -> dict[str, Any]:
    """Create a fixture for judge response JSON.

    Returns:
        A dictionary representing a typical judge response
    """
    return {
        "adapter": {
            "ha_modernity": 0.8,
            "reasoning_depth": 0.7,
            "functionality": 0.9,
            "completeness": 0.75,
            "style": 0.85,
        },
        "baseline": {
            "ha_modernity": 0.3,
            "reasoning_depth": 0.4,
            "functionality": 0.5,
            "completeness": 0.45,
            "style": 0.55,
        },
    }


def create_student_response_fixture() -> str:
    """Create a fixture for student model response.

    Returns:
        A string representing a typical student model response
    """
    return (
        "Machine learning is a type of artificial intelligence that allows "
        "computers to learn from data without being explicitly programmed. "
        "It uses statistical techniques to enable computers to improve at "
        "tasks through experience."
    )


def create_json_judge_response_fixture() -> str:
    """Create a fixture for judge response as JSON string.

    Returns:
        A JSON string representing judge scores
    """
    import json

    return json.dumps(create_judge_response_fixture())


# =============================================================================
# MODULE INJECTION (for testing code that imports inference modules)
# =============================================================================


def enable_fake_inference() -> None:
    """Insert fake inference modules into sys.modules.

    After calling this function, importing code that uses inference clients
    will use the mock implementations.
    """
    import sys
    from unittest.mock import MagicMock

    global _MOCK_REGISTRY

    # Create mock module for src.audit.inference
    inference_module = types.ModuleType("src.audit.inference")
    inference_module.__spec__ = MagicMock()

    # Add mock classes to the module
    inference_module.BaseInferenceClient = MockBaseInferenceClient
    inference_module.GeminiClient = MockGeminiClient
    inference_module.VLLMClient = MockVLLMClient
    inference_module.ClaudeClient = MockClaudeClient
    inference_module.InferenceRouter = MockInferenceRouter
    inference_module._GEMINI_AVAILABLE = True

    sys.modules["src.audit.inference"] = inference_module
    _MOCK_REGISTRY.append("src.audit.inference")


def disable_fake_inference() -> None:
    """Remove previously injected fake modules from sys.modules."""
    import sys

    global _MOCK_REGISTRY

    for name in list(_MOCK_REGISTRY):
        sys.modules.pop(name, None)
        _MOCK_REGISTRY.remove(name)

    clear_mock_responses()


__all__ = [
    # Registry functions
    "register_mock_response",
    "clear_mock_responses",
    # Mock classes
    "MockBaseInferenceClient",
    "MockGeminiClient",
    "MockVLLMClient",
    "MockClaudeClient",
    "MockInferenceRouter",
    # Fixture creators
    "create_gemini_fixture",
    "create_vllm_fixture",
    "create_claude_fixture",
    "create_router_fixture",
    "create_judge_response_fixture",
    "create_student_response_fixture",
    "create_json_judge_response_fixture",
    # Module injection
    "enable_fake_inference",
    "disable_fake_inference",
]
