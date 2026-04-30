#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Anchor Dataset Downloader Module

Downloads anchor datasets from HuggingFace Hub using streaming, parses them
in their native format (xlam-function-calling-60k, FineTome-100k, Magicoder),
applies subsampling by token budget, and exports partial JSONL files.

Location: src/curation/anchor_dataset_downloader.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import tiktoken

from src.utils.schema import DatasetRecord, Message

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass(slots=True, frozen=True)
class AnchorDatasetConfig:
    """Configuration for an anchor dataset from HuggingFace Hub.

    Attributes:
        hf_id: HuggingFace dataset ID (e.g., 'Salesforce/xlam-function-calling-60k')
        split: Dataset split to download (e.g., 'train', 'test')
        format: Native format of the dataset ('xlam', 'sharegpt', 'openai_messages')
        token_budget_pct: Percentage of total token budget allocated to this dataset
    """

    hf_id: str
    split: str = "train"
    format: str = "sharegpt"
    token_budget_pct: float = 70.0


# =============================================================================
# ROLE MAPPINGS
# =============================================================================

# Role mapping from various formats to ChatML standard
_SHAREGPT_ROLE_MAPPING: dict[str, str] = {
    "human": "user",
    "gpt": "assistant",
    "system": "system",
    "tool": "tool",
}

_XLAM_ROLE_MAPPING: dict[str, str] = {
    "human": "user",
    "gpt": "assistant",
}


# =============================================================================
# ANCHOR DATASET DOWNLOADER
# =============================================================================


class AnchorDatasetDownloader:
    """Downloads, parses, subsamples, and exports anchor datasets from HuggingFace Hub.

    This class provides a complete workflow for downloading anchor datasets,
    converting them to ChatML format, applying token-based subsampling,
    and exporting to JSONL.

    Supported dataset formats:
    - xlam: xlam-function-calling-60k format with function_call field
    - sharegpt: FineTome-100k and Magicoder format with conversations array
    - openai_messages: Already in ChatML format with messages array

    Example:
        >>> configs = [
        ...     AnchorDatasetConfig(
        ...         hf_id="Salesforce/xlam-function-calling-60k",
        ...         split="train",
        ...         format="xlam",
        ...         token_budget_pct=30.0
        ...     ),
        ... ]
        >>> downloader = AnchorDatasetDownloader(configs)
        >>> records = downloader.download_all()
        >>> downloader.export(records, Path("output.jsonl"))
    """

    def __init__(
        self,
        configs: list[AnchorDatasetConfig],
        tokenizer_model: str = "cl100k_base",
    ) -> None:
        """Initialize the AnchorDatasetDownloader.

        Args:
            configs: List of anchor dataset configurations.
            tokenizer_model: TikToken model for token counting.
        """
        self._configs = configs
        self._tokenizer = tiktoken.get_encoding(tokenizer_model)

    @property
    def configs(self) -> list[AnchorDatasetConfig]:
        """Return the list of dataset configurations."""
        return self._configs

    def download(self, config: AnchorDatasetConfig) -> Iterator[dict[str, Any]]:
        """Download a dataset from HuggingFace Hub using streaming.

        This method uses the datasets library's streaming mode to avoid
        downloading the entire dataset to disk.

        Args:
            config: Configuration for the dataset to download.

        Yields:
            Individual records from the dataset.

        Note:
            This method attempts to use the datasets library. If not available,
            it falls back to using huggingface_hub for file-based downloads.
        """
        logger.info("Downloading dataset %s (split: %s)", config.hf_id, config.split)

        try:
            # Try using the datasets library for streaming
            from datasets import load_dataset

            dataset = load_dataset(
                config.hf_id,
                split=config.split,
                streaming=True,
            )

            for record in dataset:
                yield record

        except ImportError:
            # Fallback to huggingface_hub snapshot_download
            logger.warning(
                "datasets library not available, using huggingface_hub fallback"
            )
            yield from self._download_via_hub(config)

    def _download_via_hub(self, config: AnchorDatasetConfig) -> Iterator[dict[str, Any]]:
        """Download dataset files using huggingface_hub.

        This is a fallback method when the datasets library is not available.

        Args:
            config: Configuration for the dataset to download.

        Yields:
            Individual records from the dataset files.
        """
        from huggingface_hub import list_repo_files

        # List all data files in the repository
        files = list(list_repo_files(config.hf_id, repo_type="dataset"))

        # Filter for common data file extensions
        data_files = [f for f in files if f.endswith((".json", ".jsonl"))]

        if not data_files:
            logger.warning("No data files found in %s", config.hf_id)
            return

        # Download and parse each file
        from huggingface_hub import hf_hub_download

        for file_path in data_files:
            try:
                local_path = hf_hub_download(
                    repo_id=config.hf_id,
                    filename=file_path,
                    repo_type="dataset",
                )

                # Parse based on file extension
                if file_path.endswith(".jsonl"):
                    with open(local_path, encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                yield json.loads(line)
                elif file_path.endswith(".json"):
                    import ast

                    with open(local_path, encoding="utf-8") as f:
                        content = f.read()
                        # Try to parse as JSON array
                        try:
                            data = json.loads(content)
                            if isinstance(data, list):
                                yield from data
                            else:
                                yield data
                        except json.JSONDecodeError:
                            # Try Python literal eval
                            try:
                                data = ast.literal_eval(content)
                                if isinstance(data, list):
                                    yield from data
                                else:
                                    yield data
                            except (ValueError, SyntaxError):
                                logger.warning("Could not parse file: %s", file_path)

            except Exception as e:
                logger.warning("Failed to download file %s: %s", file_path, e)
                continue

    def parse(
        self,
        data: Iterator[dict[str, Any]],
        format_type: str,
        origin: str,
    ) -> Iterator[DatasetRecord]:
        """Parse raw dataset records into DatasetRecord format.

        Args:
            data: Iterator of raw dataset records.
            format_type: Format type ('xlam', 'sharegpt', 'openai_messages').
            origin: Origin identifier for metadata.

        Yields:
            DatasetRecord objects in ChatML format.
        """
        for record in data:
            try:
                if format_type == "xlam":
                    messages = self._parse_xlam(record)
                elif format_type == "sharegpt":
                    messages = self._parse_sharegpt(record)
                elif format_type == "openai_messages":
                    messages = self._parse_openai_messages(record)
                else:
                    logger.warning("Unknown format type: %s, skipping record", format_type)
                    continue

                # Calculate token count
                content = " ".join(m.content for m in messages)
                token_count = len(self._tokenizer.encode(content))

                dataset_record = DatasetRecord(
                    messages=messages,
                    metadata={
                        "origin": origin,
                        "type": "anchor",
                        "format": "chatml",
                        "token_count": token_count,
                    },
                )

                yield dataset_record

            except Exception as e:
                logger.warning("Failed to parse record: %s", e)
                continue

    def _parse_xlam(self, record: dict[str, Any]) -> list[Message]:
        """Parse xlam-function-calling-60k format to ChatML.

        Args:
            record: Raw xlam format record.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            ValueError: If required fields are missing.
        """
        if "conversations" not in record:
            raise ValueError("xlam format requires 'conversations' field")

        conversations = record["conversations"]
        messages = []

        for conv in conversations:
            if "from" not in conv or "value" not in conv:
                continue

            role = _XLAM_ROLE_MAPPING.get(conv["from"], conv["from"])
            content = conv["value"]

            # Handle function_call if present
            if "function_call" in conv:
                fc = conv["function_call"]
                content = f"{content}\n\n<tool_call>{fc['name']}</tool_call>"

            messages.append(Message(role=role, content=content))

        return messages

    def _parse_sharegpt(self, record: dict[str, Any]) -> list[Message]:
        """Parse ShareGPT format (FineTome, Magicoder) to ChatML.

        Args:
            record: Raw ShareGPT format record.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            ValueError: If required fields are missing.
        """
        if "conversations" not in record:
            raise ValueError("ShareGPT format requires 'conversations' field")

        conversations = record["conversations"]
        messages = []

        for conv in conversations:
            if "from" not in conv or "value" not in conv:
                continue

            role = _SHAREGPT_ROLE_MAPPING.get(conv["from"], conv["from"])
            content = conv["value"]

            messages.append(Message(role=role, content=content))

        return messages

    def _parse_openai_messages(self, record: dict[str, Any]) -> list[Message]:
        """Parse OpenAI Messages format to ChatML.

        This is a passthrough since OpenAI Messages is already in ChatML format.

        Args:
            record: Raw OpenAI Messages format record.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            ValueError: If required fields are missing.
        """
        if "messages" not in record:
            raise ValueError("OpenAI Messages format requires 'messages' field")

        messages_data = record["messages"]
        messages = []

        for msg in messages_data:
            if "role" not in msg or "content" not in msg:
                continue

            messages.append(Message(role=msg["role"], content=msg["content"]))

        return messages

    def subsample(
        self,
        records: list[DatasetRecord],
        token_budget: int,
    ) -> list[DatasetRecord]:
        """Subsample records to fit within token budget.

        Selects records in order until the token budget is exhausted.

        Args:
            records: List of DatasetRecord objects.
            token_budget: Maximum number of tokens to include.

        Returns:
            List of DatasetRecord objects within token budget.
        """
        selected = []
        total_tokens = 0

        for record in records:
            token_count = record.metadata.get("token_count", 0)

            if total_tokens + token_count <= token_budget:
                selected.append(record)
                total_tokens += token_count
            else:
                # Check if we can still add this record
                if token_count <= token_budget - total_tokens:
                    selected.append(record)
                    total_tokens += token_count

        logger.info(
            "Subsampled %d records with %d tokens (budget: %d)",
            len(selected),
            total_tokens,
            token_budget,
        )

        return selected

    def export(
        self,
        records: list[DatasetRecord],
        output_path: Path,
    ) -> None:
        """Export records to JSONL format.

        Args:
            records: List of DatasetRecord objects to export.
            output_path: Path to the output JSONL file.

        Raises:
            IOError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")

        logger.info("Exported %d records to %s", len(records), output_path)

    def download_all(
        self,
        total_token_budget: int | None = None,
    ) -> list[DatasetRecord]:
        """Download all configured datasets, parse, and subsample.

        Args:
            total_token_budget: Total token budget for all datasets combined.
                If None, no subsampling is applied.

        Returns:
            List of all downloaded and processed DatasetRecord objects.
        """
        all_records = []

        # Calculate token budget per dataset based on percentages
        if total_token_budget is None:
            token_budgets = {config.hf_id: float("inf") for config in self._configs}
        else:
            token_budgets = {
                config.hf_id: int(total_token_budget * config.token_budget_pct / 100)
                for config in self._configs
            }

        for config in self._configs:
            logger.info(
                "Processing dataset %s with token budget %d",
                config.hf_id,
                token_budgets[config.hf_id],
            )

            # Download
            raw_data = self.download(config)

            # Parse
            parsed_records = list(
                self.parse(raw_data, config.format, config.hf_id)
            )

            logger.info(
                "Downloaded and parsed %d records from %s",
                len(parsed_records),
                config.hf_id,
            )

            # Subsample if budget is specified
            if token_budgets[config.hf_id] != float("inf"):
                parsed_records = self.subsample(
                    parsed_records,
                    token_budgets[config.hf_id],
                )

            all_records.extend(parsed_records)

        logger.info(
            "Total records downloaded: %d",
            len(all_records),
        )

        return all_records


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_anchor_configs(path: Path) -> list[AnchorDatasetConfig]:
    """Load anchor dataset configurations from a YAML file.

    Args:
        path: Path to the anchors configuration YAML file.

    Returns:
        List of AnchorDatasetConfig objects.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config file is invalid.
    """
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None or "anchors" not in data:
        raise ValueError("Config file must contain 'anchors' list")

    configs = []
    for anchor in data["anchors"]:
        configs.append(
            AnchorDatasetConfig(
                hf_id=anchor["hf_id"],
                split=anchor.get("split", "train"),
                format=anchor.get("format", "sharegpt"),
                token_budget_pct=anchor.get("token_budget_pct", 70.0),
            )
        )

    return configs
