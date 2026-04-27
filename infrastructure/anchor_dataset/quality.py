#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from dataclasses import dataclass, field
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    score: float = 0.0


class QualityChecker:
    ANTI_LAZINESS_PATTERNS = ["...", "# TODO", "pass # implement", "# resto del codigo"]

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self._tool_call_re = re.compile(r"\[TOOL_CALL:[^\]]*\]")

    def check(self, record: AnchorRecord, target_turns: int) -> QualityResult:
        reasons = []

        # Anti-laziness check
        trajectory = record.expected_trajectory
        for pat in self.ANTI_LAZINESS_PATTERNS:
            if pat in trajectory:
                reasons.append("anti_laziness")
                break

        # Turn count check
        if abs(record.turn_count - target_turns) > 1:
            reasons.append("turn_count_mismatch")

        # Quality score check
        if record.expected_quality_score < self.threshold:
            reasons.append("low_quality_score")

        # Tool call syntax check
        if "[TOOL_CALL:" in trajectory:
            if not self._tool_call_re.search(trajectory):
                reasons.append("tool_call_syntax")

        return QualityResult(
            passed=len(reasons) == 0,
            reasons=reasons,
            score=record.expected_quality_score,
        )

    def check_raw(self, data: dict, target_turns: int) -> QualityResult:
        trajectory = data.get("expected_trajectory", "")
        reasons = []

        for pat in self.ANTI_LAZINESS_PATTERNS:
            if pat in trajectory:
                reasons.append("anti_laziness")
                break

        turn_count = data.get("turn_count", 0)
        if abs(turn_count - target_turns) > 1:
            reasons.append("turn_count_mismatch")

        quality_score = data.get("expected_quality_score", 0.0)
        if quality_score < self.threshold:
            reasons.append("low_quality_score")

        if "[TOOL_CALL:" in trajectory:
            if not self._tool_call_re.search(trajectory):
                reasons.append("tool_call_syntax")

        return QualityResult(
            passed=len(reasons) == 0,
            reasons=reasons,
            score=quality_score,
        )


class CircuitBreaker:
    def __init__(
        self,
        threshold: float = 0.2,
        batch_size: int = 10,
        consecutive_pass_threshold: int = 10,
    ):
        self.threshold = threshold
        self.batch_size = batch_size
        self.consecutive_pass_threshold = consecutive_pass_threshold
        self._results: list[bool] = []
        self._phase: str = "warmup"
        self._consecutive_passes: int = 0
        self._triggered: bool = False

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def triggered(self) -> bool:
        return self._triggered

    def record_result(self, passed: bool) -> None:
        self._results.append(passed)
        if passed:
            self._consecutive_passes += 1
        else:
            self._consecutive_passes = 0
        self._transition_phase()

    def _transition_phase(self) -> None:
        n = len(self._results)
        if n < 5:
            self._phase = "warmup"
        elif n < 10:
            self._phase = "calibration"
        else:
            self._phase = "production"

    def should_switch(self) -> bool:
        if self._phase != "production":
            return False
        if len(self._results) < self.batch_size:
            return False
        # Check last batch_size results
        recent = self._results[-self.batch_size :]
        failures = sum(1 for r in recent if not r)
        failure_rate = failures / len(recent)
        if failure_rate >= self.threshold:
            self._triggered = True
            return True
        return False

    def try_reset(self) -> bool:
        if not self._triggered:
            return False
        if self._consecutive_passes >= self.consecutive_pass_threshold:
            self._triggered = False
            self._results.clear()
            self._consecutive_passes = 0
            self._phase = "warmup"
            return True
        return False

    def get_failure_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if not r) / len(self._results)

    def _evaluate_batch(self, batch: list[bool]) -> bool:
        """Evaluate a batch of results; return True if failure rate >= threshold."""
        if not batch:
            return False
        failures = sum(1 for r in batch if not r)
        return (failures / len(batch)) >= self.threshold
