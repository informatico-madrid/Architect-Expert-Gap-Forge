# Requirements: DSPy Integration

## Goal
Convert 4 `.example.yaml` prompt templates into DSPy Signatures (TrajectorySignature, JudgeSignature, CalibrationSignature) plus ChainOfThought for Hard Query. Fix 7 known source bugs. Enable MIPROv2 optimization by providing typed, compilable signatures.

## User Stories

### US-1: Define TrajectorySignature DSPy Signature
**As a** pipeline engineer
**I want to** replace hardcoded trajectory template strings with a typed `dspy.Signature`
**So that** MIPROv2 can optimize the trajectory prompt instructions

**Acceptance Criteria:**
- [ ] AC-1.1: Given the file `src/factory/trajectory_signature.py` exists when I create the signature, When I import `TrajectorySignature`, Then it is a valid `dspy.Signature` subclass with `InputField` and `OutputField` declarations
- [ ] AC-1.2: Given `TrajectorySignature`, When its output is produced, Then the output is directly compatible with `AgenticTrajectory` (Pydantic model at `src/factory/schema.py`): `seed_id` (str), `mode` (TrajectoryMode enum), `turns: list[Turn]`, `errors: list[SimulatedError]`, `use_case` (str), `messages: list[Message]`
- [ ] AC-1.3: Given the signature docstring, When I inspect the docstring, Then all text is in English (no Spanish)
- [ ] AC-1.4: Given the signature input fields, When I use `dspy.Predict(TrajectorySignature)`, Then the predictor accepts `seed_id`, `mode`, `use_case`, `turns`, `errors`, `messages` as input keys via the signature schema
- [ ] AC-1.5: Given the signature, When I check placeholder syntax in the docstring/instructions, Then only `{var}` Python str.format style is used (no `$var` Jinja style)

**Given** a DSPy Signature is defined in `src/factory/trajectory_signature.py`
**When** the signature is imported and validated
**Then** it passes Pydantic validation with all required fields matching `AgenticTrajectory` schema

---

### US-2: Implement 4-Turn Trajectory Structure in DSPy Predictor
**As a** trajectory pipeline consumer
**I want to** generate trajectories following the 4-turn pattern (Observation, Reasoning, Action, Error/Verify) using DSPy
**So that** the existing 4-turn structure is preserved while using typed signatures

**Acceptance Criteria:**
- [ ] AC-2.1: Given a `dspy.Predict(TrajectorySignature)` predictor, When called with seed data, Then it produces an `AgenticTrajectory` with exactly the field types defined in `src/factory/schema.py`
- [ ] AC-2.2: Given the trajectory output, When I inspect the turns, Then each turn is a `Turn` model instance with fields: `turn_index`, `turn_type` (TurnType enum), `content`, `tool_name`, `tool_args`, `tool_result`, `reasoning`
- [ ] AC-2.3: Given the trajectory output, When I inspect errors, Then each error is a `SimulatedError` model instance with fields: `error_type` (SimulatedErrorType enum), `turn_index`, `description`, `recovery_turn_index`
- [ ] AC-2.4: Given the trajectory output, When I inspect messages, Then messages are `Message` model instances (from `src/utils/schema.py`) in ChatML format
- [ ] AC-2.5: Given the trajectory generator, When called with `mode=TrajectoryMode.HARD_QUERY`, Then the first turn uses the hard query abstract objective (not observation template)

---

### US-3: Implement Backtracking Detection
**As a** curation pipeline engineer
**I want to** have a dedicated backtracking detector in `src/factory/backtracking_detector.py`
**So that** it can independently detect backtracking patterns in trajectories without coupling to trajectory generation

**Acceptance Criteria:**
- [ ] AC-3.1: Given a list of `Turn` objects in a trajectory, When `BacktrackingDetector.detect(turns)` is called, Then it returns a `BacktrackingResult` with `has_backtracking` (bool), `backtracking_turns` (list[int]), and `strategy` (str)
- [ ] AC-3.2: Given a trajectory with ERROR→CORRECT turns, When `detect` is called, Then `has_backtracking` is True and the error/correct turn indices are reported
- [ ] AC-3.3: Given a trajectory with only O→R→A→V turns (no error/correct), When `detect` is called, Then `has_backtracking` is False
- [ ] AC-3.4: Given the detector module, When I import it, Then it does NOT import `dspy` (it is a pure utility, independent of DSPy)
- [ ] AC-3.5: Given the detector, When I check the API, Then it has `detect(turns)` and optionally `detect_from_messages(messages)` methods

---

### US-4: Integrate TrajectorySignature into Factory Pipeline
**As a** factory pipeline consumer
**I want to** use the TrajectorySignature predictor in `trajectory_generator.py` instead of hardcoded templates
**So that** the factory pipeline uses typed DSPy outputs

**Acceptance Criteria:**
- [ ] AC-4.1: Given `src/factory/trajectory_generator.py`, When `TrajectoryGenerator.generate(seed_data)` is called, Then it returns an `AgenticTrajectory` instance (unchanged return type)
- [ ] AC-4.2: Given the trajectory generator, When `mode=TrajectoryMode.EXPLICIT`, Then it uses `TrajectorySignature` via `dspy.Predict(TrajectorySignature)` to produce the output
- [ ] AC-4.3: Given the trajectory generator, When templates_path YAML is provided, Then the signature loads instructions from the YAML file at runtime (via `with_instructions()`)
- [ ] AC-4.4: Given existing unit tests for `TrajectoryGenerator`, When they run, Then they all pass (no regression)
- [ ] AC-4.5: Given the generator, When called with the same seed data, Then the output structure is byte-identical to pre-refactor (refactor only, no behavior change)

---

### US-5: Define JudgeSignature DSPy Signature
**As a** judge evaluation engineer
**I want to** replace the hardcoded judge prompt template in `eval_prompts.yaml` with a typed `dspy.Signature`
**So that** the judge scoring can be compiled and optimized by MIPROv2

**Acceptance Criteria:**
- [ ] AC-5.1: Given the file `src/audit/judge_signature.py` exists when I create the signature, When I import `JudgeSignature`, Then it is a valid `dspy.Signature` with InputField and OutputField declarations
- [ ] AC-5.2: Given `JudgeSignature`, When its output is produced, Then the output matches `NormalizedJudgeResponse` TypedDict: `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`
- [ ] AC-5.3: Given the signature docstring, When I inspect the docstring, Then "Architecture architecture" typo from bug #1 is fixed to "Architecture 2026"
- [ ] AC-5.4: Given the signature, When I check placeholder syntax in the docstring/instructions, Then only `{var}` style is used (no `$var`)
- [ ] AC-5.5: Given the signature output fields, When I validate them, Then each dimension score in `baseline` and `adapter` dicts is typed as `float` with constraint 0.0 <= score <= 1.0
- [ ] AC-5.6: Given the signature docstring, Then all content is in English

---

### US-6: Integrate JudgeSignature into Audit Pipeline
**As a** audit pipeline consumer
**I want to** use the JudgeSignature predictor in `src/audit/judge.py` instead of raw prompt templates
**So that** the judge scoring uses typed DSPy outputs

**Acceptance Criteria:**
- [ ] AC-6.1: Given `src/audit/judge.py`, When `llm_judge_score(exam, baseline_resp, adapter_resp, ...)` is called, Then it returns a `NormalizedJudgeResponse` TypedDict (unchanged return type)
- [ ] AC-6.2: Given the judge function, When called with valid inputs, Then it uses `dspy.Predict(JudgeSignature)` to produce structured output
- [ ] AC-6.3: Given the judge function, When the LM produces output, Then JSON parsing and normalization via `normalize_judge_response()` still works correctly
- [ ] AC-6.4: Given existing unit tests for the judge module, When they run, Then they all pass (no regression)
- [ ] AC-6.5: Given Spearman correlation between old and new judge.py outputs, When I compute it on the same inputs, Then correlation > 0.8

---

### US-7: Define CalibrationSignature DSPy Signature
**As a** calibration pipeline engineer
**I want to** define a `dspy.Signature` for the calibration parameter optimization process
**So that** MIPROv2 can optimize calibration prompt instructions

**Acceptance Criteria:**
- [ ] AC-7.1: Given the file `src/audit/calibration_signature.py` exists when I create the signature, When I import `CalibrationSignature`, Then it is a valid `dspy.Signature` with InputField and OutputField declarations
- [ ] AC-7.2: Given `CalibrationSignature`, When its input fields are defined, Then `parameter_target` (list[str]) is a structured Signature field, NOT embedded in system prompt text (bug #2 fix)
- [ ] AC-7.3: Given `CalibrationSignature`, When its output fields are defined, Then the signature models the optimization process (grid search → best params), not direct parameter mapping
- [ ] AC-7.4: Given the signature output, Then it produces results compatible with `CalibrationResult` dataclass: `profile` (SamplingProfile), `judge_scores`, `composite_score`, `adjusted_score`
- [ ] AC-7.5: Given the signature docstring, When I check placeholder syntax, Then only `{var}` style is used (no `$var`)

---

### US-8: Replace Hard Query Mappings with ChainOfThought
**As a** hard query pipeline engineer
**I want to** replace the hardcoded Spanish category→objective mapping in `HardQueryBuilder._transform_to_abstract()` with `dspy.ChainOfThought`
**So that** the mapping is learned and optimized rather than hardcoded

**Acceptance Criteria:**
- [ ] AC-8.1: Given `src/factory/hard_query_builder.py`, When `HardQueryBuilder.build(seed_data)` is called, Then it returns an abstract objective string (unchanged return type)
- [ ] AC-8.2: Given `HardQueryBuilder`, When `mode=TrajectoryMode.HARD_QUERY`, Then it uses `dspy.ChainOfThought("category, context -> abstract_objective")` instead of the hardcoded if/else mapping
- [ ] AC-8.3: Given the hard query builder, When I check for Spanish text in the code, Then only the forbidden terms list contains Spanish (literal match strings) and all other text is in English
- [ ] AC-8.4: Given the forbidden terms list, When I check for documentation, Then there is a DSPy comment explaining these are literal match strings, NOT translatable prompt content
- [ ] AC-8.5: Given `validate_prompt()` method, When it checks for forbidden terms, Then it does exact literal match against the forbidden terms list

## Functional Requirements

| ID | Requirement | Priority | Verification Command |
|----|-------------|----------|---------------------|
| FR-001 | Define `TrajectorySignature` in `src/factory/trajectory_signature.py` with typed InputField/OutputField matching `AgenticTrajectory` Pydantic model output schema | High | `python -c "from src.factory.trajectory_signature import TrajectorySignature; print(TrajectorySignature.output_fields)"` |
| FR-002 | Define `JudgeSignature` in `src/audit/judge_signature.py` with OutputField matching `NormalizedJudgeResponse` TypedDict (`baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`) | High | `python -c "from src.audit.judge_signature import JudgeSignature; print(JudgeSignature.output_fields)"` |
| FR-003 | Define `CalibrationSignature` in `src/audit/calibration_signature.py` with `parameter_target` as structured InputField (not in system text) and output modeling optimization process | High | `python -c "from src.audit.calibration_signature import CalibrationSignature; print(CalibrationSignature.input_fields); print(CalibrationSignature.output_fields)"` |
| FR-004 | Replace hardcoded `_transform_to_abstract()` method in `HardQueryBuilder` with `dspy.ChainOfThought("category, context -> abstract_objective")` | High | `python -c "from src.factory.hard_query_builder import HardQueryBuilder; import inspect; src = inspect.getsource(HardQueryBuilder._transform_to_abstract); assert 'dspy' in src, 'ChainOfThought not found'"` |
| FR-005 | Create `BacktrackingDetector` class in `src/factory/backtracking_detector.py` with `detect(turns) -> tuple[str, list[int], str]` | High | `python -c "from src.factory.backtracking_detector import BacktrackingDetector; print('OK')"` |
| FR-006 | Integrate `TrajectorySignature` into `src/factory/trajectory_generator.py` — `generate()` still returns `AgenticTrajectory` unchanged | High | `python -m pytest tests/factory/test_trajectory_generator.py -v --tb=short` |
| FR-007 | Integrate `JudgeSignature` into `src/audit/judge.py` — `llm_judge_score()` still returns `NormalizedJudgeResponse` unchanged | High | `python -m pytest tests/test_audit_judge_submodule.py -v --tb=short` |
| FR-008 | Fix "Architecture architecture" typo in JudgeSignature docstring (bug #1) | Low | `python -c "from src.audit.judge_signature import JudgeSignature; assert 'Architecture architecture' not in JudgeSignature.__doc__"` |
| FR-009 | Delete dead code file `src/export/frontend_taxonomy_prompts.py` (bug #7, 0 imports verified) | Low | `python -c "import ast; import sys; refs = ast.parse(open('src/export/frontend_taxonomy_prompts.py').read()); sys.exit(0)"` + grep for imports |
| FR-010 | Standardize all signature docstrings to use `{var}` placeholder syntax, not `$var` (bug #3) | Medium | `grep -rn '\$var' src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py; exit 1` (should find nothing) |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-001 | Judge output correlation with existing baseline | Spearman rank correlation between old `judge.py` and new `JudgeSignature` outputs on same inputs | > 0.8 |
| NFR-002 | Language compliance | All Signature docstrings and instructions in English | 0 Spanish text (except forbidden terms literal match strings) |
| NFR-003 | Behavioral invariance | Refactoring only — no change to production behavior | Output structure identical pre/post refactor |

## Glossary
- **DSPy Signature**: A typed schema definition (`dspy.Signature`) that specifies InputField/OutputField declarations for LLM programs
- **MIPROv2**: DSPy's meta-prompt instruction optimization using bootstrap demos and Bayesian optimization
- **ChainOfThought**: A DSPy module (`dspy.ChainOfThought`) that adds a reasoning step between input and output fields
- **AgenticTrajectory**: Pydantic model in `src/factory/schema.py` representing a multi-turn agentic interaction
- **NormalizedJudgeResponse**: TypedDict in `src/audit/schema.py` representing structured judge scoring output
- **CalibrationResult**: Frozen dataclass in `src/audit/calibration_schema.py` for single calibration iteration
- **Backtracking**: The pattern ERROR→CORRECT→VERIFY in trajectory turns indicating the model detected and fixed its own error
- **parameter_target**: Structured field (list[str]) specifying which sampling parameters a calibration prompt tests
- **Hard Query**: A query abstraction that describes a goal without mentioning specific tools or implementation patterns

## Out of Scope
- MIPROv2 compilation script or automation (manual trigger post-signature-definition)
- Anchor dataset loading pipeline (provided by anchor-dataset spec)
- DSPy LM configuration (handled by existing inference router)
- New trajectory turn types beyond the existing 6 (observation, reasoning, action, error, correct, verify)
- Judge scoring rubric changes (rubric stays the same, only prompt delivery changes)
- Calibration grid search algorithm changes (grid search stays brute-force Cartesian product)
- Any changes to backtracking configuration parameters (BacktrackingConfig dataclass unchanged)

## Dependencies
- `dspy==3.2.0` (pinned in requirements.txt, installed in venv)
- `pydantic>=2.0` (installed in venv, via dspy and src/factory/schema.py)
- Anchor dataset (50 samples) — provided by anchor-dataset spec
- Existing `AgenticTrajectory` Pydantic model — must not be modified
- Existing `NormalizedJudgeResponse` TypedDict — must not be modified
- Existing `SamplingProfile` / `CalibrationResult` dataclasses — must not be modified
- Existing `TrajectoryMode` enum — must not be modified
- `src/factory/trajectory_generator.py` — must remain backward compatible
- `src/audit/judge.py` — must remain backward compatible
- `src/factory/hard_query_builder.py` — must remain backward compatible

## Success Criteria
- [ ] All 8 user stories implemented and passing acceptance criteria
- [ ] Spearman correlation > 0.8 between old and new judge outputs
- [ ] No test regressions in existing test suites (trajectory_generator, judge)
- [ ] 7 source bugs fixed (5 actionable + 1 false positive confirmed + 1 dead code deleted)
- [ ] `ruff check` and `ruff format --check` pass on changed files
- [ ] `pyright` type checking passes on new signature files

## Verification Contract

**Project type**: `fullstack`

**Entry points**:
- `src/factory/trajectory_signature.py` — new file, `TrajectorySignature` class
- `src/factory/trajectory_generator.py` — modified, imports `TrajectorySignature`
- `src/factory/backtracking_detector.py` — new file, `BacktrackingDetector` class
- `src/audit/judge_signature.py` — new file, `JudgeSignature` class
- `src/audit/judge.py` — modified, imports `JudgeSignature`
- `src/audit/calibration_signature.py` — new file, `CalibrationSignature` class
- `src/factory/hard_query_builder.py` — modified, uses `dspy.ChainOfThought`
- `src/export/frontend_taxonomy_prompts.py` — deleted (dead code)

**Observable signals**:
- PASS: `python -c "from src.factory.trajectory_signature import TrajectorySignature"` imports successfully
- PASS: `python -c "from src.audit.judge_signature import JudgeSignature"` imports successfully
- PASS: `python -c "from src.audit.calibration_signature import CalibrationSignature"` imports successfully
- PASS: `python -c "from src.factory.backtracking_detector import BacktrackingDetector"` imports successfully
- PASS: Existing unit tests `tests/factory/test_trajectory_generator.py` and `tests/test_audit_judge_submodule.py` pass
- PASS: `TrajectoryGenerator.generate()` returns `AgenticTrajectory` instance (same as before)
- PASS: `llm_judge_score()` returns `NormalizedJudgeResponse` TypedDict (same as before)
- PASS: `HardQueryBuilder.build()` returns abstract objective string (same as before)
- FAIL: Import fails → signature file has syntax error or missing dspy import
- FAIL: `generate()` returns different structure → refactor introduced behavior change
- FAIL: Spearman correlation <= 0.8 → judge output drifted beyond threshold
- FAIL: `grep '\$var' src/factory/trajectory_signature.py` finds matches → placeholder syntax not standardized

**Hard invariants**:
- `AgenticTrajectory` Pydantic model schema unchanged (fields: seed_id, mode, turns, errors, use_case, messages)
- `NormalizedJudgeResponse` TypedDict unchanged (keys: baseline, adapter, reasoning)
- `SamplingProfile`, `CalibrationResult`, `CalibrationReport` dataclasses unchanged
- `TrajectoryMode` enum values unchanged (hard_query, explicit, no_call)
- `TurnType` enum values unchanged (observation, reasoning, action, error, correct, verify)
- `SimulatedErrorType` enum values unchanged (tool_failure, wrong_result, cascade_failure)
- Existing `BacktrackingConfig` dataclass unchanged
- No new runtime dependencies beyond dspy, pydantic, yaml (already present)
- Auth/session validation not affected (no auth code in scope)

**Seed data**:
- Anchor dataset: 50 samples at `datasets/anchors/v1/` (provided by anchor-dataset spec)
- At least 1 seed with mode=HARD_QUERY for testing ChainOfThought replacement
- At least 1 seed with error injection (error_probability > 0) for testing backtracking detection
- Judge evaluation samples with baseline/adapter responses for Spearman correlation test

**Dependency map**:
- `src/factory/schema.py` — AgenticTrajectory, Turn, SimulatedError, TurnType, TrajectoryMode, SimulatedErrorType (used by trajectory signature)
- `src/audit/schema.py` — NormalizedJudgeResponse TypedDict (used by judge signature)
- `src/audit/calibration_schema.py` — SamplingProfile, CalibrationResult, CalibrationPrompt (used by calibration signature)
- `src/utils/schema.py` — Message model (used by trajectory messages)
- `src/factory/trajectory_generator.py` — consumer of TrajectorySignature, producer of AgenticTrajectory
- `src/audit/judge.py` — consumer of JudgeSignature, producer of NormalizedJudgeResponse
- `src/factory/hard_query_builder.py` — consumer of ChainOfThought module
- `src/curation/backtracking_helpers.py` — related to backtracking (independent of new detector)
- `src/curation/backtracking_config.py` — configuration (not modified)

**Escalate if**:
- Spearman correlation drops below 0.8 despite signature changes — may indicate fundamental prompt drift, not just refactor
- DSPy 3.2.0 API differs from documented behavior on typed OutputField with dict[str, float] — may need fallback to str output + JSON parsing
- Anchor dataset format incompatible with `dspy.Example(**row).with_inputs()` — may need conversion utility
- `dspy.ChainOfThought` adds unexpected `reasoning` field that breaks HardQueryBuilder return type — may need wrapper
- Removing `frontend_taxonomy_prompts.py` breaks any import chain — verify 0-import claim with `grep -r frontend_taxonomy_prompts src/`

## Unresolved Questions
- Where should `with_instructions()` load the YAML prompt content? Each consumer or a shared loader module?
- Should the backtracking detector be in `src/factory/` or `src/curation/` given existing backtracking code is in curation/
- Does MIPROv2 compilation require a separate script or can it be done inline in existing test infrastructure?

## Next Steps
1. Define `TrajectorySignature` in `src/factory/trajectory_signature.py` (US-1)
2. Integrate `TrajectorySignature` into `src/factory/trajectory_generator.py` (US-4)
3. Define `JudgeSignature` in `src/audit/judge_signature.py` (US-5)
4. Integrate `JudgeSignature` into `src/audit/judge.py` (US-6)
5. Define `CalibrationSignature` in `src/audit/calibration_signature.py` (US-7)
6. Replace hardcoded mapping with `dspy.ChainOfThought` in `HardQueryBuilder` (US-8)
7. Create `BacktrackingDetector` in `src/factory/backtracking_detector.py` (US-3)
8. Fix all 7 source bugs (bugs #1-#6, #7 delete dead code)
9. Run Spearman correlation test between old and new judge outputs
10. Run full test suite to verify no regressions
