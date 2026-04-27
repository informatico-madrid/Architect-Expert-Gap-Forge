#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0



from src.curation import backtracking_helpers as br
from src.curation import backtrack_strategy as br_strategy


def test_extract_replace_think_block():
    content = "pre<think>think_text</think>post"
    think, rest = br.extract_think_block(content)
    assert "think_text" in think
    assert rest == "post"
    new = br.replace_think_block(content, "NEW_THINK")
    assert new == "NEW_THINK</think>post"


def test_sanitize_generated_reasoning_removes_code_and_tool_calls():
    text = (
        "Explanation\n```python\nprint('x')\n```\n"
        'More <tool_call>{"arguments": {"content": "file content"}}</tool_call>`inline`<tag>bad</tag>\n'
    )
    cleaned = br._sanitize_generated_reasoning(text)
    assert "print(" not in cleaned
    assert "tool_call" not in cleaned
    assert "<tag>" not in cleaned


def test_detect_language_hint():
    en = "This is the test and it will work"
    es = "esto es la prueba y vamos a usar la función"
    assert br._detect_language_hint(en) == "English"
    assert br._detect_language_hint(es) == "Spanish"
    assert br._detect_language_hint("") == "English"


def test_extract_executable_code_from_fenced_and_tool_call():
    mixed = (
        "Some text\n```python\nx=1\n```\n"
        '<tool_call>{"arguments": {"content": "filecontent"}}</tool_call>'
    )
    extracted = br._extract_executable_code(mixed)
    assert "x=1" in extracted
    assert "filecontent" in extracted


def test_strip_python_comments():
    code = "x = 1  # comment\nprint('# not a comment inside string')\n# full comment\n"
    stripped = br._strip_python_comments(code)
    lines = stripped.splitlines()
    # The stripper is a line-based heuristic; ensure comments are removed
    assert "#" not in stripped
    assert "print(" in lines[1]


def test_load_legacy_regexes_and_validate(tmp_path):
    yaml_path = tmp_path / "legacy.yaml"
    yaml_path.write_text("legacy_patterns:\n  - pattern: 'deprecated_api'\n")
    legacy = br_strategy._load_legacy_regexes(str(yaml_path))
    assert isinstance(legacy, tuple) and len(legacy) == 1

    # resolution contains deprecated_api inside fenced code — should be detected
    new_think = "A" * 40 + " deprecated_api()"
    resolution = "```python\ndeprecated_api()\n```"
    ok, reason = br_strategy._validate_resolution_no_legacy(
        new_think, resolution, legacy
    )
    assert not ok
    assert "deprecated_api" in reason

    # no legacy patterns — should pass
    ok2, _ = br_strategy._validate_resolution_no_legacy(new_think, resolution, ())
    assert ok2
