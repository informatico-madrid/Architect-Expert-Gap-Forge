#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorManifest, AnchorRecord


class JSONLExporter:
    def write_all(self, records: list[AnchorRecord], path: str | Path) -> None:
        path = Path(path)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            for rec in records:
                f.write(json.dumps(rec.model_dump()) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.rename(str(tmp_path), str(path))

    def generate_manifest(
        self,
        records: list[AnchorRecord],
        provider_name: str,
        cb_triggered: bool,
        failed_count: int,
    ) -> AnchorManifest:
        return AnchorManifest(
            total_samples=len(records),
            provider=provider_name,
            cb_triggered=cb_triggered,
            failed_count=failed_count,
            generation_timestamp=datetime.datetime.utcnow().isoformat(),
        )
