# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
YAML Adapter for Home Assistant Blueprints and YAML Files.

This adapter provides:
- YAML parsing using pyyaml
- Blueprint pattern extraction
- Trigger/Condition/Action pattern extraction
- Jinja expression detection
- Dependency extraction

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.utils.extractors.base import (
    Dependency,
    ExtractorAdapter,
    ParseError,
    ParseResult,
)
from src.utils.extractors.extractors.yaml_base import (
    BlueprintPattern,
    TriggerPattern,
    ConditionPattern,
    ActionPattern,
    JinjaExpressionPattern,
    extract_jinja_variables,
    extract_jinja_filters,
    extract_jinja_tests,
)

logger = logging.getLogger(__name__)

# Try to import yaml (PyYAML)
try:
    import yaml
    YAML_AVAILABLE = True
    # Register custom constructor for !input tags
    def input_constructor(loader, node):
        """Custom constructor for !input tags."""
        return loader.construct_scalar(node)

    yaml.SafeLoader.add_constructor('!input', input_constructor)
except ImportError:
    YAML_AVAILABLE = False
    yaml = None


class YamlAdapter(ExtractorAdapter):
    """Adapter for parsing YAML files (blueprints, automations, etc.).

    This adapter provides:
    - YAML parsing using PyYAML
    - Blueprint pattern extraction (name, description, domain, input)
    - Trigger/Condition/Action pattern extraction
    - Jinja expression detection (!input, {{ }}, filters)
    - Dependency extraction

    Attributes:
        use_regex_fallback: Whether to use regex fallback for YAML parsing.
    """

    def __init__(self, use_regex_fallback: bool = True):
        """Initialize YamlAdapter.

        Args:
            use_regex_fallback: Whether to use regex fallback for YAML parsing.
        """
        self.use_regex_fallback = use_regex_fallback

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a YAML file and extract patterns.

        Args:
            file_path: Path to the YAML file to parse.

        Returns:
            ParseResult containing parsed content, YAML tree, and patterns.

        Raises:
            ParseError: If the file cannot be parsed.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        yaml_tree = None
        patterns: List[Any] = []

        if YAML_AVAILABLE:
            try:
                yaml_tree = yaml.safe_load(raw_content)
            except yaml.YAMLError as e:
                # Handle custom tags like !input by falling back to regex parsing
                if 'could not determine a constructor for the tag' in str(e):
                    jinja_vars = extract_jinja_variables(raw_content, str(file_path))
                    jinja_filters = extract_jinja_filters(raw_content, str(file_path))
                    jinja_tests = extract_jinja_tests(raw_content, str(file_path))

                    jinja_patterns = []
                    for var in jinja_vars:
                        jinja_patterns.append(
                            JinjaExpressionPattern(
                                expression="{{ " + var.name + " }}",
                                expression_type="variable",
                                file_path=str(file_path),
                                line_number=var.line_number,
                                variable_name=var.name,
                            )
                        )
                    for filter_item in jinja_filters:
                        jinja_patterns.append(
                            JinjaExpressionPattern(
                                expression="{{ " + filter_item.source + " | " + filter_item.filter + " }}",
                                expression_type="filter",
                                file_path=str(file_path),
                                line_number=filter_item.line_number,
                                variable_name=filter_item.source,
                                filter_name=filter_item.filter,
                            )
                        )
                    for test in jinja_tests:
                        jinja_patterns.append(
                            JinjaExpressionPattern(
                                expression="{{ " + test.source + " is " + test.test + " }}",
                                expression_type="test",
                                file_path=str(file_path),
                                line_number=test.line_number,
                                variable_name=test.source,
                                filter_name=test.test,
                            )
                        )

                    dependencies = self._extract_dependencies(raw_content)

                    return ParseResult(
                        file_path=file_path,
                        ast_tree=None,
                        raw_content=raw_content,
                        dependencies=tuple(dependencies),
                    )
                raise ParseError(
                    file_path=file_path,
                    line=getattr(e, 'problem_mark', None) and e.problem_mark.line + 1 or 1,
                    message=f"YAML syntax error: {str(e)}",
                )
        elif self.use_regex_fallback:
            # Fallback: extract patterns using regex
            patterns = self._extract_patterns_from_content(raw_content, str(file_path))
        else:
            raise ParseError(
                file_path=file_path,
                line=1,
                message="PyYAML not available and regex fallback disabled",
            )

        # Extract Jinja expressions from content
        jinja_vars = extract_jinja_variables(raw_content, str(file_path))
        jinja_filters = extract_jinja_filters(raw_content, str(file_path))
        jinja_tests = extract_jinja_tests(raw_content, str(file_path))

        # Convert to patterns
        jinja_patterns = []
        for var in jinja_vars:
            jinja_patterns.append(
                JinjaExpressionPattern(
                    expression="{{ " + var.name + " }}",
                    expression_type="variable",
                    file_path=str(file_path),
                    line_number=var.line_number,
                    variable_name=var.name,
                )
            )
        for filter in jinja_filters:
            jinja_patterns.append(
                JinjaExpressionPattern(
                    expression="{{ " + filter.source + " | " + filter.filter + " }}",
                    expression_type="filter",
                    file_path=str(file_path),
                    line_number=filter.line_number,
                    variable_name=filter.source,
                    filter_name=filter.filter,
                )
            )
        for test in jinja_tests:
            jinja_patterns.append(
                JinjaExpressionPattern(
                    expression="{{ " + test.source + " is " + test.test + " }}",
                    expression_type="test",
                    file_path=str(file_path),
                    line_number=test.line_number,
                    variable_name=test.source,
                    filter_name=test.test,
                )
            )

        # Combine all patterns
        all_patterns = patterns + jinja_patterns

        # Extract dependencies
        dependencies = self._extract_dependencies(raw_content)

        return ParseResult(
            file_path=file_path,
            ast_tree=yaml_tree,  # Using ast_tree field for YAML tree
            raw_content=raw_content,
            dependencies=tuple(dependencies),
        )

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a YAML file.

        Args:
            file_path: Path to the YAML file to analyze.

        Returns:
            List of Dependency objects.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        return self._extract_dependencies(raw_content)

    def _extract_patterns_from_content(self, content: str, file_path: str) -> List[Any]:
        """Extract patterns from YAML content using regex.

        This is a fallback method for when PyYAML is not available.

        Args:
            content: YAML content
            file_path: Path to the file

        Returns:
            List of extracted patterns
        """
        patterns: List[Any] = []

        # Extract blueprint patterns
        blueprint_match = re.search(
            r'blueprint:\s*\n\s*name:\s*["\']([^"\']+)["\']\s*\n\s*description:\s*["\']([^"\']+)["\']',
            content,
            re.MULTILINE
        )
        if blueprint_match:
            line_number = content[: blueprint_match.start()].count("\n") + 1
            patterns.append(
                BlueprintPattern(
                    name=blueprint_match.group(1),
                    description=blueprint_match.group(2),
                    domain="automation",
                    input={},
                    file_path=file_path,
                    line_number=line_number,
                )
            )

        # Extract trigger patterns
        trigger_pattern = re.compile(
            r'trigger:\s*\n((?:[ \t]+[-]\s+platform:\s*["\']([^"\']+)["\'](?:\s*\n[ \t]+[^:]+)*|.*?)(?=\n(?:trigger:|condition:|action:|input:|$)))',
            re.MULTILINE | re.DOTALL
        )
        for match in trigger_pattern.finditer(content):
            line_number = content[: match.start()].count("\n") + 1
            platform_match = re.search(r'platform:\s*["\']([^"\']+)["\']', match.group(1))
            if platform_match:
                patterns.append(
                    TriggerPattern(
                        platform=platform_match.group(1),
                        file_path=file_path,
                        line_number=line_number,
                    )
                )

        # Extract condition patterns
        condition_pattern = re.compile(
            r'condition:\s*\n((?:[ \t]+condition:\s*["\']([^"\']+)["\'](?:\s*\n[ \t]+[^:]+)*|.*?)(?=\n(?:trigger:|condition:|action:|input:|$)))',
            re.MULTILINE | re.DOTALL
        )
        for match in condition_pattern.finditer(content):
            line_number = content[: match.start()].count("\n") + 1
            condition_match = re.search(r'condition:\s*["\']([^"\']+)["\']', match.group(1))
            if condition_match:
                patterns.append(
                    ConditionPattern(
                        condition=condition_match.group(1),
                        file_path=file_path,
                        line_number=line_number,
                    )
                )

        # Extract action patterns
        action_pattern = re.compile(
            r'action:\s*\n((?:[ \t]+service:\s*["\']([^"\']+)["\'](?:\s*\n[ \t]+[^:]+)*|.*?)(?=\n(?:trigger:|condition:|action:|input:|$)))',
            re.MULTILINE | re.DOTALL
        )
        for match in action_pattern.finditer(content):
            line_number = content[: match.start()].count("\n") + 1
            service_match = re.search(r'service:\s*["\']([^"\']+)["\']', match.group(1))
            if service_match:
                patterns.append(
                    ActionPattern(
                        service=service_match.group(1),
                        file_path=file_path,
                        line_number=line_number,
                    )
                )

        return patterns

    def _extract_dependencies(self, raw_content: str) -> List[Dependency]:
        """Extract dependencies from YAML content.

        Args:
            raw_content: YAML content

        Returns:
            List of Dependency objects
        """
        dependencies: List[Dependency] = []
        seen: Set[str] = set()

        # Extract service calls: domain.service
        service_pattern = re.compile(r'service:\s*["\']?(\w+)\.(\w+)["\']?')
        for match in service_pattern.finditer(raw_content):
            domain = match.group(1)
            service = match.group(2)
            dep_name = f"{domain}/{service}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="external",
                    )
                )

        # Extract entity IDs - standard YAML format
        entity_pattern = re.compile(r'entity_id:\s*["\']?(\w+)\.(\w+)["\']?')
        for match in entity_pattern.finditer(raw_content):
            domain = match.group(1)
            entity = match.group(2)
            dep_name = f"{domain}/{entity}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="entity",
                    )
                )

        # Extract entity IDs from !input references (Home Assistant blueprint format)
        # Pattern: entity_id: !input 'variable_name' or entity_id: !input "variable_name"
        input_entity_pattern = re.compile(r'entity_id:\s*!input\s*[\'"]([^\'"]+)[\'"]')
        for match in input_entity_pattern.finditer(raw_content):
            var_name = match.group(1)
            # !input variables are entity references
            dep_name = f"!input/{var_name}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="entity",
                    )
                )

        # Extract !input variables (Home Assistant specific)
        input_pattern = re.compile(r'!input\s+["\']([^"\']+)["\']')
        for match in input_pattern.finditer(raw_content):
            var_name = match.group(1)
            dep_name = f"!input/{var_name}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="input",
                    )
                )

        return dependencies

    @staticmethod
    def _classify_module(name: str) -> str:
        """Classify a module as standard, external, or entity.

        Args:
            name: Module name to classify.

        Returns:
            "entity" if it's an entity ID, "external" otherwise.
        """
        if "." in name:
            domain = name.split(".")[0]
            # Common Home Assistant domains
            ha_domains = {
                "automation", "binary_sensor", "camera", "climate", "configurator",
                "counter", "date", "datetime", "device_tracker", "geo_location",
                "group", "homeassistant", "history_states", "homekit", "input_boolean",
                "input_button", "input_datetime", "input_number", "input_select",
                "input_text", "light", "lock", "mailbox", "notify", "persistent_notification",
                "person", "phone_device", "proximity", "recorder", "remote", "scene",
                "script", "sensor", "simple_alarm", "sun", "switch", "timer", "tts",
                "uptime", "updater", "vacuum", "valve", "verisure", "weather", "zone",
                "media_player", "fan", "cover", "alarm_control_panel", "stt", "vacuum",
            }
            if domain in ha_domains:
                return "entity"
        return "external"
