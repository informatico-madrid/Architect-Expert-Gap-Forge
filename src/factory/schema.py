#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Factory Schema Definitions

Factory-specific Pydantic v2 immutable models for agentic trajectory generation.
Includes turn types, trajectory modes, error simulation, and trajectory structures.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

import json
import logging
from enum import Enum
from typing import Any

import xml.etree.ElementTree as ET

from pydantic import BaseModel, Field

from src.utils.schema import (
    CompositionReport,
    DatasetRecord,
    Message,
)

logger = logging.getLogger(__name__)

# XML tool call format constants (qwen3_coder pattern)
XML_TOOL_CALL_START = "<tool_call>"
XML_TOOL_CALL_END = "</tool_call>"
XML_TOOL_NAME_START = "<tool_name>"
XML_TOOL_NAME_END = "</tool_name>"
XML_TOOL_ARGS_START = "<tool_args>"
XML_TOOL_ARGS_END = "</tool_args>"

# Threshold for auto-selecting XML format (bytes in JSON representation)
XML_SIZE_THRESHOLD = 500


def serialize_tool_call_xml(name: str, args: dict) -> str:
    """
    Serialize a tool call to XML format (qwen3_coder pattern).

    This format avoids escaping issues with multiline code, quotes, and special
    characters that would require escaping in JSON.

    Args:
        name: Tool name
        args: Tool arguments dictionary

    Returns:
        XML-formatted tool call string
    """
    # Build XML structure
    tool_call = ET.Element("tool_call")

    tool_name_elem = ET.SubElement(tool_call, "tool_name")
    tool_name_elem.text = name

    tool_args_elem = ET.SubElement(tool_call, "tool_args")
    # Use the raw dict as content - ElementTree handles serialization
    for key, value in args.items():
        _add_dict_as_xml(tool_args_elem, key, value)

    # Convert to string with pretty formatting preserved
    xml_str = ET.tostring(tool_call, encoding="unicode")

    # Wrap in tool_call tags if not already included
    if not xml_str.startswith(XML_TOOL_CALL_START):
        xml_str = f"{XML_TOOL_CALL_START}{xml_str}{XML_TOOL_CALL_END}"

    return xml_str


def _add_dict_as_xml(parent: ET.Element, key: str, value: Any) -> None:
    """Recursively add a dictionary to XML elements."""
    item = ET.SubElement(parent, "item")
    item.set("key", str(key))

    if value is None:
        item.set("type", "null")
    elif isinstance(value, bool):
        item.set("type", "bool")
        item.text = str(value)
    elif isinstance(value, int):
        item.set("type", "int")
        item.text = str(value)
    elif isinstance(value, float):
        item.set("type", "float")
        item.text = str(value)
    elif isinstance(value, dict):
        item.set("type", "dict")
        for k, v in value.items():
            _add_dict_as_xml(item, k, v)
    elif isinstance(value, list):
        item.set("type", "list")
        for i, v in enumerate(value):
            _add_dict_as_xml(item, str(i), v)
    else:
        item.set("type", "str")
        item.text = str(value)


def parse_tool_call_xml(text: str) -> tuple[str, dict]:
    """
    Parse a tool call from XML format back to name and arguments.

    Args:
        text: XML-formatted tool call string

    Returns:
        Tuple of (tool_name, tool_args_dict)

    Raises:
        ValueError: If XML is malformed or missing required elements
    """
    # Clean up whitespace
    text = text.strip()

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        logger.error("Failed to parse XML tool call: %s", e)
        raise ValueError(f"Invalid XML format: {e}") from e

    # Handle both wrapped and unwrapped tool_call root
    if root.tag == "tool_call":
        tool_name_elem = root.find("tool_name")
        tool_args_elem = root.find("tool_args")
    else:
        # Assume it's a tool_name or tool_args element
        tool_name_elem = root.find(".//tool_name")
        tool_args_elem = root.find(".//tool_args")

    if tool_name_elem is None:
        raise ValueError("Missing <tool_name> element in XML")

    tool_name = tool_name_elem.text or ""

    if tool_args_elem is None:
        return tool_name, {}

    # Parse arguments from XML
    tool_args = _parse_xml_to_dict(tool_args_elem)

    return tool_name, tool_args


def _parse_xml_to_dict(element: ET.Element) -> dict:
    """Recursively parse XML elements back to a dictionary."""
    result: dict = {}

    for item in element.findall("item"):
        key = item.get("key")
        if key is None:
            continue

        value_type = item.get("type", "str")

        if value_type == "null":
            result[key] = None
        elif value_type == "bool":
            result[key] = item.text.lower() == "true" if item.text else False
        elif value_type == "int":
            result[key] = int(item.text) if item.text else 0
        elif value_type == "float":
            result[key] = float(item.text) if item.text else 0.0
        elif value_type == "dict":
            result[key] = _parse_xml_to_dict(item)
        elif value_type == "list":
            result[key] = _parse_xml_to_list(item)
        else:
            # Default to string
            result[key] = item.text if item.text else ""

    return result


def _parse_xml_to_list(element: ET.Element) -> list:
    """Recursively parse XML elements back to a list."""
    result: list = []

    # Find all items and sort by index
    items = element.findall("item")
    sorted_items = sorted(
        items, key=lambda x: int(x.get("key", 0)) if x.get("key", "").isdigit() else 0
    )

    for item in sorted_items:
        value_type = item.get("type", "str")

        if value_type == "null":
            result.append(None)
        elif value_type == "bool":
            result.append(item.text.lower() == "true" if item.text else False)
        elif value_type == "int":
            result.append(int(item.text) if item.text else 0)
        elif value_type == "float":
            result.append(float(item.text) if item.text else 0.0)
        elif value_type == "dict":
            result.append(_parse_xml_to_dict(item))
        elif value_type == "list":
            result.append(_parse_xml_to_list(item))
        else:
            result.append(item.text if item.text else "")

    return result


def should_use_xml_format(args: dict) -> bool:
    """
    Determine if XML format should be used based on argument size.

    Automatically selects XML format when the JSON serialized args exceed
    the threshold to avoid escaping issues with large/multiline content.

    Args:
        args: Tool arguments dictionary

    Returns:
        True if XML format should be used (>500 bytes in JSON), False otherwise
    """
    if not args:
        return False

    json_size = len(json.dumps(args))
    return json_size > XML_SIZE_THRESHOLD


class TurnType(str, Enum):
    """Type of turn in an agentic trajectory."""

    OBSERVATION = "observation"
    REASONING = "reasoning"
    ACTION = "action"
    ERROR = "error"
    CORRECT = "correct"
    VERIFY = "verify"


class TrajectoryMode(str, Enum):
    """Mode for trajectory generation."""

    HARD_QUERY = "hard_query"
    EXPLICIT = "explicit"
    NO_CALL = "no_call"


class SimulatedErrorType(str, Enum):
    """Type of simulated error for trajectory injection."""

    TOOL_FAILURE = "tool_failure"
    WRONG_RESULT = "wrong_result"
    CASCADE_FAILURE = "cascade_failure"


class Turn(BaseModel):
    """A single turn in an agentic trajectory."""

    model_config = {"frozen": True}

    turn_index: int = Field(description="Index of this turn in the trajectory")
    turn_type: TurnType = Field(
        description="Type of turn: observation/reasoning/action/error/correct/verify"
    )
    content: str = Field(description="Turn content or tool output")
    tool_name: str | None = Field(default=None, description="Tool name if action turn")
    tool_args: dict | None = Field(
        default=None, description="Tool arguments if action turn"
    )
    tool_result: str | None = Field(default=None, description="Tool execution result")
    reasoning: str | None = Field(
        default=None, description="Model reasoning if available"
    )


class SimulatedError(BaseModel):
    """Simulated error injected into a trajectory."""

    model_config = {"frozen": True}

    error_type: SimulatedErrorType = Field(description="Type of simulated error")
    turn_index: int = Field(description="Turn index where error is injected")
    description: str = Field(description="Description of the error")
    recovery_turn_index: int | None = Field(
        default=None, description="Index of turn that corrects the error"
    )


class AgenticTrajectory(BaseModel):
    """An agentic multi-turn trajectory with backtracking and error injection."""

    model_config = {"frozen": True}

    seed_id: str = Field(description="Seed identifier")
    mode: TrajectoryMode = Field(
        description="Trajectory generation mode: hard_query/explicit/no_call"
    )
    turns: list[Turn] = Field(default_factory=list, description="List of turns")
    errors: list[SimulatedError] = Field(
        default_factory=list, description="Injected errors in trajectory"
    )
    use_case: str = Field(description="Use case domain (e.g., home_assistant)")
    messages: list[Message] = Field(
        default_factory=list, description="Serialized ChatML messages"
    )


# Re-export shared entities from utils schema
__all__ = [
    "AgenticTrajectory",
    "CompositionReport",
    "DatasetRecord",
    "Message",
    "parse_tool_call_xml",
    "serialize_tool_call_xml",
    "should_use_xml_format",
    "SimulatedError",
    "SimulatedErrorType",
    "TrajectoryMode",
    "Turn",
    "TurnType",
    "XML_SIZE_THRESHOLD",
]
