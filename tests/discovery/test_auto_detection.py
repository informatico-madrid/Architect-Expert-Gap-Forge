import pytest
from pathlib import Path
import tempfile
from src.discovery.file_scanner import _detect_strategy


class TestDetectStrategy:
    def test_detect_strategy_yaml(self):
        """Repository with only YAML files should detect as 'yaml'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "themes").mkdir()
            (root / "themes" / "dark.yaml").write_text("key: value")
            (root / "templates").mkdir()
            (root / "templates" / "automation.jinja").write_text("template")

            strategy = _detect_strategy(root)
            assert strategy == "yaml"

    def test_detect_strategy_typescript(self):
        """Repository with only TS files should detect as 'typescript'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "button.ts").write_text("export {}")
            (root / "src" / "card.tsx").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_detect_strategy_fallback(self):
        """Empty repository should detect as 'directory'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".git").mkdir()  # Only git directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_detect_strategy_exclusions(self):
        """Files in excluded directories should not be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TypeScript in node_modules should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "test.ts").write_text("export {}")
            # TypeScript in src should be detected
            (root / "src").mkdir()
            (root / "src" / "test.ts").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"
