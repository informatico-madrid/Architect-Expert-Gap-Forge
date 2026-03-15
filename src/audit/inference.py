#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""AEGF Inference Clients — Strategy pattern for inference backends.

Provides a common interface ``BaseInferenceClient`` and two concrete
implementations (``GeminiClient`` and ``VLLMClient``) that encapsulate call
logic to different backends. The ``InferenceRouter`` automatically resolves
which client to use based on configuration.
"""

from __future__ import annotations

import abc
import logging
import os
import subprocess
import time
from typing import Any
from src.schemas.common import InferencePayload, ChatMessage

import requests

__all__ = [
    "BaseInferenceClient",
    "GeminiClient",
    "VLLMClient",
    "ClaudeClient",
    "InferenceRouter",
]

logger = logging.getLogger("AEGF.Inference")

# ---------------------------------------------------------------------------
# Optional Gemini SDK import
# ---------------------------------------------------------------------------

_GEMINI_AVAILABLE = False
try:
    from google import genai as _genai  # type: ignore[import]
    from google.genai import types as _genai_types  # type: ignore[import]

    _GEMINI_AVAILABLE = True
except ImportError:
    _genai = None  # type: ignore[assignment]
    _genai_types = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Base class (Strategy interface)
# ---------------------------------------------------------------------------


class BaseInferenceClient(abc.ABC):
    """Abstract interface for LLM inference clients.

    Template Method: ``generate_with_retry`` is implemented here once using
    ``generate`` (abstract) as the primitive operation. Subclasses only need
    to implement ``generate``; they inherit retry + exponential backoff for free.

    Subclasses MUST set ``_backend_name`` to a human-readable label used in
    log and error messages (e.g. ``"Gemini"``, ``"vLLM"``).
    """

    _backend_name: str = "unknown"

    @abc.abstractmethod
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
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a text completion and return the raw response string.

        Parameters
        ----------
        prompt : str
            User message / prompt.
        system_prompt : str | None
            Optional system instruction.
        max_tokens : int
            Max output tokens.
        temperature : float
            Sampling temperature.
        top_k : int | None
            Top-k sampling parameter (vLLM only).
        min_p : float | None
            Minimum probability threshold for nucleus sampling (vLLM only).
        repetition_penalty : float | None
            Repetition penalty (vLLM only).
        json_mode : bool
            When True, request structured JSON output from the backend.
        """

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
        retries: int = 3,
        retry_delay: float = 5.0,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate with exponential-backoff retry on transient errors.

        Concrete Template Method — calls ``self.generate()`` internally.
        Backoff: ``retry_delay * 2^(attempt-1)`` (1×, 2×, 4×, …).
        Override is never required; change ``generate`` instead.
        """
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return self.generate(
                    prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_k=top_k,
                    min_p=min_p,
                    repetition_penalty=repetition_penalty,
                    json_mode=json_mode,
                    tools=tools,
                )
            except Exception as exc:
                last_exc = exc
                wait = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "%s attempt %d/%d failed: %s — retrying in %.1fs",
                    self._backend_name,
                    attempt,
                    retries,
                    exc,
                    wait,
                )
                time.sleep(wait)
        raise RuntimeError(
            f"{self._backend_name} generation failed after {retries} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Gemini Client
# ---------------------------------------------------------------------------


class GeminiClient(BaseInferenceClient):
    """Google Gemini client via the ``google-genai`` SDK.

    Uses the Gemini API for professor/judge calls, freeing local GPU for
    training or vLLM inference.
    """

    _backend_name = "Gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        if not _GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai SDK is required for GeminiClient. "
                "Install with: pip install google-genai"
            )
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is required for GeminiClient")
        self._client = _genai.Client(api_key=api_key)
        self._model = model

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
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        # Note: Gemini API doesn't support top_k, min_p, or repetition_penalty
        # These parameters are accepted for API consistency but ignored
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = _genai_types.GenerateContentConfig(**config_kwargs)
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text or ""


# ---------------------------------------------------------------------------
# vLLM Client (OpenAI-compatible HTTP API)
# ---------------------------------------------------------------------------


class VLLMClient(BaseInferenceClient):
    """vLLM client via OpenAI-compatible HTTP endpoint.

    Supports any server exposing `/v1/chat/completions` following the OpenAI
    schema (vLLM, TGI, llama.cpp, etc.).
    """

    _backend_name = "vLLM"

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
        model: str = "qwen3-30b-a3b-thinking-fp8",
    ) -> None:
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
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: InferencePayload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        # Add vLLM-specific sampling parameters if provided
        if top_k is not None:
            payload["top_k"] = top_k
        if min_p is not None:
            payload["min_p"] = min_p
        if repetition_penalty is not None:
            payload["repetition_penalty"] = repetition_penalty
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        # Tools disabled - using text-only inference
        # if tools:
        #     payload["tools"] = tools

        resp = requests.post(
            f"{self._api_url}/chat/completions",
            json=payload,
            timeout=3600,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Claude Client (Claude Code CLI wrapper)
# ---------------------------------------------------------------------------


class ClaudeClient(BaseInferenceClient):
    """Claude Code CLI client wrapper.

    Uses the Claude Code CLI (claude) for inference via subprocess.
    Supports model selection via CLAUDE_MODEL environment variable or model argument.
    """

    _backend_name = "Claude"

    def __init__(self, model: str = "MiniMax-M2.5") -> None:
        self._model = model or os.getenv("CLAUDE_MODEL", "MiniMax-M2.5")
        self._cli_path = self._find_claude_cli()

    def _find_claude_cli(self) -> str:
        """Find the Claude CLI executable path."""
        # Check if running in a specific environment
        cli_path = os.getenv("CLAUDE_CLI_PATH")
        if cli_path and os.path.isfile(cli_path):
            return cli_path

        # Check common paths
        common_paths = [
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            os.expanduser("~/.local/bin/claude"),
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path

        # Fall back to just 'claude' and hope it's in PATH
        return "claude"

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
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        # Build the full prompt with system prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # Claude Code CLI doesn't support all the parameters we have
        # Build the command: claude -p --print < prompt
        cmd = [self._cli_path, "-p", "--print"]

        # Add model if specified (Claude CLI supports --model flag)
        if self._model:
            cmd.extend(["--model", self._model])

        # Add max tokens (Claude CLI uses --max-tokens)
        if max_tokens:
            cmd.extend(["--max-tokens", str(max_tokens)])

        # Claude CLI doesn't directly support temperature, top_k, min_p, repetition_penalty
        # These would need to be handled differently or ignored

        try:
            result = subprocess.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Claude CLI failed with code {result.returncode}: {result.stderr}"
                )
            return result.stdout
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Claude CLI timed out after 300 seconds") from exc
        except FileNotFoundError:
            raise RuntimeError(
                f"Claude CLI not found at {self._cli_path}. "
                "Please ensure Claude Code CLI is installed and in PATH, "
                "or set CLAUDE_CLI_PATH environment variable."
            ) from None


# ---------------------------------------------------------------------------
# Router — resolves the correct client based on configuration
# ---------------------------------------------------------------------------


class InferenceRouter:
    """Resolves and caches the appropriate client according to the configured backend.

    Usage::

        router = InferenceRouter()
        professor = router.professor(backend="auto", gemini_model="gemini-2.5-flash")
        student   = router.student(backend="vllm", api_url="...", model="qwen3-...")
    """

    def __init__(self) -> None:
        self._cache: dict[str, BaseInferenceClient] = {}

    def professor(
        self,
        backend: str = "auto",
        gemini_model: str = "gemini-2.5-flash",
        vllm_model: str = "qwen3-30b-a3b-thinking-fp8",
        api_url: str = "http://localhost:8000/v1",
        claude_model: str = "MiniMax-M2.5",
    ) -> BaseInferenceClient:
        """Resolve the professor/judge client (prefers Gemini to save GPU, or Claude)."""
        resolved = self._resolve_backend(backend)
        key = f"professor:{resolved}:{gemini_model if resolved == 'gemini' else vllm_model if resolved == 'vllm' else claude_model}"
        if key not in self._cache:
            if resolved == "gemini":
                self._cache[key] = GeminiClient(model=gemini_model)
            elif resolved == "claude":
                self._cache[key] = ClaudeClient(model=claude_model)
            else:
                self._cache[key] = VLLMClient(api_url=api_url, model=vllm_model)
            logger.info("Professor client: %s (%s)", resolved, key)
        return self._cache[key]

    def student(
        self,
        backend: str = "vllm",
        gemini_model: str = "gemini-2.5-flash",
        model: str = "qwen3-30b-a3b-thinking-fp8",
        api_url: str = "http://localhost:8000/v1",
        claude_model: str = "MiniMax-M2.5",
    ) -> BaseInferenceClient:
        """Resolve the student (baseline/adapter) inference client."""
        key = f"student:{backend}:{model if backend == 'vllm' else gemini_model if backend == 'gemini' else claude_model}"
        if key not in self._cache:
            if backend == "gemini":
                self._cache[key] = GeminiClient(model=gemini_model)
            elif backend == "claude":
                self._cache[key] = ClaudeClient(model=claude_model)
            else:
                self._cache[key] = VLLMClient(api_url=api_url, model=model)
            logger.info("Student client: %s (%s)", backend, key)
        return self._cache[key]

    @staticmethod
    def _resolve_backend(backend: str) -> str:
        """Resolve 'auto' to a concrete backend name."""
        if backend == "auto":
            if _GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
                return "gemini"
            return "vllm"
        if backend not in ("gemini", "vllm", "claude"):
            raise ValueError(f"Unknown backend: {backend}. Must be one of: gemini, vllm, claude")
        return backend
