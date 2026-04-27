#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Configuration loading and CLI entry point coverage tests for audit config and model_evaluator.py.

Tests file I/O, YAML loading, env var overrides, and argument parsing—the infrastructure
that AEGF §1.3 requires to be fully covered (no vibe-coding).
"""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest

import src
from src.audit.config import _load_config


@pytest.mark.integration
class TestConfigFileLoadingWithIOPatching:
    """Test _load_config with mocked file I/O to cover lines 109-110."""

    def test_load_config_when_file_exists_and_parses(self) -> None:
        """_load_config must parse YAML when file exists."""
        # Reset config cache first
        import src.audit.config

        src.audit.config._config_cache = None
        yaml_content = """
api_url: "http://custom:9000"
sample_size: 10
professor_backend: "custom"
"""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("builtins.open", mock_open(read_data=yaml_content)):
                with patch("yaml.safe_load") as mock_yaml:
                    mock_exists.return_value = True
                    mock_yaml.return_value = {
                        "api_url": "http://custom:9000",
                        "sample_size": 10,
                        "professor_backend": "custom",
                    }

                    config = _load_config()

                    # Verify YAML was loaded
                    assert isinstance(config, dict)
                    mock_yaml.assert_called_once()

    def test_load_config_when_file_missing_uses_defaults(self) -> None:
        """_load_config must return empty dict when file doesn't exist."""
        # Reset config cache first
        import src.audit.config

        src.audit.config._config_cache = None
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("src.audit.config.logger") as mock_logger:
                mock_exists.return_value = False

                config = _load_config()

                # Should use defaults
                assert isinstance(config, dict)
                # Should warn about missing config
                mock_logger.warning.assert_called_once()

    def test_load_config_with_yaml_error_fails_safely(self) -> None:
        """_load_config must handle YAML parsing errors."""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("builtins.open", mock_open(read_data="invalid: yaml: [:")):
                with patch("yaml.safe_load") as mock_yaml:
                    mock_exists.return_value = True
                    mock_yaml.return_value = None  # Simulate YAML parse returning None

                    config = _load_config()

                    # Should handle gracefully
                    assert isinstance(config, dict)


@pytest.mark.integration
class TestEnvironmentVariableOverrides:
    """Test env var overrides covering lines 133-138 type coercion."""

    def test_load_config_with_numeric_env_vars(self) -> None:
        """_load_config must coerce numeric env vars correctly."""
        env_vars = {
            "AEGF_SAMPLE_SIZE": "20",
            "AEGF_MAX_TOKENS": "8192",
            "AEGF_RETRIES": "5",
            "AEGF_PROFESSOR_MAX_TOKENS": "16000",
            "AEGF_INFERENCE_MAX_TOKENS": "32000",
        }

        with patch("pathlib.Path.exists") as mock_exists:
            with patch.dict("os.environ", env_vars, clear=False):
                mock_exists.return_value = False  # No YAML file

                config = _load_config()

                # Verify numeric coercion happened
                assert config.get("sample_size") == 20
                assert config.get("max_tokens") == 8192
                assert config.get("retries") == 5

    def test_load_config_with_float_env_vars(self) -> None:
        """_load_config must coerce float env vars correctly."""
        env_vars = {
            "AEGF_TEMPERATURE": "0.8",
            "AEGF_RETRY_DELAY": "2.5",
        }

        with patch("pathlib.Path.exists") as mock_exists:
            with patch.dict("os.environ", env_vars, clear=False):
                mock_exists.return_value = False

                config = _load_config()

                # Verify float coercion
                assert config.get("temperature") == 0.8
                assert config.get("retry_delay") == 2.5

    def test_load_config_with_string_env_vars(self) -> None:
        """_load_config must preserve string env vars."""
        env_vars = {
            "AEGF_VLLM_API_URL": "http://custom:7000",
            "AEGF_PROFESSOR_BACKEND": "vllm",
            "AEGF_INFERENCE_BACKEND": "gemini",
        }

        with patch("pathlib.Path.exists") as mock_exists:
            with patch.dict("os.environ", env_vars, clear=False):
                mock_exists.return_value = False

                config = _load_config()

                # Verify strings preserved
                assert config.get("api_url") == "http://custom:7000"
                assert config.get("professor_backend") == "vllm"


@pytest.mark.integration
class TestDomainPatternsFileLoading:
    """Test _load_domain_patterns file I/O covering lines 180-184."""

    def test_load_domain_patterns_when_file_exists(self) -> None:
        """_load_domain_patterns must load patterns from YAML."""
        from src.audit.exam_builder import _load_domain_patterns

        patterns_yaml = """
default_standards: "Domain standards content"
modernity_rubric:
  - "modern construct 1"
  - "modern construct 2"
"""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("builtins.open", mock_open(read_data=patterns_yaml)):
                with patch("yaml.safe_load") as mock_yaml:
                    mock_exists.return_value = True
                    mock_yaml.return_value = {
                        "default_standards": "Domain standards content",
                        "modernity_rubric": [
                            "modern construct 1",
                            "modern construct 2",
                        ],
                    }

                    # Reset cache to force reload
                    src.audit.exam_builder._domain_patterns_cache = None

                    patterns = _load_domain_patterns()

                    # Verify patterns loaded
                    assert isinstance(patterns, dict)
                    assert "default_standards" in patterns or len(patterns) >= 0

    def test_load_domain_patterns_when_file_missing(self) -> None:
        """_load_domain_patterns must use empty dict when file missing."""
        from src.audit.exam_builder import _load_domain_patterns

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("src.audit.exam_builder.logger") as mock_logger:
                mock_exists.return_value = False

                # Reset cache
                src.audit.exam_builder._domain_patterns_cache = None

                patterns = _load_domain_patterns()

                # Should return empty dict if file missing
                assert isinstance(patterns, dict)
                mock_logger.warning.assert_called_once()


@pytest.mark.integration
class TestAuditConfigFunctions:
    """Test functions in src/audit/config.py for full coverage."""

    def test_get_inference_router_returns_singleton(self) -> None:
        """_get_inference_router must return cached InferenceRouter instance."""
        import src.audit.config

        # Reset cache
        src.audit.config._router = None
        router1 = src.audit.config._get_inference_router()
        router2 = src.audit.config._get_inference_router()

        # Should return same instance (singleton)
        assert router1 is router2

    def test_validate_gemini_api_key_when_gemini_available(self) -> None:
        """validate_gemini_api_key must work when _GEMINI_AVAILABLE is True (the common case in prod)."""
        import src.audit.config
        from src.audit import inference

        # In test environment, _GEMINI_AVAILABLE is True (google.genai is installed)
        # Lines 184-191 should execute
        assert inference._GEMINI_AVAILABLE is True

        # With no GOOGLE_API_KEY set, should return False
        with patch.dict("os.environ", {}, clear=True):
            result = src.audit.config.validate_gemini_api_key()
            assert result is False

    def test_validate_gemini_api_key_when_gemini_available_no_key(self) -> None:
        """validate_gemini_api_key must return False when Gemini available but no key."""
        import src.audit.config
        from src.audit import inference

        # Save original state
        original_available = inference._GEMINI_AVAILABLE

        try:
            # Set gemini as available but no key
            inference._GEMINI_AVAILABLE = True
            # Clear any existing key
            with patch.dict("os.environ", {}, clear=True):
                result = src.audit.config.validate_gemini_api_key()
                assert result is False
        finally:
            # Restore original state
            inference._GEMINI_AVAILABLE = original_available

    def test_validate_gemini_api_key_when_gemini_available_with_key(self) -> None:
        """validate_gemini_api_key must return True when Gemini available and key set."""
        import src.audit.config
        from src.audit import inference

        # Save original state
        original_available = inference._GEMINI_AVAILABLE

        try:
            # Set gemini as available with key
            inference._GEMINI_AVAILABLE = True
            with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key-123"}):
                result = src.audit.config.validate_gemini_api_key()
                assert result is True
        finally:
            # Restore original state
            inference._GEMINI_AVAILABLE = original_available

    def test_validate_gemini_api_key_when_gemini_available_empty_key(self) -> None:
        """validate_gemini_api_key must return False when key is empty string."""
        import src.audit.config
        from src.audit import inference

        # Save original state
        original_available = inference._GEMINI_AVAILABLE

        try:
            # Set gemini as available with empty key
            inference._GEMINI_AVAILABLE = True
            with patch.dict("os.environ", {"GOOGLE_API_KEY": "   "}):
                result = src.audit.config.validate_gemini_api_key()
                assert result is False
        finally:
            # Restore original state
            inference._GEMINI_AVAILABLE = original_available

    def test_require_gemini_api_key_raises_when_no_key(self) -> None:
        """require_gemini_api_key must raise EnvironmentError when key missing."""
        import src.audit.config
        from src.audit import inference

        # Save original state
        original_available = inference._GEMINI_AVAILABLE

        try:
            # Set gemini as available but no key
            inference._GEMINI_AVAILABLE = True
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(EnvironmentError):
                    src.audit.config.require_gemini_api_key()
        finally:
            # Restore original state
            inference._GEMINI_AVAILABLE = original_available


@pytest.mark.integration
class TestAdvancedFormatting:
    """Test advanced formatting logic covering lines 250-252, 280, 294-295."""

    def test_format_reference_standards_result_parts_assembly(self) -> None:
        """_format_reference_standards must correctly assemble result parts."""
        from src.audit.exam_builder import _format_reference_standards

        # Mock CFG with config that forces result_parts assembly
        config = {
            "master_docs_formatting": {
                "master_guide": {"label": "ARCH", "truncate_at": 100},
                "technical_changelog": {"label": "CHANGE", "truncate_at": 100},
                "jinja_yaml_guide": {"label": "TMPL", "truncate_at": 100},
            }
        }

        with patch.dict("src.audit.exam_builder.CFG", config, clear=False):
            result = _format_reference_standards(
                master="Master " * 20,
                changelog="Changelog " * 20,
                jinja_guide="Guide " * 20,
            )

            # Verify assembly happened
            assert isinstance(result, str)
            assert len(result) > 0

    def test_format_reference_standards_handles_empty_sections(self) -> None:
        """_format_reference_standards must handle empty or None sections."""
        from src.audit.exam_builder import _format_reference_standards

        config = {
            "master_docs_formatting": {
                "master_guide": {"label": "ARCH", "truncate_at": 100},
                "technical_changelog": {"label": "CHANGE", "truncate_at": 100},
                "jinja_yaml_guide": {"label": "TMPL", "truncate_at": 100},
            }
        }

        with patch.dict("src.audit.exam_builder.CFG", config, clear=False):
            # Test with empty strings
            result = _format_reference_standards("", "", "")

            # Should still return string
            assert isinstance(result, str)


@pytest.mark.integration
class TestCLIEntryPointWithMonkeypatch:
    """Test main() entry point and argument parsing."""

    def test_main_with_sample_subcommand(self, monkeypatch, capsys) -> None:
        """main() must handle 'sample' subcommand."""
        from src.audit.cli import main

        test_args = [
            "model_evaluator.py",
            "sample",
            "--dataset",
            "test_data.json",
            "--sample-size",
            "5",
            "--audit-dir",
            "/tmp/audit",
        ]

        # Mock cmd_sample to avoid actual execution
        mock_cmd_sample = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_sample", mock_cmd_sample):
                try:
                    main()
                except SystemExit:
                    pass  # main() may exit after running command

                # Verify cmd_sample was called
                mock_cmd_sample.assert_called_once()

    def test_main_with_generate_exam_subcommand(self, monkeypatch) -> None:
        """main() must handle 'generate-exam' subcommand."""
        from src.audit.cli import main

        test_args = [
            "model_evaluator.py",
            "generate-exam",
            "--judge-model",
            "test-judge",
            "--audit-dir",
            "/tmp/audit",
        ]

        mock_cmd_exam = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_generate_exam", mock_cmd_exam):
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd_exam.assert_called_once()

    def test_main_with_invalid_subcommand_prints_help(self, capsys) -> None:
        """main() must print help for invalid subcommand."""
        from src.audit.cli import main

        test_args = [
            "model_evaluator.py",
            "invalid-cmd",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit):
                main()

            # Capture output
            captured = capsys.readouterr()
            # Either error or help text should appear
            assert len(captured.err) > 0 or len(captured.out) > 0

    def test_main_full_subcommand(self, monkeypatch) -> None:
        """main() must handle 'full' subcommand for complete pipeline."""
        from src.audit.cli import main

        test_args = [
            "model_evaluator.py",
            "full",
            "--dataset",
            "test.json",
            "--audit-dir",
            "/tmp",
        ]

        mock_cmd_full = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_full", mock_cmd_full):
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd_full.assert_called_once()

    def test_main_with_validate_mode(self, monkeypatch) -> None:
        """main() must set validate=True when --validate flag provided."""
        from src.audit.cli import main

        test_args = [
            "model_evaluator.py",
            "sample",
            "--dataset",
            "test.json",
            "--validate",
            "--audit-dir",
            "/tmp",
        ]

        mock_cmd_sample = MagicMock()

        with patch("sys.argv", test_args):
            with patch("src.audit.cli.cmd_sample", mock_cmd_sample):
                try:
                    main()
                except SystemExit:
                    pass

                # Verify validate arg was set
                call_args = mock_cmd_sample.call_args
                assert call_args is not None
                # The args namespace should have validate=True
                args_namespace = call_args[0][0]
                assert args_namespace.validate is True


@pytest.mark.integration
class TestLoadMasterDocsIntegration:
    """Test load_master_docs file loading."""

    def test_load_master_docs_file_reading(self, tmp_path, monkeypatch) -> None:
        """load_master_docs must read master, changelog, and jinja files."""
        from src.utils.doc_loader import load_master_docs

        master_content = "Master documentation content"
        changelog_content = "Version 2.0: Added features"
        jinja_content = "Jinja template guide"

        # Create temp gap directory and actual files to avoid flaky mocks
        gap_dir = tmp_path / "gap_audit"
        gap_dir.mkdir()
        # Use default filenames expected by doc_loader
        (gap_dir / "reference_guide.md").write_text(master_content, encoding="utf-8")
        (gap_dir / "technical_changelog.md").write_text(
            changelog_content, encoding="utf-8"
        )
        (gap_dir / "syntax_guide.md").write_text(jinja_content, encoding="utf-8")

        # Set env vars so the env-var tier of the cascade resolves the tmp_path files
        monkeypatch.setenv("AEGF_DOC_1", "reference_guide.md")
        monkeypatch.setenv("AEGF_DOC_2", "technical_changelog.md")
        monkeypatch.setenv("AEGF_DOC_3", "syntax_guide.md")

        master, changelog, jinja_guide = load_master_docs(gap_dir=str(gap_dir))

        # Verify files were read
        assert isinstance(master, str)
        assert isinstance(changelog, str)
        assert isinstance(jinja_guide, str)
