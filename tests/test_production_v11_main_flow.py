#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.factory import pipeline_runner as pr_module
from src.factory import prompt_builder as pb_module
from src.factory.checkpoint import make_checkpoint_key
from src.factory.pipeline_runner import main_async as pv_main_async


FUNCTIONAL_UNIT_TXT = """=== LOGICAL ENTITY: test_entity ===
Context: HA sensor
Type: FUNCTIONAL_UNIT
[ARCH_HEADER]
MODULE: ha_sensor
REPO_PREFIX: my_repo
--- FILE: sensor.py ---
def async_setup_entry(hass, entry): pass
--- FILE: test_sensor.py ---
def test_sensor(): pass
"""


def _accepted_sample_for_frag(frag: dict) -> dict:
    ck = make_checkpoint_key(frag["name"], frag.get("virtual_filename", ""))
    return {
        "status": "accepted",
        "sample": {
            "id": f"v11_nominal_{ck}",
            "conversation": [
                {"role": "user", "content": "u"},
                {
                    "role": "assistant",
                    "content": "<think>r</think><tool_call>[]</tool_call>",
                },
            ],
            "metadata": {
                "curation": {"kept": True},
                "checkpoint_key": ck,
                "example_type": "nominal",
                "evol_difficulty": "easy",
                "gold_injected": True,
            },
            "filter_text": "f",
        },
    }


def test_main_async_processes_fragments_writes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Create a tiny raw_dir with one FUNCTIONAL_UNIT bundle
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "bundle1.txt").write_text(FUNCTIONAL_UNIT_TXT, encoding="utf-8")
    # Create a local Gap dir with the three required master docs
    gap = tmp_path / "Gap"
    gap.mkdir()
    (gap / "HA_MASTER_GUIDE_2026.md").write_text(
        "# HA Guide\nsome content", encoding="utf-8"
    )
    (gap / "technical_changelog_2026.md").write_text(
        "## Changelog\nbreaking change info", encoding="utf-8"
    )
    (gap / "HA_JINJA_YAML_GUIDE_2026.md").write_text(
        "## Jinja Guide\ntriggers:", encoding="utf-8"
    )

    # Stub prompt helpers to avoid loading taxonomy
    monkeypatch.setattr(
        "src.factory.prompt_builder._prompt", lambda key: f"<{key}>", raising=False
    )
    monkeypatch.setattr(
        "src.factory.prompt_builder._render",
        lambda template, **subs: template,
        raising=False,
    )

    # Deterministic assignment to avoid randomness
    monkeypatch.setattr(
        pr_module,
        "assign_example_type",
        lambda frag, has_legacy=False: SimpleNamespace(
            example_type="nominal", difficulty="easy"
        ),
    )

    # Replace generate_sample_async with a fast accepted-response stub
    async def fake_generate(
        client,
        model,
        frag,
        example_type,
        evol_difficulty,
        master,
        changelog,
        semaphore,
        has_legacy=False,
        legacy_patterns=None,
        jinja_guide="",
        state=None,
    ):
        return _accepted_sample_for_frag(frag)

    monkeypatch.setattr(
        "src.factory.pipeline_runner.generate_sample_async", fake_generate
    )

    # Avoid instantiating real AsyncOpenAI (not used by the stub)
    class DummyAsyncOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(pr_module, "AsyncOpenAI", DummyAsyncOpenAI, raising=False)

    # Build args namespace expected by main_async (set attributes on instance)
    class Args:
        pass

    args = Args()
    args.test = 1
    args.limit = None
    args.workers = 1
    args.model = "m"
    args.base_url = "http://localhost"
    args.api_key = "k"
    args.output = str(tmp_path / "out.jsonl")
    args.seed = 42
    args.think_filter = True
    args.think_filter_min_chars = 5000
    args.resume = False
    args.raw_dir = str(raw_dir)
    args.extensions = None
    args.theory = False
    args.theory_reps = 1
    args.gap_dir = str(gap)
    args.taxonomy = None

    # main_async expects args._gap_dir to be Path
    args._gap_dir = Path(args.gap_dir)

    # Run the async pipeline
    asyncio.run(pv_main_async(args))

    # Validate that output file was created and contains JSON lines
    out_path = Path(args.output)
    assert out_path.exists()
    lines = [l for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 1
    rec = json.loads(lines[0])
    assert (
        rec.get("id", "").startswith("v11_nominal_")
        or rec.get("metadata", {}).get("example_type") == "nominal"
    )


def test_main_async_blueprint_and_governance_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Build raw_dir containing a MODULE_BLUEPRINT, GOVERNANCE_RULES and a FUNCTIONAL_UNIT
    raw_dir = tmp_path / "raw2"
    raw_dir.mkdir()

    module_blueprint = """=== LOGICAL ENTITY: my_integration_blueprint ===
Context: Blueprint data
Type: MODULE_BLUEPRINT
[MODULE_MAP]
MODULE: my_mod
REPO_PREFIX: my_repo
--- FILE: blueprint.txt ---
MODULE: my_mod
--- BUNDLE_END
"""

    governance_bundle = """=== LOGICAL ENTITY: repo_governance ===
Context: governance
Type: GOVERNANCE_RULES
[GOVERNANCE_HEADER]
MODULE: rules
REPO_PREFIX: my_repo
--- FILE: gov1.md ---
# Rules
rule: value
"""

    functional_unit = FUNCTIONAL_UNIT_TXT

    (raw_dir / "bp.txt").write_text(module_blueprint, encoding="utf-8")
    (raw_dir / "gov.txt").write_text(governance_bundle, encoding="utf-8")
    (raw_dir / "fu.txt").write_text(functional_unit, encoding="utf-8")

    # Minimal Gap files
    gap = tmp_path / "Gap"
    gap.mkdir()
    (gap / "HA_MASTER_GUIDE_2026.md").write_text(
        "# HA Guide\ncontent", encoding="utf-8"
    )
    (gap / "technical_changelog_2026.md").write_text(
        "## Changelog\ninfo", encoding="utf-8"
    )
    (gap / "HA_JINJA_YAML_GUIDE_2026.md").write_text(
        "## Jinja\ntriggers:", encoding="utf-8"
    )

    # Stubs
    monkeypatch.setattr(pb_module, "_prompt", lambda key: f"<{key}>", raising=False)
    monkeypatch.setattr(
        pb_module, "_render", lambda template, **subs: template, raising=False
    )
    monkeypatch.setattr(
        pr_module,
        "assign_example_type",
        lambda frag, has_legacy=False: SimpleNamespace(
            example_type="nominal", difficulty="easy"
        ),
        raising=False,
    )

    async def fake_generate(
        client,
        model,
        frag,
        example_type,
        evol_difficulty,
        master,
        changelog,
        semaphore,
        has_legacy=False,
        legacy_patterns=None,
        jinja_guide="",
        state=None,
    ):
        return _accepted_sample_for_frag(frag)

    monkeypatch.setattr(
        "src.factory.pipeline_runner.generate_sample_async", fake_generate
    )
    monkeypatch.setattr(
        "src.factory.pipeline_runner.AsyncOpenAI",
        lambda *a, **k: SimpleNamespace(),
        raising=False,
    )

    # Args
    class Args:
        pass

    args = Args()
    args.test = 2
    args.limit = None
    args.workers = 1
    args.model = "m"
    args.base_url = "http://localhost"
    args.api_key = "k"
    args.output = str(tmp_path / "out2.jsonl")
    args.seed = 42
    args.think_filter = True
    args.think_filter_min_chars = 5000
    args.resume = False
    args.raw_dir = str(raw_dir)
    args.extensions = None
    args.theory = False
    args.theory_reps = 1
    args.gap_dir = str(gap)
    args.taxonomy = None
    args._gap_dir = Path(args.gap_dir)

    # Run and assert output created
    asyncio.run(pv_main_async(args))
    out_path = Path(args.output)
    assert out_path.exists()
    lines = [l for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 1
