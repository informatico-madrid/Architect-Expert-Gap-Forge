#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Pytest configuration and fixtures for AEGF tests.

This module provides shared fixtures and configuration for all tests.
DO NOT REMOVE - used by pipeline and CI/CD
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.audit.schema import ExamRecord, SampleRecord, ScoreCard

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(filename: str) -> dict[str, Any]:
    """Load a JSON fixture file."""
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def tmp_repo_path() -> Path:
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()
        owner_dir = repo_path / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)
        yield repo_path


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code for testing."""
    return """
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b

def calculate_total(items: list) -> float:
    '''Calculate total price from items.'''
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
"""


@pytest.fixture
def sample_typescript_code() -> str:
    """Sample TypeScript code for testing."""
    return """
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';

  render() {
    return html`<button>${this.label}</button>`;
  }
}
"""


@pytest.fixture
def sample_php_code() -> str:
    """Sample PHP code for testing."""
    return """<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }
}
"""


@pytest.fixture
def sample_yaml_code() -> str:
    """Sample YAML code for testing."""
    return """
# Home Assistant automation
automation:
  - alias: "Light Control"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.toggle
"""


@pytest.fixture
def sample_record():
    """Create a sample SampleRecord for testing."""
    from src.audit.schema import SampleRecord

    return SampleRecord(
        id="test-sample-1",
        example_type="nominal",
        evol_difficulty="easy",
        fragment_name="test.py",
        source_file="test.py",
        user_prompt="test",
        reference_response="test",
        gold_injected=False,
        ldi=0.85,
    )


@pytest.fixture
def golden_sample() -> SampleRecord:
    """Load a golden SampleRecord from fixture.

    Used by tests/test_model_evaluator_error_cases.py and
    tests/test_model_evaluator_integration_paths.py.
    """
    data = _load_fixture("sample_record.json")
    return SampleRecord(
        id=data["id"],
        example_type=data["example_type"],
        evol_difficulty=data["evol_difficulty"],
        fragment_name=data["fragment_name"],
        source_file=data["source_file"],
        user_prompt=data["user_prompt"],
        reference_response=data["reference_response"],
        gold_injected=data["gold_injected"],
        ldi=data["ldi"],
        reference_standards=data["reference_standards"],
        gap_analysis=data["gap_analysis"],
    )


@pytest.fixture
def golden_exam(golden_sample: SampleRecord) -> ExamRecord:
    """Load a golden ExamRecord from fixture."""
    data = _load_fixture("exam_record.json")
    return ExamRecord.from_sample(
        golden_sample,
        exam_question=data["exam_question"],
        eval_criteria=data["eval_criteria"],
        target_patterns=data["target_patterns"],
    )


@pytest.fixture
def manifest_json() -> str:
    """Sample manifest.json for HA integrations."""
    return '{"name": "Test Integration", "domain": "test"}'


@pytest.fixture
def gap_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory (alias for gap_dir)."""
    return Path(__file__).parent / "fixtures"


# Legacy fixtures for backward compatibility
def make_exam_record(
    sample: SampleRecord | None = None,
    sample_id: str = "test-sample-1",
    exam_question: str = "Test exam question",
    eval_criteria: list[str] | None = None,
    target_patterns: list[str] | None = None,
    example_type: str = "nominal",
    evol_difficulty: str = "easy",
    fragment_name: str = "test.py",
    source_file: str = "test.py",
    user_prompt: str = "test",
    reference_response: str = "test",
    gold_injected: bool = False,
    ldi: float = 0.85,
    reference_standards: str = "",
    gap_analysis: str = "",
) -> ExamRecord:
    """Create a sample ExamRecord for testing.

    Can be called in two ways:
    1. With a SampleRecord: make_exam_record(sample=some_sample)
    2. With explicit fields: make_exam_record(sample_id="x", ...)

    Args:
        sample: Optional SampleRecord to elevate to ExamRecord.
        sample_id: Sample record ID (used if sample not provided).
        exam_question: Generated exam question.
        eval_criteria: Evaluation criteria list.
        target_patterns: Target patterns list.
        example_type: Type of example.
        evol_difficulty: Difficulty level.
        fragment_name: Fragment name.
        source_file: Source file path.
        user_prompt: User prompt.
        reference_response: Reference response.
        gold_injected: Whether gold was injected.
        ldi: LDI score.
        reference_standards: Reference standards.
        gap_analysis: Gap analysis.

    Returns:
        A new ExamRecord instance.
    """
    if eval_criteria is None:
        eval_criteria = []
    if target_patterns is None:
        target_patterns = []

    # If sample is provided, elevate it to ExamRecord
    if sample is not None:
        return ExamRecord.from_sample(sample, exam_question=exam_question)

    # Otherwise, construct from fields
    return ExamRecord(
        id=sample_id,
        exam_question=exam_question,
        eval_criteria=eval_criteria,
        target_patterns=target_patterns,
        example_type=example_type,
        evol_difficulty=evol_difficulty,
        fragment_name=fragment_name,
        source_file=source_file,
        user_prompt=user_prompt,
        reference_response=reference_response,
        gold_injected=gold_injected,
        ldi=ldi,
        reference_standards=reference_standards,
        gap_analysis=gap_analysis,
    )


def make_sample(
    id: str = "test-sample-1",
    example_type: str = "nominal",
    evol_difficulty: str = "easy",
    fragment_name: str = "test.py",
    source_file: str = "test.py",
    user_prompt: str = "test",
    reference_response: str = "test",
    gold_injected: bool = False,
    ldi: float = 0.85,
    reference_standards: str = "",
    gap_analysis: str = "",
) -> SampleRecord:
    """Create a sample SampleRecord for testing.

    Args:
        id: Sample record ID.
        example_type: Type of example.
        evol_difficulty: Difficulty level.
        fragment_name: Fragment name.
        source_file: Source file path.
        user_prompt: User prompt.
        reference_response: Reference response.
        gold_injected: Whether gold was injected.
        ldi: LDI score.
        reference_standards: Reference standards.
        gap_analysis: Gap analysis.

    Returns:
        A new SampleRecord instance.
    """
    return SampleRecord(
        id=id,
        example_type=example_type,
        evol_difficulty=evol_difficulty,
        fragment_name=fragment_name,
        source_file=source_file,
        user_prompt=user_prompt,
        reference_response=reference_response,
        gold_injected=gold_injected,
        ldi=ldi,
        reference_standards=reference_standards,
        gap_analysis=gap_analysis,
    )


def make_scorecard(
    record_id: str = "test-sample-1",
    example_type: str = "nominal",
    fragment_name: str = "test.py",
    sample_id: str = "test-sample-1",
    ha_modernity: float = 0.85,
    reasoning_depth: float = 0.85,
    functionality: float = 0.85,
    completeness: float = 0.85,
    style: float = 0.85,
    judge_reasoning: str = "",
    notes: str = "",
) -> ScoreCard:
    """Create a sample ScoreCard for testing.

    Args:
        record_id: Record ID.
        example_type: Example type.
        fragment_name: Fragment name.
        sample_id: Sample ID (alias for record_id).
        ha_modernity: HA modernity score.
        reasoning_depth: Reasoning depth score.
        functionality: Functionality score.
        completeness: Completeness score.
        style: Style score.
        judge_reasoning: Judge reasoning text.
        notes: Notes text.

    Returns:
        A new ScoreCard instance.
    """
    return ScoreCard(
        record_id=record_id,
        example_type=example_type,
        fragment_name=fragment_name,
        sample_id=sample_id,
        ha_modernity=ha_modernity,
        reasoning_depth=reasoning_depth,
        functionality=functionality,
        completeness=completeness,
        style=style,
        judge_reasoning=judge_reasoning,
        notes=notes,
    )


@pytest.fixture
def scorecard() -> ScoreCard:
    """Create a sample ScoreCard for testing."""
    return make_scorecard()


@pytest.fixture
def audit_report() -> ScoreCard:
    """Create a sample ScoreCard for testing (named audit_report for schema tests)."""
    from src.audit.schema import AuditReport

    return AuditReport()


@pytest.fixture
def prompts_yaml_path() -> Path:
    """Path to prompt configuration file for testing."""
    return Path(__file__).parent / "fixtures" / "prompts" / "prompt_manager.yaml"


@pytest.fixture
def raw_records(tmp_path: Path) -> list[dict[str, Any]]:
    """Create sample raw records for testing."""
    records: list[dict[str, Any]] = []
    example_types = ["nominal", "contrast", "error_recovery", "theory"]
    for i, et in enumerate(example_types):
        # Create multiple records per type to allow for proper sampling tests
        for j in range(3):
            records.append(
                {
                    "id": f"{et}-{i}-{j}",
                    "metadata": {
                        "example_type": et,
                        "evol_difficulty": "medium",
                        "fragment_name": f"frag_{i}_{j}",
                        "source_file": f"components/{et}/{i}_{j}.py",
                        "gold_injected": True,
                        "ldi": 0.7 + i * 0.01 + j * 0.001,
                        "reference_standards": "Use entry.runtime_data.",
                        "gap_analysis": "Legacy pattern detected.",
                    },
                    "conversation": [
                        {
                            "role": "user",
                            "content": f"Implement {et} component {i} variant {j}.",
                        },
                        {
                            "role": "assistant",
                            "content": "<think>OK</think>\n```python\npass\n```",
                        },
                    ],
                }
            )
    return records
