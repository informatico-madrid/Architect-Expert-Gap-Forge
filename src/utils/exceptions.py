#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Shared Exceptions

Shared exception classes used across Factory, Curation, and Training modules.
Provides clear, specific error types for different failure modes.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails.

    Used for validating configuration files, environment variables,
    and training hyperparameters (e.g., NEFTune alpha range).
    """

    pass


class NormalizationError(ValueError):
    """Raised when data format normalization fails.

    Used when converting between formats (Alpaca, ShareGPT, ChatML)
    fails due to missing required fields or invalid structure.
    """

    pass


class CheckpointError(IOError):
    """Raised when checkpoint read/write operations fail.

    Used for disk I/O errors during checkpoint persistence,
    corruption detection, or atomic write failures.
    """

    pass


class DeduplicationError(ValueError):
    """Raised when deduplication logic encounters an error.

    Used for hash computation failures, duplicate detection
    errors, or when duplicate removal would result in data loss.
    """

    pass


class TeacherAPIError(RuntimeError):
    """Raised when the Teacher model API call fails.

    Used for API errors (rate limits, timeouts, server errors),
    authentication failures, and when max retries are exhausted.
    """

    pass
