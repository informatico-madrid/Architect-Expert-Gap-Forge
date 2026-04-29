#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Additional async tests for production_v11 flows.

These exercises cover theory-sample generation, poison detection,
and an end-to-end small `main_async` run in theory mode using a
fake AsyncOpenAI client to avoid network calls.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


import src.factory.prompt_builder as pb_module
import src.factory.pipeline_runner as pr_module
from src.factory import config as cfg_module
from src.factory.cli import main as cli_main, parse_args as cli_parse_args
from src.factory.pipeline_runner import generate_sample_async, main_async


class FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, *args, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


class FakeClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


def make_theory_frag(name: str = "T1") -> dict:
    return {
        "name": name,
        "type": "theory",
        "subtype": "doc",
        "virtual_filename": f"theory/{name}.md",
        "section_content": "",
        "original": "",
        "source_doc": "MASTER_GUIDE",
    }


def test_generate_theory_sample_success_and_failure(monkeypatch):
    monkeypatch.setattr(pb_module, "_prompt", lambda key: "prompt")
    monkeypatch.setattr(
        pb_module,
        "THEORY_QUESTION_TEMPLATES",
        [{"template": "Write theory about $section_title", "type": "doc"}],
    )
    # Success: assistant returns <think>reason</think> + long answer (>150 chars)
    answer = "A" * 200
    content = f"<think>{'reasoning' * 30}</think>{answer}"
    client = FakeClient(content)
    sem = asyncio.Semaphore(1)
    frag = make_theory_frag("Sec1")
    res = asyncio.run(
        pr_module.generate_theory_sample_async(
            client, "m", frag, "master", "changelog", sem
        )
    )
    assert res["status"] == "accepted"
    assert (
        "theory" in res["sample"]["metadata"]["example_type"]
        or res["sample"]["metadata"]["example_type"] == "theory"
    )

    # Failure: answer too short -> rejected after retries
    short_content = "<think>r</think>short"
    client2 = FakeClient(short_content)
    res2 = asyncio.run(
        pr_module.generate_theory_sample_async(
            client2, "m", frag, "master", "changelog", sem
        )
    )
    assert res2["status"] == "rejected"

    # Edge case: </think> without <think> -> should parse reasoning from before </think>
    edge_content = f"reasoning text</think>{answer}"
    client3 = FakeClient(edge_content)
    res3 = asyncio.run(
        pr_module.generate_theory_sample_async(
            client3, "m", frag, "master", "changelog", sem
        )
    )
    assert res3["status"] == "accepted"


def test_generate_sample_async_poison_and_legacy(monkeypatch):
    monkeypatch.setattr(pb_module, "_prompt", lambda key: "prompt")
    monkeypatch.setattr(
        pb_module, "LEGACY_2023_PATTERNS", [{"legacy_code": "# old 2023 code pattern"}]
    )
    # Prepare a clean tool_call with long generated content (passes LDI)
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "mod.py", "content": "x" * 300},
    }
    content = (
        f"<think>{'r' * 200}</think><tool_call>{json.dumps(tool_json)}</tool_call>"
    )
    client = FakeClient(content)
    sem = asyncio.Semaphore(1)

    frag = {
        "name": "fragX",
        "virtual_filename": "mod_frag.py",
        "original": "# original code",
        "context": "ctx",
        "skeleton": "def s(): pass",
        "test_original": "# t",
        "test_filename": "tests/mod_frag_test.py",
        "subtype": "functional_unit",
    }

    # Monkeypatch post_validate_output to detect a toxic pattern
    monkeypatch.setattr(
        "src.factory.pipeline_runner.post_validate_output", lambda code, t, s: ["toxic"]
    )
    res = asyncio.run(
        generate_sample_async(
            client,
            "m",
            frag,
            "nominal",
            "easy",
            "master",
            "changelog",
            sem,
            has_legacy=False,
        )
    )
    assert res["status"] in ("accepted", "rejected")
    if res["status"] == "accepted":
        assert res["sample"]["metadata"]["curation"].get("auto_rejected") is True

    # Legacy branch: when has_legacy=True, gold_injected must be False
    res2 = asyncio.run(
        generate_sample_async(
            client,
            "m",
            frag,
            "contrast",
            None,
            "master",
            "changelog",
            sem,
            has_legacy=True,
            legacy_patterns=["old"],
        )
    )
    assert res2["status"] in ("accepted", "rejected")
    if res2["status"] == "accepted":
        assert res2["sample"]["metadata"]["gold_injected"] is False


def test_main_async_theory_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(pb_module, "_prompt", lambda key: "prompt")
    # Create minimal master/changelog/jinja guide with one long section
    gap = tmp_path / "gapdir"
    gap.mkdir()
    master = gap / cfg_module._MASTER_GUIDE_FILENAME
    changelog = gap / cfg_module._TECHNICAL_CHANGELOG_FILENAME
    jinja = gap / cfg_module._JINJA_YAML_GUIDE_FILENAME
    master.write_text("# Section One\n" + "X" * 300)
    changelog.write_text("# Changelog\n" + "Y" * 300)
    jinja.write_text("JINJA GUIDE")

    # Fake AsyncOpenAI to return a long answer
    answer = "Z" * 200
    fake_resp = f"<think>{'r' * 200}</think>{answer}"

    class FakeAsyncOpenAI:
        def __init__(self, base_url=None, api_key=None):
            self.chat = SimpleNamespace(completions=FakeCompletions(fake_resp))

    monkeypatch.setattr(pr_module, "AsyncOpenAI", FakeAsyncOpenAI)

    # Run main_async in theory mode (test limited)
    class Args:
        theory = True
        theory_reps = 1
        test = 1
        workers = 1
        base_url = "x"
        api_key = "k"
        model = "m"
        _gap_dir = gap
        output = str(tmp_path / "out.jsonl")
        resume = False

    asyncio.run(main_async(Args()))

    # Output file should exist (writer created by main_async)
    assert Path(Args.output).exists()
    # Remove file to keep workspace clean
    Path(Args.output).unlink()


def test_main_function(monkeypatch):
    """Test main function with mocked dependencies."""
    # Mock sys.argv
    monkeypatch.setattr(
        "sys.argv", ["production_v11.py", "--test", "1", "--output", "/tmp/test.jsonl"]
    )

    # Mock Path in the module
    mock_base_dir = MagicMock()
    mock_config_dir = MagicMock()
    mock_data_dir = MagicMock()
    mock_gap_dir = MagicMock()
    mock_taxonomy_path = MagicMock()
    mock_taxonomy_path.exists.return_value = True

    def mock_path(path_str):
        if str(path_str) == pb_module.__file__:
            return mock_base_dir
        elif "taxonomy" in str(path_str):
            return mock_taxonomy_path
        elif "Gap" in str(path_str):
            return mock_gap_dir
        else:
            return MagicMock()

    monkeypatch.setattr(pr_module, "Path", mock_path)

    # Set up path hierarchy
    mock_base_dir.resolve.return_value = mock_base_dir
    mock_base_dir.parent = mock_base_dir
    mock_base_dir.__truediv__.side_effect = lambda x: {
        "configs": mock_config_dir,
        "data": mock_data_dir,
    }.get(x, mock_gap_dir)
    mock_config_dir.__truediv__.return_value = mock_taxonomy_path
    mock_data_dir.__truediv__.return_value = mock_gap_dir

    # Mock load_taxonomy
    monkeypatch.setattr(pr_module, "load_taxonomy", MagicMock())
    monkeypatch.setattr(
        pb_module,
        "_TAX",
        {"prompts": {"system": {"theory": "system"}, "user": {"theory": "user"}}},
    )

    # Mock random.seed
    monkeypatch.setattr("random.seed", MagicMock())

    # Mock main_async to avoid creating coroutine
    mock_main_async = AsyncMock()
    monkeypatch.setattr("src.factory.cli.main_async", mock_main_async)

    # Call main - should not raise exceptions
    cli_main()

    # Verify that main_async was called
    mock_main_async.assert_called_once()


def test_parse_args_basic(monkeypatch):
    """Test parse_args function with basic arguments."""
    monkeypatch.setattr(
        "sys.argv", ["production_v11.py", "--test", "5", "--workers", "2"]
    )
    args = cli_parse_args()
    assert args.test == 5
    assert args.workers == 2


def test_parse_args_full(monkeypatch):
    """Test parse_args function with all arguments."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "production_v11.py",
            "--test",
            "10",
            "--workers",
            "4",
            "--limit",
            "100",
            "--resume",
            "data/test.jsonl",
            "--output",
            "output.jsonl",
            "--theory",
            "--theory-reps",
            "3",
            "--gap-dir",
            "data/Gap",
            "--taxonomy",
            "configs/taxonomy.yaml",
            "--seed",
            "123",
        ],
    )
    args = cli_parse_args()
    assert args.test == 10
    assert args.workers == 4
    assert args.limit == 100
    assert args.resume == "data/test.jsonl"
    assert args.output == "output.jsonl"
    assert args.theory is True
    assert args.theory_reps == 3
    assert args.gap_dir == "data/Gap"
    assert args.taxonomy == "configs/taxonomy.yaml"
    assert args.seed == 123
