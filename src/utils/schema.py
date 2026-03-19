#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Shared Schema Definitions

Shared entities used across Factory and Curation modules.
Provides immutable Pydantic v2 models for dataset records and composition reports.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict as TypedDictExtended


class Message(BaseModel):
    """Single message in a conversation."""

    model_config = {"frozen": True}

    role: str = Field(description="Role: system, user, assistant, or tool")
    content: str = Field(description="Message content")


class RecordMetadata(TypedDictExtended, total=False):
    """Metadata for a dataset record."""

    origin: NotRequired[str]
    type: NotRequired[str]
    use_case: NotRequired[str]
    token_count: NotRequired[int]
    format: NotRequired[str]
    seed_id: NotRequired[str]


class DatasetRecord(BaseModel):
    """A dataset record with messages and metadata."""

    model_config = {"frozen": True}

    messages: list[Message] = Field(default_factory=list, description="Conversation messages")
    metadata: RecordMetadata = Field(
        default_factory=dict, description="Record metadata"
    )


class CompositionReport(BaseModel):
    """Report on dataset composition after mixing."""

    model_config = {"frozen": True}

    records_by_origin: dict[str, int] = Field(
        default_factory=dict, description="Record counts by origin"
    )
    token_pct_by_origin: dict[str, float] = Field(
        default_factory=dict, description="Token percentages by origin"
    )
    type_distribution: dict[str, int] = Field(
        default_factory=dict, description="Distribution by record type"
    )
    discarded_count: int = Field(default=0, description="Number of discarded records")
    discarded_reasons: dict[str, int] = Field(
        default_factory=dict, description="Reasons for discards"
    )
