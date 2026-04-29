# Epic 0: Infrastructure Setup -- Research Findings

## BMAD Source Documents

This research was guided by the following BMAD documentation:

| Source | Role |
|--------|------|
| [epics.md v4.0](../../../_bmad-output/planning-artifacts/epics.md) | Story definitions (0.1-0.4), acceptance criteria, dependencies |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | Architecture, FR/NFR definitions, DSPy integration context |
| [aegf-autonomous-forge-product-brief.md](../../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) | Hard-coding evidence, problem statement |
| [architecture.md](../../../_bmad-output/planning-artifacts/architecture.md) | 2-layer architecture decisions |
| [sprint-status.yaml](../../../_bmad-output/implementation-artifacts/sprint-status.yaml) | Dependency map, NFR tracking, story status |
| [technical-research-ralph-dspy-compatibility.md](../../../_bmad-output/planning-artifacts/research/aegf-technology-validation-research-2026-04-22.md) | Tech stack validation |
| [brainstorming-deep-validation-2026-04-21.md](../../../_bmad-output/brainstorming/brainstorming-deep-validation-2026-04-21.md) | Validation findings |
| [research-dspy-langgraph-aegf-2026-04-21.md](../../../_bmad-output/brainstorming/research-dspy-langgraph-aegf-2026-04-21.md) | Technical research findings |

## 1. Codebase Analysis

### 1.1 infrastructure/ Directory
- **No top-level `infrastructure/` directory exists.** It would need to be created.
- `specs/aegf-infrastructure/` exists but is nearly empty (only `.progress.md` and `.ralph-state.json`).
- `tests/infrastructure/` exists but is empty (only `__pycache__/`).
- **Conclusion**: The infrastructure module is a greenfield create, not a refactor.

### 1.2 Existing Baseline-Related Code

**`scripts/benchmark/`** (fully implemented, ~570 lines total):
- `measure_performance.py` (347 lines): Measures throughput (files/hour/worker), latency (mean, p95, p99), and error rates for Stage 1 Discovery processor. Targets: throughput >= 1000 files/hour/worker, mean < 200ms, P95 < 1s.
- `compare_baseline.py` (224 lines): Compares current results against stored baselines with configurable threshold (default 10%).
- `baselines/` subdirectory: **Empty** -- no baseline JSONs have been saved yet.
- Uses `numpy` (not currently in requirements.txt -- needs to be added).
- References `src.utils.extractors.factory.get_adapter()` and `src.utils.extractors.base.ParseError`.

**Existing calibration fixtures** (`tests/fixtures/`):
- `calibration_results.json` (full calibration result structure with scores, profiles, statistics)
- `calibration_checkpoint.json` (mid-run checkpoint for resume capability)
- `calibration_prompts.json` (5 example calibration prompts)
- `judge_scoring_response.json` (judge evaluation output with 5 dimensions)

### 1.3 Prompt Externalization Status

**Existing pattern**: Taxonomy-based YAML externalization.
- Prompts are loaded from YAML taxonomy files via `_prompt(key)` in `prompt_builder.py`.
- Two active taxonomy locations:
  - `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml` (active)
  - `configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml`
- Prompt categories under `prompts.system` and `prompts.user`:
  - `system.python.base`, `system.python.nominal_suffix`, `system.python.contrast_suffix`, `system.python.error_recovery_suffix`, `system.python.blueprint_context`, `system.python.governance_context`
  - `system.jinja.base`, `system.jinja.nominal_suffix`, `system.jinja.contrast_suffix`, `system.jinja.error_recovery_suffix`
  - `system.theory`
  - `system.php_legacy.context`
  - `user.python.nominal_easy`, `user.python.nominal_medium`, `user.python.nominal_hard_*`, `user.python.contrast`, `user.python.error_recovery`, `user.python.functional_unit`
  - `user.jinja.*` (parallel to user.python)
  - `user.theory` (template pool from taxonomy)

**What's NOT externalized**:
- No `.example.yaml` files exist for trajectory, hard_query, judge, or calibration prompts.
- Only one `.example.yaml` exists in the entire codebase: `data/raw/homeassistant/Odianosen25/Monitor-App/apps/home_presence_app/home_presence_app.example.yaml` (unrelated data file).
- Master documents (`HA_MASTER_GUIDE_2026.md`, `technical_changelog_2026.md`, `HA_JINJA_YAML_GUIDE_2026.md`) ARE external and loaded at runtime from `tests/fixtures/master_docs/`.

**Judge/Calibration prompts**:
- `src/audit/judge.py` (280 lines): Judge evaluation logic, but prompts themselves appear to be in taxonomy YAML, not hardcoded.
- `src/audit/calibration.py` (3,710 lines): Large calibration module. The judge scoring dimensions (ha_modernity, reasoning_depth, functionality, completeness, style) come from the calibration config, not hardcoded.
- `src/audit/prompt_manager.py` (90 lines): Minor, excluded from coverage.

### 1.4 Anchor Dataset Status

**Existing seed data**:
- `tests/fixtures/seed_examples.yaml`: 8 HA seed examples + 5 PHP legacy seeds (total 13 seeds). Already structured for externalization.
- `tests/fixtures/calibration_examples.json`: 5 calibration prompts with 4 sampling profiles and mock calibration results.
- `tests/fixtures/anchor_dataset_examples.json`: Fixture data for `AnchorDatasetDownloader` tests (not actual anchor data, but test fixtures with xlam, sharegpt, and openai_messages formats).
- `tests/fixtures/dedup_examples.json`: 237 lines of dedup test cases.
- `tests/fixtures/eval_bpb_examples.json`: 206 lines of eval test cases.
- `tests/fixtures/dataset_mixer_examples.json`: Dataset mixer configuration + specialized/anchor record examples.

**Reference corpus**: `tests/fixtures/reference_corpus/homeassistant/` contains 5 repos (repo1-repo5), each with minimal files (~3 files in repo1).

### 1.5 Dependencies (requirements.txt + pyproject.toml)

**Current runtime dependencies**:
```
PyYAML>=6.0, pydantic>=2.0, requests>=2.28, google-genai>=1.0,
python-dotenv>=1.0, tqdm>=4.64, httpx>=0.27, huggingface-hub>=0.22,
datasets>=2.19, tiktoken>=0.7, click>=8.1
```

**Current dev/test dependencies** (requirements-dev.txt / pyproject.toml):
```
openai>=1.0.0, pytest>=9.0, pytest-cov>=7.0, pytest-randomly>=3.0,
pytest-asyncio>=0.24, psutil>=5.9, ruff>=0.9
```

**Missing from requirements (but used in code)**:
- `numpy` -- used by `scripts/benchmark/measure_performance.py` but NOT in requirements.txt. Script imports it directly at line 34.

**Dependencies needed for Epic 0 stories**:
- Story 0.1 (baselines): `numpy` (already used, just needs adding), `scipy` (for Spearman correlation).
- Story 0.2 (prompts): No new deps (uses existing PyYAML).
- Story 0.3 (anchors): `datasets` already present (>=2.19), `tiktoken` already present (>=0.7), `huggingface-hub` already present. May need `pandas` for dataset manipulation.
- Story 0.4 (compatibility): `dspy>=2.5.x`, `langgraph>=0.2.x`, `torch`, `openai` (already in dev).

### 1.6 Test Structure and Coverage

- **49 test files**, 14,451 total lines across tests/.
- Coverage target: **85%** (tool.coverage.report.fail_under = 85).
- Covered modules: `src/audit`, `src/utils`, `src/factory`, `src/curation`, `src/discovery`.
- Existing test files relevant to Epic 0:
  - `test_model_evaluator.py`, `test_model_evaluator_*.py` (audit/calibration)
  - `test_prompt_manager.py`
  - `test_audit_calibration.py`
  - `test_audit_judge_submodule.py`
  - `test_production_v11*.py` (factory/prompt building)
  - `tests/unit/test_*` (discovery/extractor tests)
  - `tests/verification/test_module_blueprint_cross_language.py`

## 2. Seam Identification

### 2.1 Natural Module Boundaries

| Story | Target Module | Dependencies On | Depends On |
|-------|--------------|-----------------|------------|
| 0.1 | `scripts/benchmark/` + `tests/infrastructure/` | None (uses existing scripts) | None |
| 0.2 | `configs/stage_2_factory/taxonomy/*.yaml` + new `.example.yaml` files | Existing taxonomy loading in `prompt_builder.py` | None |
| 0.3 | `tests/fixtures/anchor_dataset_*.json` + `scripts/` | `datasets`, `tiktoken` (runtime deps) | None for creation, needs models for generation |
| 0.4 | `pyproject.toml` + `requirements.txt` | None | None |

### 2.2 Parallel Execution Analysis

**Stories 0.1, 0.2, and 0.4 can run in parallel**:
- 0.1 writes to `scripts/benchmark/` and `tests/infrastructure/` -- no overlap with other stories.
- 0.2 writes to `configs/` taxonomy YAMLs and creates `.example.yaml` files -- no overlap with other stories.
- 0.4 writes to `pyproject.toml` and `requirements.txt` -- only potential conflict is if 0.1 needs to add numpy (but numpy is already used, so 0.4 could just ensure it's present).
- No shared file modifications between 0.1, 0.2, and 0.4.

**Story 0.3 runs on the critical path**:
- It requires external model inference (for generating the 100-200 anchor samples).
- It needs the most time (generation + consensus review).
- Other stories (especially 0.1 for measuring baselines) depend on anchor data being available.
- The anchor dataset is the "data anchor" for DSPy MIPROv2 -- other optimization work builds on top of it.

### 2.3 File-Level Dependencies

```
Story 0.4 (deps)  --->  Story 0.1 (baselines, needs numpy/scipy)
Story 0.4 (deps)  --->  Story 0.3 (anchors, needs datasets/tiktoken)
Story 0.2 (prompts) -- No downstream deps; can be done anytime
Story 0.3 (anchors) --> Story 0.1 (baselines need anchor data to measure)
```

## 3. Constraint Discovery

### 3.1 Existing Patterns for Externalizing Prompts
**Pattern already exists and is well-established**:
- Taxonomy YAML files under `configs/stage_2_factory/taxonomy/{profile}/prompts_taxonomy.yaml`
- Template rendering via `string.Template` (safe_substitute with $ placeholders)
- Dot-separated key access: `_prompt("system.python.nominal_suffix")`
- Module-level state populated at import via `load_taxonomy(path)`
- Test state injection via `set_test_state(TaxonomyState)` in prompt_builder.py

**Gap**: No `.example.yaml` files exist for the four required prompt types (trajectory, hard_query, judge, calibration). This is a new pattern that would need to be added alongside the existing taxonomy pattern.

### 3.2 Test Infrastructure
- Strong test infrastructure already exists (49 files, 14k+ lines).
- `conftest.py` in tests/ provides shared fixtures.
- Pytest markers: `unit`, `integration`, `slow`.
- pytest-asyncio configured for async tests.
- Coverage excluded modules are well-defined in pyproject.toml.
- Test fixtures directory is well-organized with typed JSON fixtures.

### 3.3 requirements.txt / pyproject.toml State
- **Dual dependency management**: Both `requirements.txt` (runtime) and `pyproject.toml` (build + dev) exist. Epic 0.4 will need to reconcile these.
- `numpy` is already imported but not declared -- this is a bug that Epic 0.4 should fix.
- `datasets>=2.19` and `tiktoken>=0.7` already present (satisfies Story 0.3).
- `openai>=1.0.0` only in dev, not runtime (Story 0.4 may need to move it).
- Adding `dspy>=2.5.x`, `langgraph>=0.2.x`, `torch` would increase dependency surface significantly.

### 3.4 Existing Fixture Files That Could Feed Anchor Dataset
- `seed_examples.yaml`: 13 seeds with HA and PHP legacy contexts (already structured for externalization).
- `calibration_examples.json`: 5 prompts with structured scoring dimensions.
- `anchor_dataset_examples.json`: Test fixtures for xlam, sharegpt, openai_messages formats (useful as format templates).
- `dataset_mixer_examples.json`: Examples of anchor vs specialized record proportions.
- `dedup_examples.json` and `eval_bpb_examples.json`: Structured JSONL test data.
- `master_docs/`: 3 master documents already externalized (template for anchor data loading pattern).

### 3.5 Key Risks and Constraints

1. **numpy missing from requirements.txt**: Critical bug. `scripts/benchmark/measure_performance.py` imports numpy but it's not declared. This blocks Story 0.1 from working.
2. **No baseline JSONs exist**: `scripts/benchmark/baselines/` is empty. Story 0.1 must first RUN the benchmark to create initial baselines before it can compare.
3. **Anchor data generation is model-dependent**: Story 0.3 needs access to an LLM (OpenAI/Gemini/vLLM) and environment variables. This is an external dependency not captured in code.
4. **Dependency explosion risk**: Adding DSPy, LangGraph, and PyTorch adds significant footprint (~3GB with PyTorch). Needs careful version pinning.
5. **Spearman correlation not implemented anywhere**: `measure_recall.py` script exists but its content is not yet examined. If Spearman metrics are needed for Story 0.1, they must be implemented from scratch or use scipy.

## 4. Epic Decomposition Validation (2026-04-23)

### 4.1 Spec 1: baseline-measurement (S)

**INDEPENDENCE**: OK, but has implicit dependencies.

**Confirmed**:
- `infrastructure/` directory does NOT exist -- greenfield create. Confirmed.
- `scripts/benchmark/baselines/` is empty. Confirmed -- only `homeassistant.json` exists (performance data from Mar 11).
- `scripts/benchmark/compare_baseline.py` (224 lines) provides reusable pattern. Confirmed.
- `numpy` is used by `measure_performance.py:34` and `src/audit/eval_bpb.py:30` and `src/utils/extractors/python_ast_adapter.py:347` -- NOT in requirements.txt. Confirmed.
- `scipy` is NOT installed in the environment. Confirmed (`scipy NOT available`).

**Issues found**:
- **Schema mismatch**: `compare_baseline.py` handles performance metrics (latency_ms, throughput_files_per_hour, error_rate). The baseline JSONs for Spearman and calibration will have a completely different schema. Pattern reuse is superficial -- the JSON structure differs.
- **`baseline_results/` directory does NOT exist**: The spec writes runtime data there but doesn't note it needs creation. Same for `datasets/anchors/v1/` (Spec 3).
- **Rollback check is not Python infrastructure**: The rollback verification is a git operation, not a Python module. Including it in the same spec blurs scope.
- **Hidden dep on `tests/infrastructure/`**: The research notes this directory exists but is empty (`__pycache__/` only). If tests are expected, the empty directory is there.

**Verdict**: Can be built independently after Spec 4. The `scipy` dep is the only blocking one. Size estimate (S) is reasonable.

### 4.2 Spec 2: prompt-externalization (XS)

**INDEPENDENCE**: Technically independent, but significantly underestimated in complexity.

**Confirmed**:
- `prompt_builder.py` uses `_prompt()` which loads from `configs/stage_2_factory/taxonomy/*/prompts_taxonomy.yaml`. Confirmed via code review.
- `judge.py` uses `PromptManager` (from `src/audit/prompt_manager.py`) loading from `configs/stage_5_evaluation/eval_prompts.yaml`. Confirmed (lines 190-212).
- `trajectory_generator.py` loads from `configs/stage_2_factory/prompts/trajectory_templates.yaml` (NOT hardcoded strings). Confirmed.
- `hard_query_builder.py` loads from `configs/stage_2_factory/prompts/hard_query_templates.yaml` (NOT hardcoded strings). Confirmed.
- `calibration.py` uses `load_calibration_prompts_from_yaml()` from `configs/stage_5_evaluation/calibration_prompts.yaml`. Confirmed.

**Critical Issues**:
1. **Prompt sources are WRONG**: The spec says extract from `trajectory_generator.py`, `hard_query_builder.py`, `judge.py`, and `calibration.py`. But NEITHER of the first two files has hardcoded prompts -- they load from YAML. `judge.py` already uses PromptManager with YAML. The actual externalization target is the **taxonomy YAMLs**, not the Python files.
2. **Missing prompt keys** (FIXED): `_prompt("system.php_legacy.context")` is called in `prompt_builder.py:691` but `php_legacy/` has NO `prompts_taxonomy.yaml` file. The call IS caught by try/except at line 702 with a fallback return of doctrine + snippet inline. KeyError handled via existing exception handler.
3. **`user.theory` does not exist**: The spec mentions `system.theory` and `user.theory` but the taxonomy only has `system.theory` -- `user.theory` is not a key in the taxonomy. The codebase uses `THEORY_QUESTION_TEMPLATES` (loaded from `theory_question_templates` key in taxonomy) with `.format()`, not a `_prompt("user.theory")` call.
4. **`generic_domain/` has no prompts**: Only `agentic_taxonomy.yaml.example` and `plugin_architecture.yaml.example` exist in that directory. No prompts to extract.
5. **Naming mismatch**: The spec calls for `.example.yaml` suffixes but `PromptManager` in production uses `.yaml` (no `.example`). The naming convention creates confusion about whether files are templates or actual configs.
6. **Taxonomy files are in Spanish**: The taxonomy YAML contains Spanish content (the training target language). The spec says "English prompts" but the actual prompts are in Spanish. DSPy MIPROv2 would optimize based on Spanish prompts -- this needs to be addressed explicitly.

**Verdict**: Technically independent. Size (XS) is appropriate if scope is reduced to **documenting** existing YAML sources rather than "extracting from Python files." The spec should be renamed to "prompt-documentation" or the scope redefined to "catalog all existing prompt sources with their YAML paths."

### 4.3 Spec 3: anchor-dataset (L)

**INDEPENDENCE**: OK, but the domain distribution claim is unrealistic.

**Confirmed**:
- `infrastructure/` is greenfield. Same as Spec 1 -- both write to this directory.
- `tests/fixtures/seed_examples.yaml` exists (13 seeds). Confirmed.
- `tests/fixtures/calibration_examples.json` exists (5 examples). Confirmed.
- `tests/fixtures/anchor_dataset_examples.json` exists (format fixtures). Confirmed.
- `tests/fixtures/reference_corpus/homeassistant/` has 5 repos. Confirmed.

**Issues found**:
- **Domain distribution is wrong**: The spec says 40% HA, 30% PHP, 20% TypeScript, 10% Other. But the codebase taxonomy only has `home_assistant`, `php_legacy`, and `generic_domain`. There is NO TypeScript or JS taxonomy, no JS/TS reference corpus. The 20% TypeScript slice is impossible to fill from existing codebase data.
- **Shared directory conflict**: Both Spec 1 and Spec 3 write to `infrastructure/`. Spec 1 creates `infrastructure/baselines/` and `infrastructure/rollback_check.py`. Spec 3 creates `infrastructure/anchor_dataset_builder.py`. If parallel branches are used, the `infrastructure/` directory itself may not exist on the base branch. This is a known risk the spec acknowledges but doesn't provide a mitigation strategy for (e.g., "whichever spec runs first creates the dir").
- **`generic_domain` has no prompts**: As noted above, `generic_domain/` has `agentic_taxonomy.yaml.example` and `plugin_architecture.yaml.example` but no `prompts_taxonomy.yaml`. These could serve as "Other" category sources, but the spec should confirm what "Other" data looks like.
- **Manifest schema is inconsistent**: The spec shows `"total_samples": 150` and `"domain_distribution": {"home_assistant": 60, ...}` which sums to 150 -- but the distribution keys don't include TypeScript/JS which was specified as 20% (30 samples).
- **Manual verification is a bottleneck, not a feature**: 100-200 samples requiring manual verification is 100-200 human-hours minimum. The 5-10 day estimate is optimistic if one person is doing this. This should be explicitly called out as requiring dedicated human effort, not just "external dependency."

**Verdict**: Can be built independently after Spec 1 and 2 merge. The L size estimate is plausible but the domain distribution needs correction. The dependency on external LLM for sample generation is the real blocker, not the code.

### 4.4 Spec 4: dependency-compatibility (XS)

**INDEPENDENCE**: Fully independent.

**Confirmed**:
- `numpy` used in 3 files, not in requirements.txt. Confirmed.
- `scipy` not installed. Confirmed.
- Dual dependency management: `requirements.txt` (runtime) + `pyproject.toml` (build + dev). Confirmed.
- `openai>=1.0.0` only in dev. Confirmed.
- `datasets>=2.19` and `tiktoken>=0.7` in requirements.txt. Confirmed.
- `torch` is not explicitly listed -- comes via DSPy transitive dep.

**Issues found**:
- **`openai` should be in requirements.txt**: DSPy uses `openai` at runtime (not just dev). The spec notes this but the implementation notes should explicitly say "move openai from dev to runtime."
- **torch transitive dep**: The spec says `torch` as a new dep but it comes via DSPy. If version pinning is needed, the actual constraint is `dspy[...]` which pulls a specific torch version. This should be documented explicitly.
- **Weak dep on Spec 2**: The spec says "depends on Spec 2 (prompt-externalization)" but correctly notes it's weak. This dependency should be removed from the graph entirely -- dependency checking has nothing to do with prompt structure.

**Verdict**: Can be built independently. XS size is appropriate. Should be the FIRST spec to run (unblocks Spec 1).

### 4.5 Dependency Graph Validation

**Current graph**:
```
Spec 4 ──► Spec 1 ──► Spec 3
Spec 2 ──┘          ──►
```

**Corrected graph**:
```
Spec 4 ──► Spec 1 ──► Spec 3
Spec 2 ──┘          ──►
```

The dependency graph is CORRECT. Minor correction: Spec 2 should be listed as having NO dependency on Spec 4 (prompt externalization doesn't need scipy/numpy). The current diagram shows both parallel but it's worth being explicit.

**Missing edge**: None. The graph is correct.

### 4.6 Shared File Conflicts

| Files | Spec 1 | Spec 3 | Spec 4 | Resolution |
|-------|--------|--------|--------|------------|
| `infrastructure/` | Creates | Creates | Creates | Spec 1 or 3 creates first |
| `infrastructure/baselines/` | Creates | - | - | No conflict |
| `infrastructure/anchor_dataset_builder.py` | - | Creates | - | No conflict |
| `infrastructure/dependency_check.py` | - | - | Creates | No conflict |
| `infrastructure/rollback_check.py` | Creates | - | - | No conflict |
| `requirements.txt` | May update | - | Updates | Spec 4 must run first |
| `pyproject.toml` | May update | - | Updates | Spec 4 must run first |
| `baseline_results/` | Creates | - | - | No conflict |
| `datasets/anchors/v1/` | - | Creates | - | No conflict |

**Key finding**: Spec 4 should be executed first to avoid merge conflicts on `requirements.txt` and `pyproject.toml`. Spec 1 and 3 don't touch these files, so no conflict there. The `infrastructure/` directory is shared between Spec 1 and 3, but since both create files within it, whichever creates the directory first (via `mkdir -p`) will be the winner.

### 4.7 Missing Specs?

1. **Test infrastructure for new code**: The spec says "No test suite required (Epic 1 will add tests)" but the new infrastructure scripts (baselines, dependency_check, anchor_dataset_builder) are Python modules that should have at least import tests. This is a gap.
2. **Prompt source catalog**: Given the complexity of prompt sources (taxonomy YAMLs, eval_prompts.yaml, hard_query_templates.yaml, trajectory_templates.yaml, calibration_prompts.yaml), a separate spec for "cataloging all prompt sources with their YAML paths" would be more valuable than the vague "externalization" spec.

### 4.8 Unnecessary Specs?

None identified. All four specs serve distinct purposes. However, Spec 2's scope should be narrowed to documentation/cataloging rather than code changes.

### 4.9 Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Test | `make test` | Makefile |
| Coverage | `make coverage` | Makefile |
| CI lint | `python scripts/check_headers.py --check` | .github/workflows/header-check.yml |
| CI test | `python -m pytest tests/ --cov=src/` | Makefile + pyproject.toml |
| Lint | `ruff` | pyproject.toml [tool.ruff] |
| TypeCheck | Not found | pyproject.toml has no mypy/pyright |
| Build | Not found | No build step beyond setuptools |

**No package.json exists** -- this is a pure Python project.
**No E2E framework** -- only pytest (unit/integration/slow markers).
**CI** runs: headers check, pytest, and a discovery dry-run.

### 4.10 Recommendations

1. **Rerun Spec 4 first** -- it unblocks everything else and has no deps.
2. **Narrow Spec 2 to prompt source documentation** -- catalog existing YAML paths, don't try to "extract" from Python files that aren't hardcoded.
3. **Fix Spec 3 domain distribution** -- remove TypeScript/JS (20%) and replace with `generic_domain` or increase HA/PHP proportions.
4. **Fix Spec 1 scope** -- move rollback_check.py to a separate utility or into the existing `scripts/benchmark/` directory.
5. **Add test infrastructure spec** -- even minimal import tests for new Python modules prevent future breakage.
6. **Fix the `system.php_legacy.context` bug** -- this is a pre-existing bug that the spec should address before adding new infrastructure.
7. **Clarify `.example.yaml` vs `.yaml` naming** -- the distinction between template and config files is important for `PromptManager` consumers.
8. **Language clarification** -- taxonomy prompts are in Spanish; this affects MIPROv2 optimization. The spec should explicitly state whether prompts will be translated to English or kept in Spanish.

---

## 5. Qdrant Memory Insights (Knowledge Transfer from BMAD)

This section captures architectural decisions, Party Mode consensus, and critical findings from the BMAD brainstorming sessions that were stored in Qdrant but not yet referenced in this epic's documentation.

### 5.1 Critical Findings (CRITICAL — 9/10 severity)

**Finding 1: DSPy and LangGraph NEVER implemented** (Deep Validation, 2026-04-21)
- Triple verified: 0 results in .py files, 0 in pyproject.toml dependencies, 0 in entire repo
- Distillate document lists files that don't exist — this is PLANNED state, not implemented
- **Impact**: Epic 0 (this epic) is greenfield for DSPy/LangGraph integration

**Finding 2: ~220 tests exist but ALL are mock-based** (Murat Test Architect, 2026-04-22)
- MagicMock, AsyncMock, patch — no integration tests with real LLM model
- Structure is tested, quality is NOT validated
- **Impact**: Story 0.1 baseline measurements are the first real quality metrics

**Finding 3: Anchor Dataset is CRITICAL path item** (Party Mode, 2026-04-23)
- Without anchors, MIPROv2 compiles to vacuum (4/4 agents agree)
- Story 0.3 must complete before any Epic 1 DSPy Signature work
- **Impact**: Spec 3 (anchor-dataset) is on the critical path, not optional

### 5.2 Architecture Decisions (HIGH — 7/10 severity)

**Decision 1: DSPy Integration = Direct Refactor, NOT feature flag** (Architecture Decisions, 2026-04-22)
- DSPy Signatures replace hardcoded prompts IN-PLACE, original code REMOVED
- No `JUDGE_USE_DSPY=1` flag — this is a clean refactor, not a feature toggle
- **Interface**: DSPy wrapper classes expose same interface as original modules

**Decision 2: TrajectorySignature = Structured inputs** (Architecture Decisions, 2026-04-22)
- Fields: `domain_context` (str), `difficulty` (str), `turn_count` (int), `legacy_pattern` (str)
- Output: `trajectory` (str), `tool_usage_patterns` (list[str])
- NOT a flat text signature — structured with typed fields

**Decision 3: 4-turn trajectories (not 1-turn)** (Architecture Decisions, 2026-04-22)
- 1-turn causes tool-use forgetting in trained model
- 4-turn structure enables correct tool usage pattern learning
- Story 1.2a implements the 4-turn structure

**Decision 4: LangGraph NO for Capa 1, YES for Capa 3** (LangGraph Correction, 2026-04-22)
- Capa 1 (training pipeline): Ralph Loop sufficient, linear flow
- Capa 3 (inference/migration): LangGraph multi-agent debate (Architect→Coder→Auditor→Consenso)
- **Impact**: Epic 3 uses LangGraph, Epic 0 and Epic 1 do NOT

### 5.3 Testing Strategy (HIGH — 7/10 severity)

**Murat Test Architect Recommendations** (2026-04-22):
1. **No real LLM integration tests** for judge scoring — needs 3-tier testing (unit+mocks, integration+LLM on CI cache, e2e+frozen model)
2. **No regression baseline** for DSPy vs hardcoded judge — Story 0.1 provides this
3. **No feature flag rollback test** for `JUDGE_USE_DSPY` — not applicable (Direct Refactor pattern)
4. **Deterministic temperature=0.0** for judge — ensures reproducibility
5. **Spearman correlation** metric for DSPy validation (> 0.8 threshold)
6. **Anchor evaluations** (50 samples) as ground truth for correlation

### 5.4 Implementation Phases (HIGH — 7/10 severity)

**3-Phase Implementation with Decision Gate** (Deep Validation, 2026-04-21):
- **Phase 0**: 1-2 days validation (Spec 010 smoke test + DSPy Judge design)
- **Phase 1**: 5-7 days DSPy Judge (gate: Spearman correlation > 0.8 with judge.py)
- **Phase 2**: 7-10 days MIPROv2 optimization (if Phase 1 passed)
- **Phase 3**: 10-14 days DSPy Factory (if Phase 2 passed)
- **Total**: 23-33 days if everything works, 5 days if pivot after Phase 1

**Failure Metric**: Spearman correlation < 0.5 → pivot to BootstrapFewShot

### 5.5 Pre-existing Bugs (HIGH — 7/10 severity)

**Bug 1: `numpy` missing from requirements.txt** (Murat, 2026-04-22)
- Used by `scripts/benchmark/measure_performance.py:34` but NOT declared
- Must be fixed by Spec 4 (dependency-compatibility) before Spec 1 can run
- Pre-existing bug, not introduced by Epic 0

**Bug 2: `system.php_legacy.context` calls non-existent taxonomy** (Research, 2026-04-23)
- `prompt_builder.py:691` calls `_prompt("system.php_legacy.context")`
- `php_legacy/` has NO `prompts_taxonomy.yaml` file — only `master_symfony_hex.md` and `snippets/`
- This WILL fail at runtime — needs to be flagged as issue

**Bug 3: TypeScript/JS domain (20%) in anchor dataset is impossible** (Research, 2026-04-23)
- Spec 3 says 20% TypeScript/JS but codebase has NO TypeScript/JS taxonomy
- Must be replaced with `generic_domain` or increase HA/PHP proportions
- See Section 4.3 recommendation #3

### 5.6 Competitive Context (MEDIUM — 5/10 severity)

**AEGF + DSPy = domain-specific prompt optimization with feedback loops**
- No other project combines synthetic data generation with automatic prompt compilation
- Master Docs provide architectural context that generic DSPy projects lack
- Anchor dataset is competitive IP — manually verified, not auto-generated

**Fine-tuning complements DSPy (not competitive)**
- DSPy optimizes prompts, fine-tuning modifies model weights
- Both can be used together in Epic 2 pipeline

### 5.7 Party Mode v4.0 Changes Reference

| Change | Severity | Consensus | Status |
|--------|----------|-----------|--------|
| Story 0.3: Anchor Dataset Creation | CRITICAL (9/10) | 4/4 | In Spec 3 |
| Story 0.4: Dependency Compatibility | HIGH (7/10) | 3/4 | In Spec 4 |
| Story 1.2 split → 1.2a + 1.2b | HIGH (7/10) | Winston+Amelia | Epic 1 |
| Story 3.2 split → 3.2a + 3.2b + 3.2c | HIGH (7/10) | Winston+Amelia | Epic 3 |
| Epic 2.4 → Epic X (inter-epic gate) | MEDIUM (5/10) | Winston | Gate |
| NFR-007 redefined | MEDIUM (5/10) | Mary | In epic.md |

### 5.8 Qdrant Memory Sources

| Memory ID | Topic | Date |
|-----------|-------|------|
| deep-validation-dspy-langgraph | Critical findings | 2026-04-21 |
| murat-test-architect-dspy-aegf | Testing gaps | 2026-04-22 |
| architecture-decisions-2026-04-22 | DSPy decisions | 2026-04-22 |
| langgraph-correction-2026-04-22 | LangGraph layers | 2026-04-22 |
| aegf-architecture-v2 | 3-layer architecture | 2026-04-22 |
| aegf-architecture-v3 | 2-layer unified | 2026-04-22 |
| aegf-epics-v4-party-mode | Party Mode changes | 2026-04-23 |
| sprint-review-amelia | Development issues | 2026-04-22 |
| architectural-review-winston | Winston review | 2026-04-22 |
| technology-validation-2026-04-22 | Tech stack status | 2026-04-22 |
| repository-decision-2026-04-22 | Stay in current repo | 2026-04-22 |
