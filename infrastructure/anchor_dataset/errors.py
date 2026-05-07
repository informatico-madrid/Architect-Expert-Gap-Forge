#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""
Anchor Dataset — Exception Hierarchy

Anchor dataset exception classes. Base error plus domain-specific subclasses.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""


class AnchorDatasetError(RuntimeError):
    """Base error for all anchor dataset failures.

    All anchor dataset exceptions inherit from this class,
    allowing callers to catch any anchor dataset problem with a single handler.
    """

    pass


class ValidationError(AnchorDatasetError):
    """Raised when anchor dataset validation fails.

    Used for missing required fields, invalid record structure,
    schema mismatches, or when data does not meet quality thresholds.
    """

    pass


class ProviderError(AnchorDatasetError):
    """Raised when a data provider operation fails.

    Used for upstream service failures (API errors, timeouts, rate limits),
    authentication problems, and when provider data is unavailable.
    """

    pass


class SerializationError(AnchorDatasetError):
    """Raised when serialization or deserialization fails.

    Used for JSON/parquet read/write errors, encoding issues,
    and when converting between internal and external formats.
    """

    pass


class ConfigurationError(AnchorDatasetError):
    """Raised when anchor dataset configuration is invalid.

    Used for missing config keys, invalid parameter values,
    conflicting settings, or unavailable external dependencies.
    """

    pass


class SeedError(AnchorDatasetError):
    """Raised when seeding operations fail.

    Used for seed computation errors, missing seed data,
    or when the seed source is unreachable or corrupted.
    """

    pass


class CheckpointError(AnchorDatasetError):
    """Raised when checkpoint operations fail.

    Used for checkpoint read/write errors, corruption detection,
    or atomic write failures during checkpoint persistence.
    """

    pass
