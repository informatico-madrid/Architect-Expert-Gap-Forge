"""Unit tests for CalibrationSignature field types and structure."""
import pytest


class TestCalibrationSignature:
    """Tests for CalibrationSignature defined in src.audit.calibration_signature."""

    def test_input_field_count(self):
        from src.audit.calibration_signature import CalibrationSignature
        assert len(CalibrationSignature.input_fields) == 9

    def test_input_fields_names(self):
        from src.audit.calibration_signature import CalibrationSignature
        expected = {"parameter_target", "evaluation_focus", "question", "temperature",
                    "top_k", "min_p", "quality_target", "judge_scores", "composite_score"}
        assert set(CalibrationSignature.input_fields.keys()) == expected

    def test_output_field_count(self):
        from src.audit.calibration_signature import CalibrationSignature
        assert len(CalibrationSignature.output_fields) == 4

    def test_output_fields_names(self):
        from src.audit.calibration_signature import CalibrationSignature
        expected = {"best_profile_json", "reasoning", "parameter_effectiveness", "composite_score"}
        assert set(CalibrationSignature.output_fields.keys()) == expected

    def test_parameter_target_type(self):
        from src.audit.calibration_signature import CalibrationSignature
        f = CalibrationSignature.input_fields
        assert f["parameter_target"].annotation == list[str]

    def test_docstring_present(self):
        from src.audit.calibration_signature import CalibrationSignature
        assert CalibrationSignature.__doc__ is not None
        assert len(CalibrationSignature.__doc__.strip()) > 50
