---
name: aegf-infrastructure
goal: ML Engineer puede validar todo objectivamente con metrics y baselines antes de implementar features. Tiene datos ancla para DSPy MIPROv2 y dependencias compatibles.
version: 5.0
date: 2026-04-24
status: draft
storyCount: 4
specs:
  - baseline-measurement
  - prompt-externalization
  - anchor-dataset
  - dependency-compatibility
---

# Epic: aegf-infrastructure

## Epic Goal

ML Engineer gets objective baselines, externalized prompts, anchor datasets, and dependency validation -- all prerequisites for DSPy MIPROv2 optimization in Epic 1.

## BMAD Sources

This epic is decomposed from **BMAD Epic 0: Infrastructure Setup** (`_bmad-output/planning-artifacts/epics.md` v4.0).
All 4 stories, acceptance criteria, and user outcomes are sourced directly from the BMAD epics document.

| BMAD Document | Role in This Epic |
|---------------|-------------------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | **Primary** — story definitions, AC, dependencies, NFR mapping |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | PRD requirements (FR-008, FR-009, FR-010, NFR-001, NFR-002, NFR-007, NFR-009) |
| [aegf-autonomous-forge-product-brief.md](../../../_bmad-output/planning-artifacts/aegf-autonomous-forge-product-brief.md) | Problem statement, hard-coding evidence, product vision |
| [architecture.md](../../../_bmad-output/planning-artifacts/architecture.md) | Architecture decisions, 2-layer structure context |
| [sprint-status.yaml](../../../_bmad-output/implementation-artifacts/sprint-status.yaml) | Story tracking, dependency map, NFR tracking (v2.0) |
| [technical-research-ralph-dspy-compatibility.md](../../../_bmad-output/planning-artifacts/research/aegf-technology-validation-research-2026-04-22.md) | DSPy compatibility research validating Epic 0 approach |
| [PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md](../../../_bmad-output/planning-artifacts/PRD-EXPLICADO-PARA-HUMANOS-TONTOS.md) | Reference: plain-language explanation of pipeline stages |
| [implementation-readiness-report.md](../../../_bmad-output/planning-artifacts/implementation-readiness-report.md) | Reference: readiness assessment |
| [project-context.md](../../../_bmad-output/project-context.md) | Reference: AI agent project context |
| [innovation-strategy-2026-04-22.md](../../../_bmad-output/innovation/innovation-strategy-2026-04-22.md) | Reference: strategic context |

### Story References (epics.md line numbers)

| Story | epics.md Reference |
|-------|-------------------|
| 0.1 Baseline Measurement | `epics.md:206` |
| 0.2 Prompt Externalization | `epics.md:230` |
| 0.3 Anchor Dataset | `epics.md:255` |
| 0.4 Dependency Compatibility | `epics.md:280` |

## Smart Ralph Sync (2026-04-24)

Corrections applied after the `dependency-compatibility` spec completed verification (19/19 tasks, all QGs APPROVED).
Changes align BMAD artifacts with verified findings from Smart Ralph deep research.

| Correction | BMAD Claim | Verified Fact | Action |
|------------|-----------|---------------|--------|
| dspy-ai deprecated | "dspy-ai package is deprecated" (epics.md v4.0 line 817) | Both `dspy` and `dspy-ai` are active on PyPI (latest 3.2.0). Neither is deprecated. | Removed "deprecated" claim; kept recommendation to use `dspy` directly (avoids unnecessary indirection) |
| datasets version | `>=2.19,<3.0` (epics.md line 99, 814) | Spec uses exact pin `==2.21.0` per FR-1 version pinning rationale | Aligned both docs to `==2.21.0` |
| openai version | `openai>=1.0.0` only in dev (epics.md line 316, epic.md line 304/315) | Now pinned `==2.32.0` in requirements.txt. The `>=1.0.0` reference was the pre-existing bug | Updated references to reflect `==2.32.0` |
| torch statement | "torch via DSPy" in original BMAD Party Mode (corrupted) | Correct: torch is NOT from DSPy (dspy 3.x removed torch dependency) | Already correct in current epics.md — no fix needed |
| scipy missing | Mentioned in baseline-measurement spec but never in epics.md | scipy is NOT in requirements.txt, NOT in dependency-compatibility scope, NOT installed | Noted as cross-spec gap: baseline-measurement requires scipy but dependency-compatibility never added it. Baseline-measurement must add `scipy` to its own scope |
| dspy-ai risk | "dspy-ai resolves to dspy (wrapper, do not use)" (research.md) | dspy-ai depends on dspy as a runtime dep. Both packages are active. "Do not use" is advice, not fact | Removed from epic.md implementation notes |

### Sync Status

| Artifact | Status |
|----------|--------|
| `_bmad-output/planning-artifacts/epics.md` | Updated v5.0 (deprecated claim, datasets version, openai version) |
| `specs/_epics/aegf-infrastructure/epic.md` | Updated v5.0 (openai version, sync section added) |
| `specs/dependency-compatibility` | COMPLETE (19/19 tasks, QG-05 APPROVED) |
| `specs/baseline-measurement` | scipy gap identified — must add to its own requirements |

## Scope

### IN Scope

- Spearman correlation baseline measurement between judge.py scores and reference
- Calibration quality baseline capture
- Prompt externalization from taxonomy YAMLs + hardcoded strings to `.example.yaml` files
- Anchor dataset creation (100-200 samples, 4 domain categories)
- Dependency compatibility validation (dspy, langgraph, torch, openai)
- NFR-009 rollback verification

### OUT of Scope

- DSPy Signature definitions (Epic 1)
- LangGraph graph implementation (Epic 3)
- Actual MIPROv2 optimization runs (Epic 1)
- Training pipeline (Epic 2)
- Any code refactoring that changes production behavior

## Specs

### Spec 1: baseline-measurement

**Goal:** As an ML Engineer, I want baseline metrics captured before implementing DSPy features, so that I can objectively measure whether DSPy improves or degrades performance.

**Acceptance Criteria:**

1. **Given** the project needs a Spearman correlation baseline for DSPy validation
   **When** I run `infrastructure/baselines/measure_spearman_baseline.py` on a reference dataset
   **Then** a Spearman correlation score is produced and stored in `baseline_results/spearman_judge_baseline.json`
   **And** the script reuses `scripts/benchmark/compare_baseline.py` patterns for result storage

2. **Given** the project needs a calibration quality baseline
   **When** I run `infrastructure/baselines/run_calibration_baseline.py`
   **Then** current calibration quality scores (LDI, coherence) are recorded in `baseline_results/calibration_baseline.json`

3. **Given** NFR-009 requires rollback verification
   **When** I execute `git revert HEAD~1` on a test commit
   **Then** the codebase reverts in < 1 minute with no corruption
   **And** `git status` shows clean working tree after revert

4. **Given** the project needs an MIPROv2 compile time baseline
   **When** I run `infrastructure/baselines/measure_mipro_compile_baseline.py`
   **Then** current grid search duration is measured and stored (for NFR-007 redefinition: MIPROv2 compile <= 3x baseline)

**Implementation Notes:**
- `infrastructure/` directory does NOT exist -- must be created
- `scripts/benchmark/baselines/` subdirectory exists but is EMPTY (no baseline JSONs have been saved)
- `scripts/benchmark/compare_baseline.py` (224 lines) provides a reusable pattern for result storage
- Spearman correlation must be built from scratch or use `scipy.stats.spearmanr` -- neither exists in the codebase
- `numpy` is imported by `measure_performance.py` but NOT declared in requirements.txt -- this is a pre-existing bug

**MVP Scope:**
- 3 Python scripts in `infrastructure/baselines/`
- 1 Python script for rollback verification (can be a quick CLI test, not a full module)
- Minimal JSON output format matching existing benchmark patterns
- No test suite required (Epic 1 will add tests for baseline-dependent features)

**Dependencies:** Spec 4 (dependency-compatibility) must complete first -- scipy and numpy must be in requirements.txt before baseline scripts can run.

**Interface Contracts:**
- **Writes:** `infrastructure/baselines/measure_spearman_baseline.py`, `infrastructure/baselines/run_calibration_baseline.py`, `infrastructure/baselines/measure_mipro_compile_baseline.py`, `infrastructure/rollback_check.py`
- **Writes (runtime data):** `baseline_results/spearman_judge_baseline.json`, `baseline_results/calibration_baseline.json`
- **Reads:** `scripts/benchmark/compare_baseline.py` (pattern reuse), existing judge.py output, calibration results
- **Produces JSON schema:**
  ```json
  {
    "type": "spearman_baseline|calibration_baseline|mipro_compile",
    "timestamp": "ISO8601",
    "score": <float>,
    "details": {}
  }
  ```

**Estimated Size:** S (4 files, 200-400 LOC, 1-2 days)

---

### Spec 2: prompt-externalization

**Goal:** As an ML Engineer, I want existing taxonomy prompts cataloged and mirrored into `.example.yaml` template files with English translations, so that DSPy can manage them as language-agnostic external configuration.

**Acceptance Criteria:**

1. **Given** prompts already exist in YAML taxonomy files under `configs/stage_2_factory/taxonomy/*/prompts_taxonomy.yaml` (loaded by `prompt_builder.py`) and in `src/audit/judge.py` via `PromptManager` loading `eval_prompts.yaml`
   **When** I catalog all prompts and create `.example.yaml` template files
   **Then** 4 `.example.yaml` files are created with English prompt translations:
     - `src/factory/prompts_trajectory.example.yaml`
     - `src/factory/prompts_hard_query.example.yaml`
     - `src/audit/prompts_judge.example.yaml`
     - `src/audit/prompts_calibration.example.yaml`

2. **Given** prompts are cataloged and translated
   **When** code references the external config
   **Then** existing functionality is preserved
   **And** Spearman correlation > 0.8 with existing judge.py scores (no regression)

3. **Given** the existing taxonomy YAML pattern
   **When** `.example.yaml` files are created alongside the taxonomy files
   **Then** both patterns coexist without conflict (taxonomy is for Stage 2; `.example.yaml` is for DSPy)

**Implementation Notes:**
- Prompts are ALREADY externalized in YAML taxonomy files -- NOT hardcoded in Python
- The task is to: (1) catalog existing prompts from taxonomy YAMLs, (2) translate to English, (3) create `.example.yaml` template files for DSPy consumption
- No `.example.yaml` files exist anywhere in the codebase -- this is a new naming convention
- Current prompts are in Spanish; English translation is part of the scope
- Some taxonomy keys may be broken (e.g., `system.php_legacy.context` references a taxonomy that doesn't exist) -- note these as issues, not blockers
- Key prompt categories: system.python.*, system.jinja.*, system.theory, system.php_legacy.*, user.python.*, user.jinja.*, user.theory

**MVP Scope:**
- 4 `.example.yaml` template files with English prompt translations
- Catalog of all existing prompts with source taxonomy file references
- Reference code that shows how to load from `.example.yaml` (not full refactor -- Epic 1)
- Inventory of broken/missing taxonomy keys

**Dependencies:** None (can start immediately, parallel with Spec 4).

**Interface Contracts:**
- **Writes:** 4 `.example.yaml` files under `src/factory/` and `src/audit/`
- **Reads:** `src/factory/prompt_builder.py` (taxonomy keys), `src/audit/judge.py`, `src/audit/calibration.py`
- **YAML schema per file:**
  ```yaml
  prompts:
    <prompt_key>:
      system: "<english prompt text with $placeholders>"
      user: "<english user prompt with $placeholders>"
  ```
- **Naming convention:** `<module>.example.yaml` -- `.example` suffix signals "template, copy and customize"

**Estimated Size:** XS (4 files, < 300 LOC total, < 1 day)

---

### Spec 3: anchor-dataset

**Goal:** As an ML Engineer, I want a domain-specific anchor dataset of 100-200 samples with ground truth labels, so that DSPy MIPROv2 can compile and optimize signatures effectively.

**Acceptance Criteria:**

1. **Given** the need for MIPROv2 bootstrap data
   **When** I run `infrastructure/anchor_dataset_builder.py`
   **Then** it produces 100-200 samples with:
     - Input: `domain_context`, `difficulty`, `turn_count`, `legacy_pattern`
     - Expected output: `trajectory`, `tool_usage_patterns` (for TrajectorySignature)
     - Expected output: `coherence`, `overall` (for JudgeSignature)
     - Expected output: `optimized_parameters`, `quality_score` (for CalibrationSignature)

2. **Given** anchor dataset samples are generated
   **When** I inspect the distribution
   **Then** samples cover domains matching existing taxonomy structure:
     - Home Assistant (Python/HA-YAML/Jinja) -- 40%
     - PHP Legacy (oscommerce, wordpress, zencart, symfony) -- 30%
     - Generic domain (Python/PHP) -- 20%
     - Other (YAML configs, HA addons) -- 10%

3. **Given** anchor samples are created
   **When** I check the storage
   **Then** data is stored in `datasets/anchors/v1/anchor_dataset.jsonl`
   **And** metadata is stored in `datasets/anchors/v1/anchor_manifest.json`

4. **Given** each anchor sample
   **When** I verify it
   **Then** each sample includes ground truth labels marked as manually verified

**Implementation Notes:**
- `infrastructure/` directory must be created (Spec 1 also needs it)
- Seed data exists: `tests/fixtures/seed_examples.yaml` (13 seeds), `tests/fixtures/calibration_examples.json` (5 examples), `tests/fixtures/anchor_dataset_examples.json` (format fixtures)
- Reference corpus: `tests/fixtures/reference_corpus/homeassistant/` contains 5 repos
- **TAXONOMY CONSTRAINT:** Only `home_assistant`, `php_legacy`, and `generic_domain` taxonomies exist. No TypeScript taxonomy. Distribution must reflect existing taxonomy structure.
- Each anchor sample requires manual verification -- this is intellectual property, not auto-generated
- Party Mode consensus (4/4): This is the CRITICAL path item. Without anchors, MIPROv2 compiles to vacuum.
- Generation requires external model inference (OpenAI/Gemini/vLLM) -- external dependency
- **HUMAN BOTTLENECK:** 100-200 manually verified samples = ~100-200 human-hours. Consider starting with 50 samples (v0.1) and expanding iteratively.

**MVP Scope:**
- Builder script in `infrastructure/anchor_dataset_builder.py`
- Output directory: `datasets/anchors/v1/`
- JSONL format with manifest
- Manual verification workflow documented (checklist, not automated tests)
- **PHASED APPROACH:** v0.1 = 50 samples (minimum viable for MIPROv2 bootstrap), v0.2 = 100-200 samples
- Distribution percentages match existing taxonomy: HA 40%, PHP 30%, Generic 20%, Other 10%

**Dependencies:** Spec 1 (baseline-measurement) -- needs baseline scores to validate anchor quality; Spec 2 (prompt-externalization) -- needs English prompts for generating anchor trajectories.

**Interface Contracts:**
- **Writes:** `infrastructure/anchor_dataset_builder.py`, `datasets/anchors/v1/anchor_dataset.jsonl`, `datasets/anchors/v1/anchor_manifest.json`
- **Reads:** `tests/fixtures/seed_examples.yaml` (seed data), `tests/fixtures/anchor_dataset_examples.json` (format reference), baseline results from Spec 1
- **JSONL record schema:**
  ```json
  {
    "id": "anchor_001",
    "domain": "home_assistant|php_legacy|generic_domain|other",
    "difficulty": "easy|medium|hard",
    "turn_count": 4,
    "legacy_pattern": "string",
    "domain_context": "string",
    "expected_trajectory": "string",
    "expected_tool_usage_patterns": ["string"],
    "expected_coherence": 0.85,
    "expected_overall": 0.80,
    "expected_optimized_parameters": {},
    "expected_quality_score": 0.82,
    "verified": true,
    "verified_by": "string"
  }
  ```
- **Manifest schema:**
  ```json
  {
    "version": "v1",
    "created": "ISO8601",
    "total_samples": 50,
    "domain_distribution": {"home_assistant": 20, "php_legacy": 15, "generic_domain": 10, "other": 5},
    "difficulty_distribution": {"easy": 10, "medium": 25, "hard": 15}
  }
  ```
  (v0.1 targets 50 samples; v0.2 scales to 100-200)

**Estimated Size:** L (1 builder script + 2 data files + fixtures, 200-500 LOC + ~50-200 manually verified samples. Human verification is the bottleneck, not code: ~100-200 human-hours)

---

### Spec 4: dependency-compatibility

**Goal:** As a Platform Operator, I want to validate that new dependencies (dspy, langgraph, torch, openai) are compatible with existing ones, so that the project can install and run without version conflicts.

**Acceptance Criteria:**

1. **Given** new dependencies required by Epic 1 and Epic 3:
     - `dspy==3.2.0` (DSPy MIPROv2) — exact pin, rapid release cadence
     - `langgraph==0.2.76` (Layer 2 state machine) — exact pin, `<1.0` upper bound
     - `torch` (NOT from DSPy; must be added explicitly if ML workloads needed)
     - `openai==2.32.0` (moved from dev to runtime) — exact pin
   **When** I add them to `requirements.txt` and run `pip install -r requirements.txt`
   **Then** no version conflicts are reported and all deps install at pinned versions

2. **Given** new dependencies are installed
   **When** I run existing tests
   **Then** all existing tests pass with new dependencies installed

3. **Given** new dependencies are installed
   **When** I run `python -c "import dspy; import langgraph"`
   **Then** no import errors occur

4. **Given** dependency state is documented
   **When** I read `docs/dependency-compatibility.md`
   **Then** it contains: dependency tree, known CVEs (litellm 6 CVEs documented), Python 3.14 CI caveats, version matrix, strict pinning rationale

**Implementation Notes:**
- `numpy` is imported by `scripts/benchmark/measure_performance.py` but NOT in requirements.txt -- pre-existing bug that must be fixed
- Dual dependency management: `requirements.txt` (runtime) + `pyproject.toml` (build + dev) -- must reconcile both
- **Version pinning CRITICAL:** litellm releases every 2.4 days, openai every 5-7 days, dspy every 1-3 months. `>=` ranges are dangerous. Use exact pins (`==`) for all new deps.
- **litellm CVE risk:** litellm 1.82.6 (pinned by dspy 3.2.0 via `<=1.82.6`) has 6 CVEs. Must document this risk and decide on mitigation strategy.
- **datasets 4.x risk:** Latest datasets is 4.8.4 (from 2.21.0). Must pin `datasets==2.21.0` to prevent silent upgrade.
- **tokenizers/tiktoken Python 3.14:** No wheels available. Must pin `<0.13.0` and ensure CI has Rust toolchain.
- `datasets==2.21.0` and `tiktoken>=0.7,<0.13` already present (satisfies Spec 3 needs)
- `openai` was only in dev (was `>=1.0.0`, now pinned `==2.32.0`), moved to runtime for DSPy
- `google-genai>=1.0` already in requirements.txt as optional inference backend

**MVP Scope:**
- `infrastructure/dependency_check.py` -- validates install compatibility
- Updated `requirements.txt` with new deps, bugfix (numpy), AND strict version pins
- Updated `pyproject.toml` to match
- `docs/dependency-compatibility.md` -- documentation of dependency tree, known CVEs, CI caveats, version matrix

**Dependencies:** None. BMAD lists Spec 2 as a dependency but it's weak -- dependency checks don't depend on prompt structure. Spec 4 should run FIRST to fix the numpy bug early.

**Note:** `openai==2.32.0` was moved from `requirements-dev.txt` to `requirements.txt` (runtime dependency for DSPy).

**Interface Contracts:**
- **Writes:** `infrastructure/dependency_check.py`, `requirements.txt`, `pyproject.toml`, `docs/dependency-compatibility.md`
- **Reads:** Existing `requirements.txt`, `pyproject.toml`
- **dependency_check.py output:** Exit code 0 on success, non-zero on conflict. Prints dependency tree to stdout.

**Estimated Size:** XS (3-4 files, < 200 LOC, < 1 day)

---

## Dependencies (Spec-Level Graph)

```
Spec 4: dependency-compatibility    ──┐
Spec 2: prompt-externalization    ────┤ (parallel start, no deps)
                                       ▼
Spec 1: baseline-measurement   ───────► (needs scipy/numpy from Spec 4)
Spec 2: prompt-externalization ───────┘ (parallel, independent of 1 and 4)
                                       │
Spec 3: anchor-dataset            ─────┼──► (needs baselines + English prompts)
                                       │
Spec 4: dependency-compatibility    ───┘
```

| Spec | Depends On | Can Start When |
|------|-----------|----------------|
| Spec 4 (dependency-compatibility) | None | Immediately (RUN FIRST to fix numpy bug) |
| Spec 2 (prompt-externalization) | None | Immediately (parallel with Spec 4) |
| Spec 1 (baseline-measurement) | Spec 4 | Spec 4 PR merged |
| Spec 3 (anchor-dataset) | Spec 1, Spec 2 | Both PRs merged |

## Interface Contracts

### Shared Directory: `infrastructure/`

Created by Spec 1 and Spec 3. Must be created first (by whichever spec runs first).

```
infrastructure/
├── baselines/           # Spec 1: measurement scripts
│   ├── measure_spearman_baseline.py
│   ├── run_calibration_baseline.py
│   └── measure_mipro_compile_baseline.py
├── anchor_dataset_builder.py   # Spec 3: dataset generation
└── dependency_check.py         # Spec 4: validation
```

### Runtime Data Directories

```
baseline_results/          # Spec 1: baseline JSON outputs
├── spearman_judge_baseline.json
└── calibration_baseline.json

datasets/anchors/v1/       # Spec 3: anchor dataset
├── anchor_dataset.jsonl
└── anchor_manifest.json
```

### Prompt Template Schema

All `.example.yaml` files follow the same structure:

```yaml
# src/factory/prompts_trajectory.example.yaml
prompts:
  trajectory_system:
    system: "You are a migration expert..."
    user: "Analyze this legacy codebase..."
  trajectory_user_nominal:
    user: "Given this code..."
  # ... more prompts
```

### Baseline Result Schema

All baseline JSONs follow:

```json
{
  "type": "spearman_baseline",
  "timestamp": "2026-04-23T00:00:00Z",
  "score": 0.85,
  "details": {
    "sample_count": 50,
    "method": "scipy.stats.spearmanr"
  }
}
```

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| numpy missing from requirements.txt (pre-existing bug) | HIGH | Spec 4 fixes this immediately; Spec 1 depends on it |
| Disk impact (dspy+langgraph base ~595 MB; +1.5 GB torch CPU; +3.0 GB torch full) | LOW | Document in dependency-compatibility.md |
| litellm 6 CVEs blocked by dspy constraint | HIGH | Accept risk + monitor dspy; pin exact versions |
| tokenizers/tiktoken no Python 3.14 wheels | MEDIUM | Pin <0.13.0 for tiktoken; add Rust to CI |
| litellm 6 CVEs blocked by dspy constraint | HIGH | Accept risk + monitor dspy releases, or pin dspy exact and track updates |
| tokenizers/tiktoken no Python 3.14 wheels | MEDIUM | Pin `<0.13.0`, add Rust to CI, or target Python 3.13 for production |
| datasets 4.x API breakage | HIGH | Pin `datasets==2.21.0` (not `>=2.19`) |
| langchain-core in langgraph exclusion list | MEDIUM | Pin `langgraph==0.2.76` and `langchain-core` exact |
| Anchor dataset generation requires external model | HIGH | External dependency not controlled by code; requires API keys/credentials |
| Spearman correlation not implemented anywhere | MEDIUM | Use scipy.stats.spearmanr; add scipy to requirements |
| `infrastructure/` is greenfield (no existing patterns) | LOW | Follow `scripts/benchmark/` pattern for structure |
| `.example.yaml` pattern is new (no precedent) | LOW | Follow existing taxonomy YAML pattern; `.example` suffix is conventional |
| Prompt extraction from taxonomy YAMLs | MEDIUM | Prompt keys are in `prompt_builder.py` module-level `_TAX` dict; extraction is straightforward mapping |

## Execution Plan

### Phase 1: Foundation (Parallel, 1-2 days)

**Spec 4 (dependency-compatibility)** and **Spec 2 (prompt-externalization)** run in parallel.

- Spec 4: Add scipy, numpy, dspy, langgraph, torch to requirements.txt + pyproject.toml. Write `dependency_check.py`. Document litellm CVEs and Python 3.14 CI caveats. Use strict exact version pins (`==`).
- Spec 2: Extract prompts from `prompt_builder.py` taxonomy + judge.py/calibration.py into 4 `.example.yaml` files.

### Phase 2: Baselines (1-2 days)

**Spec 1 (baseline-measurement)** after Spec 4 merges.

- Create `infrastructure/baselines/` directory
- Write 3 measurement scripts + 1 rollback check
- Run baselines to produce initial data

### Phase 3: Anchor Dataset (5-10 days)

**Spec 3 (anchor-dataset)** after Spec 1 and Spec 2 merge.

- Create `infrastructure/anchor_dataset_builder.py`
- Generate 100-200 samples (requires external model + human verification)
- Store in `datasets/anchors/v1/`

### Parallelization Opportunities

- Phase 1: 2 specs fully parallelizable (no shared file modifications)
- Phase 2: Dependent on Phase 1 only for dependencies (not prompts)
- Phase 3: Longest phase, human verification is the bottleneck

### Critical Path

```
Spec 4 ──► Spec 1 ──► Spec 3
Spec 2 ──┘          ──►
```

Spec 2 is NOT on the critical path but should be done before Spec 3 (prompts externalized).

### Total Timeline Estimate

- Fast case (parallel): 1-2 days (Phase 1) + 1-2 days (Phase 2) + 5-10 days (Phase 3) = 7-14 days
- With sequential Phase 1: 2-4 days (Phase 1) + 1-2 days (Phase 2) + 5-10 days (Phase 3) = 8-16 days
