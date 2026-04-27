"""Unit tests for TrajectorySignature field types and structure."""
import pytest


class TestTrajectorySignature:
    """Tests for TrajectorySignature defined in src.factory.trajectory_signature."""

    def test_input_field_count(self):
        from src.factory.trajectory_signature import TrajectorySignature
        assert len(TrajectorySignature.input_fields) == 9

    def test_input_fields_names(self):
        from src.factory.trajectory_signature import TrajectorySignature
        expected = {"seed_id", "mode", "use_case", "question", "context",
                    "error_probability", "has_error", "is_cascade", "tool_format"}
        assert set(TrajectorySignature.input_fields.keys()) == expected

    def test_output_field_count(self):
        from src.factory.trajectory_signature import TrajectorySignature
        assert len(TrajectorySignature.output_fields) == 4

    def test_output_fields_names(self):
        from src.factory.trajectory_signature import TrajectorySignature
        expected = {"turns_json", "errors_json", "messages_json", "inferred_use_case"}
        assert set(TrajectorySignature.output_fields.keys()) == expected

    def test_output_field_types(self):
        from src.factory.trajectory_signature import TrajectorySignature
        f = TrajectorySignature.output_fields
        assert f["turns_json"].annotation == str
        assert f["errors_json"].annotation == str
        assert f["messages_json"].annotation == str
        assert f["inferred_use_case"].annotation == str

    def test_input_field_types(self):
        from src.factory.trajectory_signature import TrajectorySignature
        f = TrajectorySignature.input_fields
        assert f["seed_id"].annotation == str
        assert f["mode"].annotation == str
        assert f["use_case"].annotation == str
        assert f["question"].annotation == str
        assert f["context"].annotation == str
        assert f["error_probability"].annotation == float
        assert f["has_error"].annotation == bool
        assert f["is_cascade"].annotation == bool
        assert f["tool_format"].annotation == str

    def test_docstring_present(self):
        from src.factory.trajectory_signature import TrajectorySignature
        assert TrajectorySignature.__doc__ is not None
        assert len(TrajectorySignature.__doc__.strip()) > 50
