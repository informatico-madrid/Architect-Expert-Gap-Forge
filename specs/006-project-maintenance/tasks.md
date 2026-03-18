# Tasks: Project Maintenance

**Feature**: 006-project-maintenance  
**Date**: 2026-03-18  
**Status**: Draft  
**Spec**: [specs/006-project-maintenance/spec.md](specs/006-project-maintenance/spec.md)

## Overview

This file contains all implementation tasks for the project maintenance feature. Tasks are organized by user story and ordered by dependencies.

## Task Summary

| Phase | User Story | Tasks | Description |
|-------|------------|-------|-------------|
| Phase 1 | Setup | 2 | Project initialization and tooling |
| Phase 1b | Error Handling | 3 | Edge case coverage |
| Phase 2 | Foundational | 5 | Blocking prerequisites |
| Phase 3 | US1 | 4 | Formatting tooling |
| Phase 4 | US2 | 3 | Backend configuration |
| Phase 5 | US3 | 6 | Merger scripts organization |
| Phase 6 | US4 | 6 | Rapid experimentation pipeline |
| **Total** | | **29** | |

## Dependencies

- **US1** (Formatting) → **US2** (Backend) → **US3** (Merger) → **US4** (Experimentation)
- All phases are independent except for the sequential order shown above
- Tasks within each phase can be executed in parallel

## Phase 1: Setup (Project Initialization)

### Goal
Initialize the project structure and ensure all prerequisites are in place.

### Independent Test
- [ ] `make fmt` and `make lint` work correctly
- [ ] All dependencies can be installed from `requirements-dev.txt`

---

#### Task 1.1: Add ruff to requirements-dev.txt

**Description**: Add `ruff>=0.9` to `requirements-dev.txt` so developers can install it with other dev dependencies.

**Done when**:
- [x] `ruff>=0.9` is in `requirements-dev.txt`
- [x] `pip install -r requirements-dev.txt` installs ruff
- [x] `make fmt` and `make lint` work correctly

**File path**: `requirements-dev.txt`

**Verify**:
```bash
pip show ruff  # Should show ruff is installed
ruff --version  # Should show version >= 0.9
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US1]

---

#### Task 1.2: Verify Makefile uses ruff

**Description**: Verify that the Makefile already uses ruff for `make fmt` and `make lint` commands.

**Done when**:
- [x] `make fmt` runs ruff format
- [x] `make lint` runs ruff check
- [x] Commands are documented in Makefile

**File path**: `Makefile`

**Verify**:
```bash
grep -A 2 "^fmt:" Makefile  # Should show ruff format
grep -A 2 "^lint:" Makefile  # Should show ruff check
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US1]

---

## Phase 1b: Error Handling (NEW - Edge Case Coverage)

### Goal
Implement robust error handling for all critical operations to prevent silent failures and provide clear error messages.

### Independent Test
- [ ] All error conditions produce clear, actionable error messages
- [ ] System fails fast on critical conditions (disk space, API key missing)
- [ ] Checkpoint/resume functionality works for long-running operations

---

#### Task 1.3: Implement Gemini API key validation

**Description**: Add validation to ensure clear error message when Gemini backend is used without GOOGLE_API_KEY.

**Done when**:
- [x] System checks for GOOGLE_API_KEY when backend is set to "gemini"
- [x] Clear error message displayed: "GOOGLE_API_KEY environment variable is required for Gemini backend"
- [x] Error message includes guidance on how to set the variable

**File path**: `src/audit/config.py` or backend router

**Verify**:
```bash
# Test without GOOGLE_API_KEY set
unset GOOGLE_API_KEY
python -c "from src.audit.config import get_backend; get_backend('gemini')"  # Should show clear error
```

**Estimated time**: 10 minutes

**Labels**: [P1] [Edge Case]

---

#### Task 1.4: Implement disk space validation

**Description**: Add disk space validation to experiment pipeline to fail fast with clear error message.

**Done when**:
- [x] System checks available disk space before starting experiment
- [x] Minimum required space defined (e.g., 10 GB for training)
- [x] Clear error message: "Insufficient disk space. Required: X GB, Available: Y GB"
- [x] Validation runs before any file operations

**File path**: `src/research/experiment_orchestrator.py`

**Verify**:
```bash
# Test with low disk space (simulate)
python -c "from src.research.experiment_orchestrator import ExperimentOrchestrator; exp = ExperimentOrchestrator(...); exp._validate_disk_space()"  # Should validate
```

**Estimated time**: 15 minutes

**Labels**: [P1] [Edge Case]

---

#### Task 1.5: Implement checkpoint resume for tokenizer training

**Description**: Add checkpoint and resume functionality for tokenizer training to handle failures gracefully.

**Done when**:
- [x] Training progress saved at regular intervals (e.g., every 1000 steps)
- [x] System can resume from last checkpoint on restart
- [x] Progress file saved in output directory with step number and state
- [x] Clear error message if checkpoint is corrupted

**File path**: `src/research/train_tokenizer.py`

**Verify**:
```bash
# Test checkpoint creation
python src/research/train_tokenizer.py --output-dir output/tokenizers/test --checkpoint-interval 1000  # Should create checkpoint files

# Test resume
python src/research/train_tokenizer.py --output-dir output/tokenizers/test --resume-from-checkpoint  # Should resume from last checkpoint
```

**Estimated time**: 30 minutes

**Labels**: [P1] [Edge Case]

**Description**: Add `ruff>=0.9` to `requirements-dev.txt` so developers can install it with other dev dependencies.

**Done when**:
- [x] `ruff>=0.9` is in `requirements-dev.txt`
- [x] `pip install -r requirements-dev.txt` installs ruff
- [x] `make fmt` and `make lint` work correctly

**File path**: `requirements-dev.txt`

**Verify**:
```bash
pip show ruff  # Should show ruff is installed
ruff --version  # Should show version >= 0.9
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US1]

---

## Phase 2: Foundational (Blocking Prerequisites)

### Goal
Complete all foundational tasks that block user story implementation.

### Independent Test
- [ ] All foundational tasks complete successfully
- [ ] No blocking issues for user story implementation

---

#### Task 2.1: Create src/merger/ directory

**Description**: Create the `src/merger/` directory with `__init__.py` to make it a Python package.

**Done when**:
- [x] `src/merger/` directory exists
- [x] `src/merger/__init__.py` exists with proper exports
- [x] Directory is importable as `from src.merger import ...`

**File path**: `src/merger/__init__.py`

**Verify**:
```bash
python -c "from src.merger import merge_shards; print('Import successful')"
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US3]

---

#### Task 2.2: Create src/research/ directory

**Description**: Create the `src/research/` directory if it doesn't exist.

**Done when**:
- [x] `src/research/` directory exists
- [x] Ready for new research utilities

**File path**: `src/research/`

**Verify**:
```bash
ls -la src/research/  # Should show directory exists
```

**Estimated time**: 2 minutes

**Labels**: [P1] [US4]

---

#### Task 2.3: Create configs/stage_4_training/axolotl/ directory

**Description**: Create the `configs/stage_4_training/axolotl/` directory if it doesn't exist.

**Done when**:
- [x] `configs/stage_4_training/axolotl/` directory exists
- [x] Ready for Axolotl README

**File path**: `configs/stage_4_training/axolotl/`

**Verify**:
```bash
ls -la configs/stage_4_training/axolotl/  # Should show directory exists
```

**Estimated time**: 2 minutes

**Labels**: [P1] [US4]

---

#### Task 2.4: Create ExperimentVariant dataclass

**Description**: Create the `ExperimentVariant` dataclass in `src/research/models.py` as defined in data-model.md.

**Done when**:
- [x] File `src/research/models.py` exists
- [x] `ExperimentVariant` dataclass defined with all fields
- [x] Validation rules implemented (dedup_threshold, gold_injection_rate ranges)
- [x] Computed properties (description) implemented
- [x] Includes header and proper typing

**File path**: `src/research/models.py`

**Verify**:
```bash
python -c "from src.research.models import ExperimentVariant; v = ExperimentVariant(name='test', dedup_threshold=0.95, gold_injection_rate=0.1, min_length=512); print(v.description)"  # Should print description
```

**Estimated time**: 20 minutes

**Labels**: [P1] [Data Model]

---

#### Task 2.5: Create TrainingRun dataclass

**Description**: Create the `TrainingRun` dataclass in `src/research/models.py` as defined in data-model.md.

**Done when**:
- [x] `TrainingRun` dataclass defined with all fields
- [x] Validation rules implemented (val_bpb > 0, mfu_percent in range)
- [x] Computed properties (efficiency_score) implemented
- [x] Includes header and proper typing

**File path**: `src/research/models.py`

**Verify**:
```bash
python -c "from src.research.models import TrainingRun; r = TrainingRun(...); print(r.efficiency_score)"  # Should calculate efficiency score
```

**Estimated time**: 20 minutes

**Labels**: [P1] [Data Model]

**Description**: Create the `src/merger/` directory with `__init__.py` to make it a Python package.

**Done when**:
- [x] `src/merger/` directory exists
- [x] `src/merger/__init__.py` exists with proper exports
- [x] Directory is importable as `from src.merger import ...`

**File path**: `src/merger/__init__.py`

**Verify**:
```bash
python -c "from src.merger import merge_shards; print('Import successful')"
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US3]

---

**Description**: Create the `src/research/` directory if it doesn't exist.

**Done when**:
- [x] `src/research/` directory exists
- [x] Ready for new research utilities

**File path**: `src/research/`

**Verify**:
```bash
ls -la src/research/  # Should show directory exists
```

**Estimated time**: 2 minutes

**Labels**: [P1] [US4]

---

**Description**: Create the `configs/stage_4_training/axolotl/` directory if it doesn't exist.

**Done when**:
- [x] `configs/stage_4_training/axolotl/` directory exists
- [x] Ready for Axolotl README

**File path**: `configs/stage_4_training/axolotl/`

**Verify**:
```bash
ls -la configs/stage_4_training/axolotl/  # Should show directory exists
```

**Estimated time**: 2 minutes

**Labels**: [P1] [US4]

---

## Phase 3: User Story 1 - Establish Canonical Development Tooling

### Goal
Establish ruff as the canonical formatter with clear tooling and documentation.

### Independent Test
- [x] Running `make fmt` on the entire codebase completes in under 30 seconds and reports zero style violations
- [x] Installing development dependencies via `pip install -r requirements-dev.txt` includes ruff
- [x] Zero CI failures due to style violations

---

#### Task 3.1: Add ruff>=0.9 to requirements-dev.txt

**Description**: Add `ruff>=0.9` to `requirements-dev.txt` to ensure developers can install all required tooling from a single file.

**Done when**:
- [x] `ruff>=0.9` is in `requirements-dev.txt`
- [x] `pip install -r requirements-dev.txt` installs ruff
- [x] `make fmt` and `make lint` work correctly

**File path**: `requirements-dev.txt`

**Verify**:
```bash
pip show ruff  # Should show ruff is installed
ruff --version  # Should show version >= 0.9
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US1]

---

#### Task 3.2: Format codebase with ruff

**Description**: Run `make fmt` to format the entire codebase with ruff standards.

**Done when**:
- [x] `make fmt` completes without errors
- [x] All Python files are formatted according to ruff standards
- [x] No style violations remain

**File path**: All Python files in codebase

**Verify**:
```bash
make lint  # Should report zero violations
```

**Estimated time**: 15 minutes

**Labels**: [P1] [US1]

---

#### Task 3.3: Verify make fmt completes in <30 seconds

**Description**: Measure and verify that `make fmt` completes in under 30 seconds.

**Done when**:
- [x] `time make fmt` shows execution time <30 seconds
- [x] No performance issues detected

**File path**: N/A (verification task)

**Verify**:
```bash
time make fmt  # Should show <30 seconds
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US1]

---

#### Task 3.4: Verify zero CI failures due to style

**Description**: Verify that there are zero CI failures due to style violations.

**Done when**:
- [x] CI passes without style-related failures
- [x] `make lint` reports zero violations
- [x] All developers can push without style issues

**File path**: CI configuration, Makefile

**Verify**:
```bash
make lint  # Should report zero violations
```

**Estimated time**: 10 minutes

**Labels**: [P1] [US1]

---

## Phase 4: User Story 2 - Ensure Safe Default Inference Backend

### Goal
Set vLLM as the default inference backend to prevent accidental Gemini API usage.

### Independent Test
- [x] Running the evaluation pipeline without setting `GOOGLE_API_KEY` uses vLLM as the backend
- [x] Developer can override to Gemini by setting `AEGF_PROFESSOR_BACKEND=gemini`

---

#### Task 4.1: Change DEFAULT_PROFESSOR_BACKEND in src/audit/config.py

**Description**: Change `DEFAULT_PROFESSOR_BACKEND` from `"auto"` to `"vllm"` in `src/audit/config.py`.

**Done when**:
- [x] `src/audit/config.py:140` has `DEFAULT_PROFESSOR_BACKEND = "vllm"`
- [x] No references to `"auto"` remain for professor backend
- [x] CI uses vLLM without GOOGLE_API_KEY

**File path**: `src/audit/config.py`

**Verify**:
```bash
grep "DEFAULT_PROFESSOR_BACKEND" src/audit/config.py  # Should show "vllm"
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US2]

---

#### Task 4.2: Update eval_config.yaml professor_backend

**Description**: Change `professor_backend` from `"auto"` to `"vllm"` in `configs/stage_5_evaluation/eval_config.yaml`.

**Done when**:
- [x] `configs/stage_5_evaluation/eval_config.yaml:21` has `professor_backend: "vllm"`
- [x] Evaluation pipeline uses vLLM by default
- [x] CI runs successfully without GOOGLE_API_KEY

**File path**: `configs/stage_5_evaluation/eval_config.yaml`

**Verify**:
```bash
grep "professor_backend" configs/stage_5_evaluation/eval_config.yaml  # Should show "vllm"
```

**Estimated time**: 5 minutes

**Labels**: [P1] [US2]

---

#### Task 4.3: Verify CI uses vLLM by default

**Description**: Verify that CI runs successfully without GOOGLE_API_KEY set.

**Done when**:
- [x] CI passes with `GOOGLE_API_KEY` unset
- [x] vLLM is used as professor backend in CI
- [x] No accidental Gemini API calls

**File path**: CI configuration, src/audit/config.py

**Verify**:
```bash
# Run CI without GOOGLE_API_KEY
unset GOOGLE_API_KEY
make test  # Should use vLLM, not Gemini
```

**Estimated time**: 10 minutes

**Labels**: [P1] [US2]

---

## Phase 5: User Story 3 - Organize Merger Scripts

### Goal
Move all merge scripts from `data/weights/` to `src/merger/` for better organization.

### Independent Test
- [x] All merge-related scripts exist in `src/merger/` and can be imported as `from src.merger import ...`
- [x] Directory structure is clean and scripts are discoverable

---

#### Task 5.1: Create src/merger/ directory structure

**Description**: Create the `src/merger/` directory with `__init__.py` to make it a Python package.

**Done when**:
- [x] `src/merger/` directory exists
- [x] `src/merger/__init__.py` exists with proper exports
- [x] Directory is importable as `from src.merger import ...`

**File path**: `src/merger/__init__.py`

**Verify**:
```bash
python -c "from src.merger import merge_shards; print('Import successful')"
```

**Estimated time**: 5 minutes

**Labels**: [P2] [US3]

---

#### Task 5.2: Move stage1 scripts to src/merger/

**Description**: Move all 9 Python scripts from `data/weights/stage1_pure/` to `src/merger/`.

**Scripts to move**:
- `check_alignment.py`
- `clean_dna.py`
- `dna_fix_v2.py`
- `dna_strict.py`
- `final_ignition.py`
- `merge_shards.py`
- `repair_dna.py`
- `repair_triple_dna.py`
- `shotgun_dna.py`

**Done when**:
- [x] All 9 scripts moved to `src/merger/`
- [x] No scripts remain in `data/weights/stage1_pure/`
- [x] All import paths updated if needed

**File path**: `src/merger/*.py`

**Verify**:
```bash
ls -la src/merger/*.py | wc -l  # Should be 10 (9 scripts + __init__.py)
```

**Estimated time**: 10 minutes

**Labels**: [P2] [US3]

---

#### Task 5.3: Move stage2 scripts to src/merger/

**Description**: Move all 5 Python scripts from `data/weights/stage2_final_consolidated/` to `src/merger/`.

**Scripts to move**:
- `analisis_avanzado.py`
- `diagnostico.py`
- `fusionar_final.py`
- `repara_stage2.py`
- `guardar_tokenizador.py`

**Done when**:
- [x] All 5 scripts moved to `src/merger/`
- [x] No scripts remain in `data/weights/stage2_final_consolidated/`
- [x] All import paths updated if needed

**File path**: `src/merger/*.py`

**Verify**:
```bash
ls -la src/merger/*.py | wc -l  # Should be 15 (14 scripts + __init__.py)
```

**Estimated time**: 10 minutes

**Labels**: [P2] [US3]

---

#### Task 5.4: Update __init__.py exports

**Description**: Update `src/merger/__init__.py` to export all merge scripts for easy import.

**Done when**:
- [x] All 14 scripts are exported in `__init__.py`
- [x] Import works as `from src.merger import merge_shards, dna_fix_v2, ...`

**File path**: `src/merger/__init__.py`

**Verify**:
```bash
python -c "from src.merger import merge_shards, dna_fix_v2, fusionar_final; print('All imports successful')"
```

**Estimated time**: 5 minutes

**Labels**: [P2] [US3]

---

#### Task 5.5: Verify importability of all scripts

**Description**: Verify that all scripts can be imported as a Python module.

**Done when**:
- [x] All 14 scripts can be imported
- [x] No import errors occur
- [x] Import paths are correct

**File path**: `src/merger/`

**Verify**:
```bash
python -c "from src.merger import *; print('All imports successful')"
```

**Estimated time**: 5 minutes

**Labels**: [P2] [US3]

---

#### Task 5.6: Clean up data/weights/ directories

**Description**: Remove empty directories from `data/weights/stage1_pure/` and `data/weights/stage2_final_consolidated/` after migration.

**Done when**:
- [x] No scripts remain in `data/weights/stage1_pure/`
- [x] No scripts remain in `data/weights/stage2_final_consolidated/`
- [x] Directories are clean or removed

**File path**: `data/weights/stage1_pure/`, `data/weights/stage2_final_consolidated/`

**Verify**:
```bash
ls -la data/weights/stage1_pure/*.py  # Should show no .py files
ls -la data/weights/stage2_final_consolidated/*.py  # Should show no .py files
```

**Estimated time**: 5 minutes

**Labels**: [P2] [US3]

---

## Phase 6: User Story 4 - Enable Rapid Experimentation Pipeline

### Goal
Create a fast experimental workflow for rapid iteration on dataset variants and model configurations.

### Independent Test
- [x] Running a complete experiment loop (generate variant → tokenize → train fast_mode → evaluate → report) in under 30 minutes
- [x] Researcher can identify the best configuration in minutes rather than hours

---

#### Task 6.1: Create src/research/train_tokenizer.py

**Description**: Create `src/research/train_tokenizer.py` to train and save a canonical BPE tokenizer.

**Done when**:
- [x] File exists at `src/research/train_tokenizer.py`
- [x] Trains BPE tokenizer from corpus
- [x] Saves tokenizer files (vocab.json, merges.txt, tokenizer_config.json)
- [x] Includes header and proper typing

**File path**: `src/research/train_tokenizer.py`

**Verify**:
```bash
python src/research/train_tokenizer.py --help  # Should show usage
```

**Estimated time**: 30 minutes

**Labels**: [P3] [US4]

---

#### Task 6.2: Create src/audit/eval_bpb.py

**Description**: Create `src/audit/eval_bpb.py` to evaluate models using the BPB (bits per byte) metric.

**Done when**:
- [x] File exists at `src/audit/eval_bpb.py`
- [x] Computes BPB metric for model checkpoints
- [x] Outputs results in structured format (JSON/TSV)
- [x] Includes header and proper typing

**File path**: `src/audit/eval_bpb.py`

**Verify**:
```bash
python src/audit/eval_bpb.py --help  # Should show usage
```

**Estimated time**: 20 minutes

**Labels**: [P3] [US4]

---

#### Task 6.3: Create src/research/experiment_orchestrator.py

**Description**: Create `src/research/experiment_orchestrator.py` to coordinate dataset variant generation, tokenization, training, and evaluation.

**Done when**:
- [x] File exists at `src/research/experiment_orchestrator.py`
- [x] Implements `ExperimentOrchestrator` class with all public methods
- [x] Coordinates full experiment loop (generate → tokenize → train → evaluate → report)
- [x] Supports fast_mode and normal_mode
- [x] Includes header and proper typing

**File path**: `src/research/experiment_orchestrator.py`

**Verify**:
```bash
python -c "from src.research.experiment_orchestrator import ExperimentOrchestrator; print('Import successful')"
```

**Estimated time**: 60 minutes

**Labels**: [P3] [US4]

---

#### Task 6.4: Create docs/experiments.md

**Description**: Create `docs/experiments.md` documenting the rapid experimentation workflow.

**Done when**:
- [x] File exists at `docs/experiments.md`
- [x] Documents quick start (5 minutes)
- [x] Documents full workflow (10 minutes)
- [x] Includes common patterns (grid search, iterative refinement, ablation)
- [x] Includes troubleshooting section
- [x] Uses "fast_mode" terminology consistently

**File path**: `docs/experiments.md`

**Verify**:
```bash
cat docs/experiments.md | head -50  # Should show proper documentation
```

**Estimated time**: 30 minutes

**Labels**: [P3] [US4]

---

#### Task 6.5: Create configs/stage_4_training/axolotl/README.md

**Description**: Create `configs/stage_4_training/axolotl/README.md` with tokenizer compatibility guidance for Axolotl.

**Done when**:
- [x] File exists at `configs/stage_4_training/axolotl/README.md`
- [x] Documents 3 options: use base, add tokens, expand embeddings
- [x] Documents trade-offs for each option
- [x] Includes configuration examples
- [x] Clear guidance on tokenizer compatibility with Axolotl

**File path**: `configs/stage_4_training/axolotl/README.md`

**Verify**:
```bash
cat configs/stage_4_training/axolotl/README.md | head -30  # Should show guidance
```

**Estimated time**: 15 minutes

**Labels**: [P3] [US4]

---

#### Task 6.6: Implement results registration in TSV/DB

**Description**: Implement structured results registration for experiment pipeline in TSV format with metadata.

**Done when**:
- [x] Results registered in `output/experiments/results.tsv`
- [x] Metadata included: variant parameters, creator, timestamp, parent_variant
- [x] All metrics recorded: val_bpb, peak_vram_mb, mfu_percent, total_tokens_M
- [x] Append-only format for historical tracking

**File path**: `src/research/experiment_orchestrator.py`

**Verify**:
```bash
cat output/experiments/results.tsv | head  # Should show structured results with metadata
```

**Estimated time**: 25 minutes

**Labels**: [P3] [US4] [FR-013]

**Description**: Create `src/research/train_tokenizer.py` to train and save a canonical BPE tokenizer.

**Done when**:
- [x] File exists at `src/research/train_tokenizer.py`
- [x] Trains BPE tokenizer from corpus
- [x] Saves tokenizer files (vocab.json, merges.txt, tokenizer_config.json)
- [x] Includes header and proper typing

**File path**: `src/research/train_tokenizer.py`

**Verify**:
```bash
python src/research/train_tokenizer.py --help  # Should show usage
```

**Estimated time**: 30 minutes

**Labels**: [P3] [US4]

---

**Description**: Create `src/audit/eval_bpb.py` to evaluate models using the BPB (bits per byte) metric.

**Done when**:
- [x] File exists at `src/audit/eval_bpb.py`
- [x] Computes BPB metric for model checkpoints
- [x] Outputs results in structured format (JSON/TSV)
- [x] Includes header and proper typing

**File path**: `src/audit/eval_bpb.py`

**Verify**:
```bash
python src/audit/eval_bpb.py --help  # Should show usage
```

**Estimated time**: 20 minutes

**Labels**: [P3] [US4]

---

**Description**: Create `src/research/experiment_orchestrator.py` to coordinate dataset variant generation, tokenization, training, and evaluation.

**Done when**:
- [x] File exists at `src/research/experiment_orchestrator.py`
- [x] Implements `ExperimentOrchestrator` class with all public methods
- [x] Coordinates full experiment loop (generate → tokenize → train → evaluate → report)
- [x] Supports fast mode and normal mode
- [x] Includes header and proper typing

**File path**: `src/research/experiment_orchestrator.py`

**Verify**:
```bash
python -c "from src.research.experiment_orchestrator import ExperimentOrchestrator; print('Import successful')"
```

**Estimated time**: 60 minutes

**Labels**: [P3] [US4]

---

**Description**: Create `docs/experiments.md` documenting the rapid experimentation workflow.

**Done when**:
- [x] File exists at `docs/experiments.md`
- [x] Documents quick start (5 minutes)
- [x] Documents full workflow (10 minutes)
- [x] Includes common patterns (grid search, iterative refinement, ablation)
- [x] Includes troubleshooting section

**File path**: `docs/experiments.md`

**Verify**:
```bash
cat docs/experiments.md | head -50  # Should show proper documentation
```

**Estimated time**: 30 minutes

**Labels**: [P3] [US4]

---

**Description**: Create `configs/stage_4_training/axolotl/README.md` with tokenizer compatibility guidance for Axolotl.

**Done when**:
- [x] File exists at `configs/stage_4_training/axolotl/README.md`
- [x] Documents 3 options: use base, add tokens, expand embeddings
- [x] Documents trade-offs for each option
- [x] Includes configuration examples

**File path**: `configs/stage_4_training/axolotl/README.md`

**Verify**:
```bash
cat configs/stage_4_training/axolotl/README.md | head -30  # Should show guidance
```

**Estimated time**: 15 minutes

**Labels**: [P3] [US4]

---

## Success Criteria

- **SC-001**: Running `make fmt` on the entire codebase completes in under 30 seconds and reports zero style violations ✅
- **SC-002**: Installing development dependencies via `pip install -r requirements-dev.txt` includes ruff ✅
- **SC-003**: The evaluation pipeline uses vLLM as the default professor backend in 100% of CI runs without requiring `GOOGLE_API_KEY` ✅
- **SC-004**: A developer can override the professor backend to Gemini by setting a single environment variable (`AEGF_PROFESSOR_BACKEND=gemini`) ✅
- **SC-005**: All references to `src/merger/` in documentation point to an existing implementation ✅
- **SC-006**: A researcher can run a complete experiment loop in under 30 minutes using fast_mode ✅
- **SC-007**: The experiment pipeline can compare 10 different dataset variants and identify the best configuration in under 5 minutes ✅
- **SC-008**: The documentation provides clear steps for a new researcher to run their first experiment in under 10 minutes ✅
- **SC-009**: The Axolotl README includes clear guidance on tokenizer compatibility with 3 documented options (use base, add tokens, expand embeddings) and their trade-offs ✅
- **SC-010**: Zero CI failures due to style violations after enforcing ruff formatting ✅

## Edge Case Coverage (NEW)

- **EC-001**: Clear error message when Gemini backend used without GOOGLE_API_KEY ✅ (Task 1.3)
- **EC-002**: Fail fast with clear error message when disk space insufficient ✅ (Task 1.4)
- **EC-003**: Checkpoint and resume functionality for tokenizer training failures ✅ (Task 1.5)
- **EC-004**: All error handling produces actionable error messages ✅ (Task 1.3-1.5)

## Data Model Implementation (NEW)

- **DM-001**: ExperimentVariant dataclass implemented with validation ✅ (Task 2.4)
- **DM-002**: TrainingRun dataclass implemented with efficiency_score ✅ (Task 2.5)
- **DM-003**: Results registration in TSV format with metadata ✅ (Task 6.6)

## Notes

- Tasks marked with `[x]` in "Done when" are considered complete when verified
- All tasks include file paths for easy navigation
- Estimated times are guidelines and may vary based on codebase size
- Tasks can be executed in parallel within each phase
- Verify each task before marking it as complete
- [x] All import paths updated if needed

**Verify**:
```bash
ls -la src/merger/*.py | wc -l  # Should be 10 (9 scripts + __init__.py)
```

**Estimated time**: 10 minutes

---

**Description**: Move all 5 Python scripts from `data/weights/stage2_final_consolidated/` to `src/merger/`.

**Scripts to move**:
- `analisis_avanzado.py`
- `diagnostico.py`
- `fusionar_final.py`
- `repara_stage2.py`
- `guardar_tokenizador.py`

**Done when**:
- [x] All 5 scripts moved to `src/merger/`
- [x] No scripts remain in `data/weights/stage2_final_consolidated/`
- [x] All import paths updated if needed

**Verify**:
```bash
ls -la src/merger/*.py | wc -l  # Should be 15 (14 scripts + __init__.py)
```

**Estimated time**: 10 minutes

---

**Description**: Update `src/merger/__init__.py` to export all merge scripts for easy import.

**Done when**:
- [x] All 14 scripts are exported in `__init__.py`
- [x] Import works as `from src.merger import merge_shards, dna_fix_v2, ...`

**Verify**:
```bash
python -c "from src.merger import merge_shards, dna_fix_v2, fusionar_final; print('All imports successful')"
```

**Estimated time**: 5 minutes

---

### Phase 2: Formatting Tooling

**Description**: Add `ruff>=0.9` to `requirements-dev.txt` so developers can install it with other dev dependencies.

**Done when**:
- [x] `ruff>=0.9` is in `requirements-dev.txt`
- [x] `pip install -r requirements-dev.txt` installs ruff
- [x] `make fmt` and `make lint` work correctly

**Verify**:
```bash
pip show ruff  # Should show ruff is installed
ruff --version  # Should show version >= 0.9
```

**Estimated time**: 5 minutes

---

**Description**: Run `make fmt` to format the entire codebase with ruff standards.

**Done when**:
- [x] `make fmt` completes without errors
- [x] All Python files are formatted according to ruff standards
- [x] No style violations remain

**Verify**:
```bash
make lint  # Should report zero violations
```

**Estimated time**: 15 minutes

---

### Phase 3: Default Backend Configuration

**Description**: Change `DEFAULT_PROFESSOR_BACKEND` from `"auto"` to `"vllm"` in `src/audit/config.py`.

**Done when**:
- [x] `src/audit/config.py:140` has `DEFAULT_PROFESSOR_BACKEND = "vllm"`
- [x] No references to `"auto"` remain for professor backend
- [x] CI uses vLLM without GOOGLE_API_KEY

**Verify**:
```bash
grep "DEFAULT_PROFESSOR_BACKEND" src/audit/config.py  # Should show "vllm"
```

**Estimated time**: 5 minutes

---

**Description**: Change `professor_backend` from `"auto"` to `"vllm"` in `configs/stage_5_evaluation/eval_config.yaml`.

**Done when**:
- [x] `configs/stage_5_evaluation/eval_config.yaml:21` has `professor_backend: "vllm"`
- [x] Evaluation pipeline uses vLLM by default
- [x] CI runs successfully without GOOGLE_API_KEY

**Verify**:
```bash
grep "professor_backend" configs/stage_5_evaluation/eval_config.yaml  # Should show "vllm"
```

**Estimated time**: 5 minutes

---

**Description**: Verify that CI runs successfully without GOOGLE_API_KEY set.

**Done when**:
- [x] CI passes with `GOOGLE_API_KEY` unset
- [x] vLLM is used as professor backend in CI
- [x] No accidental Gemini API calls

**Verify**:
```bash
# Run CI without GOOGLE_API_KEY
unset GOOGLE_API_KEY
make test  # Should use vLLM, not Gemini
```

**Estimated time**: 10 minutes

---

### Phase 4: Rapid Experimentation Pipeline

**Description**: Create `src/research/train_tokenizer.py` to train and save a canonical BPE tokenizer.

**Done when**:
- [x] File exists at `src/research/train_tokenizer.py`
- [x] Trains BPE tokenizer from corpus
- [x] Saves tokenizer files (vocab.json, merges.txt, tokenizer_config.json)
- [x] Includes header and proper typing

**Verify**:
```bash
python src/research/train_tokenizer.py --help  # Should show usage
```

**Estimated time**: 30 minutes

---

**Description**: Create `src/audit/eval_bpb.py` to evaluate models using the BPB (bits per byte) metric.

**Done when**:
- [x] File exists at `src/audit/eval_bpb.py`
- [x] Computes BPB metric for model checkpoints
- [x] Outputs results in structured format (JSON/TSV)
- [x] Includes header and proper typing

**Verify**:
```bash
python src/audit/eval_bpb.py --help  # Should show usage
```

**Estimated time**: 20 minutes

---

**Description**: Create `src/research/experiment_orchestrator.py` to coordinate dataset variant generation, tokenization, training, and evaluation.

**Done when**:
- [x] File exists at `src/research/experiment_orchestrator.py`
- [x] Implements `ExperimentOrchestrator` class with all public methods
- [x] Coordinates full experiment loop (generate → tokenize → train → evaluate → report)
- [x] Supports fast mode and normal mode
- [x] Includes header and proper typing

**Verify**:
```bash
python -c "from src.research.experiment_orchestrator import ExperimentOrchestrator; print('Import successful')"
```

**Estimated time**: 60 minutes

---


**Description**: Create `docs/experiments.md` documenting the rapid experimentation workflow.

**Done when**:
- [x] File exists at `docs/experiments.md`
- [x] Documents quick start (5 minutes)
- [x] Documents full workflow (10 minutes)
- [x] Includes common patterns (grid search, iterative refinement, ablation)
- [x] Includes troubleshooting section

**Verify**:
```bash
cat docs/experiments.md | head -50  # Should show proper documentation
```

**Estimated time**: 30 minutes

---


**Description**: Create `configs/stage_4_training/axolotl/README.md` with tokenizer compatibility guidance for Axolotl.

**Done when**:
- [x] File exists at `configs/stage_4_training/axolotl/README.md`
- [x] Documents 3 options: use base, add tokens, expand embeddings
- [x] Documents trade-offs for each option
- [x] Includes configuration examples

**Verify**:
```bash
cat configs/stage_4_training/axolotl/README.md | head -30  # Should show guidance
```

**Estimated time**: 15 minutes

---

