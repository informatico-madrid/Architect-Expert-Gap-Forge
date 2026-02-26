#!/usr/bin/env python3
import json
import re
from pathlib import Path

JSONL = Path("data/synthetic/hacs_platinum_v1 copy.jsonl")
# Change this ID to debug a specific sample, or extend parser to accept CLI args
TARGET_ID = "gold_test_currency"

if not JSONL.exists():
    print("File not found:", JSONL)
    raise SystemExit(1)

found = False
with JSONL.open('r', encoding='utf-8') as f:
    for lineno, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get('id') == TARGET_ID:
            found = True
            conv = obj.get('conversation', [])
            print(f"Found {TARGET_ID} at line {lineno}; turns={len(conv)}")
            assistant_idx = [i for i, m in enumerate(conv) if isinstance(m, dict) and m.get('role') == 'assistant']
            print("assistant indices:", assistant_idx)

            combined = ' '.join([m.get('content', '') for m in conv if isinstance(m, dict)])
            print("contains '</think><tool_call>'?", '</think><tool_call>' in combined)
            print("combined length:", len(combined))
            print("--- combined snippet (first 400 chars) ---")
            print(repr(combined[:400]))

            # Original regex approach (as in uploader)
            think_match = re.search(r'<think>(.*?)</think>', combined, re.DOTALL)
            tool_match = re.search(r'<tool_call>(.*?)</tool_call>', combined, re.DOTALL)

            print("think_match?", bool(think_match))
            print("tool_match?", bool(tool_match))
            thought_extracted = think_match.group(1).strip() if think_match else None
            code_extracted = tool_match.group(1).strip() if tool_match else None
            print("--- Original extraction ---")
            print("thought_extracted (len):", len(thought_extracted) if thought_extracted else 0)
            print(thought_extracted)
            print("code_extracted (len):", len(code_extracted) if code_extracted else 0)
            print(code_extracted)

            # Alternative robust regex (explicit [\s\S])
            think2 = re.search(r'<think>([\s\S]*?)</think>', combined)
            tool2 = re.search(r'<tool_call>([\s\S]*?)</tool_call>', combined)
            thought2 = think2.group(1).strip() if think2 else None
            code2 = tool2.group(1).strip() if tool2 else None
            print("--- Alternative extraction ([\\s\\S]) ---")
            print("thought2 (len):", len(thought2) if thought2 else 0)
            print(thought2)
            print("code2 (len):", len(code2) if code2 else 0)
            print(code2)

            break

if not found:
    print("Target not found:", TARGET_ID)
