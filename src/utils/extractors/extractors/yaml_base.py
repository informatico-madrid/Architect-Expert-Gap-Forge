# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
YAML/Blueprint Extraction Base Module

Provides base types and patterns for extracting Home Assistant blueprint
and YAML automation patterns.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class YamlPatternType(str, Enum):
    """Type of YAML pattern extracted."""

    BLUEPRINT = "blueprint"
    TRIGGER = "trigger"
    CONDITION = "condition"
    ACTION = "action"
    INPUT = "input"
    JINJA_EXPRESSION = "jinja_expression"


class JinjaTokenType(str, Enum):
    """Type of Jinja token extracted."""

    VARIABLE = "variable"
    FILTER = "filter"
    TEST = "test"
    LOOP = "loop"
    CONDITIONAL = "conditional"
    STATEMENT = "statement"


@dataclass(frozen=True)
class BlueprintPattern:
    """Pattern representing a Home Assistant blueprint definition.

    Attributes:
        name: Blueprint name
        description: Blueprint description
        domain: Blueprint domain (automation, scene, etc.)
        input: Input parameters definition
        file_path: Path to the source YAML file
        line_number: Line number where the pattern was found
        source_url: Optional source URL
        pattern_type: Type of pattern (always BLUEPRINT)
        data: Dictionary containing pattern-specific data
    """

    name: str
    description: str
    domain: str
    input: Dict[str, Any]
    file_path: str
    line_number: int
    source_url: Optional[str] = None
    pattern_type: YamlPatternType = YamlPatternType.BLUEPRINT

    def __post_init__(self):
        object.__setattr__(
            "data",
            {
                "name": self.name,
                "description": self.description,
                "domain": self.domain,
                "input": self.input,
                "source_url": self.source_url,
            },
        )


@dataclass(frozen=True)
class TriggerPattern:
    """Pattern representing a trigger definition.

    Attributes:
        platform: Trigger platform (time_pattern, state, event, etc.)
        file_path: Path to the source YAML file
        line_number: Line number where the pattern was found
        conditions: Optional trigger conditions
        for_duration: Optional time duration
        entity_id: Optional entity ID
        attribute: Optional attribute name
        from_value: Optional from value
        to_value: Optional to value
        pattern_type: Type of pattern (always TRIGGER)
        data: Dictionary containing pattern-specific data
    """

    platform: str
    file_path: str
    line_number: int
    conditions: Optional[Dict[str, Any]] = None
    for_duration: Optional[str] = None
    entity_id: Optional[str] = None
    attribute: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    pattern_type: YamlPatternType = YamlPatternType.TRIGGER

    def __post_init__(self):
        object.__setattr__(
            "data",
            {
                "platform": self.platform,
                "conditions": self.conditions,
                "for": self.for_duration,
                "entity_id": self.entity_id,
                "attribute": self.attribute,
                "from": self.from_value,
                "to": self.to_value,
            },
        )


@dataclass(frozen=True)
class ConditionPattern:
    """Pattern representing a condition definition.

    Attributes:
        condition: Condition type (state, time, numeric_state, etc.)
        file_path: Path to the source YAML file
        line_number: Line number where the pattern was found
        entity_id: Optional entity ID
        state: Optional expected state
        attribute: Optional attribute name
        value: Optional expected value
        before: Optional time before
        after: Optional time after
        before_state: Optional state before
        after_state: Optional state after
        pattern_type: Type of pattern (always CONDITION)
        data: Dictionary containing pattern-specific data
    """

    condition: str
    file_path: str
    line_number: int
    entity_id: Optional[str] = None
    state: Optional[str] = None
    attribute: Optional[str] = None
    value: Optional[str] = None
    before: Optional[str] = None
    after: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    pattern_type: YamlPatternType = YamlPatternType.CONDITION

    def __post_init__(self):
        object.__setattr__(
            "data",
            {
                "condition": self.condition,
                "entity_id": self.entity_id,
                "state": self.state,
                "attribute": self.attribute,
                "value": self.value,
                "before": self.before,
                "after": self.after,
                "before_state": self.before_state,
                "after_state": self.after_state,
            },
        )


@dataclass(frozen=True)
class ActionPattern:
    """Pattern representing an action definition.

    Attributes:
        service: Service call (domain.service)
        file_path: Path to the source YAML file
        line_number: Line number where the pattern was found
        data: Optional service data
        entity_id: Optional entity ID
        target: Optional target definition
        alias: Optional action alias
        pattern_type: Type of pattern (always ACTION)
    """

    service: str
    file_path: str
    line_number: int
    data: Optional[Dict[str, Any]] = None
    entity_id: Optional[str] = None
    target: Optional[Dict[str, Any]] = None
    alias: Optional[str] = None
    pattern_type: YamlPatternType = YamlPatternType.ACTION

    def __post_init__(self):
        object.__setattr__(
            "data",
            {
                "service": self.service,
                "data": self.data,
                "entity_id": self.entity_id,
                "target": self.target,
                "alias": self.alias,
            },
        )


@dataclass(frozen=True)
class JinjaExpressionPattern:
    """Pattern representing a Jinja expression.

    Attributes:
        expression: The raw Jinja expression
        expression_type: Type of expression (variable, filter, test, etc.)
        file_path: Path to the source YAML file
        line_number: Line number where the pattern was found
        variable_name: Optional variable name if extracted
        filter_name: Optional filter name if applied
        pattern_type: Type of pattern (always JINJA_EXPRESSION)
        data: Dictionary containing pattern-specific data
    """

    expression: str
    expression_type: str
    file_path: str
    line_number: int
    variable_name: Optional[str] = None
    filter_name: Optional[str] = None
    pattern_type: YamlPatternType = YamlPatternType.JINJA_EXPRESSION

    def __post_init__(self):
        object.__setattr__(
            "data",
            {
                "expression": self.expression,
                "type": self.expression_type,
                "variable": self.variable_name,
                "filter": self.filter_name,
            },
        )


@dataclass(frozen=True)
class JinjaVariableToken:
    """Token representing a Jinja variable.

    Attributes:
        name: Variable name
        file_path: Path to the file
        line_number: Line number
        is_safe: Whether the variable is safe (double braces)
        token_type: Type of token (always VARIABLE)
        data: Dictionary with name and is_safe
    """

    name: str
    file_path: str
    line_number: int
    is_safe: bool = False
    token_type: JinjaTokenType = JinjaTokenType.VARIABLE
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__("data", {"name": self.name, "is_safe": self.is_safe})


@dataclass(frozen=True)
class JinjaFilterToken:
    """Token representing a Jinja filter.

    Attributes:
        source: Source variable/expression
        filter: Filter name
        file_path: Path to the file
        line_number: Line number
        args: Optional filter arguments
        token_type: Type of token (always FILTER)
        data: Dictionary with source, filter, and args
    """

    source: str
    filter: str
    file_path: str
    line_number: int
    args: Optional[str] = None
    token_type: JinjaTokenType = JinjaTokenType.FILTER
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            "data", {"source": self.source, "filter": self.filter, "args": self.args}
        )


@dataclass(frozen=True)
class JinjaTestToken:
    """Token representing a Jinja test.

    Attributes:
        source: Source variable/expression
        test: Test name
        file_path: Path to the file
        line_number: Line number
        token_type: Type of token (always TEST)
        data: Dictionary with source and test
    """

    source: str
    test: str
    file_path: str
    line_number: int
    token_type: JinjaTokenType = JinjaTokenType.TEST
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__("data", {"source": self.source, "test": self.test})


@dataclass(frozen=True)
class JinjaLoopToken:
    """Token representing a Jinja loop.

    Attributes:
        loop_variable: Loop variable name
        collection: Collection being iterated
        file_path: Path to the file
        line_number: Line number
        loop_type: Type of loop (for, with)
        token_type: Type of token (always LOOP)
        data: Dictionary with loop_variable and collection
    """

    loop_variable: str
    collection: str
    file_path: str
    line_number: int
    loop_type: str = "for"
    token_type: JinjaTokenType = JinjaTokenType.LOOP
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            "data",
            {"loop_variable": self.loop_variable, "collection": self.collection},
        )


@dataclass(frozen=True)
class JinjaConditionalToken:
    """Token representing a Jinja conditional.

    Attributes:
        file_path: Path to the file
        line_number: Line number
        condition: Condition expression
        is_else: Whether this is an else block
        is_elif: Whether this is an elif block
        token_type: Type of token (always CONDITIONAL)
        data: Dictionary with condition and is_else/is_elif flags
    """

    file_path: str
    line_number: int
    condition: Optional[str] = None
    is_else: bool = False
    is_elif: bool = False
    token_type: JinjaTokenType = JinjaTokenType.CONDITIONAL
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.is_else:
            object.__setattr__("data", {"condition": "else", "is_else": True})
        elif self.is_elif:
            object.__setattr__("data", {"condition": self.condition, "is_elif": True})
        else:
            object.__setattr__("data", {"condition": self.condition, "is_elif": False})


@dataclass(frozen=True)
class JinjaStatementToken:
    """Token representing a Jinja statement.

    Attributes:
        statement_type: Type of statement (set, if, for, block, macro, etc.)
        content: Statement content
        file_path: Path to the file
        line_number: Line number
        token_type: Type of token (always STATEMENT)
        data: Dictionary with type and content
    """

    statement_type: str
    content: str
    file_path: str
    line_number: int
    token_type: JinjaTokenType = JinjaTokenType.STATEMENT
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            "data", {"type": self.statement_type, "content": self.content}
        )


# Regex patterns for extraction

# Jinja variable patterns
JINJA_VAR_PATTERN = re.compile(
    r"\{\{([^{}]+?)\}\}",  # Double braces (unsafe in HTML context)
    re.MULTILINE,
)
JINJA_SAFE_VAR_PATTERN = re.compile(
    r"\{\{([^{}]+?)\}\}",  # Double braces (alias for JINJA_VAR_PATTERN)
    re.MULTILINE,
)

# Jinja filter patterns
JINJA_FILTER_PATTERN = re.compile(r"\{\{([^{}]+?)\s*\|([^{}]+?)\}\}", re.MULTILINE)

# Jinja test patterns
JINJA_TEST_PATTERN = re.compile(
    r"\{\{([^{}]+?)\s+(is|is\s+not)\s+([^{}]+?)\}\}", re.MULTILINE
)

# Jinja loop patterns
JINJA_LOOP_PATTERN = re.compile(
    r"\{%\s*for\s+([^{}]+?)\s+in\s+([^{}]+?)\s*%\}", re.MULTILINE
)

# Jinja conditional patterns
JINJA_IF_PATTERN = re.compile(r"\{%\s*if\s+([^{}]+?)\s*%\}", re.MULTILINE)
JINJA_ELSE_PATTERN = re.compile(r"\{%\s*else\s*%\}", re.MULTILINE)
JINJA_ELIF_PATTERN = re.compile(r"\{%\s*elif\s+([^{}]+?)\s*%\}", re.MULTILINE)

# Jinja statement patterns
JINJA_STATEMENT_PATTERN = re.compile(
    r"\{%\s*(set|for|if|block|macro|extends|include|import|from)\s+([^{}]+?)\s*%\}",
    re.MULTILINE,
)


def extract_jinja_variables(content: str, file_path: str) -> List[JinjaVariableToken]:
    """Extract Jinja variables from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaVariableToken objects
    """
    tokens: List[JinjaVariableToken] = []
    for match in JINJA_VAR_PATTERN.finditer(content):
        var_name = match.group(1).strip()
        if (
            var_name
            and not var_name.startswith("if")
            and not var_name.startswith("for")
        ):
            line_number = content[: match.start()].count("\n") + 1
            tokens.append(
                JinjaVariableToken(
                    name=var_name,
                    file_path=file_path,
                    line_number=line_number,
                    is_safe=False,
                )
            )
    return tokens


def extract_jinja_filters(content: str, file_path: str) -> List[JinjaFilterToken]:
    """Extract Jinja filters from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaFilterToken objects
    """
    tokens: List[JinjaFilterToken] = []
    for match in JINJA_FILTER_PATTERN.finditer(content):
        source = match.group(1).strip()
        filter_name = match.group(2).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaFilterToken(
                source=source,
                filter=filter_name,
                file_path=file_path,
                line_number=line_number,
            )
        )
    return tokens


def extract_jinja_tests(content: str, file_path: str) -> List[JinjaTestToken]:
    """Extract Jinja tests from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaTestToken objects
    """
    tokens: List[JinjaTestToken] = []
    for match in JINJA_TEST_PATTERN.finditer(content):
        source = match.group(1).strip()
        test_name = match.group(3).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaTestToken(
                source=source,
                test=test_name,
                file_path=file_path,
                line_number=line_number,
            )
        )
    return tokens


def extract_jinja_loops(content: str, file_path: str) -> List[JinjaLoopToken]:
    """Extract Jinja loops from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaLoopToken objects
    """
    tokens: List[JinjaLoopToken] = []
    for match in JINJA_LOOP_PATTERN.finditer(content):
        loop_var = match.group(1).strip()
        collection = match.group(2).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaLoopToken(
                loop_variable=loop_var,
                collection=collection,
                file_path=file_path,
                line_number=line_number,
            )
        )
    return tokens


def extract_jinja_conditionals(
    content: str, file_path: str
) -> List[JinjaConditionalToken]:
    """Extract Jinja conditionals from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaConditionalToken objects
    """
    tokens: List[JinjaConditionalToken] = []

    # If statements
    for match in JINJA_IF_PATTERN.finditer(content):
        condition = match.group(1).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaConditionalToken(
                condition=condition,
                file_path=file_path,
                line_number=line_number,
                is_else=False,
                is_elif=False,
            )
        )

    # Elif statements
    for match in JINJA_ELIF_PATTERN.finditer(content):
        condition = match.group(1).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaConditionalToken(
                condition=condition,
                file_path=file_path,
                line_number=line_number,
                is_else=False,
                is_elif=True,
            )
        )

    # Else statements
    for match in JINJA_ELSE_PATTERN.finditer(content):
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaConditionalToken(
                condition=None,
                file_path=file_path,
                line_number=line_number,
                is_else=True,
                is_elif=False,
            )
        )

    return tokens


def extract_jinja_statements(content: str, file_path: str) -> List[JinjaStatementToken]:
    """Extract Jinja statements from template content.

    Args:
        content: Template content
        file_path: Path to the template file

    Returns:
        List of JinjaStatementToken objects
    """
    tokens: List[JinjaStatementToken] = []
    for match in JINJA_STATEMENT_PATTERN.finditer(content):
        statement_type = match.group(1).strip()
        content_str = match.group(2).strip()
        line_number = content[: match.start()].count("\n") + 1
        tokens.append(
            JinjaStatementToken(
                statement_type=statement_type,
                content=content_str,
                file_path=file_path,
                line_number=line_number,
            )
        )
    return tokens
