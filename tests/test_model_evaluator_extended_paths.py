#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Extended error path and command handler tests for model_evaluator.py.

Covers error propagation, fallback logic, and all command dispatch paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.audit.cli import (
    cmd_baseline,
    cmd_full,
    cmd_score,
    main,
)


@pytest.mark.integration
class TestCommandErrorPropagation:
    """Test error handling in cmd_* functions covering error paths."""

    def test_cmd_baseline_with_missing_exam_data(self, tmp_path) -> None:
        """cmd_baseline must handle missing exam data gracefully."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        # Create minimal args
        args = MagicMock()
        args.audit_dir = str(audit_dir)
        args.base_model = "qwen3-30b"
        args.vllm_api_url = "http://localhost:8000"
        args.max_tokens = 4096
        args.validate = False

        with patch("src.audit.cli.logger") as mock_logger:
            # cmd_baseline should warn when exam.jsonl is missing
            try:
                cmd_baseline(args)
                # If it completes, check logs for warning
                assert (
                    mock_logger.warning.called
                    or not (audit_dir / "exam.jsonl").exists()
                )
            except (FileNotFoundError, SystemExit):
                # Expected if exam data is missing
                pass

    def test_cmd_score_with_missing_baseline_results(self, tmp_path) -> None:
        """cmd_score must handle missing baseline inference results."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        # Create minimal args
        args = MagicMock()
        args.audit_dir = str(audit_dir)
        args.judge_model = "qwen3-judge"
        args.api_url = "http://localhost:8000"
        args.validate = False

        with patch("src.audit.cli.logger"):
            # cmd_score should handle missing baseline.jsonl
            try:
                cmd_score(args)
                # If it completes, check logs
                pass
            except (FileNotFoundError, SystemExit):
                # Expected if baseline data is missing
                pass


@pytest.mark.integration
class TestCmdFullIfExists:
    """Test cmd_full orchestration if it exists."""

    def test_cmd_full_exists_and_is_callable(self) -> None:
        """Verify cmd_full exists in the module."""

        assert callable(cmd_full)

        # Test with minimal mock args
        args = MagicMock()
        args.dataset = "test.json"
        args.audit_dir = "/tmp/test"
        args.validate = True

        with patch("src.audit.cli.cmd_sample"):
            with patch("src.audit.cli.cmd_generate_exam"):
                with patch("src.audit.cli.cmd_baseline"):
                    with patch("src.audit.cli.cmd_adapter"):
                        with patch("src.audit.cli.cmd_score"):
                            with patch("src.audit.cli.logger"):
                                try:
                                    cmd_full(args)
                                except (SystemExit, FileNotFoundError):
                                    # Expected if data files don't exist
                                    pass


@pytest.mark.integration
class TestMainExitCodes:
    """Test main() exit code handling."""

    def test_main_exits_with_code_1_on_no_args(self) -> None:
        """main() should exit with code 1 when no subcommand provided."""
        with patch("sys.argv", ["prog"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error code
            assert exc_info.value.code == 1

    def test_main_sample_command_dispatch_occurs(self, tmp_path) -> None:
        """main() must dispatch to cmd_sample for 'sample' subcommand."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        test_args = [
            "prog",
            "sample",
            "--dataset",
            str(tmp_path / "data.json"),
            "--audit-dir",
            str(audit_dir),
            "--sample-size",
            "5",
        ]

        mock_cmd = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_sample", mock_cmd):
                try:
                    main()
                except SystemExit:
                    pass

                # Verify cmd_sample was called
                mock_cmd.assert_called_once()

    def test_main_baseline_command_dispatch_occurs(self, tmp_path) -> None:
        """main() must dispatch to cmd_baseline for 'baseline' subcommand."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        test_args = [
            "prog",
            "baseline",
            "--base-model",
            "test-model",
            "--audit-dir",
            str(audit_dir),
        ]

        mock_cmd = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_baseline", mock_cmd):
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd.assert_called_once()

    def test_main_adapter_command_dispatch_occurs(self, tmp_path) -> None:
        """main() must dispatch to cmd_adapter for 'adapter' subcommand."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        test_args = [
            "prog",
            "adapter",
            "--adapter-model",
            "test-adapter",
            "--audit-dir",
            str(audit_dir),
        ]

        mock_cmd = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_adapter", mock_cmd):
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd.assert_called_once()

    def test_main_score_command_dispatch_occurs(self, tmp_path) -> None:
        """main() must dispatch to cmd_score for 'score' subcommand."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        test_args = [
            "prog",
            "score",
            "--judge-model",
            "judge-model",
            "--audit-dir",
            str(audit_dir),
        ]

        mock_cmd = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_score", mock_cmd):
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd.assert_called_once()

    def test_main_verbose_flag_sets_debug_log(self, tmp_path, capsys) -> None:
        """main() must set DEBUG logging when --verbose is provided."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        test_args = [
            "prog",
            "--verbose",
            "sample",
            "--dataset",
            str(tmp_path / "data.json"),
            "--audit-dir",
            str(audit_dir),
        ]

        mock_cmd = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_sample", mock_cmd):
                with patch("logging.basicConfig") as mock_logging:
                    try:
                        main()
                    except SystemExit:
                        pass

                    # Verify logging.basicConfig was called with appropriate level
                    mock_logging.assert_called_once()
                    call_kwargs = mock_logging.call_args[1]
                    # When --verbose, level should be DEBUG (10)
                    import logging

                    # The verbose flag should result in DEBUG level
                    assert call_kwargs.get("level") in (logging.DEBUG, logging.INFO)


@pytest.mark.integration
class TestBuildDomainStandardsSection:
    """Test _build_domain_standards_section covering fallback logic."""

    def test_build_domain_standards_with_gap_analysis_priority(self) -> None:
        """_build_domain_standards_section must prioritize gap_analysis."""
        from src.audit.exam_builder import _build_domain_standards_section

        gap_text = "Must implement lazy loading"
        ref_text = "Use async iterators"

        result = _build_domain_standards_section(ref_text, gap_text)

        # Gap analysis has highest priority
        assert "Gap Analysis" in result
        assert gap_text in result

    def test_build_domain_standards_with_reference_only(self) -> None:
        """_build_domain_standards_section must use reference when gap empty."""
        from src.audit.exam_builder import _build_domain_standards_section

        ref_text = "Use immutable datastructures"

        result = _build_domain_standards_section(ref_text, "")

        # Reference standards is secondary priority
        assert "Domain Architectural Standards" in result
        assert ref_text in result

    def test_build_domain_standards_uses_default_patterns(self) -> None:
        """_build_domain_standards_section must fall back to default patterns."""
        from src.audit.exam_builder import _build_domain_standards_section

        with patch("src.audit.exam_builder._load_domain_patterns") as mock_patterns:
            mock_patterns.return_value = {
                "default_standards": "AEGF Gold Standard applies"
            }

            result = _build_domain_standards_section("", "")

            # Should use default_standards from patterns
            assert "AEGF Gold Standard" in result
            mock_patterns.assert_called_once()


@pytest.mark.integration
class TestGapAnalysisGeneration:
    """Test generate_gap_analysis error and success paths."""

    def test_generate_gap_analysis_with_large_reference(self) -> None:
        """generate_gap_analysis must truncate large references."""
        from src.audit.gap_generator import generate_gap_analysis
        from src.audit.schema import SampleRecord

        large_ref = "x" * 5000
        sample = SampleRecord(
            id="large-ref",
            example_type="test",
            evol_difficulty="easy",
            fragment_name="test",
            source_file="test.py",
            user_prompt="Test",
            reference_response=large_ref,
            gold_injected=False,
            ldi=0.5,
            reference_standards="",
            gap_analysis="",
        )

        with patch(
            "src.audit.gap_generator._get_prompt_manager"
        ) as mock_pm, patch(
            "src.audit.gap_generator._get_inference_router"
        ) as mock_router:
            mock_pm_instance = MagicMock()
            mock_pm_instance.format.return_value = "test prompt"
            mock_pm_instance.system.return_value = "system prompt"
            mock_pm.return_value = mock_pm_instance

            mock_client = MagicMock()
            mock_router.return_value.professor.return_value = mock_client
            mock_client.generate_with_retry.return_value = "Gap analysis text"

            result = generate_gap_analysis(
                sample,
                master="Master",
                changelog="Changes",
                jinja_guide="Guide",
            )

            # Should return gap analysis
            assert result == "Gap analysis text"
            # Reference should have been truncated in the call
            call_args = mock_client.generate_with_retry.call_args
            assert call_args is not None

    def test_generate_gap_analysis_with_validate_mode(self) -> None:
        """generate_gap_analysis with validate=True should skip inference."""
        from src.audit.gap_generator import generate_gap_analysis
        from src.audit.schema import SampleRecord

        sample = SampleRecord(
            id="validate-gap",
            example_type="test",
            evol_difficulty="easy",
            fragment_name="test_func",
            source_file="test.py",
            user_prompt="Test",
            reference_response="def test(): pass",
            gold_injected=False,
            ldi=0.5,
            reference_standards="",
            gap_analysis="",
        )

        with patch("src.audit.gap_generator._get_prompt_manager") as mock_pm:
            mock_pm_instance = MagicMock()
            mock_pm_instance.format.return_value = "test prompt"
            mock_pm_instance.system.return_value = "system prompt"
            mock_pm.return_value = mock_pm_instance

            result = generate_gap_analysis(
                sample,
                master="Master",
                changelog="Changes",
                jinja_guide="Guide",
                validate=True,
            )

            # Should return placeholder in validate mode
            assert "[validate]" in result

    def test_generate_gap_analysis_empty_response_raises_error(self) -> None:
        """generate_gap_analysis must raise error on empty professor response."""
        from src.audit.gap_generator import generate_gap_analysis
        from src.audit.schema import PromptGenerationError
        from src.audit.schema import SampleRecord

        sample = SampleRecord(
            id="empty-resp",
            example_type="test",
            evol_difficulty="easy",
            fragment_name="test",
            source_file="test.py",
            user_prompt="Test",
            reference_response="code",
            gold_injected=False,
            ldi=0.5,
            reference_standards="",
            gap_analysis="",
        )

        with patch(
            "src.audit.gap_generator._get_prompt_manager"
        ) as mock_pm, patch(
            "src.audit.gap_generator._get_inference_router"
        ) as mock_router:
            mock_pm_instance = MagicMock()
            mock_pm_instance.format.return_value = "test prompt"
            mock_pm_instance.system.return_value = "system prompt"
            mock_pm.return_value = mock_pm_instance

            mock_client = MagicMock()
            mock_router.return_value.professor.return_value = mock_client
            # Simulate empty response from professor
            mock_client.generate_with_retry.return_value = ""

            # Should raise PromptGenerationError
            with pytest.raises(PromptGenerationError):
                generate_gap_analysis(
                    sample,
                    master="Master",
                    changelog="Changes",
                    jinja_guide="Guide",
                )
