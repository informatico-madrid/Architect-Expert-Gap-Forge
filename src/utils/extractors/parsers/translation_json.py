"""Translation JSON parser for i18n JSON files."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TranslationEntry:
    """Represents a single translation entry from a JSON file."""

    key: str
    value: str
    file_path: str
    is_leaf: bool


def _is_leaf_node(value: Any) -> bool:
    """Check if a value is a leaf node (string-only or ICU message)."""
    if isinstance(value, str):
        return True
    if isinstance(value, dict) and value:
        # Check if all values are strings (nested translation object)
        return all(isinstance(v, str) for v in value.values())
    return False


def _has_icu_placeholders(text: str) -> bool:
    """Check if text contains ICU message format placeholders."""
    # Match {name}, {count, plural, ...}, {name, plural, ...}, etc.
    icu_pattern = r'\{[^}]+\}'
    return bool(re.search(icu_pattern, text))


def _flatten_dict(
    data: Any,
    parent_key: str = '',
    file_path: str = '',
) -> list[TranslationEntry]:
    """Recursively flatten nested JSON to dot-path keys.

    Args:
        data: The JSON data (dict, list, or primitive)
        parent_key: The accumulated dot-path key prefix
        file_path: Path to the source file

    Returns:
        List of TranslationEntry objects for leaf nodes
    """
    entries = []

    if isinstance(data, dict):
        for key, value in data.items():
            dot_key = f"{parent_key}.{key}" if parent_key else key
            if _is_leaf_node(value):
                # Leaf node: either a string or a dict with only string values
                if isinstance(value, str):
                    entries.append(TranslationEntry(
                        key=dot_key,
                        value=value,
                        file_path=file_path,
                        is_leaf=True,
                    ))
                else:
                    # Dict with string values - recurse to flatten it
                    entries.extend(_flatten_dict(value, dot_key, file_path))
            else:
                # Intermediate category - recurse
                entries.extend(_flatten_dict(value, dot_key, file_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            dot_key = f"{parent_key}[{i}]"
            entries.extend(_flatten_dict(item, dot_key, file_path))

    return entries


class TranslationJsonParser:
    """Parser for Home Assistant translation JSON files.

    Provides methods to parse translation JSON files and extract
    translation entries as flattened dot-path keys.
    """

    @staticmethod
    def parse(file_path: Path) -> list[TranslationEntry]:
        """Parse a translation JSON file and extract translation entries.

        Flattens nested JSON structure to dot-path keys (e.g., "ui.card.title").
        Identifies leaf nodes (strings or string-only dicts) vs intermediate categories.
        Preserves ICU message format placeholders in values.

        Args:
            file_path: Path to the translation JSON file

        Returns:
            List of TranslationEntry objects for each translation key

        Example:
            >>> entries = TranslationJsonParser.parse(Path("strings.json"))
            >>> for entry in entries:
            ...     print(f"{entry.key}: {entry.value[:50]}...")
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        file_path_str = str(file_path)
        return _flatten_dict(data, '', file_path_str)


def parse_translation_json(file_path: Path) -> list[TranslationEntry]:
    """Parse a translation JSON file and extract translation entries.

    Flattens nested JSON structure to dot-path keys (e.g., "ui.card.title").
    Identifies leaf nodes (strings or string-only dicts) vs intermediate categories.
    Preserves ICU message format placeholders in values.

    Args:
        file_path: Path to the translation JSON file

    Returns:
        List of TranslationEntry objects for each translation key

    Example:
        >>> entries = parse_translation_json(Path("strings.json"))
        >>> for entry in entries:
        ...     print(f"{entry.key}: {entry.value[:50]}...")
    """
    return TranslationJsonParser.parse(file_path)
