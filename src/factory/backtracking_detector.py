# SPDX-License-Identifier: Apache-2.0
"""Backtracking detector — pure utility module (no external AI framework imports).

Detects ERROR->CORRECT patterns in agentic trajectories to identify
backtracking behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.factory.schema import Message, Turn, TurnType


@dataclass(frozen=True)
class BacktrackingResult:
    """Result of backtracking detection."""

    detected: bool
    indices: list[int]  # [error_turn_index, correct_turn_index]
    reason: str  # "error_recovery", "none", "no_turns"


class BacktrackingDetector:
    """Detect backtracking (ERROR->CORRECT) patterns in trajectories."""

    @staticmethod
    def detect(turns: list[Turn]) -> BacktrackingResult:
        """Detect ERROR->CORRECT patterns in a list of turns.

        Returns:
            BacktrackingResult with detected flag, indices, and reason.
        """
        if not turns:
            return BacktrackingResult(detected=False, indices=[], reason="no_turns")

        for i in range(len(turns) - 1):
            if (
                turns[i].turn_type == TurnType.ERROR
                and turns[i + 1].turn_type == TurnType.CORRECT
            ):
                return BacktrackingResult(
                    detected=True,
                    indices=[turns[i].turn_index, turns[i + 1].turn_index],
                    reason="error_recovery",
                )

        return BacktrackingResult(detected=False, indices=[], reason="none")

    @staticmethod
    def detect_from_messages(messages: list[Message]) -> BacktrackingResult:
        """Detect backtracking from message content.

        Scans message content for error->correction patterns.
        """
        if not messages:
            return BacktrackingResult(detected=False, indices=[], reason="no_turns")

        # Look for error/correction patterns in message content
        for i in range(len(messages) - 1):
            content_lower = messages[i].content.lower()
            if "error" in content_lower or "fail" in content_lower:
                next_content_lower = messages[i + 1].content.lower()
                if (
                    "correct" in next_content_lower
                    or "fix" in next_content_lower
                    or "recovery" in next_content_lower
                ):
                    return BacktrackingResult(
                        detected=True,
                        indices=[i, i + 1],
                        reason="error_recovery",
                    )

        return BacktrackingResult(detected=False, indices=[], reason="none")
