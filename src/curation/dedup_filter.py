#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF — Dedup Filter Module.

Phase 0 (exact deduplication) and Phase 3 (semantic deduplication) logic
for the NeMo Curator Suite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from typing import TYPE_CHECKING, List, Optional, Set

from src.schemas.common import RawRecord

if TYPE_CHECKING:
    from src.curation.curator_pipeline import CurationStats

logger = logging.getLogger(__name__)

# Default constants
DEFAULT_DEDUP_THRESHOLD: float = 0.85
DEFAULT_QUALITY_CUTOFF: float = 0.23
DEFAULT_MINHASH_PERMS: int = 128
DEFAULT_SHINGLE_K: int = 5

# Optional dependency guard
_DATASKETCH_AVAILABLE = False
try:
    from datasketch import MinHash, MinHashLSH  # type: ignore

    _DATASKETCH_AVAILABLE = True
except ImportError:
    pass


# ===========================================================================
# Phase 0 — Exact deduplication (SHA-256)
# ===========================================================================


def exact_dedup(
    records: List[RawRecord],
    stats: "CurationStats",
) -> List[RawRecord]:
    """Remove records whose full conversation is byte-identical to a prior record."""
    seen: Set[str] = set()
    kept: List[RawRecord] = []
    for rec in records:
        h = hashlib.sha256(
            json.dumps(rec.get("conversation", ""), sort_keys=True).encode()
        ).hexdigest()
        if h in seen:
            stats.exact_duplicates += 1
        else:
            seen.add(h)
            kept.append(rec)
    logger.info(
        "Exact dedup: %d removed, %d remaining", stats.exact_duplicates, len(kept)
    )
    return kept


# ===========================================================================
# Phase 3 — Semantic deduplication helpers
# ===========================================================================


def _extract_assistant_text(rec: RawRecord) -> str:
    """Extract concatenated assistant turns from a record."""
    for key in ("assistant", "assistant_response", "response", "output", "text"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    conversation = rec.get("conversation")
    if isinstance(conversation, list):
        parts: List[str] = []
        for msg in conversation:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content") or msg.get("text") or msg.get("value")
                if isinstance(content, str):
                    parts.append(content.strip())
            elif isinstance(msg, str):
                parts.append(msg.strip())
        if parts:
            return "\n".join(parts).strip()
    thought = rec.get("thought_extracted") or rec.get("thoughts")
    if isinstance(thought, str) and thought.strip():
        return thought.strip()
    return ""


def _heuristic_quality_score(text: str) -> float:
    """Heuristic quality score in [0, 1] — higher is better.

    Treat only alphabetic words as tokens so numeric-only strings
    (e.g. "123 456 789") do not produce an artificially high score.
    """
    if not text.strip():
        return 0.0
    # Only consider alphabetic words of length >= 2 as valid tokens
    tokens = re.findall(r"[a-z]{2,}", text.lower())
    if not tokens:
        return 0.0
    n = len(tokens)
    unique_ratio = len(set(tokens)) / n
    most_common_frac = Counter(tokens).most_common(1)[0][1] / n
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]
    has_repeated = any(c >= 3 for _, c in Counter(sentences).most_common())
    ellipsis_count = text.count("...")
    score = 0.6 * unique_ratio + 0.4 * (1.0 - most_common_frac)
    if has_repeated:
        score *= 0.35
    if ellipsis_count > 2:
        score *= 0.60
    return max(0.0, min(1.0, score))


def _char_shingles(text: str, k: int = DEFAULT_SHINGLE_K) -> Set[str]:
    normalised = re.sub(r"\s+", " ", text.strip().lower()).replace(" ", "_")
    if not normalised:
        return set()
    if len(normalised) < k:
        return {normalised}
    return {normalised[i : i + k] for i in range(len(normalised) - k + 1)}


def _build_clusters_datasketch(
    texts: List[str],
    threshold: float,
    num_perm: int,
    shingle_k: int,
) -> Optional[List[List[int]]]:
    if not _DATASKETCH_AVAILABLE:
        return None
    logger.info(
        "MinHash-LSH clustering (num_perm=%d, threshold=%.2f)", num_perm, threshold
    )
    shingles = [_char_shingles(t, k=shingle_k) for t in texts]
    minhashes = []
    for sh in shingles:
        m = MinHash(num_perm=num_perm)
        for s in sh:
            m.update(s.encode("utf-8"))
        minhashes.append(m)
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for idx, m in enumerate(minhashes):
        lsh.insert(str(idx), m)
    visited: Set[int] = set()
    clusters: List[List[int]] = []
    for i, m in enumerate(minhashes):
        if i in visited:
            continue
        candidates = {int(x) for x in lsh.query(m)}
        group: List[int] = []
        for j in sorted(candidates):
            Si, Sj = shingles[i], shingles[j]
            union = len(Si | Sj) or 1
            if len(Si & Sj) / union >= threshold:
                group.append(j)
        for j in group:
            visited.add(j)
        clusters.append(sorted(group))
    return clusters


def _build_clusters_naive(
    texts: List[str],
    threshold: float,
    shingle_k: int,
) -> List[List[int]]:
    logger.warning(
        "datasketch unavailable — falling back to O(n²) Jaccard. "
        "Install datasketch for large datasets: pip install datasketch"
    )
    shingles = [_char_shingles(t, k=shingle_k) for t in texts]
    n = len(texts)
    visited: Set[int] = set()
    clusters: List[List[int]] = []
    for i in range(n):
        if i in visited:
            continue
        group = [i]
        visited.add(i)
        Si = shingles[i]
        for j in range(i + 1, n):
            if j in visited:
                continue
            Sj = shingles[j]
            union = len(Si | Sj) or 1
            if len(Si & Sj) / union >= threshold:
                group.append(j)
                visited.add(j)
        clusters.append(group)
    return clusters


# ===========================================================================
# Phase 3 — Semantic deduplication
# ===========================================================================


def semantic_dedup(
    records: List[RawRecord],
    stats: "CurationStats",
    *,
    threshold: float = DEFAULT_DEDUP_THRESHOLD,
    quality_cutoff: float = DEFAULT_QUALITY_CUTOFF,
    num_perm: int = DEFAULT_MINHASH_PERMS,
    shingle_k: int = DEFAULT_SHINGLE_K,
) -> List[RawRecord]:
    """Quality-gate + MinHash-LSH semantic deduplication."""
    # Annotate
    for rec in records:
        rec["_text"] = _extract_assistant_text(rec)
        rec["_qs"] = _heuristic_quality_score(rec["_text"])

    # Quality gate
    low_q = [r for r in records if r["_qs"] < quality_cutoff]
    candidates = [r for r in records if r["_qs"] >= quality_cutoff]
    stats.low_quality_score += len(low_q)
    logger.info(
        "Quality gate (cutoff=%.2f): %d kept, %d dropped",
        quality_cutoff,
        len(candidates),
        len(low_q),
    )

    texts = [r["_text"] for r in candidates]
    clusters = _build_clusters_datasketch(
        texts, threshold, num_perm=num_perm, shingle_k=shingle_k
    ) or _build_clusters_naive(texts, threshold, shingle_k=shingle_k)

    idx_map = {i: rec for i, rec in enumerate(candidates)}
    removed_idx: Set[int] = set()
    kept_records: List[RawRecord] = []

    for cluster in clusters:
        if not cluster:
            continue
        if len(cluster) == 1:
            kept_records.append(idx_map[cluster[0]])
        else:
            best = max(
                cluster, key=lambda i: (idx_map[i]["_qs"], len(idx_map[i]["_text"]), -i)
            )
            for i in cluster:
                if i == best:
                    kept_records.append(idx_map[i])
                else:
                    removed_idx.add(i)

    clustered = {i for cl in clusters for i in cl}
    for i, rec in idx_map.items():
        if i not in clustered:
            kept_records.append(rec)

    stats.semantic_duplicates += len(removed_idx)

    final: List[RawRecord] = []
    for r in kept_records:
        r_out = {k: v for k, v in r.items() if not k.startswith("_")}
        r_out.setdefault("metadata", {})
        r_out["metadata"]["curation"] = {"kept": True, "quality_score": r["_qs"]}
        final.append(r_out)

    logger.info(
        "Semantic dedup (threshold=%.2f): %d clusters, %d kept, %d removed",
        threshold,
        len(clusters),
        len(final),
        len(removed_idx),
    )
    return final
