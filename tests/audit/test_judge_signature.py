"""Unit tests for JudgeSignature field types and structure."""
import pytest


class TestJudgeSignature:
    """Tests for JudgeSignature defined in src.audit.judge_signature."""

    def test_input_field_count(self):
        from src.audit.judge_signature import JudgeSignature
        assert len(JudgeSignature.input_fields) == 5

    def test_input_fields_names(self):
        from src.audit.judge_signature import JudgeSignature
        expected = {"exam_question", "eval_criteria", "target_patterns",
                    "baseline_response", "adapter_response"}
        assert set(JudgeSignature.input_fields.keys()) == expected

    def test_output_field_count(self):
        from src.audit.judge_signature import JudgeSignature
        assert len(JudgeSignature.output_fields) == 3

    def test_output_fields_names(self):
        from src.audit.judge_signature import JudgeSignature
        expected = {"baseline", "adapter", "reasoning"}
        assert set(JudgeSignature.output_fields.keys()) == expected

    def test_output_field_types(self):
        from src.audit.judge_signature import JudgeSignature
        f = JudgeSignature.output_fields
        assert f["baseline"].annotation == dict[str, float]
        assert f["adapter"].annotation == dict[str, float]
        assert f["reasoning"].annotation == str

    def test_no_architecture_architecture_typo(self):
        from src.audit.judge_signature import JudgeSignature
        assert "Architecture architecture" not in (JudgeSignature.__doc__ or "")
