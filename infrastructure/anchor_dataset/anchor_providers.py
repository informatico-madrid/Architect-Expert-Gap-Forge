#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Anchor dataset generation providers."""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod

import requests

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord


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
        api_key = os.environ.get("VLLM_API_KEY") or "sk-master-bunker-2026"

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
