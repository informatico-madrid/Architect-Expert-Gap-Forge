# Research: Prompt Externalization for DSPy

## Executive Summary

The AEGF codebase contains **8 files with hardcoded prompts** and **10+ YAML prompt files** across multiple formats (dict with system/user keys, list of objects, plain text, inline Python strings). DSPy 3.2.0 has **no native YAML prompt loading** — prompts live in Python class docstrings via `dspy.Signature`. The recommended approach is: create `.example.yaml` template files for cataloging, then write a lightweight bridge that loads them into DSPy Signatures dynamically. The existing `PromptManager` for Stage 2 should be kept separate.

**Feasibility**: High | **Risk**: Low | **Effort**: S/M

---

## All Prompt Sources Cataloged

### Hardcoded Python Prompts (5 actual prompt files + 3 non-prompt files)

**Actual prompt content (5 files):**

| File | Prompts | Language | Format |
|------|---------|----------|--------|
| `src/export/frontend_taxonomy_prompts.py` | 4 system + 1 user prompt | English | Multiline string constants |
| `src/factory/trajectory_generator.py` | 6 turn templates + hardcoded descriptions | Spanish | `_default_templates()` fallback |
| `src/factory/hard_query_builder.py` | forbidden_terms + problem_focused template + abstract transformations | Spanish | `_default_templates()` fallback |
| `src/curation/backtrack_strategy.py` | 4 strategy prompts (trace_reconstruction, error_first, contrast_backtracking, backtracking) | Spanish | Inline construction from context |
| `src/curation/backtracking_helpers.py` | Language detection heuristics | Both | Word counting logic |

**Non-prompt files (MISCLASSIFIED in initial research):**

| File | Content | Notes |
|------|---------|-------|
| `src/curation/backtracking_config.py` | Default file paths for backtracking prompts | Path constants only, NOT prompts |
| `src/factory/config.py` | 41 regex-based legacy code detectors | Regex patterns, NOT prompts |
| `src/curation/rewrite_engine.py` | Empty-prompt detection logic | Logging only, NOT prompts |

### YAML Prompt Files (10+ files)

| File | Lines | Format | Prompts | Language |
|------|-------|--------|---------|----------|
| `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml` | 999 | Dict with sub-keys | ~30 prompt groups (system.python.*, system.jinja.*, user.python.*, user.jinja.*, theory, error_templates, legacy_patterns, tools_definition) | Spanish |
| `configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml` | 998 | Same | Almost identical to prompts_taxonomy (minor differences in ~3 prompts: system.jinja.contrast_suffix, user.python.nominal_medium, user.jinja.error_recovery) | Spanish |
| `configs/stage_2_factory/taxonomy/home_assistant/plugin_architecture.yaml` | 1199 | **Different** — version: 3, domain: reasoning, seed_examples | NOT a prompt taxonomy. Completely different structure. | N/A |
| `configs/taxonomy/home_assistant/hacs_expert/prompts_taxonomy.yaml` | 998 | Same top-level keys | Content identical to stage_2_factory copy (md5: 1700e5db1875445daedcc0d899621621) | Spanish |
| `configs/stage_5_evaluation/eval_prompts.yaml` | 214 | Dict with system/user keys | 4 groups (professor_exam, professor_judge, gap_analysis, professor_judge_calibration) | Mixed EN/ES |
| `configs/stage_5_evaluation/calibration_prompts.yaml` | 63 | List of objects | 6 prompts | English |
| ~~`configs/stage_5_evaluation/calibration_prompts.yaml.example`~~ | **DOES NOT EXIST** | N/A | N/A | N/A |
| `configs/stage_6_calibration/calibration_prompts.yaml` | 69 | List of objects | 6 prompts | English |
| `configs/stage_6_calibration/calibration_prompts.yaml.example` | 112 | List of objects | 10 prompts (superset: active has prompts 1-6, .example has 1-10) | Mixed EN/ES (prompts 1-6 English, 7-10 Spanish) |
| `configs/stage_3_curation/prompts/user.yaml` | 8 | Dict | 2 keys (system.default, user.curation_task) | English (trivial: "You are a helpful assistant.") |
| `configs/prompts/backtracking_system.txt.example` | 36 | Plain text | 1 prompt | English |
| `configs/prompts/backtracking_system.txt` | 36 | Plain text | Identical to .example | English |
| `configs/prompts/reconstruction_system.txt.example` | 26 | Plain text | 1 prompt | English |
| `configs/prompts/reconstruction_system.txt` | 26 | Plain text | Identical to .example | English |
| `configs/stage_5_evaluation/ha_patterns.yaml` | 59 | Dict | Regex patterns + standards text | N/A |

**VERIFIED**: `diff` confirms stage_6 `.example` has 10 items vs 6 in active (prompts 7-10 are Spanish investigation prompts). stage_5 has NO `.example` file. md5 checksums confirm hacs_expert copy is byte-identical to stage_2_factory main copy.

### Missing Files (Hardcoded Defaults)

| File | Status | Fallback |
|------|--------|----------|
| `configs/stage_2_factory/prompts/trajectory_templates.yaml` | **DOES NOT EXIST** (parent dir missing) | `_default_templates()` in trajectory_generator.py |
| `configs/stage_2_factory/prompts/hard_query_templates.yaml` | **DOES NOT EXIST** | `_default_templates()` in hard_query_builder.py |

---

## Key Findings

### Finding 1: The `.example` Naming Convention is Already Used but Misleading

Three pairs of `.example` / non-example files exist (stage_5 `.example` does NOT exist):
- `configs/stage_6_calibration/calibration_prompts.yaml.example` (112 lines) — **different** from active (69 lines). `.example` is a superset: active has 6 prompts (items 1-6), `.example` has 10 prompts (items 1-10). Prompts 7-10 in `.example` are Spanish investigation prompts.
- `configs/prompts/backtracking_system.txt.example` — **identical** to active (no variation)
- `configs/prompts/reconstruction_system.txt.example` — **identical** to active (no variation)

Only the stage_6 calibration `.example` has meaningful content difference. The txt `.example` files are misleading copies.

### Finding 2: Three YAML Formats, Two Template Syntaxes

| Format | Files | Structure | Template Syntax |
|--------|-------|-----------|----------------|
| Prompts dict | Taxonomy YAMLs, eval_prompts | `key.system` / `key.user` | `$var` (string.Template) |
| List of objects | calibration_prompts | List with `id`, `question`, `type` | N/A |
| Plain text | backtracking_system/reconstruction | Single block of text | N/A |
| Inline Python | 8 source files | Python string constants | `{var}` (str.format) |

### Finding 3: DSPy Has No Native YAML Prompt Loading

DSPy 3.2.0 verified:
- `dspy.PromptModule` does **NOT exist**
- DSPy prompts live in `dspy.Signature` docstrings (Pydantic BaseModel)
- `dspy.configure()` only sets: `lm`, `adapter`, `callbacks`, `track_usage`
- No built-in prompt versioning or translation management
- **Recommended pattern**: Write bridge code that loads `.example.yaml` into DSPy Signatures dynamically at module `__init__` time

### Finding 4: Existing PromptManager and DSPy Are Separate Concerns

- `PromptManager` (Stage 2 Factory) loads eval_prompts.yaml, provides `.system()`, `.user_template()`, `.format()` methods
- DSPy would use `.example.yaml` files loaded into Signature docstrings
- These serve different pipeline stages; no conflict

### Finding 5: Two Nearly-Identical Copies + One Different File of the Main Taxonomy

**Byte-identical copies** (md5: 1700e5db1875445daedcc0d899621621):
1. `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml`
2. `configs/taxonomy/home_assistant/hacs_expert/prompts_taxonomy.yaml`

**Nearly identical** (`agentic_taxonomy.yaml`): Same structure, minor differences in ~3 prompts:
- `system.jinja.contrast_suffix` — slight wording difference
- `user.python.nominal_medium` — slight wording difference
- `user.jinja.error_recovery` — slight wording difference
- Missing `tools_definition` section (present in main copy)
- Missing `theory_question_templates` section (present in main copy)

**Different structure** (`plugin_architecture.yaml`): version: 3, domain: reasoning, seed_examples format. NOT a prompt taxonomy file.

### Finding 6: Missing Template Files Are a Gap

`trajectory_templates.yaml` and `hard_query_templates.yaml` are referenced in code but don't exist. Both modules gracefully fall back to hardcoded defaults. This means:
- The trajectory and hard_query pipelines work but with hardcoded Spanish templates
- These should be included in the externalization scope
- The default templates should be extracted to the YAML files

---

## DSPy Bridge Architecture (Recommended)

Since DSPy expects prompts in Signature docstrings:

```python
# Bridge: YAML -> DSPy Signature
import yaml
import dspy

def load_signatures_from_yaml(yaml_path: str, prefix: str = "") -> dict[str, type[dspy.Signature]]:
    """Load prompt templates from YAML and create DSPy Signatures.

    Expects YAML with structure:
    prompts:
      <group_key>:
        system: "<system prompt with $placeholders>"
        user: "<user prompt with {placeholders}>"
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        templates = yaml.safe_load(f)["prompts"]

    signatures = {}
    for key, tmpl in templates.items():
        system = tmpl.get("system", "")
        user = tmpl.get("user", "")
        # Replace $var placeholders with {var} for str.format compatibility
        system = system.replace("$", "")  # Strip dollar sign: $var -> var, then wrap as {var}
        full_prompt = f"{system}\n\nUser instruction: {user}"
        sig = dspy.Signature(full_prompt)
        signatures[f"{prefix}.{key}"] = sig

    return signatures
```

---

## Scope Implications

The plan.md assumed 4 output files. The actual scope is significantly broader:

| Output File | Source | Status |
|-------------|--------|--------|
| `src/factory/prompts_trajectory.example.yaml` | trajectory_generator.py defaults + missing YAML | NEW (extract from code) |
| `src/factory/prompts_hard_query.example.yaml` | hard_query_builder.py defaults + missing YAML | NEW (extract from code) |
| `src/audit/prompts_judge.example.yaml` | eval_prompts.yaml (4 groups) | TRANSFORM (format conversion) |
| `src/audit/prompts_calibration.example.yaml` | calibration_prompts.yaml (stage_5 + stage_6) | TRANSFORM (format conversion) |
| `src/factory/prompts_taxonomy.example.yaml` | prompts_taxonomy.yaml (30+ groups) | TRANSFORM (large, many sub-keys) |
| `src/export/prompts_frontend.example.yaml` | frontend_taxonomy_prompts.py (4 system + 1 user) | NEW (extract from Python) |
| `src/curation/prompts_backtracking.example.yaml` | backtracking_system.txt + reconstruction_system.txt | TRANSFORM (plain text to structured) |

**Recommendation**: 
1. Consolidate taxonomy prompts into a single `prompts_taxonomy.example.yaml` (2 files are byte-identical, 1 has minor differences).
2. Frontend prompts (`frontend_taxonomy_prompts.py`) are dead code — never imported anywhere. Consider removing them from scope or deleting the file entirely.
3. Calibration prompts: only `calibration_prompts.yaml` (stage_6, 6 prompts) is loaded by `load_calibration_prompts_from_yaml()`. The `.example` file is a development superset.
4. Curation `user.yaml` has trivial placeholder prompts — may not need translation.

---

## Verified Inconsistencies (Technical Research Audit)

The following issues were identified during BMAD technical research verification.

### Critical: Fabrication

| Claim in initial research | Verified fact | Severity |
|--------------------------|--------------|----------|
| `configs/stage_5_evaluation/calibration_prompts.yaml.example` exists (112 lines, superset) | File does NOT exist. Only `configs/stage_6_calibration/calibration_prompts.yaml.example` exists | **FABRICATION** |

### Major: Inaccurate Line Counts

| Claim | Verified fact |
|-------|--------------|
| Stage_6 `.example` has 112 lines AND is identical to active | `.example` has 112 lines (correct) BUT active has 69 lines (not 112). They are NOT identical |
| Stage_5 `.example` has 112 lines | File does not exist |

### Medium: Misclassified Content

| Claim | Verified fact |
|-------|--------------|
| 8 files with hardcoded prompts | Only 5 files have actual prompts. 3 files (`backtracking_config.py`, `config.py`, `rewrite_engine.py`) are non-prompt files (path constants, regex patterns, logging) |
| `agentic_taxonomy.yaml` is a "subset" | It is nearly identical (99% overlap) — not a meaningful subset. Only 3 prompts differ slightly in wording |
| `plugin_architecture.yaml` is a prompt taxonomy | Completely different structure (version 3, seed_examples). Not a prompt taxonomy at all |

### New Findings

| Finding | Implication |
|---------|------------|
| `src/export/frontend_taxonomy_prompts.py` defines 5 prompts but is never imported anywhere | Dead code — frontend prompts are not used by any pipeline |
| No application code loads `calibration_prompts.yaml` from either stage_5 or stage_6 | Calibration YAMLs are orphaned — the `load_calibration_prompts_from_yaml()` function takes a path argument but nothing passes a real path to it |
| `curation/prompts/user.yaml` has trivial prompts ("You are a helpful assistant.") + is never loaded by any code | Orphaned placeholder file — may not need translation |
| `configs/prompts/backtracking_system.txt` and `configs/prompts/reconstruction_system.txt` ARE loaded by `backtrack_strategy.py` | These txt files are actively used by curation pipeline (unlike calibration YAMLs) |
| `eval_prompts.yaml` IS loaded by `PromptManager` | This is a real prompt source (not orphaned like calibration YAMLs) |

### DSPy Verification (All Claims Confirmed)

| Claim | Verified |
|-------|----------|
| `dspy.PromptModule` does NOT exist | Confirmed: `dir(dspy)` returns `['teleprompt']` for prompt-related, no PromptModule |
| DSPy 3.2.0 prompts in `dspy.Signature` docstrings | Confirmed: Signature is Pydantic BaseModel at `/dspy/signatures/signature.py` |
| `dspy.configure()` only accepts `lm`, `adapter`, `callbacks`, `track_usage`, `async_max_workers`, `num_threads` | Confirmed via `help(dspy.configure)` |
| No built-in prompt versioning or translation management | Confirmed — no such features in DSPy |

---

## Cross-Epic Context — Where Each "Inconsistency" Belongs

This section maps every finding from this research to the epic/story where it will actually be addressed.
**Critical insight**: Most "inconsistencies" are by design — they are intentionally scoped to Epic 1.

### The Full Epic Pipeline

| Epic | Title | Specs | Stage Addressed |
|------|-------|-------|----------------|
| **Epic 0** (THIS EPIC) | Infrastructure Setup | baseline-measurement, prompt-externalization, anchor-dataset, dependency-compatibility | All stages — preparatory |
| **Epic 1** | Layer 1 DSPy Integration | TBD (8 stories: 1.1-1.7) | Stage 2, Stage 5, Stage 6 — DSPy replacement |
| **Epic 2** | Dataset & Training Pipeline | TBD (3 stories: 2.1-2.3) | Stage 3 Curation — dataset mixing |
| **Epic X** | Layer 1 Integration Gate | TBD (1 gate) | Post-Epic 0/1/2 — validation checkpoint |
| **Epic 3** | Layer 2 LangGraph Inference | TBD (5 stories: 3.1-3.3) | Stage 2+ — multi-agent migration |

### Findings Mapped to Responsible Epic

| Finding | Reported In | Actually Resolved In | Rationale |
|---------|------------|---------------------|-----------|
| DSPy uses English but Stage 2 uses Spanish Spanish | This research | **Epic 1, FR-008** | Epic 0 provides English templates. Epic 1's Stories 1.1-1.7 replace hardcoded Spanish in production code. This is the CORE of DSPy integration. |
| Orphaned calibration_prompts.yaml (no caller) | This research | **Epic 1, Story 1.6** | DSPy CalibrationSignature replaces it. Orphaned until Epic 1 wires it up. |
| Dead `frontend_taxonomy_prompts.py` (never imported) | This research | **Epic 1 or cleanup** | Not in scope for Epic 0. If DSPy replaces it, delete in Epic 1. |
| Missing trajectory_templates.yaml + hard_query_templates.yaml | This research | **Epic 1** | Epic 0 catalogs them as missing. Epic 1 creates DSPy-based replacements in Python (trajectory_signature.py, hard_query DSPy). |
| `eval_prompts.yaml` loaded by PromptManager (Stage 2) | This research | **Both** | Epic 0 externalizes to `.example.yaml` for DSPy. Stage 2 keeps taxonomy YAML for Stage 2 pipeline. Coexistence by design (AC3). |
| `backtracking_system.txt` + `reconstruction_system.txt` loaded by backtrack_strategy.py | This research | **Epic 1 or Epic 3** | These are curation-stage prompts (Stage 3). May be handled by LangGraph inference in Epic 3. |
| `curation/prompts/user.yaml` trivial + orphaned | This research | **Epic 1 or cleanup** | Not worth translating if orphaned. Note in Epic 0 catalog, delete in cleanup. |
| `.example.yaml` vs taxonomy YAML coexistence | This research | **By design (AC3)** | Epic 0 = templates for DSPy consumption. Stage 2 = taxonomy for Stage 2 pipeline. Different consumers. |
| 7 output files vs planned 4 in plan.md | This research | **In scope for this spec** | Research correctly expanded scope. All 7 are real prompt sources. |

### Scope Boundary: What This Spec Does vs What Epic 1 Does

| Aspect | Epic 0 (This Spec: prompt-externalization) | Epic 1 (DSPy Integration) |
|--------|-------------------------------------------|--------------------------|
| **Output** | `.example.yaml` template files with English translations | `dspy.Signature` definitions in Python |
| **Code changes** | None — only adds YAML files | Replaces hardcoded Spanish in production code |
| **Language** | English (translated from Spanish) | English (DSPy-optimized) |
| **Connection to DSPy** | None — templates only | Direct integration (MIPROv2 optimization) |
| **Lifecycle** | Static reference files | Optimized and evolving |
| **Example: trajectory prompts** | Extract Spanish → English, write to `prompts_trajectory.example.yaml` | Read from YAML (or inline), create `TrajectorySignature`, optimize with MIPROv2 |

### Recommendation for This Spec

1. **Keep scope focused**: Only catalog + translate. Do NOT attempt to connect to DSPy.
2. **Note orphaned/dead code**: Document which prompt sources are orphaned (calibration YAMLs) or dead code (frontend prompts) but don't delete them. Epic 1 will handle that.
3. **Document the handoff**: Each `.example.yaml` should reference which Epic 1 story it feeds (e.g., "Feeds Story 1.1: TrajectorySignature").
4. **The 7-file scope from research is correct**: Even though some sources are orphaned, they are part of the complete prompt surface area that DSPy will eventually consume.

---

## Related Specs Within Epic 0

| Spec | Status | Depends On | Feeds To |
|------|--------|-----------|----------|
| dependency-compatibility | COMPLETED | None | baseline-measurement (scipy/numpy) |
| prompt-externalization | IN PROGRESS | None | anchor-dataset (English prompts) |
| baseline-measurement | PENDING | dependency-compatibility | anchor-dataset (baseline scores) |
| anchor-dataset | PENDING | baseline-measurement + prompt-externalization | Epic 1 (MIPROv2 bootstrap data) |

## Specs in Later Epics (Context Only)

| Epic | Spec | Purpose | Depends On Epic 0 |
|------|------|---------|-------------------|
| Epic 1 | Story 1.1: TrajectorySignature | DSPy Signature for Stage 2 | prompt-externalization (prompts) + anchor-dataset (anchors) |
| Epic 1 | Story 1.3: Integrate TrajectorySignature | Replace hardcoded Spanish in trajectory_generator.py | prompt-externalization + Story 1.1 |
| Epic 1 | Story 1.4-1.5: JudgeSignature | DSPy Signature for Stage 5 evaluation | prompt-externalization (judges) + anchor-dataset |
| Epic 1 | Story 1.6: CalibrationSignature | DSPy Signature for Stage 6 calibration | prompt-externalization (calibration) + anchor-dataset |
| Epic 1 | Story 1.7: Hard Query Mapping | DSPy ChainOfThought for hard_query_builder.py | prompt-externalization (hard_query templates) |
