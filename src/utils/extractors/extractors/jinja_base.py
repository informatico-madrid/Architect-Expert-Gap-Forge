# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Jinja Template Extraction Base Module

Provides base types and patterns for extracting Jinja template tokens.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class JinjaTokenType(str, Enum):
    """Type of Jinja token extracted."""

    VARIABLE = "variable"
    FILTER = "filter"
    TEST = "test"
    LOOP = "loop"
    CONDITIONAL = "conditional"
    STATEMENT = "statement"


@dataclass
class JinjaVariableToken:
    """Token representing a Jinja variable.

    Attributes:
        name: Variable name
        file_path: Path to the file
        line_number: Line number
        is_safe: Whether the variable is safe (double braces)
    """

    name: str
    file_path: str
    line_number: int
    is_safe: bool = False

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.VARIABLE

    @property
    def data(self) -> Dict[str, Any]:
        return {"name": self.name, "is_safe": self.is_safe}


@dataclass
class JinjaFilterToken:
    """Token representing a Jinja filter.

    Attributes:
        source: Source variable/expression
        filter: Filter name
        file_path: Path to the file
        line_number: Line number
        args: Optional filter arguments
    """

    source: str
    filter: str
    file_path: str
    line_number: int
    args: Optional[str] = None

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.FILTER

    @property
    def data(self) -> Dict[str, Any]:
        return {"source": self.source, "filter": self.filter, "args": self.args}


@dataclass
class JinjaTestToken:
    """Token representing a Jinja test.

    Attributes:
        source: Source variable/expression
        test: Test name
        file_path: Path to the file
        line_number: Line number
    """

    source: str
    test: str
    file_path: str
    line_number: int

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.TEST

    @property
    def data(self) -> Dict[str, Any]:
        return {"source": self.source, "test": self.test}


@dataclass
class JinjaLoopToken:
    """Token representing a Jinja loop.

    Attributes:
        loop_variable: Loop variable name
        collection: Collection being iterated
        file_path: Path to the file
        line_number: Line number
        loop_type: Type of loop (for, with)
    """

    loop_variable: str
    collection: str
    file_path: str
    line_number: int
    loop_type: str = "for"

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.LOOP

    @property
    def data(self) -> Dict[str, Any]:
        return {"loop_variable": self.loop_variable, "collection": self.collection}


@dataclass
class JinjaConditionalToken:
    """Token representing a Jinja conditional.

    Attributes:
        file_path: Path to the file
        line_number: Line number
        condition: Condition expression
        is_else: Whether this is an else block
        is_elif: Whether this is an elif block
    """

    file_path: str
    line_number: int
    condition: Optional[str] = None
    is_else: bool = False
    is_elif: bool = False

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.CONDITIONAL

    @property
    def data(self) -> Dict[str, Any]:
        if self.is_else:
            return {"condition": "else", "is_else": True}
        elif self.is_elif:
            return {"condition": self.condition, "is_elif": True}
        else:
            return {"condition": self.condition, "is_elif": False}


@dataclass
class JinjaStatementToken:
    """Token representing a Jinja statement.

    Attributes:
        statement_type: Type of statement (set, if, for, block, macro, etc.)
        content: Statement content
        file_path: Path to the file
        line_number: Line number
    """

    statement_type: str
    content: str
    file_path: str
    line_number: int

    @property
    def token_type(self) -> JinjaTokenType:
        return JinjaTokenType.STATEMENT

    @property
    def data(self) -> Dict[str, Any]:
        return {"type": self.statement_type, "content": self.content}


# Regex patterns for extraction

# Jinja variable patterns
JINJA_VAR_PATTERN = re.compile(
    r"\{\{([^{}]+?)\}\}",  # Single braces
    re.MULTILINE,
)
JINJA_SAFE_VAR_PATTERN = re.compile(
    r"\{\{([^{}]+?)\}\}",  # Double braces (safe)
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
    r"\{%\s*(set|block|macro|extends|include|import|from)\s+([^{}]+?)\s*%\}",
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
