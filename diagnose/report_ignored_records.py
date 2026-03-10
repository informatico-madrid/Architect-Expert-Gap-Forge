#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Analyzes `data/synthetic/hacs_platinum_v1.jsonl` and generates
`outputs/ignored_records_report.jsonl` containing the first 50
records that would be ignored by the upload pipeline.

Output: `data_factory/outputs/ignored_records_report.jsonl` (JSONL)
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

# Paths (relative to data_factory when executed from that cwd)
INPUT_PATH = Path("data/synthetic/hacs_platinum_v1.jsonl")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUTPUT_DIR / "ignored_records_report.jsonl"

MAX_REPORT = 50
MAX_SNIPPET = 500
ARGILLA_CONTENT_LIMIT = 20000


class LDIAnalyzer:
    """Copia reducida del LDI Analyzer usado en el pipeline."""

    @staticmethod
    def count_code_tokens(text: str) -> int:
        code_tokens = 0
        json_pattern = r"\{[^}]*\}"
        json_blocks = re.findall(json_pattern, text)
        for block in json_blocks:
            code_tokens += len(re.findall(r"\w+|[{}[\]:,]", block))

        code_block_pattern = r"```[\s\S]*?```"
        code_blocks = re.findall(code_block_pattern, text)
        for block in code_blocks:
            clean_block = block.replace("```", "").strip()
            code_tokens += len(re.findall(r"\w+|[{}[\]():;=.,<>]", clean_block))

        programming_keywords = [
            "async",
            "await",
            "def",
            "class",
            "import",
            "from",
            "return",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
            "lambda",
            "yield",
            "raise",
            "assert",
            "pass",
            "break",
            "continue",
            "True",
            "False",
            "None",
            "self",
            "super",
            "__init__",
            "function",
            "const",
            "let",
            "var",
            "new",
            "this",
            "export",
        ]

        for keyword in programming_keywords:
            code_tokens += len(re.findall(r"\b" + keyword + r"\b", text))

        text_without_code = text
        for block in json_blocks + code_blocks:
            text_without_code = text_without_code.replace(block, "")

        code_symbols = r"[{}[\]():;=.,<>!&|+\-*/%]"
        code_tokens += len(re.findall(code_symbols, text_without_code))

        return code_tokens

    @staticmethod
    def count_natural_language_tokens(text: str) -> int:
        json_pattern = r"\{[^}]*\}"
        text_clean = re.sub(json_pattern, "", text)
        code_block_pattern = r"```[\s\S]*?```"
        text_clean = re.sub(code_block_pattern, "", text_clean)
        text_clean = re.sub(r"<[^>]+>", "", text_clean)
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text_clean)
        programming_keywords = {
            "async",
            "await",
            "def",
            "class",
            "import",
            "from",
            "return",
            "true",
            "false",
            "none",
            "self",
            "super",
            "function",
            "const",
        }
        natural_words = [w for w in words if w.lower() not in programming_keywords]
        return len(natural_words)

    @classmethod
    def calculate_ldi(cls, text: str) -> tuple:
        code_tokens = cls.count_code_tokens(text)
        natural_tokens = cls.count_natural_language_tokens(text)
        if natural_tokens == 0:
            return (99.9, code_tokens, natural_tokens)
        ldi = code_tokens / natural_tokens
        return (ldi, code_tokens, natural_tokens)


def analyze() -> None:
    if not INPUT_PATH.exists():
        print(f"❌ Archivo no encontrado: {INPUT_PATH}")
        return

    ignored: List[Dict[str, Any]] = []
    total = 0

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            total += 1
            if len(ignored) >= MAX_REPORT:
                # seguimos contando pero no almacenamos más de MAX_REPORT
                try:
                    _ = json.loads(line)
                except Exception:
                    pass
                continue

            try:
                sample = json.loads(line)
            except Exception as e:
                ignored.append(
                    {
                        "lineno": lineno,
                        "sample_id": None,
                        "reason": "json_decode_error",
                        "error": str(e),
                        "raw_snippet": line[:MAX_SNIPPET],
                    }
                )
                continue

            sid = sample.get("id") or sample.get("sample_id")

            conv = sample.get("conversation")
            if not isinstance(conv, list):
                ignored.append(
                    {
                        "lineno": lineno,
                        "sample_id": sid,
                        "reason": "conversation_missing_or_not_list",
                        "conversation_type": type(conv).__name__,
                    }
                )
                continue

            bad = False
            for msg in conv:
                if not isinstance(msg, dict):
                    ignored.append(
                        {
                            "lineno": lineno,
                            "sample_id": sid,
                            "reason": "conversation_entry_not_object",
                            "entry_repr": str(msg)[:MAX_SNIPPET],
                        }
                    )
                    bad = True
                    break

                content = msg.get("content")
                role = msg.get("role")
                if content is None or not isinstance(content, str):
                    ignored.append(
                        {
                            "lineno": lineno,
                            "sample_id": sid,
                            "reason": "message_content_missing_or_non_string",
                            "role": role,
                        }
                    )
                    bad = True
                    break

                if len(content) > ARGILLA_CONTENT_LIMIT:
                    # calcular LDI del assistant (turn 2) para contexto
                    assistant_text = ""
                    if len(conv) > 1 and isinstance(conv[1], dict):
                        assistant_text = conv[1].get("content", "")
                    ldi, code_toks, nat_toks = LDIAnalyzer.calculate_ldi(
                        assistant_text or ""
                    )
                    ignored.append(
                        {
                            "lineno": lineno,
                            "sample_id": sid,
                            "reason": "message_content_too_long",
                            "role": role,
                            "message_length": len(content),
                            "snippet": content[:MAX_SNIPPET],
                            "assistant_ldi": round(ldi, 3),
                            "assistant_code_tokens": code_toks,
                            "assistant_natural_tokens": nat_toks,
                        }
                    )
                    bad = True
                    break

            if bad:
                continue

    # Guardar reporte
    with OUT_PATH.open("w", encoding="utf-8") as out:
        for entry in ignored:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(
        f"Procesadas {total} líneas; registros ignorados guardados: {len(ignored)} -> {OUT_PATH}"
    )


if __name__ == "__main__":
    analyze()
