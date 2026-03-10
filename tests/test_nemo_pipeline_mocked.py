#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import json
import os
import types

import pytest

from src.curation import nemo_curator_suite as nc


def test_run_nemo_filter_pipeline_mock_success(tmp_path, monkeypatch):
    # Prepare a minimal input file
    in_path = tmp_path / "in.jsonl"
    in_path.write_text(
        json.dumps({"conversation": [{"role": "assistant", "content": "hello"}]}) + "\n"
    )
    out_dir = tmp_path / "outdir"

    # Track created client instance
    client_holder = []

    class FakeRayClient:
        def __init__(self):
            client_holder.append(self)
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class FakePipeline:
        def __init__(self, name=None):
            self.name = name
            self.stages = []
            self.ran = False

        def add_stage(self, stage):
            self.stages.append(stage)

        def run(self):
            self.ran = True

    class DummyFilter:
        def __init__(self, *a, **kw):
            pass

    class FakeJsonlReader:
        def __init__(self, file_paths):
            self.file_paths = file_paths

    class FakeJsonlWriter:
        def __init__(self, path):
            self.path = path

    class FakeModify:
        def __init__(self, modifier_fn=None, input_fields=None, output_fields=None):
            self.modifier_fn = modifier_fn

    class FakeScoreFilter:
        def __init__(self, filter_obj=None, text_field=None):
            self.filter_obj = filter_obj
            self.text_field = text_field

    # Patch NeMo names into module
    monkeypatch.setattr(nc, "_NEMO_AVAILABLE", True)
    monkeypatch.setattr(nc, "RayClient", FakeRayClient, raising=False)
    monkeypatch.setattr(nc, "Pipeline", FakePipeline, raising=False)
    monkeypatch.setattr(nc, "JsonlReader", FakeJsonlReader, raising=False)
    monkeypatch.setattr(nc, "JsonlWriter", FakeJsonlWriter, raising=False)
    monkeypatch.setattr(nc, "Modify", FakeModify, raising=False)
    monkeypatch.setattr(nc, "ScoreFilter", FakeScoreFilter, raising=False)

    # Patch the various filter classes used by the pipeline to simple dummies
    for name in [
        "WordCountFilter",
        "SymbolsToWordsFilter",
        "NonAlphaNumericFilter",
        "PunctuationFilter",
        "BoilerPlateStringFilter",
        "UrlsFilter",
        "RepeatedLinesFilter",
        "RepeatingTopNGramsFilter",
    ]:
        monkeypatch.setattr(nc, name, DummyFilter, raising=False)

    # Should not raise
    nc.run_nemo_filter_pipeline(str(in_path), str(out_dir))

    # Ensure client started and stopped
    assert client_holder, "RayClient was not instantiated"
    client = client_holder[0]
    assert getattr(client, "started", True) is True
    assert getattr(client, "stopped", True) is True


def test_run_nemo_filter_pipeline_mock_exception(tmp_path, monkeypatch):
    in_path = tmp_path / "in.jsonl"
    in_path.write_text(
        json.dumps({"conversation": [{"role": "assistant", "content": "hello"}]}) + "\n"
    )
    out_dir = tmp_path / "outdir"

    client_holder = []

    class FakeRayClient:
        def __init__(self):
            client_holder.append(self)
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class ExplodingPipeline:
        def __init__(self, name=None):
            self.name = name

        def add_stage(self, _):
            pass

        def run(self):
            raise RuntimeError("simulated pipeline failure")

    class DummyFilter:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(nc, "_NEMO_AVAILABLE", True)
    monkeypatch.setattr(nc, "RayClient", FakeRayClient, raising=False)
    monkeypatch.setattr(nc, "Pipeline", ExplodingPipeline, raising=False)
    monkeypatch.setattr(nc, "JsonlReader", lambda file_paths: None, raising=False)
    monkeypatch.setattr(nc, "JsonlWriter", lambda path: None, raising=False)
    monkeypatch.setattr(nc, "Modify", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(nc, "ScoreFilter", DummyFilter, raising=False)

    for name in [
        "WordCountFilter",
        "SymbolsToWordsFilter",
        "NonAlphaNumericFilter",
        "PunctuationFilter",
        "BoilerPlateStringFilter",
        "UrlsFilter",
        "RepeatedLinesFilter",
        "RepeatingTopNGramsFilter",
    ]:
        monkeypatch.setattr(nc, name, DummyFilter, raising=False)

    with pytest.raises(RuntimeError):
        nc.run_nemo_filter_pipeline(str(in_path), str(out_dir))

    # Ensure client was stopped in finally block
    assert client_holder, "RayClient was not instantiated"
    assert getattr(client_holder[0], "stopped", False) is True
