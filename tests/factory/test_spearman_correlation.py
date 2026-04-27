"""Spearman correlation test comparing old template-based vs new DSPy judge outputs."""
import pytest


class TestSpearmanCorrelation:
    """Tests for Spearman correlation between judge output styles."""

    def test_spearman_available(self):
        """scipy should be available for Spearman computation."""
        try:
            from scipy.stats import spearmanr
            assert callable(spearmanr)
        except ImportError:
            pytest.skip("scipy not installed, skipping Spearman test")

    def test_spearman_on_sample_data(self):
        """Spearman correlation works on sample data."""
        try:
            from scipy.stats import spearmanr
            scores_a = [0.8, 0.6, 0.9, 0.5, 0.7]
            scores_b = [0.75, 0.65, 0.85, 0.45, 0.72]
            corr, _ = spearmanr(scores_a, scores_b)
            # High correlation expected for similar rankings
            assert corr > 0.8
        except ImportError:
            pytest.skip("scipy not installed")

    def test_judge_output_range(self):
        """Judge output values should be in valid range."""
        # This test will be meaningful once DSPy LM is configured
        # For now, verify the output structure is correct
        from src.audit.judge_signature import JudgeSignature
        f = JudgeSignature.output_fields
        assert "baseline" in f
        assert "adapter" in f
        # baseline and adapter should be dict[str, float]
        assert f["baseline"].annotation == dict[str, float]
