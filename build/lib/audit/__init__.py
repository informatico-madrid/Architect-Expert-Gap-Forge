# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Audit package — high-fidelity exam-based model evaluation pipeline."""

from src.audit.exam_builder import generate_exam_question
from src.audit.gap_generator import generate_gap_analysis
from src.audit.judge import llm_judge_score
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
    NormalizedJudgeResponse,
    PromptGenerationError,
    SampleRecord,
    ScoreCard,
)
from src.audit.scorecard import compute_scorecard
from src.audit.report_writer import generate_report

__all__ = [
    # schema types
    "AuditReport",
    "ExamRecord",
    "InferenceResult",
    "NormalizedJudgeResponse",
    "PromptGenerationError",
    "SampleRecord",
    "ScoreCard",
    # core functions
    "generate_gap_analysis",
    "generate_exam_question",
    "llm_judge_score",
    "compute_scorecard",
    "generate_report",
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
