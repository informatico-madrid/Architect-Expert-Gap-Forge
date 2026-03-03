# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Audit package — high-fidelity exam-based model evaluation pipeline."""

from src.audit.persistence import (
    load_exam,
    load_inference,
    load_persisted_sample,
    persist_exam,
    persist_inference,
    persist_sample,
)
from src.audit.sampling import load_dataset, stratified_sample
from src.audit.schema import (
    AuditReport,
    ExamRecord,
    InferenceResult,
    PromptGenerationError,
    SampleRecord,
    ScoreCard,
)

__all__ = [
    # schema
    "AuditReport",
    "ExamRecord",
    "InferenceResult",
    "PromptGenerationError",
    "SampleRecord",
    "ScoreCard",
    # sampling
    "load_dataset",
    "stratified_sample",
    # persistence
    "load_exam",
    "load_inference",
    "load_persisted_sample",
    "persist_exam",
    "persist_inference",
    "persist_sample",
]
