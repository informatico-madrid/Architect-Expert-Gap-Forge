# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for scorecard module functions.

Author: Claude Opus 4.6
"""

from __future__ import annotations


class TestExtractCodeBlocks:
    """Tests for _extract_code_blocks function."""

    def test_extract_code_blocks_empty(self) -> None:
        """Test empty text returns empty string."""
        from src.audit.scorecard import _extract_code_blocks

        result = _extract_code_blocks("")
        assert result == ""

    def test_extract_code_blocks_no_fences(self) -> None:
        """Test text without code fences returns empty string."""
        from src.audit.scorecard import _extract_code_blocks

        result = _extract_code_blocks("Just plain text without code")
        assert result == ""

    def test_extract_code_blocks_single_block(self) -> None:
        """Test single code block extraction."""
        from src.audit.scorecard import _extract_code_blocks

        text = "Some text\n```python\nprint('hello')\n```\nMore text"
        result = _extract_code_blocks(text)
        assert "print('hello')" in result

    def test_extract_code_blocks_multiple_blocks(self) -> None:
        """Test multiple code blocks."""
        from src.audit.scorecard import _extract_code_blocks

        text = """```python
print('hello')
```
```javascript
console.log('world');
```"""
        result = _extract_code_blocks(text)
        assert "print('hello')" in result
        assert "console.log('world');" in result

    def test_extract_code_blocks_with_language(self) -> None:
        """Test code block with language specifier."""
        from src.audit.scorecard import _extract_code_blocks

        text = "```php\n<?php echo 'test';\n```"
        result = _extract_code_blocks(text)
        assert "<?php echo 'test';" in result
