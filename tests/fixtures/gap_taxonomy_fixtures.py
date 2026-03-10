#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Re-usable fixtures for Gap master-docs and a minimal taxonomy file.

These fixtures follow the project's existing test patterns and supply
small, self-contained files for `production_v11` tests that require
`load_master_docs` or `load_taxonomy` to succeed on-disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
import yaml


@pytest.fixture
def gap_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary Gap directory with the three required master docs."""
    (tmp_path / "HA_MASTER_GUIDE_2026.md").write_text(
        "# Master Guide\n" + "Text\n" * 50
    )
    (tmp_path / "technical_changelog_2026.md").write_text(
        "# Changelog\n" + "Entry\n" * 50
    )
    (tmp_path / "HA_JINJA_YAML_GUIDE_2026.md").write_text(
        "# Jinja Guide\n" + "Guide\n" * 50
    )
    yield tmp_path


@pytest.fixture
def taxonomy_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Write a minimal prompts taxonomy YAML that `production_v11` can load."""
    payload = {
        "prompts": {
            "system": {
                "python": {
                    "base": "[BASE]",
                    "nominal_suffix": "[NOMINAL]",
                    "contrast_suffix": "[CONTRAST]",
                    "error_recovery_suffix": "[ERROR]",
                    "blueprint_context": "[BLUEPRINT $blueprint IMPORTS $local_imports]",
                    "governance_context": "[GOV $governance]",
                },
                "jinja": {"base": "[JINJA_BASE]"},
            },
            "user": {
                "python": {
                    "nominal_easy": "easy-$context",
                    "nominal_medium": "medium-$context",
                    "nominal_hard_anchor_free": ["hard-free-$name"],
                    "nominal_hard_anchor": "hard-anchor-$name",
                    "contrast": "contrast-$legacy_code",
                    "error_recovery": "error-$error_msg",
                    "functional_unit": "functional-$context",
                }
            },
        },
        "ha_error_templates": [
            {"context_type": "python", "error": "Error {entity} at {component}"}
        ],
        "legacy_2023_patterns": [
            {"legacy_code": "hass.data[]", "context_type": "python"}
        ],
        "jinja_ha_error_templates": [
            {"context_type": "jinja", "error": "JinjaErr {entity}"}
        ],
        "jinja_legacy_2023_patterns": [
            {"legacy_code": "platform: template", "context_type": "jinja"}
        ],
        "theory_question_templates": [
            {"template": "What is {section_title}?", "type": "theory"}
        ],
        "tools_definition": [{"name": "tool"}],
    }
    path = tmp_path / "prompts_taxonomy.yaml"
    path.write_text(yaml.safe_dump(payload))
    yield path
