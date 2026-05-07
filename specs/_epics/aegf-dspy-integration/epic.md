---
name: aegf-dspy-integration
goal: Convert .example.yaml prompt templates into DSPy Signatures (Trajectory, Judge, Calibration, Hard Query) fixing 7 known source bugs. Define signatures ready for manual MIPROv2 optimization runs.
version: 1.0
date: 2026-04-26
status: complete
storyCount: 8
specs:
  - dspy-integration
---

# Epic: aegf-dspy-integration

## Epic Goal

Convert externalized `.example.yaml` prompt templates into DSPy Signatures with typed fields, fixing 7 known source bugs discovered during Epic 0. Enable MIPROv2 optimization on TrajectorySignature, JudgeSignature, CalibrationSignature, and Hard Query.

## BMAD Sources

| BMAD Document | Role in This Epic |
|---------------|-------------------|
| [epics.md](../../../_bmad-output/planning-artifacts/epics.md) | Story definitions (1.1-1.7), AC, dependencies |
| [aegf-3-layer-prd.md](../../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) | NFR-002 (Spearman > 0.8), NFR-007 (MIPROv2 compile) |
| [README.md](./README.md) | 7 known source bugs from prompt-externalization |
| [anchor-dataset epic.md](../aegf-infrastructure/epic.md) | Anchor dataset specs used as MIPROv2 bootstrap data |

### Story References

| Story | epics.md Reference | Epic 1 File |
|-------|-------------------|-------------|
| 1.1 TrajectorySignature | epics.md:328 | `src/factory/trajectory_signature.py` |
| 1.2a 4-turn structure | epics.md:350 | `src/factory/trajectory_generator.py` |
| 1.2b Backtracking | epics.md:379 | `src/factory/backtracking_detector.py` |
| 1.3 Integrate Trajectory | epics.md:402 | `src/factory/trajectory_generator.py` |
| 1.4 JudgeSignature | epics.md:421 | `src/audit/judge_signature.py` |
| 1.5 Integrate Judge | epics.md:443 | `src/audit/judge.py` |
| 1.6 CalibrationSignature | epics.md:461 | `src/audit/calibration_signature.py` |
| 1.7 Hard Query CoT | epics.md:483 | `src/factory/hard_query_builder.py` |

## Scope

### IN Scope

- 4 DSPy Signatures: TrajectorySignature, JudgeSignature, CalibrationSignature
- Hard Query ChainOfThought replacement
- 4-turn trajectory structure with tool_calls
- Backtracking detection
- Fix 7 known source bugs (typo, placeholder inconsistency, whitespace, parameter_target, forbidden_terms, dead code, protocol inconsistency)
- Spearman correlation > 0.8 with existing judge.py baseline
- MIPROv2 compile infrastructure setup (signatures defined, ready for manual runs)

### OUT of Scope

- Epic 2 (Dataset & Training Pipeline)
- Epic 3 (LangGraph State Machine)
- Actual MIPROv2 optimization runs (triggered manually after signatures defined)
- Production model deployment

## Dependencies

**Prerequisites (from Epic 0):**
- Spec 1: baseline-measurement (Spearman baseline exists)
- Spec 2: prompt-externalization (.example.yaml templates exist)
- Spec 3: anchor-dataset (50+ samples for MIPROv2 bootstrap)
- Spec 4: dependency-compatibility (dspy==3.2.0 installed)

**Execution Order:**
- 1.1 → 1.2a → 1.2b → 1.3 (trajectory pipeline chain)
- 1.4 → 1.5 (judge pipeline chain)
- 1.6 (calibration, independent of trajectory/judge)
- 1.7 (hard query, independent after 1.1 for DSPy reference)

## Interface Contracts

### TrajectorySignature
- **File:** `src/factory/trajectory_signature.py`
- **Input:** seed_id (str), mode (str), use_case (str), question (str), context (str), error_probability (float), has_error (bool), is_cascade (bool), tool_format (str)
- **Output:** turns_json (str), errors_json (str), messages_json (str), inferred_use_case (str)
- **Prompts:** from `src/factory/prompts_trajectory.example.yaml`

### JudgeSignature
- **File:** `src/audit/judge_signature.py`
- **Input:** exam_question (str), eval_criteria (str), target_patterns (str), baseline_response (str), adapter_response (str)
- **Output:** baseline (dict[str, float]), adapter (dict[str, float]), reasoning (str)
- **Prompts:** from `src/audit/prompts_judge.example.yaml`

### CalibrationSignature
- **File:** `src/audit/calibration_signature.py`
- **Input:** seed_id (str), use_case (str), category (str), context (str), parameter_target (list[str]), quality_target (float), min_quality (float), max_iterations (int)
- **Output:** best_profile_json (str), composite_score (float), reasoning (str), parameter_effectiveness (float)
- **Prompts:** from `src/audit/prompts_calibration.example.yaml`
- **parameter_target:** structured Signature field `list[str]`, NOT embedded in prompt text

### Hard Query
- **File:** `src/factory/hard_query_builder.py` (modified)
- **Input:** category (str), context (str)
- **Output:** abstract_objective (str) — English, generated via DSPy ChainOfThought

## Known Source Bugs (from Epic 0)

| # | Issue | Severity | Fix Story |
|---|-------|----------|-----------|
| 1 | Typo "Architecture architecture" in eval_prompts.yaml:10 | LOW | 1.4 |
| 2 | Calibration parameter_target stored as .system key | MEDIUM | 1.6 |
| 3 | $var vs {var} placeholder inconsistency | MEDIUM | 1.1 |
| 4 | </s> trailing space inconsistency in judge prompts | LOW | 1.4 |
| 5 | Python vs Jinja output protocol inconsistency | FALSE POSITIVE | None |
| 6 | Forbidden terms not documented for DSPy | MEDIUM | 1.7 |
| 7 | Dead code frontend_taxonomy_prompts.py | LOW | cleanup |

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| MIPROv2 needs anchor dataset to compile | HIGH | Spec 3 complete — 50 samples ready |
| Spearman regression > 0.8 boundary | HIGH | Verify after each Signature integration |
| DSPy 3.2.0 InputField/OutputField API changes | MEDIUM | Pin exact version, test early |
| prompt .example.yaml templates may have gaps | LOW | Catalog during research phase |
