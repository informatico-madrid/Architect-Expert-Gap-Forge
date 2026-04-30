#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Schemas package: canonical type definitions for the codebase.

Expose common TypedDicts used across the repo. Keep this file small
so callers can import from `src.schemas`.
"""

from .common import (
    RawRecord,
    MetadataDict,
    ConversationMessage,
    ChatMessage,
    ThinkStats,
    InferencePayload,
    NormalizedJudgeResponse,
    BundleTypedDict,
    CurationRecord,
)

__all__ = [
    "RawRecord",
    "MetadataDict",
    "ConversationMessage",
    "ChatMessage",
    "ThinkStats",
    "InferencePayload",
    "NormalizedJudgeResponse",
    "BundleTypedDict",
    "CurationRecord",
]
