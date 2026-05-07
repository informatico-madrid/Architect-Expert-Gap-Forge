#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Typed schema definitions for canonical payloads.

Prefer `TypedDict(total=False)` for external/dynamic payloads and use
these types as the contract for conversion helpers. Keep keys permissive
where fields are optional to avoid breaking legacy dicts during migration.
"""

from __future__ import annotations

from typing import TypedDict, NotRequired, Any, Dict, List


class MetadataDict(TypedDict, total=False):
    example_type: str
    evol_difficulty: str
    fragment_name: str
    source_file: str
    gold_injected: bool
    ldi: float
    reference_standards: str
    gap_analysis: str
    curation: Dict[str, Any]


class ConversationMessage(TypedDict, total=False):
    role: str
    content: str
    sender: NotRequired[str]
    value: NotRequired[str]


class RawRecord(TypedDict, total=False):
    id: str
    metadata: MetadataDict
    conversation: List[ConversationMessage]
    other: Dict[str, Any]


class ThinkStats(TypedDict, total=False):
    original_chars: int
    distilled_chars: int
    reduction_pct: float
    strategies: List[str]


class ChatMessage(ConversationMessage):
    pass


class InferencePayload(TypedDict, total=False):
    model: str
    messages: List[ChatMessage]
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    top_k: NotRequired[int]
    min_p: NotRequired[float]
    repetition_penalty: NotRequired[float]
    presence_penalty: NotRequired[float]
    response_format: NotRequired[Dict[str, Any]]


class NormalizedJudgeResponse(TypedDict, total=False):
    adapter: Dict[str, float]
    baseline: Dict[str, float]
    reasoning: NotRequired[str]


class BundleTypedDict(TypedDict, total=False):
    entity_id: str
    context: str
    type: str
    arch: Dict[str, str]
    files: Dict[str, str]
    fragment_name: str
    fragment_skeleton: str
    fragment_original: str
    fragment_context: str


class FragmentTypedDict(TypedDict, total=False):
    """TypedDict describing a code fragment / bundle used by factory pipelines.

    Use `total=False` to remain tolerant to additional fields present in
    upstream harvested fragments. Keys here cover the minimal set used by
    `production_v11.py` prompt builders and related utilities.
    """

    id: NotRequired[str]
    name: NotRequired[str]
    virtual_filename: NotRequired[str]
    context: NotRequired[str]
    skeleton: NotRequired[str]
    original: NotRequired[str]
    source_file: NotRequired[str]
    fragment_name: NotRequired[str]
    metadata: NotRequired[Dict[str, Any]]


class CurationRecord(TypedDict, total=False):
    record: RawRecord
    metadata: MetadataDict
    _text: str
    _qs: float
    reports: Dict[str, Any]


__all__ = [
    "RawRecord",
    "MetadataDict",
    "ConversationMessage",
    "ChatMessage",
    "ThinkStats",
    "InferencePayload",
    "NormalizedJudgeResponse",
    "BundleTypedDict",
    "FragmentTypedDict",
    "CurationRecord",
]
