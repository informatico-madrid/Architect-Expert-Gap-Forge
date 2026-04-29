#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0


from src.factory import config as cfg_module
from src.factory.prompt_builder import detect_legacy_patterns, load_master_docs


def test_detect_legacy_patterns_code_and_jinja():
    # Compose a code string that contains multiple legacy patterns
    code = """
def update(self):
    # legacy blocking sleep
    time.sleep(1)
    hass.data['something'] = 1
"""
    found = detect_legacy_patterns(code, subtype="code")
    assert isinstance(found, list)
    assert len(found) >= 1

    # Jinja detectors (multiline anchors)
    jinja = "trigger:\n  - platform: state\n"
    found_jinja = detect_legacy_patterns(jinja, subtype="jinja")
    assert isinstance(found_jinja, list)
    assert len(found_jinja) >= 1


def test_load_master_docs(tmp_path):
    # Create the three required master docs
    master = tmp_path / cfg_module._MASTER_GUIDE_FILENAME
    changelog = tmp_path / cfg_module._TECHNICAL_CHANGELOG_FILENAME
    jinja = tmp_path / cfg_module._JINJA_YAML_GUIDE_FILENAME
    master.write_text("MASTER CONTENT")
    changelog.write_text("CHANGELOG")
    jinja.write_text("JINJA GUIDE")

    m, c, j = load_master_docs(tmp_path)
    assert m == "MASTER CONTENT"
    assert c == "CHANGELOG"
    assert j == "JINJA GUIDE"


# main() has a CLI entrypoint that relies on sys.argv and side-effects; avoid
# calling it directly here to keep tests hermetic. Higher-level integration
# tests exercise the end-to-end CLI in other test modules.
