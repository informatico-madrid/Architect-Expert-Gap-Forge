# Requirements: Prompt Externalization

## Goal

Create `.example.yaml` template files cataloging all existing taxonomy prompts with English translations, providing DSPy with language-agnostic external configuration without modifying any production code.

## User Stories

### US-1: Catalog Trajectory Prompts
**As an** ML Engineer
**I want to** extract trajectory turn templates from hardcoded defaults in `trajectory_generator.py` into `src/factory/prompts_trajectory.example.yaml`
**So that** DSPy can consume trajectory templates as external configuration instead of hardcoded Spanish strings

**Acceptance Criteria:**
- [ ] AC-1.1: File `src/factory/prompts_trajectory.example.yaml` exists at the specified path
- [ ] AC-1.2: File follows the prescribed YAML schema (`prompts.<key>.system` + `prompts.<key>.user`)
- [ ] AC-1.3: Contains all 6 turn templates extracted from `_default_templates()` in `trajectory_generator.py`
- [ ] AC-1.4: Prompts are translated to English (original source is Spanish)
- [ ] AC-1.5: Template placeholders use `$var` syntax consistent with existing DSPy convention

### US-2: Catalog Hard Query Prompts
**As an** ML Engineer
**I want to** extract forbidden terms and the problem-focused template from `hard_query_builder.py` into `src/factory/prompts_hard_query.example.yaml`
**So that** the missing template file gap is filled and DSPy has external hard query configuration

**Acceptance Criteria:**
- [ ] AC-2.1: File `src/factory/prompts_hard_query.example.yaml` exists at the specified path
- [ ] AC-2.2: File follows the prescribed YAML schema
- [ ] AC-2.3: Contains the forbidden_terms list extracted from `hard_query_builder.py`
- [ ] AC-2.4: Contains the problem_focused template translated to English
- [ ] AC-2.5: Contains abstract transformation rules if present in source

### US-3: Catalog Judge/Evaluation Prompts
**As an** ML Engineer
**I want to** transform `configs/stage_5_evaluation/eval_prompts.yaml` (4 groups) into `src/audit/prompts_judge.example.yaml`
**So that** DSPy has an externalized English version of judge prompts

**Acceptance Criteria:**
- [ ] AC-3.1: File `src/audit/prompts_judge.example.yaml` exists at the specified path
- [ ] AC-3.2: Contains all 4 prompt groups: professor_exam, professor_judge, gap_analysis, professor_judge_calibration
- [ ] AC-3.3: Prompts with Spanish content are translated to English
- [ ] AC-3.4: Mixed EN/ES source preserves original intent through translation
- [ ] AC-3.5: YAML structure matches the prescribed schema format

### US-4: Catalog Calibration Prompts
**As an** ML Engineer
**I want to** transform `configs/stage_6_calibration/calibration_prompts.yaml` (6 active prompts) into `src/audit/prompts_calibration.example.yaml`
**So that** DSPy has external calibration prompt configuration

**Acceptance Criteria:**
- [ ] AC-4.1: File `src/audit/prompts_calibration.example.yaml` exists at the specified path
- [ ] AC-4.2: Contains all 6 active prompts from the source YAML
- [ ] AC-4.3: Prompts are translated to English (source is already English, verify fidelity)
- [ ] AC-4.4: YAML structure is consistent with prescribed schema (adapting from list-of-objects format to prompts dict format)

### US-5: Catalog Taxonomy Prompts
**As an** ML Engineer
**I want to** consolidate the main taxonomy YAML (~30 prompt groups) into `src/factory/prompts_taxonomy.example.yaml`
**So that** DSPy has a unified English reference for the Stage 2 taxonomy

**Acceptance Criteria:**
- [ ] AC-5.1: File `src/factory/prompts_taxonomy.example.yaml` exists at the specified path
- [ ] AC-5.2: Contains all ~30 prompt groups from the main taxonomy source
- [ ] AC-5.3: Prompt categories preserved: system.python.*, system.jinja.*, user.python.*, user.jinja.*, theory, error_templates, legacy_patterns, tools_definition
- [ ] AC-5.4: Spanish content translated to English
- [ ] AC-5.5: Only one consolidated file created (not separate files for near-identical copies)

### US-6: Catalog Frontend Taxonomy Prompts (Dead Code)
**As an** ML Engineer
**I want to** mirror `src/export/frontend_taxonomy_prompts.py` (4 system + 1 user prompt) into `src/export/prompts_frontend.example.yaml` with a note that it is dead code
**So that** the complete prompt surface area is cataloged even though this code is never imported

**Acceptance Criteria:**
- [ ] AC-6.1: File `src/export/prompts_frontend.example.yaml` exists at the specified path
- [ ] AC-6.2: Contains all 4 system + 1 user prompts from the source Python file
- [ ] AC-6.3: File header includes a comment noting the source code is dead code (never imported)
- [ ] AC-6.4: Prompts translated to English if source is not English

### US-7: Catalog Backtracking Prompts
**As an** ML Engineer
**I want to** transform plain text prompts from `configs/prompts/backtracking_system.txt` and `configs/prompts/reconstruction_system.txt` into `src/curation/prompts_backtracking.example.yaml`
**So that** DSPy has structured YAML representation of curation-stage prompts

**Acceptance Criteria:**
- [ ] AC-7.1: File `src/curation/prompts_backtracking.example.yaml` exists at the specified path
- [ ] AC-7.2: Contains both prompts: backtracking_system and reconstruction_system
- [ ] AC-7.3: Plain text format converted to structured system/user format
- [ ] AC-7.4: Prompts translated to English if source contains non-English content

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Create 7 `.example.yaml` template files across `src/factory/`, `src/audit/`, `src/export/`, `src/curation/` | High | All 7 files exist at prescribed paths |
| FR-2 | All prompts translated to English from Spanish source | High | No Spanish text remains in `.example.yaml` files (except untranslatable domain terms) |
| FR-3 | Use prescribed YAML schema: `prompts.<key>.system` + `prompts.<key>.user` | High | All files parseable by the schema validator |
| FR-4 | Preserve all original prompt content (no loss during format conversion) | High | Source prompt count matches output prompt count for each file |
| FR-5 | Convert non-dict format sources (list-of-objects, plain text) to dict format | Medium | calibration: list-of-objects -> prompts dict; backtracking: plain text -> prompts dict |
| FR-6 | Consolidate near-identical taxonomy copies into single file | Medium | Only one `prompts_taxonomy.example.yaml`; `agentic_taxonomy.yaml` differences noted in comments |
| FR-7 | Document dead code and orphaned sources in file headers | Medium | frontend prompts noted as dead code; calibration YAMLs noted as orphaned |
| FR-8 | No production code is modified | High | `git diff` shows zero changes to files outside `.example.yaml` additions |
| FR-9 | No code changes are made to any existing `.yaml` or `.py` files | High | `.example.yaml` files are the only new files |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | File creation time | Elapsed time | < 5 minutes (XS spec) |
| NFR-2 | Translation quality | English readability | All prompts understandable to English-speaking ML engineer |
| NFR-3 | Schema compliance | YAML parse success | `yaml.safe_load()` succeeds on all 7 files |

## Glossary

- **`.example.yaml`**: Template YAML file whose `.example` suffix signals "template, copy and customize" — not directly loaded by production code
- **DSPy**: Deep Learning Prompt You framework (v3.2.0) — uses Python class docstrings for prompts, no native YAML loading
- **`.default_templates()`**: Fallback method in production code that provides hardcoded Spanish prompts when YAML files are missing
- **PromptManager**: Stage 2 factory component that loads `eval_prompts.yaml` — separate concern from DSPy
- **Taxonomy YAML**: Existing `prompts_taxonomy.yaml` files in `configs/` — used by Stage 2 pipeline, not DSPy
- **Dead code**: Source code that defines prompts but is never imported or called by any pipeline
- **Orphaned**: YAML files that exist on disk but have no code path loading them
- **Epic 0**: This spec — infrastructure setup, catalog + translate only
- **Epic 1**: Future DSPy integration — replaces hardcoded Spanish, wires `.example.yaml` into DSPy Signatures

## Out of Scope

- DSPy Signature creation or integration (Epic 1, FR-008)
- Replacing hardcoded Spanish in production code (Epic 1)
- Deleting dead code (`frontend_taxonomy_prompts.py`)
- Deleting or modifying orphaned YAML files (`calibration_prompts.yaml`)
- Modifying any existing production `.py` or `.yaml` files
- Creating bridge code to load YAML into DSPy Signatures
- MIPROv2 optimization of prompts
- Spearman correlation measurement (mentioned in plan.md AC-2 — not applicable to catalog-only scope)
- The `plugin_architecture.yaml` file (confirmed NOT a prompt taxonomy)

## Dependencies

- None — this spec can start immediately, runs in parallel with dependency-compatibility spec
- Feeds into anchor-dataset spec (English prompts required before anchor creation)
- Feeds into Epic 1 stories (1.1-1.7) which will consume these `.example.yaml` files

## Success Criteria

- 7 `.example.yaml` files created at prescribed paths
- All prompts translated to English
- Zero production code modifications
- Files conform to prescribed YAML schema

## Verification Contract

**Project type**: `library`

Python package (`src/aegf.egg-info/`, no HTTP API, no browser UI). Primary interface is importable Python modules.

**Entry points**: File system — 7 `.example.yaml` files created under:
- `src/factory/prompts_trajectory.example.yaml`
- `src/factory/prompts_hard_query.example.yaml`
- `src/factory/prompts_taxonomy.example.yaml`
- `src/audit/prompts_judge.example.yaml`
- `src/audit/prompts_calibration.example.yaml`
- `src/export/prompts_frontend.example.yaml`
- `src/curation/prompts_backtracking.example.yaml`

**Observable signals**:
- PASS: All 7 files exist, parse as valid YAML, contain English text, follow prescribed schema
- FAIL: Missing file, schema mismatch, Spanish text remaining in output, production code modified

**Hard invariants**:
- No `.py` file is modified or deleted
- No existing `.yaml` file in `configs/` is modified or deleted
- No import paths are broken
- Adjacent specs (dependency-compatibility, baseline-measurement) unaffected

**Seed data**:
- Source files must exist: `trajectory_generator.py`, `hard_query_builder.py`, `eval_prompts.yaml`, `calibration_prompts.yaml`, `prompts_taxonomy.yaml`, `frontend_taxonomy_prompts.py`, `backtracking_system.txt`, `reconstruction_system.txt`

**Dependency map**:
- `anchor-dataset` spec depends on these files for English prompt references
- Epic 1 stories 1.1-1.7 consume these files as DSPy Signature bootstrap

**Escalate if**:
- Source prompt text is ambiguous or contains domain-specific terms that cannot be confidently translated
- Schema conversion for calibration (list-of-objects to dict) loses information
- Decision needed on whether to include `curation/prompts/user.yaml` (trivial "helpful assistant" placeholder)
