#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""AEGF Document Loader — Domain-agnostic reference document loader.

Provides a robust cascading mechanism to load exactly three reference
documents required by the pipeline. Filename resolution order:
1. Environment variables (`AEGF_DOC_1`, `AEGF_DOC_2`, `AEGF_DOC_3`)
2. YAML configuration file (`configs/stage_5_evaluation/eval_config.yaml`)
3. Generic internal fallbacks

This module intentionally separates the *capability* to load files from the
*specification* of which files to load (domain configuration). That allows the
evaluation pipeline to be reused for other domains without code changes.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

import yaml

__all__ = ["load_master_docs"]

logger = logging.getLogger(__name__)

# Default config path (can be overridden via env or CLI)
_DEFAULT_CONFIG_PATH: Final[Path] = Path("configs/stage_5_evaluation/eval_config.yaml")

# Generic fallbacks (domain-agnostic names)
_DEFAULT_FN_1: Final[str] = "reference_guide.md"
_DEFAULT_FN_2: Final[str] = "technical_changelog.md"
_DEFAULT_FN_3: Final[str] = "syntax_guide.md"


def _resolve_doc_names_from_cfg(cfg: dict | None) -> tuple[str | None, str | None, str | None]:
    """Extract candidate filenames from the YAML config.

    Supports both the new keys (`doc_1/doc_2/doc_3`) and the legacy
    `master_guide/technical_changelog/jinja_yaml_guide` keys for backward
    compatibility.
    """
    if not cfg or not isinstance(cfg, dict):
        return None, None, None
    md = cfg.get("master_docs") or {}
    if not isinstance(md, dict):
        return None, None, None
    f1 = md.get("doc_1") or md.get("master_guide")
    f2 = md.get("doc_2") or md.get("technical_changelog")
    f3 = md.get("doc_3") or md.get("jinja_yaml_guide")
    return f1, f2, f3


def load_master_docs(gap_dir: Path | str) -> tuple[str, str, str]:
    """Load three master documents using a configuration cascade.

    Args:
        gap_dir: Path to the directory containing documents.

    Returns:
        tuple[str, str, str]: Contents of (doc_1, doc_2, doc_3).
    """
    root_path = Path(gap_dir)

    # 1) Environment variables (preferred)
    f_1 = os.getenv("AEGF_DOC_1") or os.getenv("AEGF_MASTER_GUIDE")
    f_2 = os.getenv("AEGF_DOC_2") or os.getenv("AEGF_TECHNICAL_CHANGELOG")
    f_3 = os.getenv("AEGF_DOC_3") or os.getenv("AEGF_JINJA_YAML_GUIDE")

    # 2) YAML configuration file (if any) — merge only missing names
    if not (f_1 and f_2 and f_3) and _DEFAULT_CONFIG_PATH.exists():
        try:
            cfg = yaml.safe_load(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")) or {}
            c1, c2, c3 = _resolve_doc_names_from_cfg(cfg)
            f_1 = f_1 or c1
            f_2 = f_2 or c2
            f_3 = f_3 or c3
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read config %s: %s", _DEFAULT_CONFIG_PATH, exc)

    # 3) Internal defaults
    f_1 = f_1 or _DEFAULT_FN_1
    f_2 = f_2 or _DEFAULT_FN_2
    f_3 = f_3 or _DEFAULT_FN_3

    resolved = [
        (root_path / f_1, "Master Guide"),
        (root_path / f_2, "Technical Changelog"),
        (root_path / f_3, "Jinja/YAML Guide"),
    ]

    # Verify existence
    for path, label in resolved:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} not found at {path}. Check AEGF_DOC_* env vars or { _DEFAULT_CONFIG_PATH }"
            )

    # Read contents
    contents = [p.read_text(encoding="utf-8", errors="ignore") for p, _ in resolved]

    logger.info("Loaded %d domain documents from %s", len(contents), root_path)
    return contents[0], contents[1], contents[2]
