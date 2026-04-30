# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Factory for creating language-specific extractors.

This module provides lazy-loading of extractor adapters based on the profile
name. It follows the constitution's requirement of no import-time side effects
by performing runtime imports only when requested.
"""

from __future__ import annotations

import logging
from typing import Dict, Type

from src.utils.extractors.base import ExtractorAdapter

logger = logging.getLogger(__name__)

# Registry of adapter classes (populated lazily)
_ADAPTER_REGISTRY: Dict[str, str] = {
    "python": "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
    "python-ast": "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
    "homeassistant": "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
    "php_legacy": "src.utils.extractors.php_legacy_adapter.PhpLegacyAdapter",
    "typescript": "src.utils.extractors.typescript_adapter.TypeScriptAdapter",
    "ts": "src.utils.extractors.typescript_adapter.TypeScriptAdapter",
    "tsx": "src.utils.extractors.typescript_adapter.TypeScriptAdapter",
    "default": "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
}

# Cache for instantiated adapters
_adapter_cache: Dict[str, ExtractorAdapter] = {}


def get_adapter(profile: str) -> ExtractorAdapter:
    """Get an extractor adapter for the given profile or file extension.

    This function implements lazy loading - the adapter class is only imported
    when first requested. Subsequent calls for the same profile return a cached
    instance.

    Args:
        profile: The profile name (e.g., "python", "homeassistant", "typescript")
                 or a file extension (e.g., ".ts", ".tsx", ".py").
                 If the profile is not recognized, defaults to Python AST adapter.

    Returns:
        An ExtractorAdapter instance for the given profile.

    Example:
        >>> adapter = get_adapter("homeassistant")
        >>> result = adapter.parse_file(Path("example.py"))
        >>> adapter = get_adapter(".ts")  # also works with extensions
    """
    # Normalize profile name
    normalized = profile.lower().strip()

    # Check cache first
    if normalized in _adapter_cache:
        logger.debug("Returning cached adapter for profile: %s", normalized)
        return _adapter_cache[normalized]

    # Handle file extensions (e.g., ".ts", ".tsx", "test.ts")
    if normalized.startswith("."):
        # Bare extension like ".ts"
        ext_mapping = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".py": "python",
            ".php": "php_legacy",
        }
        normalized = ext_mapping.get(normalized, "default")
    elif "." in normalized:
        # File name with extension like "test.ts"
        ext = "." + normalized.split(".")[-1]
        ext_mapping = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".py": "python",
            ".php": "php_legacy",
        }
        normalized = ext_mapping.get(ext, "default")

    # Get adapter class path from registry (default to python if unknown)
    adapter_path = _ADAPTER_REGISTRY.get(normalized, _ADAPTER_REGISTRY["default"])

    # Lazily import and instantiate the adapter
    adapter = _load_adapter(adapter_path)

    # Cache the instance
    _adapter_cache[normalized] = adapter
    logger.info("Loaded adapter for profile: %s", normalized)

    return adapter


def _load_adapter(adapter_path: str) -> ExtractorAdapter:
    """Load an adapter class from its fully qualified path.

    Args:
        adapter_path: Fully qualified path to the adapter class.

    Returns:
        An instance of the adapter class.
    """
    try:
        module_path, class_name = adapter_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        adapter_class: Type[ExtractorAdapter] = getattr(module, class_name)
        return adapter_class()
    except ImportError as e:
        logger.error("Failed to import adapter module: %s, error: %s", module_path, e)
        raise RuntimeError(f"Failed to load adapter: {adapter_path}") from e
    except AttributeError as e:
        logger.error("Adapter class not found: %s in %s", class_name, module_path)
        raise RuntimeError(f"Adapter class not found: {adapter_path}") from e


def register_adapter(profile: str, adapter_path: str) -> None:
    """Register a new adapter for a profile.

    This function allows runtime registration of new adapters. It's useful for
    testing or adding support for new languages.

    Note: This function is not thread-safe. If multiple threads need to modify
    the registry simultaneously, external synchronization is required.

    Args:
        profile: The profile name to register.
        adapter_path: Fully qualified path to the adapter class.
    """
    _ADAPTER_REGISTRY[profile.lower().strip()] = adapter_path
    # Clear cache for this profile if it exists
    if profile.lower().strip() in _adapter_cache:
        del _adapter_cache[profile.lower().strip()]
    logger.info("Registered new adapter for profile: %s", profile)


def clear_cache() -> None:
    """Clear the adapter cache.

    This is primarily useful for testing to ensure clean state.

    Note: This function is not thread-safe. If multiple threads need to modify
    the cache simultaneously, external synchronization is required.
    """
    _adapter_cache.clear()
    logger.debug("Adapter cache cleared")
