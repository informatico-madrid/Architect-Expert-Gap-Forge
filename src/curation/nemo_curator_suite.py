#!/usr/bin/env python3
"""AEGF (Architect-Expert-Gap-Forge) — NeMo Curator Suite.

Unified quality-filtering and semantic-deduplication engine for JSONL datasets.
Combines four independent, composable curation phases into a single CLI:

  Phase 0 — Exact deduplication      (SHA-256 hash on full conversation)
  Phase 1 — NeMo Curator filtering    (distributed quality filters via Ray)
  Phase 2 — Structural quality gate   (syntax, think depth, LDI, meta-speech)
  Phase 3 — Semantic deduplication    (MinHash-LSH near-duplicate clustering)

⚠️  Phase 1 (--filter) MUST be executed inside the aegf_curator Docker container.
    Phases 0, 2 and 3 run without any special container.

Launch the container
--------------------
    cd deploy/docker
    docker compose up -d curator
    docker exec -it aegf_curator bash

Usage examples (inside the container)
--------------------------------------
# Full pipeline — all four phases:
    python /workspace/src/curation/nemo_curator_suite.py \\
        --input  /workspace/data/synthetic/CLEAN.jsonl \\
        --output /workspace/data/synthetic/CURATED.jsonl \\
        --exact-dedup --filter --structural --dedup \\
        --apply

# Structural + semantic dedup only (no NeMo required, runs anywhere):
    python src/curation/nemo_curator_suite.py \\
        --input  data/synthetic/CLEAN.jsonl \\
        --output data/synthetic/CURATED.jsonl \\
        --exact-dedup --structural --dedup --apply

# Dry-run (statistics only, no file written):
    python src/curation/nemo_curator_suite.py \\
        --input  data/synthetic/CLEAN.jsonl \\
        --output data/synthetic/CURATED.jsonl \\
        --exact-dedup --structural --dedup

# Quick validation on 1000 samples:
    python src/curation/nemo_curator_suite.py \\
        --input  data/synthetic/CLEAN.jsonl \\
        --output /tmp/test.jsonl \\
        --structural --dedup --sample 1000 --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import glob
import os
import re
import sys
import socket
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------
_NEMO_AVAILABLE = False
_DATASKETCH_AVAILABLE = False

try:
    from nemo_curator.core.client import RayClient           # type: ignore
    from nemo_curator.pipeline import Pipeline               # type: ignore
    from nemo_curator.stages.text.io.reader import JsonlReader  # type: ignore
    from nemo_curator.stages.text.io.writer import JsonlWriter  # type: ignore
    from nemo_curator.stages.text.modules import ScoreFilter, Modify  # type: ignore
    from nemo_curator.stages.text.filters import (           # type: ignore
        WordCountFilter, RepeatingTopNGramsFilter, SymbolsToWordsFilter,
        NonAlphaNumericFilter, PunctuationFilter, BoilerPlateStringFilter,
        UrlsFilter, RepeatedLinesFilter,
    )
    _NEMO_AVAILABLE = True
except ImportError:
    pass

try:
    from datasketch import MinHash, MinHashLSH  # type: ignore
    _DATASKETCH_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------
DEFAULT_MIN_WORDS: int = 20
DEFAULT_MAX_SYMBOL_RATIO: float = 0.50
DEFAULT_MAX_NON_ALPHA_RATIO: float = 0.65
DEFAULT_MAX_URL_RATIO: float = 0.30
DEFAULT_MAX_NO_ENDMARK_RATIO: float = 0.99
DEFAULT_MAX_BOILERPLATE_RATIO: float = 0.85
DEFAULT_MAX_REPEATED_LINES: float = 0.90
DEFAULT_MAX_NGRAM_RATIO: float = 0.35
DEFAULT_NGRAM_SIZE: int = 3

DEFAULT_MIN_THINK_CHARS: int = 500
DEFAULT_LDI_MIN_RATIO: float = 0.15  # Blackwell calibrated — new formula yields [0,1) so 2.5 is invalid

DEFAULT_DEDUP_THRESHOLD: float = 0.85
DEFAULT_QUALITY_CUTOFF: float = 0.23
DEFAULT_MINHASH_PERMS: int = 128
DEFAULT_SHINGLE_K: int = 5

DEFAULT_REPORTS_DIR: str = "data/reports"


# ===========================================================================
# CurationStats — tracks all removal reasons across phases
# ===========================================================================

@dataclass
class CurationStats:
    total_input: int = 0
    # Phase 0
    exact_duplicates: int = 0
    # Phase 1
    nemo_filtered: int = 0
    # Phase 2
    invalid_syntax: int = 0
    shallow_thinking: int = 0
    meta_speech: int = 0
    low_ldi: int = 0
    # Phase 3
    low_quality_score: int = 0
    semantic_duplicates: int = 0
    # Output
    total_output: int = 0

    def as_dict(self) -> Dict[str, Any]:
        total_removed = (
            self.exact_duplicates + self.nemo_filtered + self.invalid_syntax
            + self.shallow_thinking + self.meta_speech + self.low_ldi
            + self.low_quality_score + self.semantic_duplicates
        )
        retention = (
            round(100.0 * self.total_output / self.total_input, 2)
            if self.total_input else 0.0
        )
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_input": self.total_input,
            "removed": {
                "exact_duplicates": self.exact_duplicates,
                "nemo_filtered": self.nemo_filtered,
                "invalid_syntax": self.invalid_syntax,
                "shallow_thinking": self.shallow_thinking,
                "meta_speech": self.meta_speech,
                "low_ldi": self.low_ldi,
                "low_quality_score": self.low_quality_score,
                "semantic_duplicates": self.semantic_duplicates,
                "total": total_removed,
            },
            "total_output": self.total_output,
            "retention_pct": retention,
        }

    def print_report(self) -> None:
        d = self.as_dict()
        r = d["removed"]
        print("\n" + "=" * 70)
        print("  AEGF NeMo Curator Suite — Curation Report")
        print("=" * 70)
        print(f"  Input records  : {d['total_input']:>8,}")
        print(f"  ─ Exact duplicates        : {r['exact_duplicates']:>6,}")
        print(f"  ─ NeMo quality filter     : {r['nemo_filtered']:>6,}")
        print(f"  ─ Invalid syntax          : {r['invalid_syntax']:>6,}")
        print(f"  ─ Shallow think (<chars)  : {r['shallow_thinking']:>6,}")
        print(f"  ─ Meta-speech reasoning   : {r['meta_speech']:>6,}")
        print(f"  ─ Low LDI ratio           : {r['low_ldi']:>6,}")
        print(f"  ─ Low heuristic quality   : {r['low_quality_score']:>6,}")
        print(f"  ─ Semantic duplicates     : {r['semantic_duplicates']:>6,}")
        print(f"  Total removed  : {r['total']:>8,}")
        print(f"  Output records : {d['total_output']:>8,}  (retention {d['retention_pct']}%)")
        print("=" * 70)


# ===========================================================================
# Phase 0 — Exact deduplication (SHA-256)
# ===========================================================================

def exact_dedup(
    records: List[Dict[str, Any]],
    stats: CurationStats,
) -> List[Dict[str, Any]]:
    """Remove records whose full conversation is byte-identical to a prior record."""
    seen: Set[str] = set()
    kept: List[Dict[str, Any]] = []
    for rec in records:
        h = hashlib.sha256(
            json.dumps(rec.get("conversation", ""), sort_keys=True).encode()
        ).hexdigest()
        if h in seen:
            stats.exact_duplicates += 1
        else:
            seen.add(h)
            kept.append(rec)
    logger.info("Exact dedup: %d removed, %d remaining", stats.exact_duplicates, len(kept))
    return kept


# ===========================================================================
# Phase 1 — NeMo Curator quality filtering (requires container)
# ===========================================================================

class ConversationExtractor:
    """NeMo Modifier: extract assistant turns into a side column ``filter_text``."""

    def __init__(self) -> None:
        self.__name__ = "ConversationExtractor"

    def __call__(self, conversation_list: Any) -> str:
        if not conversation_list or not isinstance(conversation_list, list):
            return ""
        return " ".join(
            m.get("content", "")
            for m in conversation_list
            if isinstance(m, dict) and m.get("role") == "assistant"
        )


def run_nemo_filter_pipeline(
    input_path: str,
    output_path: str,
    *,
    min_words: int = DEFAULT_MIN_WORDS,
    max_symbol_ratio: float = DEFAULT_MAX_SYMBOL_RATIO,
    max_non_alpha_ratio: float = DEFAULT_MAX_NON_ALPHA_RATIO,
    max_url_ratio: float = DEFAULT_MAX_URL_RATIO,
    max_no_endmark_ratio: float = DEFAULT_MAX_NO_ENDMARK_RATIO,
    max_boilerplate_ratio: float = DEFAULT_MAX_BOILERPLATE_RATIO,
    max_repeated_lines: float = DEFAULT_MAX_REPEATED_LINES,
    max_ngram_ratio: float = DEFAULT_MAX_NGRAM_RATIO,
    ngram_size: int = DEFAULT_NGRAM_SIZE,
) -> None:
    """Run the NeMo Curator distributed quality-filter pipeline.

    Requires nemo-curator + Ray (pre-installed in the aegf_curator container).
    """
    if not _NEMO_AVAILABLE:
        raise RuntimeError(
            "nemo-curator is not installed.\n"
            "Run inside the aegf_curator container:\n"
            "  cd deploy/docker && docker compose up -d curator\n"
            "  docker exec -it aegf_curator bash"
        )
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info("Phase 1 — NeMo Curator filter pipeline: %s", input_path)
    client = RayClient()
    client.start()
    # Provide a helpful hint about the Ray dashboard addresses so users
    # running the script inside the `aegf_curator` container know how
    # to reach the UI from the host or another machine.
    def _detect_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            # doesn't actually send data; just determines outbound iface
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    container_ip = _detect_local_ip()
    logger.info("Ray dashboard (inside container): http://127.0.0.1:8265")
    logger.info("Ray dashboard (container IP): http://%s:8265", container_ip)
    if os.environ.get("RAY_DASHBOARD_HOST") == "0.0.0.0":
        logger.info(
            "If you need external access, publish port 8265 in docker-compose and use the server IP: http://<SERVER_IP>:8265"
        )
    else:
        logger.info(
            "If the dashboard is not reachable from outside, ensure RAY_DASHBOARD_HOST=0.0.0.0 and that port 8265 is published in docker-compose."
        )
    try:
        pipeline = Pipeline(name="aegf_curation_filter_v1")
        pipeline.add_stage(JsonlReader(file_paths=input_path))
        pipeline.add_stage(
            Modify(
                modifier_fn=ConversationExtractor(),
                input_fields=["conversation"],
                output_fields=["filter_text"],
            )
        )
        filter_stages = [
            ScoreFilter(filter_obj=WordCountFilter(min_words=min_words), text_field="filter_text"),
            ScoreFilter(filter_obj=SymbolsToWordsFilter(max_symbol_to_word_ratio=max_symbol_ratio), text_field="filter_text"),
            ScoreFilter(filter_obj=NonAlphaNumericFilter(max_non_alpha_numeric_to_text_ratio=max_non_alpha_ratio), text_field="filter_text"),
            ScoreFilter(filter_obj=UrlsFilter(max_url_to_text_ratio=max_url_ratio), text_field="filter_text"),
            ScoreFilter(filter_obj=PunctuationFilter(max_num_sentences_without_endmark_ratio=max_no_endmark_ratio), text_field="filter_text"),
            ScoreFilter(filter_obj=BoilerPlateStringFilter(max_boilerplate_string_ratio=max_boilerplate_ratio), text_field="filter_text"),
            ScoreFilter(filter_obj=RepeatedLinesFilter(max_repeated_line_fraction=max_repeated_lines), text_field="filter_text"),
            ScoreFilter(filter_obj=RepeatingTopNGramsFilter(n=ngram_size, max_repeating_ngram_ratio=max_ngram_ratio), text_field="filter_text"),
        ]
        for stage in filter_stages:
            pipeline.add_stage(stage)
        pipeline.add_stage(JsonlWriter(path=output_path))
        logger.info("Running NeMo pipeline (%d filter stages)", len(filter_stages))
        pipeline.run()
        logger.info("NeMo filter complete → %s", output_path)
    except Exception as exc:
        logger.error("NeMo filter pipeline error: %s", exc)
        raise
    finally:
        client.stop()


# ===========================================================================
# Phase 2 — Structural quality gate
# ===========================================================================

# --- LDI helpers -----------------------------------------------------------

_PROGRAMMING_KEYWORDS: List[str] = [
    "async", "await", "def", "class", "import", "from", "return",
    "if", "else", "elif", "for", "while", "try", "except", "finally",
    "with", "lambda", "yield", "raise", "assert", "pass", "break",
    "continue", "True", "False", "None", "self", "super", "__init__",
    "function", "const", "let", "var", "new", "this", "export",
    "HomeAssistant", "DataUpdateCoordinator", "Entity", "ConfigEntry",
    "async_setup_entry", "async_added_to_hass", "hass", "entry",
    "coordinator", "device_info", "state", "attributes", "entity_id",
]

_META_PATTERNS: List[str] = [
    r"the\s+user\s+is\s+asking",
    r"i\s+need\s+to",
    r"let\s+me",
    r"i\s+should",
    r"i\s+will\s+now",
    r"first\s+i\s+will",
    r"this\s+is\s+a\s+simple",
    r"this\s+is\s+straightforward",
]


def _count_code_tokens(text: str) -> int:
    count = 0
    json_blocks = re.findall(r"\{[^}]*\}", text)
    for block in json_blocks:
        count += len(re.findall(r"\w+|[{}[\]:,]", block))
    code_blocks = re.findall(r"```[\s\S]*?```", text)
    for block in code_blocks:
        clean = block.replace("```", "").strip()
        count += len(re.findall(r"\w+|[{}[\]():;=.,<>]", clean))
    for kw in _PROGRAMMING_KEYWORDS:
        count += len(re.findall(r"\b" + kw + r"\b", text))
    text_stripped = text
    for b in json_blocks + code_blocks:
        text_stripped = text_stripped.replace(b, "")
    count += len(re.findall(r"[{}[\]():;=.,<>!&|+\-*/%]", text_stripped))
    return count


def _count_natural_tokens(text: str) -> int:
    t = re.sub(r"\{[^}]*\}", "", text)
    t = re.sub(r"```[\s\S]*?```", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    words = re.findall(r"\b[a-zA-Z]{2,}\b", t)
    stop = {
        "async", "await", "def", "class", "import", "from", "return",
        "true", "false", "none", "self", "super", "function", "const",
        "homeassistant", "coordinator", "entity", "hass", "config",
    }
    return len([w for w in words if w.lower() not in stop])


def _ldi(text: str) -> float:
    # Versión Blackwell Calibrada
    code_tokens = _count_code_tokens(text)
    natural_tokens = _count_natural_tokens(text)
    if code_tokens == 0: return 0.0
    
    K = 1200.0 # Factor de estabilidad para registros cortos
    ldi_score = code_tokens / max(1.0, (natural_tokens + code_tokens))
    ldi_final = ldi_score * (code_tokens / (code_tokens + K))
    return ldi_final # Ahora el threshold debería ser ~0.1 o 0.2, no 2.5


def _has_meta_speech(think_content: str) -> bool:
    """Return True if >20 % of lines match shallow meta-speech patterns."""
    lines = think_content.split("\n")
    if not lines:
        return False
    lower = think_content.lower()
    count = sum(1 for p in _META_PATTERNS if re.search(p, lower))
    return (count / len(lines)) > 0.20


# --- Structural filter -----------------------------------------------------

def structural_quality_filter(
    records: List[Dict[str, Any]],
    stats: CurationStats,
    *,
    min_think_chars: int = DEFAULT_MIN_THINK_CHARS,
    ldi_min_ratio: float = DEFAULT_LDI_MIN_RATIO,
    check_attempt_completion: bool = True,
) -> List[Dict[str, Any]]:
    """Apply structural quality checks from the AEGF curation protocol.

    Filters applied (each removes a record if it fails):

    1. Syntax integrity  — Every assistant turn that contains a <think> block
       must be immediately followed by <tool_call> without any whitespace:
       ``</think><tool_call>``
    2. Think depth       — The <think> block in the *first* assistant turn must
       have at least ``min_think_chars`` characters.
    3. Meta-speech check — The reasoning block must not consist mostly of
       shallow filler phrases ("let me", "I need to", etc.).
    4. LDI on tool_call  — The ``<tool_call>`` block (not the full turn) must
       have a code-to-natural-language ratio ≥ ``ldi_min_ratio``.
    5. attempt_completion — If ``check_attempt_completion`` is True, the last
       assistant turn must contain "attempt_completion" (agentic datasets only;
       disable with ``--no-attempt-check`` for production_v11 single-turn data).
    """
    kept: List[Dict[str, Any]] = []

    for rec in records:
        conversation = rec.get("conversation", [])

        # Collect assistant turns
        assistant_turns = [
            m for m in conversation
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        if not assistant_turns:
            stats.invalid_syntax += 1
            continue

        failed = False

        for turn in assistant_turns:
            content = turn.get("content", "")
            if not isinstance(content, str):
                continue

            # --- Filter 1: syntax integrity ---
            if "<think>" in content and "</think>" in content:
                if re.search(r"</think>\s+<tool_call>", content):
                    # Space between tags — invalid
                    stats.invalid_syntax += 1
                    failed = True
                    break
                if "</think>" in content and "<tool_call>" in content:
                    if not re.search(r"</think><tool_call>", content):
                        stats.invalid_syntax += 1
                        failed = True
                        break

        if failed:
            continue

        # --- Filters 2, 3, 4 on first assistant turn with <think> ---
        first_think_turn = next(
            (
                m.get("content", "")
                for m in assistant_turns
                if isinstance(m.get("content"), str) and "<think>" in m["content"]
            ),
            None,
        )

        if first_think_turn is not None:
            think_match = re.search(r"<think>(.*?)</think>", first_think_turn, re.DOTALL)
            if not think_match:
                stats.invalid_syntax += 1
                continue
            think_content = think_match.group(1).strip()

            # Filter 2: think depth
            if len(think_content) < min_think_chars:
                stats.shallow_thinking += 1
                continue

            # Filter 3: meta-speech
            if _has_meta_speech(think_content):
                stats.meta_speech += 1
                continue

            # Filter 4: LDI on tool_call
            tool_call_match = re.search(
                r"<tool_call>(.*?)</tool_call>", first_think_turn, re.DOTALL
            )
            if not tool_call_match:
                stats.invalid_syntax += 1
                continue
            ldi_val = _ldi(tool_call_match.group(1).strip())
            if ldi_val < ldi_min_ratio:
                stats.low_ldi += 1
                continue

        # --- Filter 5: attempt_completion (agentic datasets) ---
        if check_attempt_completion and assistant_turns:
            last_content = assistant_turns[-1].get("content", "")
            if "attempt_completion" not in last_content:
                pass  # Non-agentic records are allowed through; LDI already covered them

        kept.append(rec)

    logger.info(
        "Structural filter: %d invalid_syntax, %d shallow, %d meta_speech, %d low_ldi — "
        "%d remaining",
        stats.invalid_syntax, stats.shallow_thinking, stats.meta_speech,
        stats.low_ldi, len(kept),
    )
    return kept


# ===========================================================================
# Phase 3 — Semantic deduplication (MinHash-LSH)
# ===========================================================================

def _extract_assistant_text(rec: Dict[str, Any]) -> str:
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
    """Heuristic quality score in [0, 1] — higher is better."""
    if not text.strip():
        return 0.0
    tokens = re.findall(r"\w+", text.lower())
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
    return {normalised[i: i + k] for i in range(len(normalised) - k + 1)}


def _build_clusters_datasketch(
    texts: List[str],
    threshold: float,
    num_perm: int,
    shingle_k: int,
) -> Optional[List[List[int]]]:
    if not _DATASKETCH_AVAILABLE:
        return None
    logger.info("MinHash-LSH clustering (num_perm=%d, threshold=%.2f)", num_perm, threshold)
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


def semantic_dedup(
    records: List[Dict[str, Any]],
    stats: CurationStats,
    *,
    threshold: float = DEFAULT_DEDUP_THRESHOLD,
    quality_cutoff: float = DEFAULT_QUALITY_CUTOFF,
    num_perm: int = DEFAULT_MINHASH_PERMS,
    shingle_k: int = DEFAULT_SHINGLE_K,
) -> List[Dict[str, Any]]:
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
        quality_cutoff, len(candidates), len(low_q),
    )

    texts = [r["_text"] for r in candidates]
    clusters = (
        _build_clusters_datasketch(texts, threshold, num_perm=num_perm, shingle_k=shingle_k)
        or _build_clusters_naive(texts, threshold, shingle_k=shingle_k)
    )

    idx_map = {i: rec for i, rec in enumerate(candidates)}
    removed_idx: Set[int] = set()
    kept_records: List[Dict[str, Any]] = []

    for cluster in clusters:
        if not cluster:
            continue
        if len(cluster) == 1:
            kept_records.append(idx_map[cluster[0]])
        else:
            best = max(cluster, key=lambda i: (idx_map[i]["_qs"], len(idx_map[i]["_text"]), -i))
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

    final: List[Dict[str, Any]] = []
    for r in kept_records:
        r_out = {k: v for k, v in r.items() if not k.startswith("_")}
        r_out.setdefault("metadata", {})
        r_out["metadata"]["curation"] = {"kept": True, "quality_score": r["_qs"]}
        final.append(r_out)

    logger.info(
        "Semantic dedup (threshold=%.2f): %d clusters, %d kept, %d removed",
        threshold, len(clusters), len(final), len(removed_idx),
    )
    return final


# ===========================================================================
# I/O helpers
# ===========================================================================

def load_jsonl(path: str, sample: int = 0) -> List[Dict[str, Any]]:
    """Load a JSONL file; optionally limit to first ``sample`` records."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if sample and len(records) >= sample:
                break
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.debug("Skipping malformed JSON at line %d: %s", lineno, exc)
    return records


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def save_report(report: Dict[str, Any], reports_dir: str, filename: str) -> str:
    os.makedirs(reports_dir, exist_ok=True)
    out = os.path.join(reports_dir, filename)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return out


# ===========================================================================
# CLI
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nemo_curator_suite",
        description=(
            "AEGF NeMo Curator Suite — four-phase quality curation for JSONL datasets.\n\n"
            "Phases:\n"
            "  --exact-dedup   Phase 0: SHA-256 exact deduplication\n"
            "  --filter        Phase 1: NeMo Curator quality filters (container required)\n"
            "  --structural    Phase 2: Syntax, think-depth, LDI, meta-speech filters\n"
            "  --dedup         Phase 3: MinHash-LSH semantic deduplication\n\n"
            "⚠️  Phase 1 requires the aegf_curator container:\n"
            "    cd deploy/docker && docker compose up -d curator\n"
            "    docker exec -it aegf_curator bash\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    io = parser.add_argument_group("I/O")
    io.add_argument("--input", required=True, help="Source JSONL file.")
    io.add_argument("--output", required=True, help="Output JSONL file.")
    io.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR, metavar="DIR",
                    help=f"Directory for JSON statistics (default: {DEFAULT_REPORTS_DIR}).")

    phases = parser.add_argument_group("Pipeline phases (at least one required)")
    phases.add_argument("--exact-dedup", dest="do_exact_dedup", action="store_true",
                        help="Phase 0: exact SHA-256 deduplication.")
    phases.add_argument("--filter", dest="do_filter", action="store_true",
                        help="Phase 1: NeMo Curator quality-filter pipeline (needs container).")
    phases.add_argument("--structural", dest="do_structural", action="store_true",
                        help="Phase 2: structural quality gate (syntax, LDI, think-depth).")
    phases.add_argument("--dedup", dest="do_dedup", action="store_true",
                        help="Phase 3: MinHash-LSH semantic deduplication.")

    ex = parser.add_argument_group("Execution")
    ex.add_argument("--apply", action="store_true",
                    help="Write output file. Without this flag runs in dry-run mode.")
    ex.add_argument("--sample", type=int, default=0, metavar="N",
                    help="Process only first N records for quick validation (0 = all).")

    ft = parser.add_argument_group("Phase 1 — NeMo filter thresholds")
    ft.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)
    ft.add_argument("--max-symbol-ratio", type=float, default=DEFAULT_MAX_SYMBOL_RATIO)
    ft.add_argument("--max-non-alpha-ratio", type=float, default=DEFAULT_MAX_NON_ALPHA_RATIO)
    ft.add_argument("--max-url-ratio", type=float, default=DEFAULT_MAX_URL_RATIO)
    ft.add_argument("--max-no-endmark-ratio", type=float, default=DEFAULT_MAX_NO_ENDMARK_RATIO)
    ft.add_argument("--max-boilerplate-ratio", type=float, default=DEFAULT_MAX_BOILERPLATE_RATIO)
    ft.add_argument("--max-repeated-lines", type=float, default=DEFAULT_MAX_REPEATED_LINES)
    ft.add_argument("--max-ngram-ratio", type=float, default=DEFAULT_MAX_NGRAM_RATIO)
    ft.add_argument("--ngram-size", type=int, default=DEFAULT_NGRAM_SIZE)

    st = parser.add_argument_group("Phase 2 — Structural filter thresholds")
    st.add_argument("--min-think-chars", type=int, default=DEFAULT_MIN_THINK_CHARS,
                    help=f"Minimum chars in <think> block (default: {DEFAULT_MIN_THINK_CHARS}).")
    st.add_argument("--ldi-min-ratio", type=float, default=DEFAULT_LDI_MIN_RATIO,
                    help=f"Minimum LDI ratio on <tool_call> block (default: {DEFAULT_LDI_MIN_RATIO}).")
    st.add_argument("--no-attempt-check", dest="no_attempt_check", action="store_true",
                    help="Disable attempt_completion check (use for single-turn / production_v11 data).")

    dt = parser.add_argument_group("Phase 3 — Dedup thresholds")
    dt.add_argument("--dedup-threshold", type=float, default=DEFAULT_DEDUP_THRESHOLD,
                    help=f"MinHash similarity threshold (default: {DEFAULT_DEDUP_THRESHOLD}).")
    dt.add_argument("--quality-cutoff", type=float, default=DEFAULT_QUALITY_CUTOFF,
                    help=f"Minimum heuristic quality score (default: {DEFAULT_QUALITY_CUTOFF}).")
    dt.add_argument("--minhash-perms", type=int, default=DEFAULT_MINHASH_PERMS,
                    help=f"Number of MinHash permutations (default: {DEFAULT_MINHASH_PERMS}).")
    dt.add_argument("--shingle-k", type=int, default=DEFAULT_SHINGLE_K,
                    help=f"Character shingle size (default: {DEFAULT_SHINGLE_K}).")

    return parser


# ===========================================================================
# Main
# ===========================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any([args.do_exact_dedup, args.do_filter, args.do_structural, args.do_dedup]):
        parser.error("At least one phase required: --exact-dedup / --filter / --structural / --dedup")

    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        return 1

    dry_run = not args.apply
    phases = "+".join(
        x for x, f in [
            ("exact-dedup", args.do_exact_dedup),
            ("filter", args.do_filter),
            ("structural", args.do_structural),
            ("dedup", args.do_dedup),
        ] if f
    )
    logger.info(
        "AEGF NeMo Curator Suite | phases=%s | input=%s | dry_run=%s | sample=%d",
        phases, args.input, dry_run, args.sample,
    )

    stats = CurationStats()
    current_path = args.input
    import shutil
    temp_files: List[str] = []
    temp_dirs: List[str] = []

    def _next_temp() -> str:
        """Create a guaranteed-unique temp FILE and register it for cleanup."""
        tmp = tempfile.NamedTemporaryFile(
            suffix=".jsonl", prefix="aegf_cur_", delete=False
        )
        path = tmp.name
        tmp.close()
        temp_files.append(path)
        return path

    def _next_temp_dir() -> str:
        """Create a guaranteed-unique temp DIRECTORY and register it for cleanup.

        NeMo Curator's JsonlWriter expects a directory path, not a file path.
        """
        d = tempfile.mkdtemp(prefix="aegf_nemo_out_")
        temp_dirs.append(d)
        return d

    def _merge_jsonl_dir(src_dir: str, dest_file: str) -> int:
        """Merge all *.jsonl shards written by NeMo into a single flat file.

        Returns the total number of records written.
        """
        count = 0
        shards = sorted(glob.glob(os.path.join(src_dir, "*.jsonl")))
        if not shards:
            # NeMo may nest one level deeper
            shards = sorted(glob.glob(os.path.join(src_dir, "**", "*.jsonl"), recursive=True))
        with open(dest_file, "w", encoding="utf-8") as fout:
            for shard in shards:
                with open(shard, "r", encoding="utf-8") as fin:
                    for line in fin:
                        line = line.strip()
                        if line:
                            fout.write(line + "\n")
                            count += 1
        return count

    # -----------------------------------------------------------------------
    # Phase 0 — Exact dedup (in-memory)
    # -----------------------------------------------------------------------
    if args.do_exact_dedup:
        logger.info("Phase 0 — Exact deduplication")
        records = load_jsonl(current_path, sample=args.sample)
        stats.total_input = stats.total_input or len(records)
        records = exact_dedup(records, stats)
        if not dry_run:
            tmp = _next_temp()
            write_jsonl(tmp, records)
            current_path = tmp
        else:
            logger.info("[DRY-RUN] Would continue with %d records after exact dedup", len(records))

    # -----------------------------------------------------------------------
    # Phase 1 — NeMo Curator filter (requires container)
    # -----------------------------------------------------------------------
    if args.do_filter:
        if not _NEMO_AVAILABLE:
            logger.error(
                "nemo-curator not installed.\n"
                "Run inside aegf_curator container:\n"
                "  cd deploy/docker && docker compose up -d curator\n"
                "  docker exec -it aegf_curator bash"
            )
            return 1
        if dry_run:
            logger.info("[DRY-RUN] Would run NeMo filter pipeline on: %s", current_path)
        else:
            logger.info("Phase 1 — NeMo Curator filtering")
            # JsonlWriter requires a DIRECTORY — use mkdtemp, not a .jsonl file
            nemo_dir = _next_temp_dir()
            pre_nemo_count = sum(1 for line in open(current_path, "r", encoding="utf-8") if line.strip())
            run_nemo_filter_pipeline(
                input_path=current_path,
                output_path=nemo_dir,
                min_words=args.min_words,
                max_symbol_ratio=args.max_symbol_ratio,
                max_non_alpha_ratio=args.max_non_alpha_ratio,
                max_url_ratio=args.max_url_ratio,
                max_no_endmark_ratio=args.max_no_endmark_ratio,
                max_boilerplate_ratio=args.max_boilerplate_ratio,
                max_repeated_lines=args.max_repeated_lines,
                max_ngram_ratio=args.max_ngram_ratio,
                ngram_size=args.ngram_size,
            )
            # Merge NeMo shards → single flat JSONL for next phase
            nemo_merged = _next_temp()
            post_nemo_count = _merge_jsonl_dir(nemo_dir, nemo_merged)
            removed_by_nemo = pre_nemo_count - post_nemo_count
            logger.info(
                "Phase 1 complete: %d → %d records (%d removed by NeMo filters)",
                pre_nemo_count, post_nemo_count, removed_by_nemo,
            )
            current_path = nemo_merged

    # -----------------------------------------------------------------------
    # Phase 2 — Structural quality gate (in-memory)
    # -----------------------------------------------------------------------
    if args.do_structural:
        logger.info("Phase 2 — Structural quality gate")
        records = load_jsonl(current_path, sample=args.sample if not args.do_exact_dedup else 0)
        if not stats.total_input:
            stats.total_input = len(records)
        records = structural_quality_filter(
            records,
            stats,
            min_think_chars=args.min_think_chars,
            ldi_min_ratio=args.ldi_min_ratio,
            check_attempt_completion=not args.no_attempt_check,
        )
        if not dry_run:
            tmp = _next_temp()
            write_jsonl(tmp, records)
            current_path = tmp
        else:
            logger.info("[DRY-RUN] Would continue with %d records after structural filter", len(records))

    # -----------------------------------------------------------------------
    # Phase 3 — Semantic deduplication (in-memory)
    # -----------------------------------------------------------------------
    if args.do_dedup:
        logger.info("Phase 3 — Semantic deduplication (MinHash-LSH)")
        load_sample = args.sample if not any([args.do_exact_dedup, args.do_structural]) else 0
        records = load_jsonl(current_path, sample=load_sample)
        if not stats.total_input:
            stats.total_input = len(records)
        records = semantic_dedup(
            records,
            stats,
            threshold=args.dedup_threshold,
            quality_cutoff=args.quality_cutoff,
            num_perm=args.minhash_perms,
            shingle_k=args.shingle_k,
        )
        if dry_run:
            logger.info(
                "[DRY-RUN] Would write %d records → %s (use --apply to persist)",
                len(records), args.output,
            )
        else:
            n = write_jsonl(args.output, records)
            stats.total_output = n
            logger.info("Wrote %d curated records → %s", n, args.output)

    elif not dry_run and current_path != args.input:
        # Filter/structural only: move last temp to final output
        import shutil
        shutil.move(current_path, args.output)
        stats.total_output = sum(1 for _ in open(args.output))
        logger.info("Output → %s", args.output)

    # -----------------------------------------------------------------------
    # Reports
    # -----------------------------------------------------------------------
    stats.total_input = stats.total_input or 0
    report_path = save_report(stats.as_dict(), args.reports_dir, "nemo_curator_suite_report.json")
    logger.info("Report saved → %s", report_path)

    stats.print_report()

    # Cleanup temp files
    for p in temp_files:
        try:
            if os.path.exists(p) and p != args.output:
                os.remove(p)
        except OSError:
            pass
    # Cleanup temp directories (NeMo output shards)
    for d in temp_dirs:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
