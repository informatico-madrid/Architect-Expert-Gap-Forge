#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the standalone `clean_lora.py` helper script."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "src/utils/clean_lora.py"


def _prepare_environment(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    shards_data: dict[str, dict[str, int]],
    index_name: str = "adapter_model.safetensors.index.json",
) -> dict[str, object]:
    data_dir = root / "data" / "outputs" / "consolidated"
    data_dir.mkdir(parents=True)

    index_path = data_dir / index_name
    weight_map: dict[str, str] = {}
    for shard_name, key_map in shards_data.items():
        for key in key_map:
            weight_map[key] = shard_name

    index_path.write_text(json.dumps({"weight_map": weight_map}), encoding="utf-8")

    saved: dict[str, object] = {}

    def fake_load(path: str) -> dict[str, int]:
        return shards_data[os.path.basename(path)]

    def fake_save(state_dict: dict[str, int], path: str) -> None:
        saved["dict"] = dict(state_dict)
        saved["path"] = path

    fake_torch_module = ModuleType("safetensors.torch")
    fake_torch_module.load_file = fake_load
    fake_torch_module.save_file = fake_save

    fake_safetensors = ModuleType("safetensors")
    fake_safetensors.torch = fake_torch_module

    monkeypatch.setitem(sys.modules, "safetensors", fake_safetensors)
    monkeypatch.setitem(sys.modules, "safetensors.torch", fake_torch_module)
    monkeypatch.setitem(sys.modules, "torch", ModuleType("torch"))

    return saved


@pytest.mark.unit
def test_clean_lora_consolidates_shards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    shards_data = {
        "shard-1.safetensors": {
            "base_model.model.model.layer.weight": 1,
            "lora_A.default.weight": 2,
        },
        "shard-2.safetensors": {
            "other.weight": 3,
        },
    }

    saved = _prepare_environment(root, monkeypatch, shards_data)
    monkeypatch.chdir(root)

    runpy.run_path(str(_SCRIPT_PATH), run_name="__main__")

    assert saved["dict"] == {
        "base_model.model.layer.weight": 1,
        "lora_A.weight": 2,
        "other.weight": 3,
    }
    assert saved["path"].endswith("data/outputs/consolidated/adapter_model.safetensors")


@pytest.mark.unit
def test_clean_lora_uses_model_index_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    shards_data = {
        "shard-a.safetensors": {
            "base_model.model.model.layer.bias": 4,
        }
    }

    saved = _prepare_environment(root, monkeypatch, shards_data, index_name="model.safetensors.index.json")
    monkeypatch.chdir(root)

    runpy.run_path(str(_SCRIPT_PATH), run_name="__main__")

    assert saved["dict"] == {"base_model.model.layer.bias": 4}
    assert saved["path"].endswith("data/outputs/consolidated/adapter_model.safetensors")
