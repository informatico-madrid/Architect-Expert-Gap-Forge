#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""
Anchor Dataset — Startup Validation

Pre-flight validation: CLI args, API keys, vLLM health, seed readiness.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from infrastructure.anchor_dataset.config import AnchorsConfig

logger = logging.getLogger(__name__)


class StartupValidator:
    VALID_PROVIDERS = {"vllm", "openai", "gemini"}

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def dry_run(self, config: AnchorsConfig) -> list[str]:
        """Run validation steps without writing or mutating configuration. Returns list of warnings."""
        self.warnings = []
        self._validate_args(config)
        self._validate_api_keys(config)
        self._health_check_vllm(config)
        self._validate_seeds(config)
        return self.warnings

    def validate(self, config: AnchorsConfig) -> None:
        """Run validations, log warnings."""
        self.dry_run(config)
        if self.warnings:
            for w in self.warnings:
                logger.warning("Startup validation: %s", w)

    def _validate_args(self, config: AnchorsConfig) -> None:
        count = getattr(config, "count", 50)
        if not (1 <= count <= 200):
            self.warnings.append(f"Count {count} out of range [1-200]")

        if config.provider not in self.VALID_PROVIDERS:
            self.warnings.append(f"Unknown provider: {config.provider}")

        try:
            json.loads(getattr(config, "domain_distribution", "{}") or "{}")
        except json.JSONDecodeError:
            self.warnings.append("Invalid domain_distribution JSON")

    def _validate_api_keys(self, config: AnchorsConfig) -> None:
        if config.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
            self.warnings.append(
                "OPENAI_API_KEY not set (required for openai provider)"
            )
        elif config.provider == "gemini" and not os.environ.get("GOOGLE_API_KEY"):
            self.warnings.append(
                "GOOGLE_API_KEY not set (required for gemini provider)"
            )
        # vLLM uses fallback auth, no key required

    def _health_check_vllm(self, config: AnchorsConfig) -> None:
        if config.provider != "vllm":
            return
        try:
            url = f"{config.vllm_url}/v1/models"
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                self.warnings.append(f"vLLM health check failed: {resp.status_code}")
        except requests.ConnectionError:
            self.warnings.append(
                "vLLM endpoint unreachable — generation will use fallback"
            )
        except requests.Timeout:
            self.warnings.append("vLLM health check timed out")

    def _validate_seeds(self, config: AnchorsConfig) -> None:
        seed_file = Path("tests/fixtures/seed_examples.yaml")
        if not seed_file.exists():
            self.warnings.append("Seed file missing: tests/fixtures/seed_examples.yaml")
            return
        with open(seed_file) as f:
            content = f.read()
        if "generic_domain" not in content and "other" not in content:
            self.warnings.append(
                "Seed file has no generic_domain/other entries — synthesis will be needed"
            )
