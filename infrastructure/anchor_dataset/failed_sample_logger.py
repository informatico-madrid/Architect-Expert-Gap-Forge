#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import dataclasses
import json
import datetime
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FailedSampleEntry:
    sample_id: str
    domain: str
    difficulty: str
    failure_reason: str
    provider: str
    attempt: int
    raw_response: str
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class FailedSampleLogger:
    MAX_RESPONSE_LEN = 2000

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        sample_id: str,
        domain: str,
        difficulty: str,
        failure_reason: str,
        provider: str,
        attempt: int,
        raw_response: str,
    ) -> None:
        entry = FailedSampleEntry(
            sample_id=sample_id,
            domain=domain,
            difficulty=difficulty,
            failure_reason=failure_reason,
            provider=provider,
            attempt=attempt,
            raw_response=raw_response[: self.MAX_RESPONSE_LEN],
        )
        with open(self.log_path, "a") as f:
            f.write(json.dumps(dataclasses.asdict(entry)) + "\n")
