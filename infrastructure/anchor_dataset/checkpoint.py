from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CheckpointData:
    completed_ids: set[str]
    failed_ids: dict[str, str]
    provider_active: str
    sample_counter: int
    domain_allocation_remaining: dict[str, int]
    timestamp: str
    circuit_breaker_triggered: bool
    next_variant_map: dict[str, str]

    def model_dump(self) -> dict:
        return {
            "completed_ids": list(self.completed_ids),
            "failed_ids": self.failed_ids,
            "provider_active": self.provider_active,
            "sample_counter": self.sample_counter,
            "domain_allocation_remaining": self.domain_allocation_remaining,
            "timestamp": self.timestamp,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "next_variant_map": self.next_variant_map,
        }

    @classmethod
    def model_validate(cls, data: dict) -> CheckpointData:
        return cls(
            completed_ids=set(data["completed_ids"]),
            failed_ids=data["failed_ids"],
            provider_active=data["provider_active"],
            sample_counter=data["sample_counter"],
            domain_allocation_remaining=data["domain_allocation_remaining"],
            timestamp=data["timestamp"],
            circuit_breaker_triggered=data["circuit_breaker_triggered"],
            next_variant_map=data["next_variant_map"],
        )


class CheckpointManager:
    def save(self, path: Path, data: CheckpointData) -> None:
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data.model_dump(), f)
            f.flush()
            os.fsync(f.fileno())
        os.rename(str(tmp_path), str(path))

    def load(self, path: Path) -> CheckpointData | None:
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return CheckpointData.model_validate(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None