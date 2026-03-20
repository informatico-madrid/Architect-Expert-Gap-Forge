#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/utils/logging.py - Logging Utilities Module."""

from __future__ import annotations

import logging
import pytest
from src.utils.logging import get_logger


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self) -> None:
        """Should return a logger instance."""
        logger = get_logger("test_module_unique_123")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self) -> None:
        """Should return logger with the specified name."""
        logger = get_logger("my.custom.module.unique")
        assert logger.name == "my.custom.module.unique"

    def test_logger_is_callable(self) -> None:
        """Logger should be callable with lazy formatting."""
        logger = get_logger("test_logger_lazy_unique")
        # Should work with lazy formatting style
        logger.info("Message with %s and %d", "string", 42)

    def test_different_modules_get_different_loggers(self) -> None:
        """Should return different logger instances for different names."""
        logger1 = get_logger("module.one.unique")
        logger2 = get_logger("module.two.unique")
        assert logger1 is not logger2
        assert logger1.name == "module.one.unique"
        assert logger2.name == "module.two.unique"

    def test_same_module_returns_same_logger(self) -> None:
        """Should return same logger instance for same module name."""
        logger1 = get_logger("same.module.unique")
        logger2 = get_logger("same.module.unique")
        assert logger1 is logger2

    def test_logger_handles_special_characters_in_name(self) -> None:
        """Should handle special characters in module name."""
        logger = get_logger("test.module.with.dots.unique")
        assert logger.name == "test.module.with.dots.unique"

    def test_logger_debug_enabled(self) -> None:
        """Should allow debug messages when level is appropriate."""
        logger = get_logger("test_logger_debug_unique")
        # Should not raise - debug should be allowed
        logger.debug("Debug message")

    def test_logger_info_works(self) -> None:
        """Should allow info messages."""
        logger = get_logger("test_logger_info_unique")
        # Should not raise
        logger.info("Info message")

    def test_logger_warning_works(self) -> None:
        """Should allow warning messages."""
        logger = get_logger("test_logger_warning_unique")
        # Should not raise
        logger.warning("Warning message")
