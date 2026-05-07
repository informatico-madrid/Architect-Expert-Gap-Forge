# Research: dspy-integration

## Executive Summary

Epic 1 converts 4 `.example.yaml` prompt templates into DSPy Signatures with typed fields, fixing 7 known source bugs discovered during Epic 0. All 7 bugs are verified in the codebase: 5 are actionable (2 MEDIUM: parameter_target in .system key, $var vs {var} inconsistency, Spanish forbidden terms undocumented; 3 LOW: typo, whitespace inconsistency, dead code), 1 is confirmed false positive. DSPy 3.2.0 supports typed InputField/OutputField via Pydantic, MIPROv2 compiles with bootstrap demos, and ChainOfThought replaces hardcoded mappings. Anchor dataset (50 samples) and all prerequisites from Epic 0 are complete.

**Feasibility: High** | **Risk: Medium** (Spearman regression boundary at 0.8, interface contract mismatches with epic.md) | **Effort: L** (8 stories, ~600-1000 LOC)

## External Research

### DSPy 3.2.0 Signature API

#### InputField/OutputField with Typed Fields
- InputField/OutputField delegate to `pydantic.Field`
- Type annotations (`int`, `float`, `list[str]`, `Optional[str]`) are preserved
- Outputs must be parsable — complex nested structures should use `str` with JSON parsing
- Constraints like `ge`/`le` work via Pydantic field constraints
- **Decision**: Use typed outputs for simple primitives (gives MIPROv2 clearer optimization targets)

#### Prompt Attachment
- Docstring = default instructions for a signature
- Use `Signature.with_instructions("new text")` to override (returns new class, no mutation)
- **No built-in `.example.yaml` loader** — must load manually via `yaml.safe_load()` + `dspy.Example(**row).with_inputs(*keys)`
- Few-shot demos live on predictors (`predictor.demos`), NOT on signatures

#### MIPROv2 Compilation
- Three phases: bootstrap demos → grounded instruction proposal → Bayesian optimization (Optuna)
- Key params: `max_bootstrapped_demos`, `max_labeled_demos`, `auto="light"/"medium"/"heavy"`
- The compiled program has optimized instructions and demos embedded on its predictors
- **Decision**: MIPROv2 is NOT part of this spec's implementation. Signatures must be defined; compilation is a manual trigger after signatures are correct.

#### ChainOfThought
- It's a module class, not a decorator
- Usage: `dspy.ChainOfThought(MySignature)` or `dspy.ChainOfThought("question -> answer")`
- Prepends a `reasoning` field between inputs and outputs
- **Decision**: Story 1.7 uses `dspy.ChainOfThought("category -> abstract_objective")` to replace hardcoded Spanish mappings

#### DSPy 3.2.0 API Changes (from 3.1)
- `requires_permission_to_run` removed (raising error if True)
- `new_signature` kwarg removed from Predict
- LM config must use `dspy.LM()` not plain string

#### DSPy Version Verification
- **Confirmed**: `dspy==3.2.0` pinned in `requirements.txt` AND installed in venv
- Source: `requirements.txt` + `pip show dspy` confirms version 3.2.0
- API claims in this research are verified against DSPy 3.2.0 source

### DSPy Signatures — Best Practices

1. **Structured typed outputs** over raw dicts — MIPROv2 optimizes clearer targets
2. **Externalized prompts** loaded from YAML, not embedded in code
3. **Few-shot demos** from anchor dataset, attached to predictors at runtime
4. **Docstring instructions** should be concise; long prompts in YAML
5. **Input validation** via Pydantic constraints (min/max for floats, regex for strings)
6. **ChainOfThought** is the default pattern for "thinking" tasks (hard query, calibration)

### Pitfalls to Avoid

- Don't store metadata (like `parameter_target`) as prompt text — use structured Signature fields
- Don't use `$var` syntax — match existing `trajectory_generator.py` convention of `{var}` (Python `str.format`)
- Don't embed DSPy Signatures in files that also contain business logic — keep them clean
- Don't run MIPROv2 compilation in this spec — signatures first, compile later manually

## Codebase Analysis

### Verified Interface Contracts (CORRECTED)

The epic.md lists incorrect output fields for signatures. Here are the actual types consumed by downstream code:

| Story | epic.md Claim | Actual Code | Discrepancy |
|-------|--------------|-------------|-------------|
| 1.1 TrajectorySignature | `trajectory (str), tool_usage_patterns (list[str])` | `AgenticTrajectory` (Pydantic model): `seed_id`, `mode`, `turns: list[Turn]`, `errors: list[SimulatedError]`, `use_case`, `messages: list[Message]` | **Critical** — no `tool_usage_patterns` exists in codebase |
| 1.4 JudgeSignature | `coherence (float), overall (float)` | `NormalizedJudgeResponse` (TypedDict): `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str` | **Critical** — no `coherence`/`overall` fields |
| 1.6 CalibrationSignature | Direct parameter→output mapping | `calibration.py` uses brute-force grid search, not direct mapping | **Significant** — signature must model optimization process, not direct mapping |
| 1.7 Hard Query | `category → abstract_objective` | `HardQueryBuilder` uses hardcoded dict mapping | **Matches** — but needs ChainOfThought replacement |

**Decision for requirements**: Each Signature output type must match the consumer data structure. New DSPy output fields must either map to existing types or replace them. The epic.md interface contracts must be updated.

### Existing Patterns

| Pattern | Source | Relevance |
|---------|--------|-----------|
| YAML prompt loading | `src/factory/prompt_builder.py` `_TAX` dict, `yaml.safe_load()` | Template for Signature prompt loading |
| Trajectory generation | `src/factory/trajectory_generator.py` — 4-turn structure with tool_calls | To be replaced by TrajectorySignature |
| Judge evaluation | `src/audit/judge.py` — `PromptManager` loading `eval_prompts.yaml` | To be replaced by JudgeSignature |
| Calibration grid search | `src/audit/calibration.py` — brute-force parameter grid | To be replaced by CalibrationSignature |
| Hard query mapping | `src/factory/hard_query_builder.py` — hardcoded Spanish category→objective mapping | To be replaced by ChainOfThought |
| Example.yaml templates | `src/factory/prompts_*.example.yaml`, `src/audit/prompts_*.example.yaml` | Source of truth for DSPy prompt content |

### Dependencies

| Dependency | Version | Source |
|------------|---------|--------|
| `dspy` | 3.2.0 (pinned) | `requirements.txt` (Spec 4) |
| `pydantic` | via dspy | Runtime dep |
| `yaml` (PyYAML) | existing | Already in requirements |
| Anchor dataset | 50 samples | `datasets/anchors/v1/` (Spec 3) |

### Constraints

1. **Spearman correlation > 0.8** — new signatures must not regress below existing judge.py baseline
2. **Prompts in English** — all DSPy Signatures must use English (not Spanish) per Epic 0 externalization
3. **4-turn trajectory structure** must be preserved (not broken by Signature redefinition)
4. **Backtracking detection** must work independently of the Signature
5. **No production behavior change** — refactor only, no new features

### Verified Source Bugs

| # | Issue | Verified Location | Fix Approach |
|---|-------|-------------------|-------------|
| 1 | Typo "Architecture architecture" | `eval_prompts.yaml:12`, `prompts_judge.example.yaml:10` | Fix in JudgeSignature docstring |
| 2 | `parameter_target` as .system text | `prompts_calibration.example.yaml:8-9` | Store as structured CalibrationSignature field |
| 3 | `$var` vs `{var}` inconsistency | `prompt_builder.py:116` ($var), `trajectory_generator.py:217` ({var}) | Standardize on `{var}` in DSPy Signatures |
| 4 | Whitespace before `</s>`/`</think>` | `prompts_taxonomy.yaml:526` (7 spaces), `prompts_taxonomy.example.yaml:58` (9 spaces) | Normalize in Signature docstrings |
| 5 | Python vs Jinja output protocol | FALSE POSITIVE — both use identical format | No fix |
| 6 | Spanish forbidden terms undocumented | `hard_query_builder.py:79,80` | Add DSPy comment: literal match strings |
| 7 | Dead code | `src/export/frontend_taxonomy_prompts.py` — 0 imports | Delete file |

## Related Specs

| Spec | Relevance | Relationship |
|------|-----------|--------------|
| baseline-measurement | Baseline Spearman scores exist | Must verify no regression after Signature changes |
| prompt-externalization | .example.yaml templates are source | Signatures consume these templates |
| anchor-dataset | 50 samples for MIPROv2 bootstrap | Datasets provide few-shot demos |
| dependency-compatibility | dspy==3.2.0 installed | Prerequisite for imports |

## Quality Commands

| Type | Command |
|------|---------|
| Lint | `ruff check infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py src/factory/ src/audit/` |
| Format | `ruff format --check src/factory/ src/audit/` |
| Types | `pyright src/factory/ src/audit/ --pythonversion 3.12` |
| Tests | `python -m pytest tests/unit/ tests/integration/test_pipeline.py -v --tb=short` |

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|-----------|-------|
| DSPy 3.2.0 stability | High | Mature API, typed fields well-supported |
| Anchor dataset readiness | High | 50 samples ready for bootstrap demos |
| Spearman regression risk | Medium | Boundary at 0.8; must verify after each Signature |
| Source bug fixes | High | All 7 bugs are well-documented and localized |
| Integration complexity | Medium | 3 pipeline chains (trajectory, judge, calibration) + 1 independent (hard query) |
| Dead code removal | High | Single file, 0 imports |

## Recommendations for Requirements

1. **FR-001**: Define TrajectorySignature — output must produce data compatible with `AgenticTrajectory` model (`turns`, `errors`, `messages`) — NOT the `tool_usage_patterns` claimed in epic.md
2. **FR-002**: Define JudgeSignature — output must match `NormalizedJudgeResponse` (`baseline`, `adapter`, `reasoning`) — NOT the `coherence/overall` claimed in epic.md; fix "Architecture architecture" typo
3. **FR-003**: Define CalibrationSignature — model optimization process (grid search → best params), NOT direct parameter mapping; store `parameter_target` as structured Signature field
4. **FR-004**: Replace `hard_query_builder.py` hardcoded mappings with `dspy.ChainOfThought("category -> abstract_objective")`; add comment documenting Spanish forbidden terms as literal match strings
5. **FR-005**: Standardize on `{var}` placeholder syntax across all signature docstrings (not `$var`)
6. **FR-006**: Create backtracking detector (`src/factory/backtracking_detector.py`); must preserve existing backtracking prompt integration from `src/curation/prompts_backtracking.example.yaml`
7. **FR-007**: Remove dead code `src/export/frontend_taxonomy_prompts.py` (0 imports, verified)
8. **FR-008**: Add test infrastructure: mock LM provider for unit tests, anchor dataset fixtures for integration tests, baseline comparison harness for Spearman > 0.8
9. **NFR-001**: Spearman correlation > 0.8 with existing judge.py baseline — verified using same inputs to both old and new code, compute Spearman on normalized outputs
10. **NFR-002**: All prompts in English (no Spanish in Signature docstrings); except forbidden terms which are literal match strings

### Architectural Decisions for Requirements

- **YAML loading**: Signatures are pure Python (typed fields + docstrings). YAML loading happens at runtime in consumers or a shared loader.
- **Signature registration**: No central registry required; each consumer imports from its signature file directly.
- **Test strategy**: Unit tests verify schema (Pydantic validation, field types). Integration tests use mock LM. No real API calls in tests.

## Open Questions

1. **MIPROv2 compilation scope**: Should this spec include a script to trigger MIPROv2 compilation, or is that Epic 2?
   - Decision: Out of scope. Signatures defined; compilation is manual post-spec trigger.

2. **Few-shot demo format**: Anchor dataset JSONL format — how to convert to `dspy.Example` objects?
   - Research answer: `dspy.Example(**row).with_inputs(*input_keys)` — straightforward mapping.

3. **Backtracking detector**: Should it be its own file or integrated into trajectory_generator.py?
   - Requirements doc says: separate file `src/factory/backtracking_detector.py`.
   - Note: Existing backtracking prompt is at `src/curation/prompts_backtracking.example.yaml` — the detector file location (factory vs curation) is an architectural decision.

4. **YAML prompt loading architecture**: Where do signatures load their prompts?
   - Options: (A) Each signature loads its own YAML at module level; (B) Shared loader module; (C) Consumers load YAML and pass to predictors at runtime.
   - Decision: Option C is cleanest for testability (consumers/loaders know which YAML to use; signatures stay pure Python). Signatures receive prompts via `with_instructions()`.

5. **DSPy Signature output vs consumer data structures**: epic.md claims TrajectorySignature outputs `tool_usage_patterns` and JudgeSignature outputs `coherence/overall` — neither exists in codebase.
   - Decision: Requirements must define signature output types that match `AgenticTrajectory`, `NormalizedJudgeResponse`, and the calibration optimization process. Interface contracts in epic.md must be updated.

6. **DSPy module vs Signature distinction**: Signatures define schema; predictors (`dspy.Predict(sig)`, `dspy.ChainOfThought(sig)`) are what you call at runtime.
   - Decision: Stories should reference predictors, not just signatures. The Signature defines schema; the Predictor does the work.

## Sources

### Web Research
- Context7: DSPy documentation (dspy repo)
- Web search: DSPy 3.2.0 changelog and API reference
- DSPy 3.2.0 PyPI release notes

### Codebase Files
- `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml`
- `configs/stage_5_evaluation/eval_prompts.yaml`
- `configs/stage_6_calibration/calibration_prompts.yaml`
- `src/factory/prompt_builder.py`
- `src/factory/trajectory_generator.py`
- `src/factory/hard_query_builder.py`
- `src/audit/judge.py`
- `src/audit/calibration.py`
- `src/factory/prompts_trajectory.example.yaml`
- `src/factory/prompts_hard_query.example.yaml`
- `src/factory/prompts_taxonomy.example.yaml`
- `src/audit/prompts_judge.example.yaml`
- `src/audit/prompts_calibration.example.yaml`
- `src/export/frontend_taxonomy_prompts.py` (dead code)
- `requirements.txt` (dspy==3.2.0)
- `specs/_epics/aegf-dspy-integration/README.md` (7 bugs)
- `specs/_epics/aegf-dspy-integration/epic.md` (spec scope)

## T4.2 Confirmation — Bug #5 (2026-04-27)

Confirmed: Python vs Jinja output protocol is a false positive. Both `build_user_nominal()` (Python path) and `build_user_nominal_jinja()` (Jinja path) use the same `_render()` function with identical substitution dicts (`context`, `virtual_filename`, `name`, `skeleton`). The only difference is the YAML template key. Output format is identical.
