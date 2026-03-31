# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Dataset configuration for test_dataset.
This file tells HuggingFace datasets how to load the dataset.
"""

import datasets
import pathlib


class TestDataset(datasets.GeneratorBasedBuilder):
    """Test dataset for unit testing."""

    VERSION = datasets.Version("1.0.0")

    def _info(self):
        return datasets.DatasetInfo(
            description="Test dataset for unit testing",
            features=datasets.Features({
                "id": datasets.Value("int32"),
                "text": datasets.Value("string"),
                "label": datasets.Value("int32"),
            }),
        )

    def _split_generators(self, dl_manager):
        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"filepath": str(pathlib.Path(__file__).parent / "train.parquet")},
            ),
            datasets.SplitGenerator(
                name=datasets.Split.TEST,
                gen_kwargs={"filepath": str(pathlib.Path(__file__).parent / "test.parquet")},
            ),
        ]

    def _generate_examples(self, filepath):
        import pandas as pd
        
        df = pd.read_parquet(filepath)
        for idx, row in df.iterrows():
            yield idx, {
                "id": int(row["id"]),
                "text": str(row["text"]),
                "label": int(row["label"]),
            }
