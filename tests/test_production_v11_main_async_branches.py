#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Tests for main_async branches in production_v11.py to increase coverage."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import src.factory.production_v11 as pv11


@pytest.fixture
def mock_args():
    """Mock args for main_async."""
    args = MagicMock()
    args.gap_dir = "/fake/gap"
    args.taxonomy_file = "/fake/taxonomy.yaml"
    args.output = None
    args.resume = None
    args.workers = 2
    args.theory = False
    args.theory_reps = 1
    args.test = None
    args.limit = None
    return args


@pytest.fixture
def mock_frags():
    """Mock expanded fragments."""
    return [
        {"name": "frag1", "virtual_filename": "file1.py", "_rep": 1},
        {"name": "frag2", "virtual_filename": "file2.py", "_rep": 1},
    ]


def test_main_async_resume_with_pending_frags(
    tmp_path, mock_args, mock_frags, monkeypatch
):
    """Test resume branch where some frags are pending."""

    async def _test():
        mock_args.theory = True
        mock_args.resume = str(tmp_path / "resume.jsonl")
        mock_args.output = str(tmp_path / "output.jsonl")

        # Mock dependencies
        monkeypatch.setattr(
            pv11,
            "load_taxonomy",
            MagicMock(
                return_value={
                    "prompts": {
                        "system": {"theory": "system"},
                        "user": {"theory": "user"},
                    }
                }
            ),
        )
        monkeypatch.setattr(
            pv11,
            "load_master_docs",
            MagicMock(return_value=("master", "changelog", "jinja")),
        )
        monkeypatch.setattr(
            pv11, "get_theory_fragments", MagicMock(return_value=mock_frags)
        )
        monkeypatch.setattr(
            pv11, "load_checkpoint", MagicMock(return_value={"frag1_file1.py_0"})
        )  # one done
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock()
        monkeypatch.setattr(
            pv11, "AsyncFileWriter", MagicMock(return_value=mock_writer)
        )
        mock_tracker = MagicMock()
        mock_tracker.record = AsyncMock()
        mock_tracker.close = MagicMock()
        monkeypatch.setattr(
            pv11, "ProgressTracker", MagicMock(return_value=mock_tracker)
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.factory.production_v11.AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        mock_generate = AsyncMock(return_value={"status": "accepted", "sample": {}})
        monkeypatch.setattr(pv11, "generate_theory_sample_async", mock_generate)

        # Run
        await pv11.main_async(mock_args)

        # Check that generate was called for the pending frag
        assert mock_generate.call_count == 2

    asyncio.run(_test())


def test_main_async_resume_all_processed(tmp_path, mock_args, mock_frags, monkeypatch):
    """Test resume branch where all frags are already processed."""

    async def _test():
        mock_args.theory = True
        mock_args.resume = str(tmp_path / "resume.jsonl")

        # Mock to return all keys done
        done_keys = {"frag1_file1.py_0", "frag2_file2.py_0"}

        monkeypatch.setattr(
            pv11, "load_taxonomy", MagicMock(return_value={"prompts": {}})
        )
        monkeypatch.setattr(
            pv11,
            "_TAX",
            {"prompts": {"system": {"theory": "system"}, "user": {"theory": "user"}}},
        )
        monkeypatch.setattr(
            pv11,
            "load_master_docs",
            MagicMock(return_value=("master", "changelog", "jinja")),
        )
        monkeypatch.setattr(
            pv11, "get_theory_fragments", MagicMock(return_value=mock_frags)
        )
        monkeypatch.setattr(pv11, "load_checkpoint", MagicMock(return_value=done_keys))

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.factory.production_v11.AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        # Run - should return early
        await pv11.main_async(mock_args)

        # No generation should happen
        # Since all processed, it returns without creating writers etc.

    asyncio.run(_test())


def test_main_async_theory_mode(tmp_path, mock_args, mock_frags, monkeypatch):
    """Test theory mode branch."""

    async def _test():
        mock_args.theory = True
        mock_args.output = str(tmp_path / "theory.jsonl")

        monkeypatch.setattr(
            pv11, "load_taxonomy", MagicMock(return_value={"prompts": {}})
        )
        monkeypatch.setattr(
            pv11, "_TAX", {"prompts": {"theory": {"system": "system", "user": "user"}}}
        )
        monkeypatch.setattr(
            pv11,
            "load_master_docs",
            MagicMock(return_value=("master", "changelog", "jinja")),
        )
        monkeypatch.setattr(
            pv11, "get_theory_fragments", MagicMock(return_value=mock_frags)
        )
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock()
        monkeypatch.setattr(
            pv11, "AsyncFileWriter", MagicMock(return_value=mock_writer)
        )
        mock_tracker = MagicMock()
        mock_tracker.record = AsyncMock()
        mock_tracker.close = MagicMock()
        monkeypatch.setattr(
            pv11, "ProgressTracker", MagicMock(return_value=mock_tracker)
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.factory.production_v11.AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        mock_generate = AsyncMock(return_value={"status": "accepted", "sample": {}})
        monkeypatch.setattr(pv11, "generate_theory_sample_async", mock_generate)

        await pv11.main_async(mock_args)

        # Check generate_theory_sample_async was called
        assert mock_generate.call_count == 2  # for 2 frags

    asyncio.run(_test())


def test_main_async_with_output_specified(tmp_path, mock_args, mock_frags, monkeypatch):
    """Test when output is explicitly specified."""

    async def _test():
        mock_args.theory = True
        mock_args.output = str(tmp_path / "output.jsonl")

        monkeypatch.setattr(
            pv11, "load_taxonomy", MagicMock(return_value={"prompts": {}})
        )
        monkeypatch.setattr(
            pv11, "_TAX", {"prompts": {"theory": {"system": "system", "user": "user"}}}
        )
        monkeypatch.setattr(
            pv11,
            "load_master_docs",
            MagicMock(return_value=("master", "changelog", "jinja")),
        )
        monkeypatch.setattr(
            pv11, "get_theory_fragments", MagicMock(return_value=mock_frags)
        )
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock()
        monkeypatch.setattr(
            pv11, "AsyncFileWriter", MagicMock(return_value=mock_writer)
        )
        mock_tracker = MagicMock()
        mock_tracker.record = AsyncMock()
        mock_tracker.close = MagicMock()
        monkeypatch.setattr(
            pv11, "ProgressTracker", MagicMock(return_value=mock_tracker)
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.factory.production_v11.AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        mock_generate = AsyncMock(return_value={"status": "accepted", "sample": {}})
        monkeypatch.setattr(pv11, "generate_theory_sample_async", mock_generate)

        await pv11.main_async(mock_args)

        # Should work without resume
        assert mock_generate.call_count == 2

    asyncio.run(_test())


def test_main_async_normal_mode(tmp_path, mock_args, monkeypatch):
    """Test normal mode (code generation) branch."""

    async def _test():
        mock_args.theory = False
        mock_args.output = str(tmp_path / "output.jsonl")

        # Mock raw_dir with a fake .txt file
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        txt_file = raw_dir / "test.txt"
        txt_file.write_text("""=== LOGICAL ENTITY: test_bundle ===
Context: test
Type: FUNCTIONAL_UNIT
[ARCH_HEADER]
MODULE: test
--- FILE: sensor.py ---
def foo(): pass
--- FILE: test_sensor.py ---
def test_foo(): pass
""")

        mock_args.raw_dir = str(raw_dir)
        mock_args.limit = None
        mock_args.extensions = None
        mock_args.test = 1  # limit to 1 frag

        # Mock dependencies
        monkeypatch.setattr(
            pv11, "load_taxonomy", MagicMock(return_value={"prompts": {}})
        )
        monkeypatch.setattr(
            pv11,
            "_TAX",
            {
                "prompts": {
                    "system": {"python": {"base": "system"}},
                    "user": {"nominal": {"code": "user"}},
                }
            },
        )
        monkeypatch.setattr(
            pv11,
            "load_master_docs",
            MagicMock(return_value=("master", "changelog", "jinja")),
        )
        monkeypatch.setattr(
            pv11, "detect_legacy_patterns", MagicMock(return_value=[])
        )  # no legacy
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock()
        monkeypatch.setattr(
            pv11, "AsyncFileWriter", MagicMock(return_value=mock_writer)
        )
        mock_tracker = MagicMock()
        mock_tracker.record = AsyncMock()
        mock_tracker.close = MagicMock()
        mock_tracker.summary = MagicMock(return_value="summary")
        monkeypatch.setattr(
            pv11, "ProgressTracker", MagicMock(return_value=mock_tracker)
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.factory.production_v11.AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        mock_generate = AsyncMock(
            return_value={
                "status": "accepted",
                "sample": {"metadata": {"example_type": "nominal"}, "conversation": []},
            }
        )
        monkeypatch.setattr(pv11, "generate_sample_async", mock_generate)

        await pv11.main_async(mock_args)

        # Check that generate_sample_async was called
        assert mock_generate.call_count == 1

    asyncio.run(_test())
