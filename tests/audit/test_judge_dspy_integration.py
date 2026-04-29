#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch


class TestLlmJudgeScoreDSPy:
    """Tests for llm_judge_score with DSPy enabled."""

    def test_get_predict_returns_none_without_lm(self):
        """Without LM configured, get_predict returns None (template path)."""
        from src.factory.dspy_utils import get_predict
        from src.audit.judge_signature import JudgeSignature

        assert get_predict(JudgeSignature) is None

    def test_dual_path_fallback(self):
        """When predictor is None, template path is used."""
        from src.factory.dspy_utils import get_predict
        from src.audit.judge_signature import JudgeSignature

        assert get_predict(JudgeSignature) is None
        # This means llm_judge_score() will use the template fallback path

    def test_llm_judge_score_with_stubbed_dspy_predictor(self):
        """Stub get_predict to return a predictor with shaped JSON, verify output.

        This verifies F-11: the DSPy path in llm_judge_score() correctly parses
        predictor output into NormalizedJudgeResponse structure.
        """
        from src.audit.judge import llm_judge_score

        # Create a mock predictor that returns shaped JSON like a real DSPy Predict would
        mock_predictor_result = Mock()
        mock_predictor_result.baseline = json.dumps(
            {"ha_modernity": 0.8, "reasoning_depth": 0.9, "functionality": 0.85}
        )
        mock_predictor_result.adapter = json.dumps(
            {"ha_modernity": 0.85, "reasoning_depth": 0.88, "functionality": 0.92}
        )
        mock_predictor_result.reasoning = "Strong reasoning with modern approach"

        # Patch at the location where get_predict is imported (judge.py)
        with patch("src.audit.judge.get_predict") as mock_get_predict:
            mock_get_predict.return_value = Mock(return_value=mock_predictor_result)

            exam = SimpleNamespace(
                id="test-1",
                user_prompt="Test question",
                exam_question="Describe architecture patterns",
                eval_criteria=["Modernity", "Reasoning", "Functionality"],
                target_patterns=["async setup", "coordinator"],
            )

            result = llm_judge_score(
                exam=exam,
                baseline_resp="Baseline response",
                adapter_resp="Adapter response",
                judge_model="test-model",
                api_url="http://localhost:8000",
            )

            # Verify output is NormalizedJudgeResponse TypedDict structure
            assert isinstance(result, dict)
            assert "baseline" in result
            assert "adapter" in result
            assert "reasoning" in result

            # Verify parsed types
            assert isinstance(result["baseline"], dict)
            assert isinstance(result["adapter"], dict)
            assert isinstance(result["reasoning"], str)

            # Verify parsed values match stubbed input
            assert result["baseline"]["ha_modernity"] == 0.8
            assert result["adapter"]["ha_modernity"] == 0.85
            assert result["reasoning"] == "Strong reasoning with modern approach"

    def test_llm_judge_score_with_dict_outputs_not_json_strings(self):
        """Test DSPy path handles dict outputs (not JSON strings).

        Some DSPy configurations return parsed dicts directly.
        """
        from src.audit.judge import llm_judge_score

        mock_predictor_result = Mock()
        mock_predictor_result.baseline = {
            "ha_modernity": 0.7,
            "reasoning_depth": 0.8,
        }
        mock_predictor_result.adapter = {
            "ha_modernity": 0.75,
            "reasoning_depth": 0.82,
        }
        mock_predictor_result.reasoning = "Good analysis"

        # Patch at the location where get_predict is imported (judge.py)
        with patch("src.audit.judge.get_predict") as mock_get_predict:
            mock_get_predict.return_value = Mock(return_value=mock_predictor_result)

            exam = SimpleNamespace(
                id="test-2",
                user_prompt="Test",
                exam_question="Question",
                eval_criteria=["Modernity"],
                target_patterns=[],
            )

            result = llm_judge_score(
                exam=exam,
                baseline_resp="Baseline",
                adapter_resp="Adapter",
                judge_model="test-model",
                api_url="http://localhost:8000",
            )

            assert result["baseline"]["ha_modernity"] == 0.7
            assert result["adapter"]["ha_modernity"] == 0.75
            assert result["reasoning"] == "Good analysis"
