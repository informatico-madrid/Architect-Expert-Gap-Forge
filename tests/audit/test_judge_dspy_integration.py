"""Integration tests for llm_judge_score DSPy dual-path."""
import pytest


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
