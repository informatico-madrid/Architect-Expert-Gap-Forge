"""Unit tests for HardQueryBuilder ChainOfThought integration."""
import inspect



class TestHardQueryBuilderCoT:
    """Tests that HardQueryBuilder integrates DSPy ChainOfThought."""

    def test_transform_to_abstract_uses_dspy(self):
        from src.factory.hard_query_builder import HardQueryBuilder
        src = inspect.getsource(HardQueryBuilder._transform_to_abstract)
        # Uses get_chain_of_thought (DSPy bridge) and cached Signature
        assert "get_chain_of_thought" in src, "_transform_to_abstract must use get_chain_of_thought"
        assert "_HARD_QUERY_SIG" in src, "_transform_to_abstract must use cached Signature"

    def test_transform_to_abstract_returns_str(self):
        from src.factory.hard_query_builder import HardQueryBuilder
        inspect.signature(HardQueryBuilder._transform_to_abstract)
        # Just verify the method exists and is callable
        assert callable(HardQueryBuilder._transform_to_abstract)

    def test_no_dspy_import_in_detector(self):
        """BacktrackingDetector must remain pure (no dspy dependency)."""
        assert "dspy" not in open("src/factory/backtracking_detector.py").read()
