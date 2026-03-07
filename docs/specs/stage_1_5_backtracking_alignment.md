# Stage 1.5 — Backtracking Alignment Specification

**Date:** 2026-03-06
**Status:** Draft
**Author:** AEGF Pipeline

---

## 1. Problem Statement

The fine-tuned model reasons correctly in its `<think>` block but still writes
legacy Home Assistant code (2023/2024 patterns). The probabilistic bias toward
old APIs is stronger than the reasoning alone can overcome. We need to train the
model to **simulate making the legacy mistake in its thinking, then catch and
correct itself** before writing the final code.

This technique—**Self-Evaluation + Backtracking**—is supported by OpenCodeReasoning
and AgentMath research: models that practice "almost committing to the wrong path
and reversing" produce statistically better outputs than models that only see
the correct path.

**CRITICAL ANTI-PATTERN (The Auditor Bias):** Previous curation attempts resulted in "post-facto audits" (e.g., "Let's analyze the provided solution. It uses X..."). This destroys the learning signal. The reasoning must be an **internal, first-person monologue of creation**, simulating the cognitive struggle from a blank canvas, strictly avoiding any language that implies the code is already written.

---

## 2. Source Dataset

**Path:** `data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl`

### 2.1 Structure per Record

```
{
  "id":           "v11_{type}_{hash}",
  "conversation": [
    {"role": "user",      "content": "<prompt with context>"},
    {"role": "assistant", "content": "...</think>\n<code block>"}
  ],
  "metadata": {
    "curation":        {"kept": true},
    "factory_version": "v10.0",
    "example_type":    "nominal|contrast|error_recovery|theory",
    "evol_difficulty":  null | "easy" | "medium" | "hard",
    "ldi":              float,
    "fragment_name":   "Module: config_flow",
    "source_file":     "acaia___init__.py",
    "gold_injected":    bool | null,
    "legacy_detected":  bool | null,
    "legacy_patterns":  ["description1", ...],
    "checkpoint_key":  "hex hash"
  },
  "filter_text": "..."
}
```

### 2.2 Dataset Statistics

| Metric               | Value   |
|----------------------|---------|
| Total records         | 19,732  |
| nominal               | 8,687   |
| contrast              | 6,785   |
| error_recovery        | 3,657   |
| theory                | 603     |
| gold_injected=True    | 13,782  |
| gold_injected=False   | 5,347   |
| legacy_detected=True  | 2,635   |
| legacy_detected=False | 16,494  |
| Avg LDI               | 1.271   |
| Has `</think>` tag    | 19,732  |
| Est. >4000 tokens     | ~6,059  |

---

## 3. Filtering Criteria

### 3.1 Hard Exclusions
1. **Theory type** → discard (no code to align)
2. **Estimated tokens > 4,000** → discard (training context budget)
3. **Records with no `</think>` tag** → discard (cannot split think/code)

### 3.2 Eligibility for Backtracking Rewrite
A record qualifies for think-block rewriting if ANY of:
- `legacy_detected == True` → highest priority (legacy patterns in source gold)
- `gold_injected == True` → the code was surgically replaced; think may not match
- `example_type in ("contrast", "error_recovery")` → pedagogically rich

Records that are `nominal`, `gold_injected=False`, `legacy_detected=False` with
high LDI are **kept as-is** (the model already reasoned and coded correctly).

### 3.3 Rewrite Strategies by Category

| Category | Rewrite Strategy |
|----------|-----------------|
| `legacy_detected=True` | **Full backtracking**: simulate the legacy impulse → self-evaluate → correct |
| `gold_injected=True, legacy_detected=False` | **Trace reconstruction**: given the gold code, reconstruct the expert reasoning path |
| `error_recovery` | **Error-first backtracking**: identify the error → propose wrong fix → catch → give correct fix |
| `contrast` | **Contrast backtracking**: present both old and new approach, explicitly reject old |
| `nominal, clean` | **Pass-through**: keep original think (already high quality) |

---

## 4. System Prompt for Think-Block Rewriting

### 4.1 Backtracking Rewrite Prompt (for legacy/contrast/error_recovery)

```
You are an expert Home Assistant developer rewriting the reasoning trace
(everything before </think>) for a training sample. The code after </think>
is SACRED and must NOT be referenced for modification.

Your task: Rewrite ONLY the reasoning block to simulate the real-time, 
internal monologue of writing this code from a BLANK CANVAS. You must follow the
Self-Evaluation + Backtracking pattern:

1. LEGACY IMPULSE: Start by proposing the legacy/old approach as your first natural instinct. Name the specific deprecated function or pattern (e.g., hass.data, async_get_registry).
2. SELF-EVALUATION: Pause and evaluate against the HA 2026 governance docs. Cite the rule that invalidates your first instinct.
3. BACKTRACKING: Explicitly reject the legacy approach with a clear rationale ("Wait, if I use X the code will fail because it is blocking...").
4. MODERN RESOLUTION: Structure the final plan using exclusively the modern API, perfectly setting up the provided solution.

CRITICAL CONSTRAINTS:
- FIRST PERSON, PRESENT TENSE ONLY ("I need to...", "My first instinct is...").
- NEVER act as an auditor or reviewer. DO NOT use phrases like "Let's analyze the provided code", "The solution avoids", or "This implementation satisfies".
- Output ONLY the reasoning text. Do NOT include </think> or any code blocks.
- Keep the reasoning concise (300-800 words).
- Write in the same language as the original reasoning.
```

### 4.2 Gold Trace Reconstruction Prompt

```
You are an expert Home Assistant developer. You are given a user prompt and the 
PERFECT HA 2026 solution code.

Your task is to REVERSE-ENGINEER the internal reasoning monologue (the <think> block) 
that an expert would have just BEFORE writing this exact code. 

Even though you are given the solution, you must PRETEND you are starting from a 
blank canvas. You must simulate the cognitive struggle:
1. Propose a legacy approach first (Legacy Impulse).
2. Correct yourself using HA 2026 architectural rules (Backtracking).
3. Plan the exact steps that lead to the provided perfect solution.

CRITICAL CONSTRAINTS:
- FIRST PERSON, PRESENT TENSE. ("I will start by...", "Wait, I shouldn't use...").
- NEVER act as an auditor reviewing code. NEVER say "The provided code uses..." or "The solution avoids...".
- Output ONLY the reasoning text. Do NOT include </think> or the code itself.
- Keep the reasoning concise (300-800 words).
- Write in the same language as the original prompt.
```

---

## 5. Existing Codebase Assets to Reuse

### 5.1 Inference Client
- **Module:** `src/audit/inference.py`
- **Class:** `VLLMClient(api_url, model)` — call `.generate(prompt, system_prompt=..., max_tokens=..., temperature=...)`
- **Also:** `InferenceRouter().student()` for cached client resolution
- **Endpoint:** `http://localhost:8000/v1` (configurable via `AEGF_VLLM_API_URL`)

### 5.2 Think Filter
- **Module:** `src/factory/think_filter.py`
- **Function:** `filter_think_content(content, min_chars)` — distills think block
- **Sacred constraint:** never modifies content after `</think>`


### 5.4 Legacy Detection
- **Module:** `src/factory/production_v11.py`
- **Function:** `detect_legacy_patterns(code, subtype)` → `List[str]`
- **Data:** `LEGACY_CODE_DETECTORS`, `JINJA_LEGACY_CODE_DETECTORS` (regex lists)

### 5.5 Common Schemas
- **Module:** `src/schemas/common.py`
- **Types:** `RawRecord`, `MetadataDict`, `ConversationMessage`, `InferencePayload`

---

## 6. Output Specification

### 6.1 Output File
`data/synthetic/v11_backtracking_aligned_YYYYMMDD_HHMMSS.jsonl`

### 6.2 Record Format
Same schema as input with additions to metadata:

```python
metadata = {
    ...original_metadata,
    "backtracking_applied": True,
    "backtracking_strategy": "full_backtracking|trace_reconstruction|error_first|contrast|pass_through",
    "original_think_chars": int,
    "rewritten_think_chars": int,
}
```

### 6.3 Quality Invariants
1. Code after `</think>` is byte-identical to source
2. Every rewritten think contains at least ONE backtracking pattern:
   - "Wait" / "Espera" (self-correction signal)
   - Explicit mention of a deprecated API being rejected
   - Transition from wrong → right approach
3. Total conversation length stays under 4,000 estimated tokens

---

## 7. Module Architecture

```
configs/stage_3_curation/
  backtracking_alignment.yaml    ← thresholds, prompts, model params

src/curation/
  backtracking_rewriter.py       ← core pipeline (SRP, <400 LOC)

tests/
  test_backtracking_rewriter.py  ← TDD tests
```

### 7.1 Public API

```python
@dataclass(slots=True, frozen=True)
class BacktrackingConfig:
    max_tokens: int = 4000
    excluded_types: tuple[str, ...] = ("theory",)
    vllm_api_url: str = "http://localhost:8000/v1"
    vllm_model: str = "qwen3-30b-a3b-thinking-fp8"
    temperature: float = 0.6
    max_generation_tokens: int = 3000
    batch_size: int = 10

def classify_rewrite_strategy(record: RawRecord) -> str: ...
def build_rewrite_prompt(record: RawRecord, strategy: str) -> tuple[str, str]: ...
def extract_think_block(content: str) -> tuple[str, str]: ...
def replace_think_block(content: str, new_think: str) -> str: ...
def passes_token_filter(record: RawRecord, max_tokens: int) -> bool: ...
def rewrite_pipeline(input_path: Path, output_path: Path, config: BacktrackingConfig) -> dict: ...
```
