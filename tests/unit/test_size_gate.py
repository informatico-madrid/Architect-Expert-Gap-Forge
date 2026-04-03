# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit Tests for SIZE Gate Filtering
====================================

Tests MIN_SIZE (300 bytes) and LOGIC_ONLY_MIN_CHARS (800 chars) gates.

Requirements: AC-2.1, AC-2.2, FR-10
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import MIN_SIZE, LOGIC_ONLY_MIN_CHARS


class TestSizeGates:
    """Unit tests for SIZE gate filtering."""

    def test_file_below_min_size_not_processed(self, tmp_path: Path) -> None:
        """Test that files below MIN_SIZE (300 bytes) are not processed.

        AC-2.1: Files smaller than MIN_SIZE should be excluded from processing.
        """
        # Create repo structure: tmp_path/owner/myrepo/custom_components/test_component/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True, exist_ok=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create very small file (below MIN_SIZE=300)
        small_file = component / "tiny.py"
        small_file.write_text("x = 1")  # Only 5 bytes

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner/myrepo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        # Output path: base_dir / output_subdir / category
        # Since category is "owner/myrepo", output is at owner/myrepo level
        output_dir = tmp_path / "output" / "owner" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT but no LOGIC_ONLY for tiny file
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        # Small file should not generate LOGIC_ONLY
        logic_only_files = [
            f for f in bundle_files
            if 'LOGIC_ONLY' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should still be emitted"
        )

        # Tiny file should not generate LOGIC_ONLY
        assert len(logic_only_files) == 0, (
            "File below MIN_SIZE should not generate LOGIC_ONLY"
        )

    def test_file_above_min_size_processed(self, tmp_path: Path) -> None:
        """Test that files above MIN_SIZE (300 bytes) are processed.

        AC-2.1: Files at or above MIN_SIZE should be included in processing.
        """
        # Create repo structure: tmp_path/owner/myrepo/custom_components/test_component/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create file at exactly MIN_SIZE (300 bytes)
        medium_file = component / "medium.py"
        medium_file.write_text("""
def process_data(data):
    '''Process incoming data and transform it.'''
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
    return result

def validate_input(data):
    '''Validate input data structure.'''
    return isinstance(data, list)

def transform_output(result):
    '''Transform the result before returning.'''
    return result

def filter_by_criteria(data, criteria):
    '''Filter data by criteria.'''
    return [item for item in data if item.get('active', True)]
""".strip())

        assert len(medium_file.read_text()) >= MIN_SIZE, "File should be at least MIN_SIZE"

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner/myrepo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        # Output path: base_dir / output_subdir / category
        # Since category is "owner/myrepo", output is at owner/myrepo level
        output_dir = tmp_path / "output" / "owner" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted for files at MIN_SIZE"
        )

    def test_file_below_logic_only_min_chars_not_type3(self, tmp_path: Path) -> None:
        """Test that files below LOGIC_ONLY_MIN_CHARS are not TYPE 3.

        AC-2.2: Files below LOGIC_ONLY_MIN_CHARS should not generate TYPE 3.
        """
        # Create repo structure: tmp_path/owner/myrepo/custom_components/test_component/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create file between MIN_SIZE and LOGIC_ONLY_MIN_CHARS
        medium_file = component / "processor.py"
        medium_file.write_text("""
def process_data(data):
    '''Process incoming data and transform it.'''
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(item)
    return result

def validate_input(data):
    '''Validate input data structure.'''
    return isinstance(data, list)

def transform_output(result):
    '''Transform the result before returning.'''
    return result

def filter_by_criteria(data, criteria):
    '''Filter data by criteria.'''
    return [item for item in data if item.get('active', True)]
""".strip())

        file_size = len(medium_file.read_text())
        assert MIN_SIZE <= file_size < LOGIC_ONLY_MIN_CHARS, (
            f"File should be between MIN_SIZE ({MIN_SIZE}) and LOGIC_ONLY_MIN_CHARS ({LOGIC_ONLY_MIN_CHARS}). "
            f"Actual size: {file_size}"
        )

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner/myrepo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        # Output path: base_dir / output_subdir / category
        # Since category is "owner/myrepo", output is at owner/myrepo level
        output_dir = tmp_path / "output" / "owner" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        # Should NOT have LOGIC_ONLY (TYPE 3)
        logic_only_files = [
            f for f in bundle_files
            if 'LOGIC_ONLY' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        assert len(logic_only_files) == 0, (
            f"File below LOGIC_ONLY_MIN_CHARS ({file_size} < {LOGIC_ONLY_MIN_CHARS}) should not generate TYPE 3"
        )

    def test_file_above_logic_only_min_chars_is_type3(self, tmp_path: Path) -> None:
        """Test that files above LOGIC_ONLY_MIN_CHARS (800 chars) are TYPE 3.

        AC-2.2: Files at or above LOGIC_ONLY_MIN_CHARS should generate TYPE 3.
        """
        # Create repo structure: tmp_path/owner/myrepo/custom_components/test_component/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create large file (>= 800 chars)
        large_file = component / "processor.py"
        large_file.write_text("""
def complex_processor(data: dict) -> dict:
    '''Process complex data transformations with multiple steps.'''
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = process_nested_dict(value)
        elif isinstance(value, list):
            result[key] = process_list(value)
        else:
            result[key] = transform_scalar(value)
    return result

def process_nested_dict(nested: dict) -> dict:
    '''Recursively process nested dictionaries.'''
    output = {}
    for k, v in nested.items():
        if isinstance(v, dict):
            output[k] = process_nested_dict(v)
        elif isinstance(v, list):
            output[k] = [transform_scalar(item) for item in v]
        else:
            output[k] = transform_scalar(v)
    return output

def process_list(items: list) -> list:
    '''Process a list of items through transformation pipeline.'''
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(process_nested_dict(item))
        elif isinstance(item, list):
            result.extend(item)
        else:
            result.append(transform_scalar(item))
    return result

def transform_scalar(value) -> str:
    '''Transform a scalar value to string representation.'''
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value.strip()
    else:
        return repr(value)

def validate_input(data: dict) -> bool:
    '''Validate input data structure and return boolean.'''
    if not isinstance(data, dict):
        return False
    for key, value in data.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (dict, list, str, int, float, bool, type(None))):
            return False
    return True

def merge_datasets(primary: dict, secondary: dict) -> dict:
    '''Merge two datasets with priority to secondary.'''
    merged = primary.copy()
    for key, value in secondary.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_datasets(merged[key], value)
        else:
            merged[key] = value
    return merged

def filter_by_criteria(data: dict, criteria: dict) -> dict:
    '''Filter dataset by criteria matching.'''
    result = {}
    for key, value in data.items():
        matches = True
        for crit_key, crit_value in criteria.items():
            if crit_key in value:
                if value[crit_key] != crit_value:
                    matches = False
                    break
        if matches:
            result[key] = value
    return result

def aggregate_metrics(metrics: list) -> dict:
    '''Aggregate metrics list into summary statistics.'''
    if not metrics:
        return {'count': 0, 'sum': 0, 'avg': 0}

    total = sum(m.get('value', 0) for m in metrics)
    count = len(metrics)
    average = total / count if count > 0 else 0

    return {
        'count': count,
        'sum': total,
        'avg': average,
        'min': min(m.get('value', 0) for m in metrics),
        'max': max(m.get('value', 0) for m in metrics)
    }

def normalize_values(data: list) -> list:
    '''Normalize values to 0-1 range.'''
    if not data:
        return []

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val

    if range_val == 0:
        return [0.0 for _ in data]

    return [(v - min_val) / range_val for v in data]
""".strip())

        # Add GOLD_PATTERN to pass gold filter (DOMAIN)
        large_file.write_text(large_file.read_text() + """

DOMAIN = "test_processor"

def get_runtime_data(entry):
    '''Get runtime data from entry.'''
    return entry.runtime_data
""")

        file_size = len(large_file.read_text())
        assert file_size >= LOGIC_ONLY_MIN_CHARS, (
            f"File should be at least LOGIC_ONLY_MIN_CHARS ({LOGIC_ONLY_MIN_CHARS}). "
            f"Actual size: {file_size}"
        )

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner/myrepo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        # Output path: base_dir / output_subdir / category
        # Since category is "owner/myrepo", output is at owner/myrepo level
        output_dir = tmp_path / "output" / "owner" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        # Should have LOGIC_ONLY (TYPE 3)
        logic_only_files = [
            f for f in bundle_files
            if 'LOGIC_ONLY' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        assert len(logic_only_files) > 0, (
            f"File at or above LOGIC_ONLY_MIN_CHARS ({file_size} >= {LOGIC_ONLY_MIN_CHARS}) should generate TYPE 3"
        )
