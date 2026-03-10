# Backtracking Alignment Pipeline — Execution Plan

**Objective:** Transform the V11 DISTILLED dataset into a new dataset that applies the "Self-Correction & Backtracking" technique from OpenCodeReasoning/AgentMath reports, forcing the model to simulate legacy errors in its `<think>` block and correct them before writing modern code.

**Source dataset:** `data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl`
- 19,732 total records
- Types: nominal (8,687), contrast (6,785), error_recovery (3,657), theory (603)
- Gold injected: True (13,782), False (5,347), None/theory (603)
- Legacy detected: True (2,635), False (16,494), None/theory (603)
- All 19,732 have `</think>` tag
- ~6,059 records approx >4,000 tokens

---

## Phase 1: Exploratory Analysis ✅ COMPLETED
- [x] Map dataset fields: `id`, `conversation`, `metadata`, `filter_text`
- [x] Map metadata fields: `curation`, `factory_version`, `example_type`, `evol_difficulty`, `ldi`, `fragment_name`, `source_file`, `gold_injected`, `legacy_detected`, `legacy_patterns`, `checkpoint_key`
- [x] Compute distributions: types, gold_injected, legacy_detected, LDI stats, token length
- [x] Identify existing tools: `VLLMClient`, `think_filter.py`, `detect_legacy_patterns()`, `InferenceRouter`

## Phase 2: Specification Document ✅ COMPLETED
- [x] Write `docs/specs/stage_1_5_backtracking_alignment.md`
- [x] Define filtering criteria based on discovered metadata
- [x] Define system prompt for think-block rewriting
- [x] Document reusable existing classes and how to use them

## Phase 3: Test-Driven Development — Unit Tests ✅ COMPLETED
- [x] Write `tests/test_backtracking_rewriter.py` covering:
  - [x] Record filtering logic (token limit, type exclusion, eligibility)
  - [x] Think-block extraction and replacement
  - [x] Backtracking prompt construction
  - [x] Dataset I/O (load, save with metadata update)
- [x] All 24 tests pass
- [x] Full suite regression: 411 tests pass

## Phase 4: Implementation ✅ COMPLETED
- [x] Create `configs/stage_3_curation/backtracking_alignment.yaml` — config
- [x] Create `src/curation/backtracking_rewriter.py` — core pipeline module
  - [x] Filtering logic (token limit, type selection)
  - [x] Think-block extraction/replacement utilities
  - [x] Backtracking prompt template construction
  - [x] Pipeline orchestrator: filter → rewrite → save
- [x] Wire up `VLLMClient` for think-block rewriting calls
- [x] Header check passes

## Phase 5: Smoke Test with Small Sample ✅ COMPLETED
- [x] Run pipeline on real records against live vLLM
- [x] `error_first` strategy: validated (1,476→2,916 chars, code preserved)
- [x] Sacred Constraint verified: code after `</think>` byte-identical
- [x] Dataset filter preview: 13,257 / 19,732 records pass filter
  - trace_reconstruction: 8,357 | full_backtracking: 2,483 | error_first: 2,417

## Phase 6: Full Pipeline Execution ✅ COMPLETED (with bug fix)
- [x] Deploy vLLM Docker container with Qwen2.5-1.5B-Instruct model
- [x] Run pipeline on full filtered dataset (~13k records)
- [x] Bug fix: Sacred constraint verification added to prevent whitespace stripping
- [x] Re-run pipeline with fix to generate clean output
- **Note:** After initial run revealed whitespace bug, fixed code now includes verification step

## Known Issues
- ~~**BUG FOUND:** Sacred constraint violation - whitespace is being stripped from code blocks (4-space indentation reduced to 1-space). This is a critical bug in the pipeline that needs to be fixed before the output can be used for training.~~ **FIXED** - Added sacred constraint verification in `apply_backtracking_rewrite()` that detects and restores original code if whitespace is modified.

---

## Key Decisions
1. **Token limit for filtering:** 4,000 tokens (~16,000 chars) — discard records exceeding this
2. **Theory type:** Excluded entirely (no code to align)
3. **Gold-injected records:** Rewrite think to match injected gold code (teacher-driven reasoning)
4. **Non-gold, clean records:** Rewrite think with backtracking pattern (self-correction)
5. **Legacy-detected records:** Prime candidates for backtracking (simulate the legacy impulse)
6. **Sacred constraint:** Code after `</think>` is NEVER modified
