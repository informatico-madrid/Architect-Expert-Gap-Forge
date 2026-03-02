#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Dataset health check and audit for PLATINUM SFT dataset.

Usage:
  diagnose/dataset_health_check.py --input data/synthetic/PLATINUM_FINAL_SFT_DATASET.jsonl \
    --report data/reports/health_audit_report.json --plot data/reports/length_distribution.png

This script checks every record and emits a JSON report with "red flags".
"""
from __future__ import annotations
import argparse
import json
import os
import re
from collections import Counter, OrderedDict
from typing import Any, Dict, List, Tuple


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s


def find_think_length(rec: Dict[str, Any]) -> int:
    for k in ("think_length", "thought_length", "thought_original_length", "think_len", "think_chars"):
        v = rec.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    for c in ("metadata", "meta", "analysis", "data", "fields"):
        sub = rec.get(c)
        if isinstance(sub, dict):
            for k in ("think_length", "thought_original_length", "think_len"):
                v = sub.get(k)
                if isinstance(v, (int, float)):
                    return int(v)
    return None


def extract_thought_text(rec: Dict[str, Any]) -> str:
    # direct candidates
    for k in ("thought_extracted", "thought", "thought_text", "think_text", "thought_original"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # nested
    for c in ("fields", "data", "metadata", "meta", "analysis"):
        sub = rec.get(c)
        if isinstance(sub, dict):
            for k, v in sub.items():
                if isinstance(k, str) and ("thought" in k or "think" in k) and isinstance(v, str) and v.strip():
                    return v.strip()
    # conversation: prefer assistant <think>
    conv = rec.get("conversation")
    if isinstance(conv, list):
        for m in conv:
            if isinstance(m, dict) and m.get("role") == "assistant":
                content = m.get("content", "")
                if not isinstance(content, str):
                    continue
                m1 = re.search(r"<think>([\s\S]*?)</think>", content, flags=re.IGNORECASE)
                if m1:
                    return m1.group(1).strip()
                if "<think>" in content.lower():
                    idx = content.lower().find("<think>")
                    return content[idx + 7 :].strip()
        # fallback: any assistant content
        for m in conv:
            if isinstance(m, dict) and m.get("role") == "assistant":
                content = m.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
    return ""


def extract_user_prompt(rec: Dict[str, Any]) -> str:
    for k in ("instruction", "user_prompt", "prompt", "user_input"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    conv = rec.get("conversation")
    if isinstance(conv, list):
        for m in conv:
            if isinstance(m, dict) and m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
    return ""


def count_tag_occurrences_in_assistant(rec: Dict[str, Any]) -> Dict[str, int]:
    conv = rec.get("conversation")
    results = {"think_pairs": 0, "tool_pairs": 0, "stray_tags_outside": 0, "valid_structure": True}
    if not isinstance(conv, list):
        return results

    for m in conv:
        if not (isinstance(m, dict) and m.get("role") == "assistant"):
            continue
        content = m.get("content", "")
        if not isinstance(content, str):
            continue

        # V11.2: Detección flexible de pensamiento (acepta texto antes de </think>)
        has_closing_think = "</think>" in content.lower()
        has_opening_think = "<think>" in content.lower()
        
        # Detección de bloques de código (tool_call o write_action)
        tool_matches = list(re.finditer(r"<(tool_call|write_action)>[\s\S]*?</\1>", content, flags=re.IGNORECASE))
        results["tool_pairs"] += len(tool_matches)

        # Lógica de Validación de Estructura Blackwell
        # -------------------------------------------
        # Caso A: Estructura estándar (Think + Tool/Action)
        if has_closing_think and len(tool_matches) >= 1:
            results["think_pairs"] = 1
            # Validamos que el pensamiento termine antes de que empiece la acción
            idx_think_end = content.lower().find("</think>")
            if idx_think_end < tool_matches[0].start():
                continue # Estructura OK
        
        # Caso B: Estructura de Teoría (Think + Texto Markdown)
        elif has_closing_think and len(tool_matches) == 0:
            results["think_pairs"] = 1
            # Si hay texto significativo después de </think>, es una muestra de teoría válida
            idx_think_end = content.lower().find("</think>")
            if len(content[idx_think_end:].strip()) > 20:
                continue # Teoría OK
        
        # Caso C: Sin etiquetas (Muestras legacy o simples)
        elif not has_closing_think and len(tool_matches) == 0:
            continue # Sin tags es válido si no se requiere razonamiento
            
        # Si llega aquí, algo está mal (etiquetas mal cerradas, orden inverso, etc.)
        results["valid_structure"] = False

    return results


def extract_tool_call_code(rec: Dict[str, Any]) -> str:
    # attempt to extract text between <tool_call>...</tool_call>
    conv = rec.get("conversation")
    if isinstance(conv, list):
        for m in conv:
            if isinstance(m, dict) and m.get("role") == "assistant":
                c = m.get("content", "")
                if not isinstance(c, str):
                    continue
                m1 = re.search(r"<tool_call>([\s\S]*?)</tool_call>", c, flags=re.IGNORECASE)
                if m1:
                    inner = m1.group(1).strip()
                    # try parse JSON
                    try:
                        obj = json.loads(inner)
                        # common pattern: {"name":..., "arguments": {"content": "..."}}
                        if isinstance(obj, dict):
                            if "arguments" in obj and isinstance(obj["arguments"], dict):
                                # common 'content' field
                                if "content" in obj["arguments"] and isinstance(obj["arguments"]["content"], str):
                                    return obj["arguments"]["content"].strip()
                            if "content" in obj and isinstance(obj["content"], str):
                                return obj["content"].strip()
                        # fallback: return pretty JSON
                        return json.dumps(obj)
                    except Exception:
                        # not JSON: return raw inner text
                        return inner
    return ""


def _remove_docstrings_and_comments(code: str) -> str:
    """Remove triple-quoted docstrings and line comments for safer heuristics."""
    if not code:
        return ""
    # remove triple-quoted strings (naive)
    code_no_doc = re.sub(r'("""|\'\'\')[\s\S]*?\1', '', code)
    # remove single-line comments
    code_no_comments = re.sub(r"#.*", '', code_no_doc)
    return code_no_comments


def _ellipsis_in_function_body(code: str) -> bool:
    """Return True if '...' appears in function bodies (not in comments/docstrings)."""
    cleaned = _remove_docstrings_and_comments(code)
    if '...' not in cleaned:
        return False
    lines = cleaned.splitlines()
    # find lines with ellipsis
    for idx, line in enumerate(lines):
        if '...' in line:
            # find a def above within 20 lines
            for k in range(max(0, idx - 20), idx + 1):
                if re.match(r"\s*def\s+\w+\s*\(.*\)\s*:", lines[k]):
                    def_indent = len(lines[k]) - len(lines[k].lstrip())
                    ell_indent = len(line) - len(line.lstrip())
                    if ell_indent > def_indent:
                        return True
    return False


def _empty_function_or_pass_detected(code: str) -> bool:
    """Detect simple empty function patterns: a function with only pass/return None."""
    cleaned = _remove_docstrings_and_comments(code)
    lines = cleaned.splitlines()
    for idx, line in enumerate(lines):
        if re.match(r"\s*def\s+\w+\s*\(.*\)\s*:", line):
            def_indent = len(line) - len(line.lstrip())
            # scan following lines until next def at same or smaller indent
            body_lines = []
            for j in range(idx + 1, min(len(lines), idx + 200)):
                lj = lines[j]
                if not lj.strip():
                    continue
                indent = len(lj) - len(lj.lstrip())
                if indent <= def_indent:
                    break
                body_lines.append(lj.strip())
            # if body_lines contain only 'pass' or 'return None' or are empty -> flag
            if not body_lines:
                return True
            stripped = [bl for bl in body_lines if bl and not bl.startswith('#')]
            if all(re.match(r'^(pass|return\s+None)($|\s+#)', bl) for bl in stripped):
                return True
    return False


def ldi_from_record(rec: Dict[str, Any]) -> Tuple[float, str]:
    # try common places and several key names; return (value, source)
    keys = ("ldi_final", "ldiScore", "ldi_score", "ldi")
    for k in keys:
        v = rec.get(k)
        if isinstance(v, (int, float)):
            return float(v), "record"
    for c in ("metadata", "meta", "analysis", "analysis_meta"):
        sub = rec.get(c)
        if isinstance(sub, dict):
            for k in keys:
                v = sub.get(k)
                if isinstance(v, (int, float)):
                    return float(v), f"{c}.{k}"
    # try nested search
    for c in ("metadata", "meta", "analysis"):
        sub = rec.get(c)
        if isinstance(sub, dict):
            for k, v in sub.items():
                if isinstance(v, (int, float)) and "ldi" in k.lower():
                    return float(v), f"{c}.{k}"

    # fallback: compute approximate LDI from lengths if code present
    code_text = extract_tool_call_code(rec) or ""
    thought = extract_thought_text(rec) or ""
    code_tokens = max(0, int(len(code_text) / 4))
    natural_tokens = max(0, int(len(thought) / 4))
    if code_tokens == 0:
        return None, "missing"
    K = 1200.0
    ldi_score = code_tokens / max(1.0, (natural_tokens + code_tokens))
    ldi_final = ldi_score * (code_tokens / (code_tokens + K))
    return float(ldi_final), "computed"


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[\.\!\?\n]+", text)
    return [p.strip() for p in parts if p and p.strip()]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="data/synthetic/PLATINUM_FINAL_SFT_DATASET.jsonl")
    parser.add_argument("--report", "-r", default="data/reports/health_audit_report.json")
    parser.add_argument("--plot", "-p", default="data/reports/length_distribution.png")
    args = parser.parse_args(argv)

    os.makedirs(os.path.dirname(args.report), exist_ok=True)

    # configure length buckets including finer granularity above 2000
    buckets = [(0, 500), (500, 1000), (1000, 2000)]
    # add 1k-wide buckets from 2k to 10k
    for start in range(2000, 10000, 1000):
        buckets.append((start, start + 1000))
    # final overflow bucket
    buckets.append((10000, float("inf")))
    bucket_counts = [0 for _ in buckets]
    total_chars = 0
    total_records = 0
    suspects = []

    # phrases for boilerplate detection (normalized)
    phrases = [
        "análisis de arquitectura y dependencias",
        "recuerda usa las leyes",
        "prohibido no redactes",
        "¡cierra el tag",
        "sé conciso y técnico",
        # English variants for universal auditing
        "architecture analysis and dependencies",
        "remember use the laws",
        "do not write the file here",
        "close the tag",
        "be concise and technical",
    ]
    phrases_norm = [normalize_text(p) for p in phrases]

    with open(args.input, "r", encoding="utf-8") as fin:
        for i, line in enumerate(fin, start=1):
            if not line.strip():
                continue
            total_records += 1
            try:
                rec = json.loads(line)
            except Exception:
                # skip unparseable
                continue

            rid = rec.get("id") or rec.get("sample_id") or f"line_{i}"
            thought = extract_thought_text(rec) or ""
            think_len = find_think_length(rec)
            if think_len is None:
                think_len = len(thought)
            total_chars += len(thought)

            # buckets
            for bi, (lo, hi) in enumerate(buckets):
                if lo <= think_len < hi:
                    bucket_counts[bi] += 1
                    break

            # prepare flags
            flags = []

            # 1) Entropy-zero / echo-of-prompt detection
            user_prompt = extract_user_prompt(rec) or ""
            if user_prompt and thought:
                un = normalize_text(user_prompt)
                tn = normalize_text(thought)
                if un:
                    occ = tn.count(un)
                    if occ > 0 and (len(un) * occ) >= 0.6 * max(1, len(tn)):
                        flags.append("ECHO_PROMPT_ENTROPY_ZERO")

            # 2) Syntax tags check (recalibrated)
            tag_info = count_tag_occurrences_in_assistant(rec)
            # If no tags at all -> OK. If tags present, validate structure and stray tokens.
            think_pairs = tag_info.get("think_pairs", 0)
            tool_pairs = tag_info.get("tool_pairs", 0)
            stray = tag_info.get("stray_tags_outside", 0)
            valid = tag_info.get("valid_structure", True)
            if (think_pairs + tool_pairs) == 0:
                pass
            else:
                if not valid or stray > 0:
                    flags.append("SINTAXIS_KO")

            # 3) Lazy coding patterns (refined)
            code_text = extract_tool_call_code(rec) or ""
            lazy_reasons = []
            if code_text:
                # ellipsis: only flag if in function body (not in comments/docstrings)
                try:
                    if _ellipsis_in_function_body(code_text):
                        lazy_reasons.append("ELLIPSIS_IN_FUNC_BODY")
                except Exception:
                    pass
                # evasive comments
                if re.search(r"#.*(resto del codigo igual|resto del código igual|implementar aqui|\[implementación\]|implementacion|implement here|to be implemented)", code_text, flags=re.IGNORECASE):
                    lazy_reasons.append("COMMENTS_EVASIVE")
                # functions empty / pass detection (refined)
                try:
                    if _empty_function_or_pass_detected(code_text):
                        lazy_reasons.append("EMPTY_FUNCTION_OR_PASS")
                except Exception:
                    pass
            if lazy_reasons:
                flags.append("LAZY_CODE_" + "+".join(sorted(set(lazy_reasons))))

            # 4) Outliers: LDI final (with fallback)
            ldi_val, ldi_source = ldi_from_record(rec)
            if ldi_val is not None:
                try:
                    if float(ldi_val) < 0.05:
                        # If LDI was computed (fallback), only flag when code portion is non-trivial
                        if ldi_source == "computed":
                            code_tokens = max(0, int(len(code_text) / 4))
                            if code_tokens >= 20:
                                flags.append("LDI_FINAL_LT_0.05_COMPUTED")
                        else:
                            flags.append("LDI_FINAL_LT_0.05")
                except Exception:
                    pass

            # 5) Short thought
            if think_len < 300:
                flags.append("THINK_TOO_SHORT_LT_300")

            # 6) Repeated sentence loop detection (higher threshold, ignore lists)
            sentences = split_sentences(thought)
            if sentences:
                # normalize and filter
                norm_sentences = [s.strip().lower() for s in sentences if s.strip()]
                c = Counter(norm_sentences)
                repeated_flag = False

                # compute longest consecutive run for each normalized sentence
                max_run = {}
                prev = None
                run = 0
                for s in norm_sentences:
                    if s == prev:
                        run += 1
                    else:
                        if prev is not None:
                            max_run[prev] = max(max_run.get(prev, 0), run)
                        run = 1
                        prev = s
                if prev is not None:
                    max_run[prev] = max(max_run.get(prev, 0), run)

                for s_text, cnt in c.items():
                    # only consider sentences that occur frequently
                    if cnt > 7:
                        # ignore short list-like repetitions as before
                        if len(s_text) < 80:
                            lines = thought.splitlines()
                            list_like = sum(1 for line in lines if line.strip().startswith(('-', '*')) and s_text in normalize_text(line))
                            if list_like >= 3:
                                continue

                        # stricter conditions: either a long consecutive run or dominates the text
                        if max_run.get(s_text, 0) >= 4:
                            repeated_flag = True
                            break
                        if cnt >= 0.5 * len(norm_sentences):
                            repeated_flag = True
                            break
                if repeated_flag:
                    flags.append("REPEATED_SENTENCE_LOOP")

            if flags:
                suspects.append({
                    "id": rid,
                    "line": i,
                    "think_length": think_len,
                    "ldi_final": ldi_val,
                    "ldi_source": ldi_source,
                    "flags": flags,
                })

    # distribution summary
    total_tokens_est = int(total_chars / 4)

    # build bucket labels dynamically to match ranges
    bucket_labels = []
    for lo, hi in buckets:
        if hi == float("inf"):
            bucket_labels.append(f"{lo}+")
        else:
            bucket_labels.append(f"{lo}-{int(hi)}")

    report = {
        "input_file": args.input,
        "total_records": total_records,
        "total_thought_chars": total_chars,
        "estimated_tokens_approx": total_tokens_est,
        "buckets": {label: count for label, count in zip(bucket_labels, bucket_counts)},
        "suspect_count": len(suspects),
        "suspects": suspects,
    }

    # write report
    with open(args.report, "w", encoding="utf-8") as outf:
        json.dump(report, outf, ensure_ascii=False, indent=2)

    # try to produce a small bar chart (optional)
    try:
        import matplotlib.pyplot as plt

        labels = bucket_labels
        counts = bucket_counts
        plt.figure(figsize=(6, 3))
        plt.bar(labels, counts, color="#2b8cbe")
        plt.title("Distribución de longitud de pensamiento")
        plt.ylabel("Registros")
        plt.tight_layout()
        plt.savefig(args.plot, dpi=150)
        plt.close()
    except Exception:
        # fallback: write a small CSV with counts
        csvp = os.path.splitext(args.plot)[0] + ".csv"
        with open(csvp, "w", encoding="utf-8") as cf:
            cf.write("bucket,count\n")
            cf.write(f"0-500,{bucket_counts[0]}\n")
            cf.write(f"500-1000,{bucket_counts[1]}\n")
            cf.write(f"1000-2000,{bucket_counts[2]}\n")
            cf.write(f"2000+,{bucket_counts[3]}\n")

    print(f"Report written: {args.report}")
    print(f"Estimated tokens (approx): {total_tokens_est}")
    print(f"Bucket counts: {report['buckets']}")  # updated labels reflect finer granularity
    print(f"Suspect_count: {len(suspects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
