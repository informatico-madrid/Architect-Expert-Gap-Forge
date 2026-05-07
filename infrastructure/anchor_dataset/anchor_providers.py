#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Anchor dataset generation providers."""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod

import httpx
import requests

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.errors import ConfigurationError


class AnchorProvider(ABC):
    """Abstract base class for anchor dataset generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 30.0,
    ) -> AnchorRecord | None:
        """Generate a single anchor record.

        Returns ``None`` on any failure (never raises).
        """


class VLLMProvider(AnchorProvider):
    """Generate anchor records via a vLLM OpenAI-compatible endpoint."""

    DEFAULT_URL = "http://localhost:8000/v1/chat/completions"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    BACKOFF_SECONDS = (1, 2, 4)

    def __init__(
        self,
        vllm_url: str | None = None,
        model: str = "default",
    ) -> None:
        self.vllm_url = vllm_url or self.DEFAULT_URL
        self.model = model

    @property
    def name(self) -> str:
        return "vllm"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 30.0,
    ) -> AnchorRecord | None:
        api_key = os.environ.get("VLLM_API_KEY")
        if api_key is None:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(
                    self.vllm_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                resp.raise_for_status()
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                record_dict = json.loads(content)
                return AnchorRecord.model_validate(record_dict)

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ):
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.BACKOFF_SECONDS[attempt])
                continue

            except Exception:
                return None

        return None


class OpenAIProvider(AnchorProvider):
    """Generate anchor records via OpenAI's API."""

    DEFAULT_MODEL = "gpt-4o"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model

    @property
    def name(self) -> str:
        return "openai"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 30.0,
    ) -> AnchorRecord | None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        }

        with httpx.Client(timeout=timeout) as client:
            for attempt in range(3):
                try:
                    resp = client.post(
                        self.API_URL,
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return AnchorRecord.model_validate(json.loads(content))
                except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError):
                    if attempt < 2:
                        time.sleep(2**attempt)
                    else:
                        return None
        return None


class GeminiProvider(AnchorProvider):
    """Generate anchor records via Google Gemini API."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model

    @property
    def name(self) -> str:
        return "gemini"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 30.0,
    ) -> AnchorRecord | None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None

        try:
            import google.genai as genai
        except ImportError:
            return None

        client = genai.Client(api_key=api_key)

        payload = [
            {"role": "user", "parts": system_prompt},
            {"role": "user", "parts": user_prompt},
        ]

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=payload,
                    config={"response_mime_type": "application/json"},
                    generation_config={"temperature": 0.4},
                )
                return AnchorRecord.model_validate(json.loads(response.text))
            except (genai.errors.APIError, json.JSONDecodeError, ValueError):
                if attempt < 2:
                    time.sleep(2**attempt)
                else:
                    return None
        return None


PROVIDER_MAP = {
    "vllm": VLLMProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(provider_name: str, config=None) -> AnchorProvider:
    """Return an instance of the named provider."""
    cls = PROVIDER_MAP.get(provider_name)
    if cls is None:
        raise ConfigurationError(
            f"Unknown provider: {provider_name}. Available: {list(PROVIDER_MAP.keys())}"
        )
    return cls()
