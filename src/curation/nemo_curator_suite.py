#!/usr/bin/env python3

"""AEGF (Architect-Expert-Gap-Forge) — NeMo Curator Suite.



Unified quality-filtering and semantic-deduplication engine for JSONL datasets.

Combines the NeMo Curator distributed pipeline (--filter) and MinHash-LSH

in-memory deduplication (--dedup) into a single composable CLI.



Usage examples

--------------

# Run both phases (filter then dedup) and persist the result:

  python src/curation/nemo_curator_suite.py \\

      --input  data/synthetic/CLEAN.jsonl \\

      --output data/synthetic/CURATED.jsonl \\

      --filter --dedup --apply



# Quality filtering only (NeMo Curator + Ray required):

  python src/curation/nemo_curator_suite.py \\

      --input  data/synthetic/CLEAN.jsonl \\

      --output data/synthetic/FILTERED.jsonl \\

      --filter --apply --min-words 100



# Semantic dedup only (dry-run, shows counts without writing):

  python src/curation/nemo_curator_suite.py \\

      --input  data/synthetic/FILTERED.jsonl \\

      --output data/synthetic/CURATED.jsonl \\

      --dedup --dedup-threshold 0.90 --quality-cutoff 0.35



Dependencies

------------

  NeMo Curator + Ray (required for --filter):

    pip install nemo-curator[ray]



  datasketch (recommended for --dedup, falls back to naive Jaccard if absent):

    pip install datasketch

"""

from __future__ import annotations



import argparse

import json

import logging

import os

import re

import sys

import tempfile

from collections import Counter, defaultdict

from pathlib import Path

from typing import Any, Dict, Iterable, List, Optional, Set



# ---------------------------------------------------------------------------

# Logging setup

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

_RAY_AVAILABLE = False

_DATASKETCH_AVAILABLE = False



try:

    from nemo_curator.core.client import RayClient  # type: ignore

    from nemo_curator.pipeline import Pipeline  # type: ignore

    from nemo_curator.stages.text.io.reader import JsonlReader  # type: ignore

    from nemo_curator.stages.text.io.writer import JsonlWriter  # type: ignore

    from nemo_curator.stages.text.modules import ScoreFilter, Modify  # type: ignore

    from nemo_curator.stages.text.filters import (  # type: ignore

        WordCountFilter,

        RepeatingTopNGramsFilter,

        SymbolsToWordsFilter,

        NonAlphaNumericFilter,

        PunctuationFilter,

        BoilerPlateStringFilter,

        UrlsFilter,

        RepeatedLinesFilter,

    )

    _NEMO_AVAILABLE = True

except ImportError:

    pass



try:

    import ray  # type: ignore

    _RAY_AVAILABLE = True

except ImportError:

    pass



try:

    from datasketch import MinHash, MinHashLSH  # type: ignore

    _DATASKETCH_AVAILABLE = True

except ImportError:

    pass



# ---------------------------------------------------------------------------

# Default threshold constants (all overridable via CLI)

# ---------------------------------------------------------------------------

DEFAULT_MIN_WORDS: int = 80

DEFAULT_MAX_SYMBOL_RATIO: float = 0.10

DEFAULT_MAX_NON_ALPHA_RATIO: float = 0.25

DEFAULT_MAX_URL_RATIO: float = 0.20

DEFAULT_MAX_NO_ENDMARK_RATIO: float = 0.85

DEFAULT_MAX_BOILERPLATE_RATIO: float = 0.40

DEFAULT_MAX_REPEATED_LINES: float = 0.70

DEFAULT_MAX_NGRAM_RATIO: float = 0.08

DEFAULT_NGRAM_SIZE: int = 3



DEFAULT_DEDUP_THRESHOLD: float = 0.85

DEFAULT_QUALITY_CUTOFF: float = 0.30

DEFAULT_MINHASH_PERMS: int = 128

DEFAULT_SHINGLE_K: int = 5



DEFAULT_REPORTS_DIR: str = "data/reports"





# ===========================================================================

# Phase 1 — Quality Filtering (NeMo Curator + Ray)

# ===========================================================================



class ConversationExtractor:

    """NeMo Curator Modifier that extracts assistant turns into a side column.



    Reads the ``conversation`` list field and concatenates all assistant

    ``content`` values into ``filter_text``.  The original ``conversation``

    field is left intact so the dataset schema is preserved.

    """



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





def run_filter_pipeline(

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

    """Run the NeMo Curator quality-filter pipeline (requires nemo-curator + Ray).



    Applies a battery of text-quality filters on the assistant portion of each

    conversation sample.  Writes the surviving records to ``output_path``.



    Parameters

    ----------

    input_path:

        Path to the source JSONL file.

    output_path:

        Destination path for filtered JSONL output.

    min_words:

        Minimum number of words required in the assistant text.

    max_symbol_ratio:

        Maximum allowed symbol-to-word ratio (e.g. 0.10 = 10%).

    max_non_alpha_ratio:

        Maximum allowed non-alphanumeric-to-text ratio.

    max_url_ratio:

        Maximum allowed URL-to-text ratio.

    max_no_endmark_ratio:

        Maximum fraction of sentences without a terminal punctuation mark.

    max_boilerplate_ratio:

        Maximum boilerplate-string ratio.

    max_repeated_lines:

        Maximum fraction of repeated lines.

    max_ngram_ratio:

        Maximum repeating top-N-gram ratio.

    ngram_size:

        N-gram order for the repeating top-N-gram filter.



    Raises

    ------

    RuntimeError

        If nemo-curator or Ray are not installed.

    FileNotFoundError

        If ``input_path`` does not exist.

    """

    if not _NEMO_AVAILABLE:

        raise RuntimeError(

            "nemo-curator is not installed. Run: pip install 'nemo-curator[ray]'"

        )

    if not os.path.exists(input_path):

        raise FileNotFoundError(f"Input file not found: {input_path}")



    logger.info("Starting NeMo Curator filter pipeline: %s", input_path)

    client = RayClient()

    client.start()



    try:

        pipeline = Pipeline(name="aegf_curation_filter_v1")



        # --- Stage 0: Load JSONL -----------------------------------------------

        pipeline.add_stage(JsonlReader(file_paths=input_path))



        # --- Stage 1: Extract assistant text into a side column ----------------

        pipeline.add_stage(

            Modify(

                modifier_fn=ConversationExtractor(),

                input_fields=["conversation"],

                output_fields=["filter_text"],

            )

        )



        # --- Stage 2: Quality filters (applied on the side column) -------------

        filter_stages = [

            ScoreFilter(

                filter_obj=WordCountFilter(min_words=min_words),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=SymbolsToWordsFilter(max_symbol_to_word_ratio=max_symbol_ratio),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=NonAlphaNumericFilter(

                    max_non_alpha_numeric_to_text_ratio=max_non_alpha_ratio

                ),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=UrlsFilter(max_url_to_text_ratio=max_url_ratio),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=PunctuationFilter(

                    max_num_sentences_without_endmark_ratio=max_no_endmark_ratio

                ),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=BoilerPlateStringFilter(

                    max_boilerplate_string_ratio=max_boilerplate_ratio

                ),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=RepeatedLinesFilter(

                    max_repeated_line_fraction=max_repeated_lines

                ),

                text_field="filter_text",

            ),

            ScoreFilter(

                filter_obj=RepeatingTopNGramsFilter(

                    n=ngram_size,

                    max_repeating_ngram_ratio=max_ngram_ratio,

                ),

                text_field="filter_text",

            ),

        ]

        for stage in filter_stages:

            pipeline.add_stage(stage)



        # --- Stage 3: Write output (includes the auxiliary filter_text column) -

        pipeline.add_stage(JsonlWriter(path=output_path))



        logger.info("Running quality-filter pipeline via Ray (%d filter stages)", len(filter_stages))

        pipeline.run()

        logger.info("Filter pipeline complete. Output written to: %s", output_path)

    except Exception as exc:

        logger.error("Critical error in NeMo filter pipeline: %s", exc)

        raise

    finally:

        client.stop()





# ===========================================================================

# Phase 2 — Semantic Deduplication (MinHash-LSH or fallback)

# ===========================================================================



def extract_assistant_text(rec: Dict[str, Any]) -> str:

    """Extract the assistant response text from a JSONL record.



    Tries several common field names before falling back to the full

    ``conversation`` list.  Returns an empty string if nothing is found.

    """

    for key in ("assistant", "assistant_response", "response", "output", "text"):

        val = rec.get(key)

        if isinstance(val, str) and val.strip():

            return val.strip()



    conversation = rec.get("conversation")

    if isinstance(conversation, list):

        parts: List[str] = []

        for msg in conversation:

            if isinstance(msg, dict):

                if msg.get("role") == "assistant":

                    content = msg.get("content") or msg.get("text") or msg.get("value")

                    if isinstance(content, str):

                        parts.append(content.strip())

            elif isinstance(msg, str):

                parts.append(msg.strip())

        if parts:

            return "\n".join(parts).strip()



    # Last-resort fallback: use reasoning/thought columns if present

    thought = rec.get("thought_extracted") or rec.get("thoughts")

    if isinstance(thought, str) and thought.strip():

        return thought.strip()



    return ""





def quality_score(text: str) -> float:

    """Compute a heuristic quality score in [0.0, 1.0] for an assistant response.



    Higher is better.  Features used:

    - Unique token ratio (breadth of vocabulary)

    - Most-common-token dominance (penalises repetitive outputs)

    - Repeated sentence count (penalises looping outputs)

    - Ellipsis abundance (penalises truncated or lazy text)

    """

    if not text or not text.strip():

        return 0.0

    tokens = re.findall(r"\w+", text.lower())

    if not tokens:

        return 0.0

    n = len(tokens)

    unique_ratio = len(set(tokens)) / n

    most_common_frac = Counter(tokens).most_common(1)[0][1] / n

    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]

    has_repeated_sentence = any(c >= 3 for _, c in Counter(sentences).most_common())

    ellipsis_count = text.count("...")



    score = 0.6 * unique_ratio + 0.4 * (1.0 - most_common_frac)

    if has_repeated_sentence:

        score *= 0.35

    if ellipsis_count > 2:

        score *= 0.60

    return max(0.0, min(1.0, score))





def _char_shingles(text: str, k: int = DEFAULT_SHINGLE_K) -> Set[str]:

    """Return a set of character k-shingles for ``text``."""

    normalised = re.sub(r"\s+", " ", text.strip().lower()).replace(" ", "_")

    if not normalised:

        return set()

    if len(normalised) < k:

        return {normalised}

    return {normalised[i : i + k] for i in range(len(normalised) - k + 1)}





def _build_clusters_datasketch(

    texts: List[str],

    threshold: float,

    num_perm: int = DEFAULT_MINHASH_PERMS,

    shingle_k: int = DEFAULT_SHINGLE_K,

) -> Optional[List[List[int]]]:

    """Build near-duplicate clusters using datasketch MinHash-LSH.



    Returns ``None`` if datasketch is unavailable.  Candidates from the LSH

    index are post-filtered with exact Jaccard over character shingles to

    remove false positives.

    """

    if not _DATASKETCH_AVAILABLE:

        return None



    logger.info("Building MinHash signatures (num_perm=%d, threshold=%.2f)", num_perm, threshold)

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

        # Refine with exact Jaccard to reduce false positives

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

    shingle_k: int = DEFAULT_SHINGLE_K,

) -> List[List[int]]:

    """Build near-duplicate clusters via brute-force O(n^2) Jaccard similarity.



    Used only when datasketch and NeMo are unavailable.  Suitable for small

    datasets (< ~5 000 records).

    """

    logger.warning(

        "Falling back to O(n^2) exact Jaccard clustering — may be slow for large inputs. "

        "Install datasketch for faster processing: pip install datasketch"

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





def deduplicate(

    records: List[Dict[str, Any]],

    *,

    threshold: float = DEFAULT_DEDUP_THRESHOLD,

    quality_cutoff: float = DEFAULT_QUALITY_CUTOFF,

    num_perm: int = DEFAULT_MINHASH_PERMS,

    shingle_k: int = DEFAULT_SHINGLE_K,

) -> Dict[str, Any]:

    """Run quality filtering and MinHash-LSH semantic deduplication in memory.



    Pipeline

    --------

    1. Extract assistant text and compute a heuristic quality score per record.

    2. Drop records below ``quality_cutoff``.

    3. Build near-duplicate clusters on the surviving records using MinHash-LSH

       (datasketch) or naive Jaccard as a fallback.

    4. Within each cluster, keep the single best exemplar (highest quality

       score, then longest text, then lowest original index).



    Returns

    -------

    dict with keys:

        ``kept``                      - List of curated records (clean copies).

        ``removed_low_quality``       - Records dropped in step 2.

        ``removed_semantic_duplicates`` - Records dropped in step 4.

        ``counts``                    - Summary statistics dict.

    """

    # Step 1 — annotate records with internal metadata

    for rec in records:

        rec["_assistant_text"] = extract_assistant_text(rec)

        rec["_quality_score"] = quality_score(rec["_assistant_text"])



    # Step 2 — quality gate

    low_quality = [r for r in records if r["_quality_score"] < quality_cutoff]

    candidates = [r for r in records if r["_quality_score"] >= quality_cutoff]

    logger.info(

        "Quality gate (cutoff=%.2f): %d kept, %d dropped",

        quality_cutoff, len(candidates), len(low_quality),

    )



    texts = [r["_assistant_text"] for r in candidates]



    # Step 3 — cluster via MinHash-LSH (best available backend)

    clusters = (

        _build_clusters_datasketch(texts, threshold, num_perm=num_perm, shingle_k=shingle_k)

        or _build_clusters_naive(texts, threshold, shingle_k=shingle_k)

    )



    # Step 4 — select best exemplar per cluster

    idx_map = {i: rec for i, rec in enumerate(candidates)}

    removed_indices: Set[int] = set()

    kept_records: List[Dict[str, Any]] = []



    for cluster in clusters:

        if not cluster:

            continue

        if len(cluster) == 1:

            kept_records.append(idx_map[cluster[0]])

        else:

            best_idx = max(

                cluster,

                key=lambda i: (

                    idx_map[i]["_quality_score"],

                    len(idx_map[i]["_assistant_text"]),

                    -i,

                ),

            )

            for i in cluster:

                if i == best_idx:

                    kept_records.append(idx_map[i])

                else:

                    removed_indices.add(i)



    # Safety: add any candidate not covered by any cluster

    clustered = {i for cl in clusters for i in cl}

    for i, rec in idx_map.items():

        if i not in clustered:

            kept_records.append(rec)



    # Build clean copies with curation metadata, strip internal keys

    final_kept: List[Dict[str, Any]] = []

    for r in kept_records:

        r_out = {k: v for k, v in r.items() if not k.startswith("_")}

        r_out.setdefault("metadata", {})

        r_out["metadata"]["curation"] = {"kept": True, "quality_score": r["_quality_score"]}

        final_kept.append(r_out)



    removed_semantic = [idx_map[i] for i in sorted(removed_indices)]



    logger.info(

        "Dedup (threshold=%.2f): %d clusters, %d kept, %d removed as duplicates",

        threshold, len(clusters), len(final_kept), len(removed_semantic),

    )



    return {

        "kept": final_kept,

        "removed_low_quality": low_quality,

        "removed_semantic_duplicates": removed_semantic,

        "counts": {

            "total_input": len(records),

            "filtered_low_quality": len(low_quality),

            "removed_semantic_duplicates": len(removed_semantic),

            "final_total": len(final_kept),

        },

    }





# ===========================================================================

# I/O helpers

# ===========================================================================



def load_jsonl(path: str) -> List[Dict[str, Any]]:

    """Load a JSONL file and return a list of parsed records.



    Skips empty lines and silently ignores malformed JSON lines.

    """

    records: List[Dict[str, Any]] = []

    with open(path, "r", encoding="utf-8") as fh:

        for lineno, line in enumerate(fh, 1):

            line = line.strip()

            if not line:

                continue

            try:

                records.append(json.loads(line))

            except json.JSONDecodeError as exc:

                logger.debug("Skipping malformed JSON at line %d: %s", lineno, exc)

    return records





def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> int:

    """Write an iterable of dicts to a JSONL file.



    Creates parent directories as needed.  Returns the number of records

    written.

    """

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    count = 0

    with open(path, "w", encoding="utf-8") as fh:

        for rec in records:

            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

            count += 1

    return count





def save_report(report: Dict[str, Any], reports_dir: str, filename: str) -> str:

    """Write a JSON report to ``reports_dir/filename``.  Returns the full path."""

    os.makedirs(reports_dir, exist_ok=True)

    report_path = os.path.join(reports_dir, filename)

    with open(report_path, "w", encoding="utf-8") as fh:

        json.dump(report, fh, ensure_ascii=False, indent=2)

    return report_path





# ===========================================================================

# CLI

# ===========================================================================



def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        prog="nemo_curator_suite",

        description=(

            "AEGF NeMo Curator Suite — quality filtering and semantic deduplication "

            "for JSONL datasets. Use --filter, --dedup, or both."

        ),

        formatter_class=argparse.ArgumentDefaultsHelpFormatter,

    )



    # Required I/O

    io_group = parser.add_argument_group("I/O")

    io_group.add_argument("--input", required=True, help="Path to source JSONL file.")

    io_group.add_argument("--output", required=True, help="Path to output JSONL file.")

    io_group.add_argument(

        "--reports-dir",

        default=DEFAULT_REPORTS_DIR,

        metavar="DIR",

        help="Directory for JSON statistics reports.",

    )



    # Phase selection

    phase_group = parser.add_argument_group("Pipeline phases (at least one required)")

    phase_group.add_argument(

        "--filter",

        dest="do_filter",

        action="store_true",

        help="Run NeMo Curator quality-filter pipeline (requires nemo-curator + Ray).",

    )

    phase_group.add_argument(

        "--dedup",

        dest="do_dedup",

        action="store_true",

        help="Run in-memory MinHash-LSH semantic deduplication.",

    )



    # Filter thresholds

    ft = parser.add_argument_group("Filter thresholds (--filter)")

    ft.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)

    ft.add_argument("--max-symbol-ratio", type=float, default=DEFAULT_MAX_SYMBOL_RATIO)

    ft.add_argument("--max-non-alpha-ratio", type=float, default=DEFAULT_MAX_NON_ALPHA_RATIO)

    ft.add_argument("--max-url-ratio", type=float, default=DEFAULT_MAX_URL_RATIO)

    ft.add_argument("--max-no-endmark-ratio", type=float, default=DEFAULT_MAX_NO_ENDMARK_RATIO)

    ft.add_argument("--max-boilerplate-ratio", type=float, default=DEFAULT_MAX_BOILERPLATE_RATIO)

    ft.add_argument("--max-repeated-lines", type=float, default=DEFAULT_MAX_REPEATED_LINES)

    ft.add_argument("--max-ngram-ratio", type=float, default=DEFAULT_MAX_NGRAM_RATIO)

    ft.add_argument("--ngram-size", type=int, default=DEFAULT_NGRAM_SIZE)



    # Dedup thresholds

    dt = parser.add_argument_group("Dedup thresholds (--dedup)")

    dt.add_argument("--dedup-threshold", type=float, default=DEFAULT_DEDUP_THRESHOLD,

                    help="MinHash similarity threshold for near-duplicate clustering.")

    dt.add_argument("--quality-cutoff", type=float, default=DEFAULT_QUALITY_CUTOFF,

                    help="Minimum heuristic quality score to retain a record.")

    dt.add_argument("--minhash-perms", type=int, default=DEFAULT_MINHASH_PERMS,

                    help="Number of MinHash permutations (higher = more accurate, slower).")

    dt.add_argument("--shingle-k", type=int, default=DEFAULT_SHINGLE_K,

                    help="Character shingle size used for MinHash signatures.")
