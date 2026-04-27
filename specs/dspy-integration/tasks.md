# Tasks: DSPy Integration (dspy-integration)

**Spec Goal**: Convert 4 `.example.yaml` prompt templates into DSPy Signatures (TrajectorySignature, JudgeSignature, CalibrationSignature) plus ChainOfThought for Hard Query. Fix 7 known source bugs.

**Workflow**: POC-first — define signatures and test schemas first, then integrate into consumers, then test, then quality.

**Total Tasks**: ~55 (fine granularity for parallelism)

**DSPy Version**: 3.2.0 (pinned, verified importable)

---

## Phase 1: POC — Define Signatures and Test Schemas

*Prove the core idea works: define all 3 DSPy Signatures + ChainOfThought, validate field types, verify Pydantic schema compatibility.*

### T1.1: Scaffold TrajectorySignature file [x]
**Do:**
1. Create `src/factory/trajectory_signature.py`
2. Add module docstring with SPDX header and brief description
3. Import `dspy`, `str | None`, `float`, `list` from typing
4. Define `TrajectorySignature(dspy.Signature)` with clear `__doc__`
5. Define input fields: `seed_id: str`, `mode: str`, `use_case: str`, `question: str`, `context: str`, `error_probability: float`, `has_error: bool`, `is_cascade: bool`, `tool_format: str`
6. Define output fields: `turns_json: str`, `errors_json: str`, `messages_json: str`, `use_case: str`
7. Write a concise docstring in English summarizing the trajectory generation purpose
8. Verify import succeeds: `python -c "from src.factory.trajectory_signature import TrajectorySignature; print(TrajectorySignature.input_fields); print(TrajectorySignature.output_fields)"`

**Files:** Created: `src/factory/trajectory_signature.py`
**Done when:** Module imports successfully; `input_fields` has 9 fields; `output_fields` has 4 fields with correct types
**Verify:** `python -c "from src.factory.trajectory_signature import TrajectorySignature; print(len(TrajectorySignature.input_fields))"`
**Commit:** `feat(dspy): scaffold TrajectorySignature with typed fields`

---

### T1.2: Define TrajectorySignature docstring from source template [x]
**Do:**
1. Read `src/factory/prompts_trajectory.example.yaml` to extract prompt content
2. Write docstring that captures the instruction for trajectory generation
3. Ensure all `{var}` placeholders use Python str.format syntax (no `$var`)
4. Ensure all text is in English (no Spanish)
5. Verify with `python -c "from src.factory.trajectory_signature import TrajectorySignature; assert '\$' not in TrajectorySignature.__doc__"`
6. Verify no Spanish words in docstring

**Files:** Modified: `src/factory/trajectory_signature.py`
**Done when:** Docstring contains English instructions; uses only `{var}` placeholders
**Verify:** `grep -c '\$' src/factory/trajectory_signature.py` returns 0
**Commit:** `feat(dspy): add TrajectorySignature docstring from prompt template`

---

### T1.3: Scaffold JudgeSignature file [x]
**Do:**
1. Create `src/audit/judge_signature.py`
2. Add module docstring with SPDX header and brief description
3. Import `dspy`, `dict`, `str`, `float` from typing
4. Define `JudgeSignature(dspy.Signature)` with typed InputField/OutputField
5. Define input fields: `exam_question: str`, `eval_criteria: str`, `target_patterns: str`, `baseline_response: str`, `adapter_response: str`
6. Define output fields: `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`
7. Verify import and field inspection

**Files:** Created: `src/audit/judge_signature.py`
**Done when:** Module imports; output fields match `NormalizedJudgeResponse` TypedDict structure
**Verify:** `python -c "from src.audit.judge_signature import JudgeSignature; print(JudgeSignature.output_fields)"`
**Commit:** `feat(dspy): scaffold JudgeSignature with typed fields matching NormalizedJudgeResponse`

---

### T1.4: Define JudgeSignature docstring with bug #1 fix [x]
**Do:**
1. Read `src/audit/prompts_judge.example.yaml` to extract the `professor_judge` section
2. Write the signature docstring from the system prompt content
3. **Bug fix #1**: Replace "Architecture architecture" with "Architecture 2026"
4. Ensure all text is in English
5. Ensure `{var}` placeholder syntax throughout
6. Verify: `python -c "from src.audit.judge_signature import JudgeSignature; assert 'Architecture architecture' not in JudgeSignature.__doc__"`

**Files:** Modified: `src/audit/judge_signature.py`
**Done when:** Docstring contains corrected "Architecture 2026" text; no "Architecture architecture" typo
**Verify:** `python -c "from src.audit.judge_signature import JudgeSignature; assert 'Architecture architecture' not in JudgeSignature.__doc__"`
**Commit:** `fix(dspy): fix "Architecture architecture" typo in JudgeSignature docstring (bug #1)`

---

### T1.5: Scaffold CalibrationSignature file [x]
**Do:**
1. Create `src/audit/calibration_signature.py`
2. Add module docstring with SPDX header and brief description
3. Import `dspy`, `list`, `str`, `float`, `dict` from typing
4. Define `CalibrationSignature(dspy.Signature)` with typed InputField/OutputField
5. Define input fields:
   - `parameter_target: list[str]` — structured field (Bug #2 fix)
   - `evaluation_focus: str`
   - `question: str`
   - `temperature: float`
   - `top_k: int`
   - `min_p: float`
   - `quality_target: str`
   - `judge_scores: dict[str, float]`
   - `composite_score: float`
6. Define output fields:
   - `best_profile_json: str`
   - `composite_score: float`
   - `reasoning: str`
   - `parameter_effectiveness: float`
7. Verify import and field inspection

**Files:** Created: `src/audit/calibration_signature.py`
**Done when:** Module imports; input fields include structured `parameter_target: list[str]`; output fields match calibration optimization output
**Verify:** `python -c "from src.audit.calibration_signature import CalibrationSignature; print(CalibrationSignature.input_fields); print(CalibrationSignature.output_fields)"`
**Commit:** `feat(dspy): scaffold CalibrationSignature with structured parameter_target field`

---

### T1.6: Define CalibrationSignature docstring with bug #2 fix [x]
**Do:**
1. Read `src/audit/prompts_calibration.example.yaml` to extract prompt patterns
2. Write the signature docstring that models the grid search -> best params optimization process
3. **Bug fix #2**: Document that `parameter_target` is a structured Signature field (list[str]), NOT embedded in system prompt text
4. Ensure `{var}` placeholder syntax throughout
5. Ensure English text only

**Files:** Modified: `src/audit/calibration_signature.py`
**Done when:** Docstring models optimization process; parameter_target documented as structured InputField
**Verify:** `python -c "from src.audit.calibration_signature import CalibrationSignature; f = CalibrationSignature.input_fields; assert 'parameter_target' in f"`
**Commit:** `fix(dspy): parameter_target as structured InputField in CalibrationSignature (bug #2)`

---

### T1.7: Validate TrajectorySignature against AgenticTrajectory schema [x]
**Do:**
1. Read `src/factory/schema.py` to understand AgenticTrajectory, Turn, SimulatedError, Message structure
2. Write a validation script that checks:
   - TrajectorySignature.output_fields produce data parsable into `AgenticTrajectory`
   - `turns_json` parses to list of dicts with `turn_index`, `turn_type`, `content`, `tool_name`, `tool_args`, `tool_result`, `reasoning`
   - `errors_json` parses to list of dicts with `error_type`, `turn_index`, `description`, `recovery_turn_index`
   - `messages_json` parses to list of dicts with `role`, `content`
3. Add the validation as a test or inline assertion

**Files:** Modified: `src/factory/trajectory_signature.py` (add validation comment/assertion)
**Done when:** All output fields are parsable into structures compatible with AgenticTrajectory model
**Verify:** `python -c "
import json
from src.factory.schema import Turn, TurnType, AgenticTrajectory
data = json.loads('{\"turn_index\":0,\"turn_type\":\"observation\",\"content\":\"test\"}')
t = Turn(**data)
assert t.turn_type == TurnType.OBSERVATION
print('Parse OK')
"`
**Commit:** `test(dspy): validate TrajectorySignature output is parsable into AgenticTrajectory schema`

---

### T1.8: Validate JudgeSignature against NormalizedJudgeResponse schema [x]
**Do:**
1. Read `src/audit/schema.py` to understand NormalizedJudgeResponse TypedDict
2. Verify JudgeSignature.output_fields types: `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`
3. Write inline validation that a JSON output matching the TypedDict is parsable
4. Confirm the 5 dimensions (ha_modernity, reasoning_depth, functionality, completeness, style) are implied

**Files:** Modified: `src/audit/judge_signature.py` (add validation comment)
**Done when:** Output fields exactly match NormalizedJudgeResponse TypedDict
**Verify:** `python -c "from src.audit.judge_signature import JudgeSignature; f = JudgeSignature.output_fields; assert f['baseline'].annotation == dict[str, float]; assert f['adapter'].annotation == dict[str, float]; assert f['reasoning'].annotation == str"`
**Commit:** `test(dspy): validate JudgeSignature output matches NormalizedJudgeResponse TypedDict`

---

### T1.9: Validate CalibrationSignature [x] against CalibrationResult schema
**Do:**
1. Read `src/audit/calibration_schema.py` to understand SamplingProfile, CalibrationResult
2. Verify CalibrationSignature.output_fields produce data compatible with CalibrationResult:
   - `best_profile_json` parses into SamplingProfile fields (temperature, top_k, min_p, repetition_penalty, presence_penalty)
   - `composite_score: float`
   - `parameter_effectiveness: float` (0.0-1.0)
3. Verify input field `parameter_target: list[str]` contains valid parameter names from VALID_PARAMETERS set

**Files:** Modified: `src/audit/calibration_signature.py` (add validation comment)
**Done when:** Output fields map to CalibrationResult fields; parameter_target typed as list[str]
**Verify:** `python -c "from src.audit.calibration_signature import CalibrationSignature; f = CalibrationSignature.input_fields; assert 'parameter_target' in f; assert f['parameter_target'].annotation == list[str]"`
**Commit:** `test(dspy): validate CalibrationSignature fields compatible with CalibrationResult schema`

---

### T1.10: Test ChainOfThought signature for Hard Query [x]
**Do:**
1. Write a minimal inline test in a temporary file or as an assertion:
   - Create `dspy.Signature("category: str, context: str -> abstract_objective: str")`
   - Wrap with `dspy.ChainOfThought`
   - Verify the signature has input fields (category, context) and output field (abstract_objective)
   - Verify ChainOfThought adds a reasoning field between inputs and outputs
2. This proves the pattern works with installed DSPy 3.2.0

**Files:** No permanent file yet — inline verification
**Done when:** `dspy.ChainOfThought` works with the simple signature; returns both reasoning and abstract_objective
**Verify:** `python -c "import dspy; s = dspy.Signature('category: str, context: str -> abstract_objective: str'); c = dspy.ChainOfThought(s); print('CoT OK')"`
**Commit:** `test(dspy): verify ChainOfThought pattern works with DSPy 3.2.0`

---

[VERIFY] Quality Checkpoint 1: All 3 Signatures defined + validated, ChainOfThought pattern proven
- `python -c "from src.factory.trajectory_signature import TrajectorySignature; from src.audit.judge_signature import JudgeSignature; from src.audit.calibration_signature import CalibrationSignature; print('All signatures imported OK')"`
- All docstrings in English, no `$var` syntax
- No behavioral changes yet — pure signature definitions only

---

## Phase 2: Refactor — Wire Signatures into Consumers

*Integrate signatures into trajectory_generator.py, judge.py, and hard_query_builder.py. Dual-path: DSPy when LM configured, template fallback otherwise.*

### T2.1: Add dspy.Predict import utility module [x]
**Do:**
1. Create `src/factory/dspy_utils.py` (shared utility for DSPy integration)
2. Implement `get_predict(signature_class, instructions=None)` that:
   - Checks if `dspy.LM` is configured (tries `dspy.settings.lm or dspy.core_lm`)
   - If LM configured: returns `dspy.Predict(signature_class.with_instructions(instructions))`
   - If LM NOT configured: returns `None` (caller falls back to templates)
3. Implement `get_chain_of_thought(signature_or_str, instructions=None)` similarly
4. Keep this module free of business logic — pure DSPy bridge

**Files:** Created: `src/factory/dspy_utils.py`
**Done when:** `get_predict()` returns a Predictor when LM configured, None otherwise; `get_chain_of_thought()` returns CoT module when LM configured
**Verify:** `python -c "from src.factory.dspy_utils import get_predict; assert get_predict(None) is None; print('Fallback OK')"`
**Commit:** `feat(dspy): add dspy_utils with LM-aware Predict/CoT factory functions`

---

### T2.2: Wire TrajectorySignature [x] into TrajectoryGenerator
**Do:**
1. Modify `src/factory/trajectory_generator.py`:
   - Add import: `from src.factory.trajectory_signature import TrajectorySignature`
   - Add import: `from src.factory.dspy_utils import get_predict`
2. In `generate()` method, add dual path:
   - Check if DSPy predictor is available via `get_predict(TrajectorySignature)`
   - If available: use predictor with seed data, parse JSON outputs (turns_json, errors_json, messages_json), construct `AgenticTrajectory`
   - If NOT available: keep existing template-based logic unchanged
3. Preserve all existing behavior: turn construction, error injection, verify turns, ChatML serialization
4. Ensure `generate()` still returns `AgenticTrajectory` (unchanged return type)

**Files:** Modified: `src/factory/trajectory_generator.py`
**Done when:** `generate()` works with both paths; existing tests pass; return type unchanged
**Verify:** `python -m pytest tests/factory/test_trajectory_generator.py -v --tb=short`
**Commit:** `refactor(dspy): wire TrajectorySignature into TrajectoryGenerator with dual-path fallback`

---

### T2.3: Wire JudgeSignature [x] into llm_judge_score
**Do:**
1. Modify `src/audit/judge.py`:
   - Add import: `from src.audit.judge_signature import JudgeSignature`
   - Add import: `from src.factory.dspy_utils import get_predict`
2. In `llm_judge_score()`, add dual path:
   - If DSPy LM configured: use `dspy.Predict(JudgeSignature)` with `json_mode=True`
   - Parse output: `baseline: dict[str, float]`, `adapter: dict[str, float]`, `reasoning: str`
   - If NOT configured: keep existing `PromptManager` + `client.generate_with_retry()` path
3. Preserve the existing error handling: `json.JSONDecodeError` -> save raw -> raise `PromptGenerationError`
4. Preserve `normalize_judge_response()` call on output

**Files:** Modified: `src/audit/judge.py`
**Done when:** `llm_judge_score()` works with both paths; existing tests pass; return type `NormalizedJudgeResponse` unchanged
**Verify:** `python -m pytest tests/test_audit_judge_submodule.py -v --tb=short`
**Commit:** `refactor(dspy): wire JudgeSignature into llm_judge_score with dual-path fallback`

---

### T2.4: Replace _transform_to_abstract with ChainOfThought [x]
**Do:**
1. Modify `src/factory/hard_query_builder.py`:
   - Add imports: `import dspy`, `from src.factory.dspy_utils import get_chain_of_thought`
   - Replace `_transform_to_abstract()` method body:
     - Create `dspy.Signature("category: str, context: str -> abstract_objective: str")`
     - Call `get_chain_of_thought(sig)` which returns CoT module or None
     - If CoT available: call `cot(category=category, context=context)`, return `result.abstract_objective`
     - If NOT available: keep existing hardcoded if/else mapping as fallback
2. Preserve the return type: `str` (abstract objective)
3. Ensure `_transform_to_abstract()` signature unchanged

**Files:** Modified: `src/factory/hard_query_builder.py`
**Done when:** `_transform_to_abstract()` uses ChainOfThought when LM configured; falls back to hardcoded mapping otherwise
**Verify:** `python -c "from src.factory.hard_query_builder import HardQueryBuilder; import inspect; src = inspect.getsource(HardQueryBuilder._transform_to_abstract); assert 'dspy' in src, 'ChainOfThought not found'"`
**Commit:** `refactor(dspy): replace _transform_to_abstract with dspy.ChainOfThought (hard_query_builder)`

---

### T2.5: Add bug #6 [x] comment to forbidden_terms
**Do:**
1. In `src/factory/hard_query_builder.py`, find the `forbidden_terms` list (line 76-82)
2. Add a DSPy comment above the list explaining these are literal match strings, NOT translatable prompt content
3. Comment should state: "Note: These are literal text match strings for forbidden-term detection, not translatable prompt content. DSPy ChainOfThought receives only category+context — forbidden_terms are only used in validate_prompt()."
4. Verify the Spanish strings ("llama al servicio", "usa el componente") remain unchanged as literal match strings

**Files:** Modified: `src/factory/hard_query_builder.py`
**Done when:** Comment documents that forbidden_terms are literal match strings; Spanish strings preserved
**Verify:** `grep -A1 "literal match" src/factory/hard_query_builder.py` returns the comment
**Commit:** `fix(dspy): document forbidden_terms as literal match strings (bug #6)`

---

### T2.6: Create BacktrackingDetector [x] class
**Do:**
1. Create `src/factory/backtracking_detector.py`
2. **Constraint: MUST NOT import dspy** — pure utility module
3. Import `Turn` and `TurnType` from `src.factory.schema`
4. Implement `BacktrackingDetector` class with:
   - `detect(turns: list[Turn]) -> tuple[bool, list[int], str]`
   - `detect_from_messages(messages: list[Message]) -> tuple[bool, list[int], str]`
5. Detection logic:
   - Find consecutive ERROR->CORRECT pairs
   - Return `(True, [error_idx, correct_idx], "error_recovery")` when found
   - Return `(False, [], "none")` when not found
   - Handle empty turns list: return `(False, [], "no_turns")`
6. Add `BacktrackingResult` dataclass for typed return

**Files:** Created: `src/factory/backtracking_detector.py`
**Done when:** Class imports successfully; `detect()` correctly identifies ERROR->CORRECT patterns; no dspy import
**Verify:** `python -c "from src.factory.backtracking_detector import BacktrackingDetector; assert 'dspy' not in open('src/factory/backtracking_detector.py').read(); print('No dspy import, OK')"`
**Commit:** `feat(dspy): add BacktrackingDetector with ERROR->CORRECT detection`

---

### T2.7: Add __init__.py [x] exports for factory module
**Do:**
1. Ensure `src/factory/__init__.py` exports new modules:
   - `BacktrackingDetector` from `backtracking_detector`
   - `TrajectorySignature` from `trajectory_signature` (if used externally)
2. No-op if `__init__.py` already handles this via lazy imports or doesn't export

**Files:** Check/Modified: `src/factory/__init__.py`
**Done when:** `from src.factory import BacktrackingDetector` works
**Verify:** `python -c "from src.factory import BacktrackingDetector; print('OK')"`
**Commit:** `chore: export BacktrackingDetector from factory __init__`

---

### T2.8: Standardize placeholder [x] syntax (bug #3)
**Do:**
1. Review all 3 signature files for `$var` syntax
2. Replace any `$var` with `{var}` in docstrings
3. Verify with: `grep -rn '\$var\|\$[a-zA-Z]' src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py` — should find nothing
4. Confirm existing production code at `trajectory_generator.py:216` uses `{var}` (it does — verified)

**Files:** Modified: `src/factory/trajectory_signature.py`, `src/audit/judge_signature.py`, `src/audit/calibration_signature.py`
**Done when:** Zero occurrences of `$var` in any signature file
**Verify:** `grep -rn '\$var' src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py; echo "exit: $?"` (should be 1 = no match)
**Commit:** `fix(dspy): standardize {var} placeholder syntax across all signatures (bug #3)`

---

### T2.9: Normalize whitespace [x] in docstrings (bug #4)
**Do:**
1. Check docstrings in all 3 signature files for trailing whitespace before special tokens like `</s>`, `</think>`, `<|end|>`, `¶`
2. Strip trailing whitespace before any special tokens in the docstring
3. Verify with a regex scan: no whitespace immediately before these tokens

**Files:** Modified: `src/factory/trajectory_signature.py`, `src/audit/judge_signature.py`, `src/audit/calibration_signature.py`
**Done when:** No whitespace before special tokens in any signature docstring
**Verify:** `grep -Pn '(</s>|<\|end\|>|</think>|¶)\s*$' src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py` — no matches
**Commit:** `fix(dspy): normalize whitespace before special tokens in signature docstrings (bug #4)`

---

[VERIFY] Quality Checkpoint 2: All consumers wired with dual-path fallback
- `python -m pytest tests/factory/test_trajectory_generator.py tests/factory/test_hard_query_builder.py tests/test_audit_judge_submodule.py -v --tb=short` — all pass
- `grep -rn 'dspy' src/factory/backtracking_detector.py` — zero matches (BacktrackingDetector is pure)
- No production behavior change: template fallback works when DSPy LM not configured

---

## Phase 3: Testing

*Unit tests for signatures, integration tests for consumers, Spearman correlation test.*

### T3.1: Unit test — TrajectorySignature field types [x]
**Do:**
1. Create `tests/factory/test_trajectory_signature.py`
2. Test that `TrajectorySignature.input_fields` contains all 9 expected input fields
3. Test that `TrajectorySignature.output_fields` contains exactly `turns_json`, `errors_json`, `messages_json`, `use_case`
4. Test that output field types are `str` for JSON fields
5. Test that input field types are correct: `str`, `float`, `bool` as appropriate

**Files:** Created: `tests/factory/test_trajectory_signature.py`
**Done when:** All field type assertions pass
**Verify:** `python -m pytest tests/factory/test_trajectory_signature.py -v --tb=short`
**Commit:** `test(dspy): unit test TrajectorySignature field types`

---

### T3.2: Unit test — JudgeSignature [x] field types
**Do:**
1. Create `tests/audit/test_judge_signature.py`
2. Test `JudgeSignature.input_fields` contains all 5 expected input fields
3. Test `JudgeSignature.output_fields` contains `baseline`, `adapter`, `reasoning`
4. Test `baseline` and `adapter` are typed as `dict[str, float]`
5. Test `reasoning` is typed as `str`
6. Test docstring does not contain "Architecture architecture"

**Files:** Created: `tests/audit/test_judge_signature.py`
**Done when:** All field type assertions pass; typo check passes
**Verify:** `python -m pytest tests/audit/test_judge_signature.py -v --tb=short`
**Commit:** `test(dspy): unit test JudgeSignature field types and bug #1 fix`

---

### T3.3: Unit test — CalibrationSignature [x] field types
**Do:**
1. Create `tests/audit/test_calibration_signature.py`
2. Test `CalibrationSignature.input_fields` contains `parameter_target` typed as `list[str]`
3. Test `CalibrationSignature.output_fields` contains `best_profile_json`, `composite_score`, `reasoning`, `parameter_effectiveness`
4. Test `parameter_effectiveness` is typed as `float`
5. Verify `parameter_target` is NOT mentioned as plain text in docstring (it's a structured field)

**Files:** Created: `tests/audit/test_calibration_signature.py`
**Done when:** All field type assertions pass; parameter_target is structured
**Verify:** `python -m pytest tests/audit/test_calibration_signature.py -v --tb=short`
**Commit:** `test(dspy): unit test CalibrationSignature field types`

---

### T3.4: Unit test — BacktrackingDetector basic [x] detection
**Do:**
1. Create `tests/factory/test_backtracking_detector.py`
2. Test `BacktrackingDetector.detect()` with empty turns: returns `(False, [], "no_turns")`
3. Test with single turn (OBSERVATION): returns `(False, [], "none")`
4. Test with ERROR->CORRECT pair: returns `(True, [error_idx, correct_idx], "error_recovery")`
5. Test with multiple backtracking patterns: returns all detected indices
6. Test with no consecutive ERROR->CORRECT: returns `(False, [], "none")`

**Files:** Created: `tests/factory/test_backtracking_detector.py`
**Done when:** All 6 test cases pass
**Verify:** `python -m pytest tests/factory/test_backtracking_detector.py -v --tb=short`
**Commit:** `test(dspy): unit test BacktrackingDetector detection logic`

---

### T3.5: Unit test — BacktrackingDetector from_messages [x]
**Do:**
1. In `tests/factory/test_backtracking_detector.py`, add tests for `detect_from_messages()`
2. Test with a list of Message objects that encode ERROR->CORRECT pattern
3. Verify it correctly extracts turn types and finds backtracking
4. Test with empty messages list

**Files:** Modified: `tests/factory/test_backtracking_detector.py`
**Done when:** `detect_from_messages()` works with Message objects
**Verify:** `python -m pytest tests/factory/test_backtracking_detector.py -v --tb=short -k from_messages`
**Commit:** `test(dspy): unit test BacktrackingDetector detect_from_messages`

---

### T3.6: Unit test — HardQueryBuilder uses [x] ChainOfThought
**Do:**
1. In `tests/factory/test_hard_query_builder.py`, add test for `_transform_to_abstract()`
2. Mock `dspy.ChainOfThought` and verify it is called with correct signature
3. Verify the method returns a string (abstract_objective)
4. Test that when LM is NOT configured, the hardcoded mapping still works as fallback

**Files:** Modified: `tests/factory/test_hard_query_builder.py`
**Done when:** Test verifies CoT is used when available; fallback works when not
**Verify:** `python -m pytest tests/factory/test_hard_query_builder.py -v --tb=short`
**Commit:** `test(dspy): unit test HardQueryBuilder ChainOfThought integration`

---

### T3.7: Integration test — TrajectoryGenerator [x] with DSPy stub
**Do:**
1. In `tests/factory/test_trajectory_generator.py`, add integration test
2. Stub the DSPy predictor to return shaped JSON for `turns_json`, `errors_json`, `messages_json`
3. Call `TrajectoryGenerator.generate(seed_data)`
4. Assert returned value is `AgenticTrajectory` instance
5. Assert returned trajectory has correct field types (turns, errors, messages)
6. Assert structure is compatible with `AgenticTrajectory` model

**Files:** Modified: `tests/factory/test_trajectory_generator.py`
**Done when:** Integration test passes with stubbed DSPy predictor
**Verify:** `python -m pytest tests/factory/test_trajectory_generator.py -v --tb=short -k dspy`
**Commit:** `test(dspy): integration test TrajectoryGenerator with stubbed DSPy predictor`

---

### T3.8: Integration test — llm_judge_score [x] with DSPy stub
**Do:**
1. In `tests/test_audit_judge_submodule.py`, add integration test
2. Stub `dspy.Predict(JudgeSignature)` to return shaped JSON matching `NormalizedJudgeResponse`
3. Call `llm_judge_score(exam, baseline_resp, adapter_resp, ...)`
4. Assert returned value is `NormalizedJudgeResponse` TypedDict
5. Assert it has `baseline`, `adapter`, `reasoning` keys with correct types

**Files:** Modified: `tests/test_audit_judge_submodule.py`
**Done when:** Integration test passes with stubbed DSPy predictor
**Verify:** `python -m pytest tests/test_audit_judge_submodule.py -v --tb=short -k dspy`
**Commit:** `test(dspy): integration test llm_judge_score with stubbed DSPy predictor`

---

### T3.9: Spearman correlation [x] test — old vs new judge outputs
**Do:**
1. Create `tests/integration/test_judge_correlation.py` (new directory if needed)
2. Implement test that runs both old and new judge paths on the same inputs:
   - Old path: `PromptManager` + `client.generate_with_retry()` (mocked)
   - New path: `JudgeSignature` + `dspy.Predict` (mocked)
3. Compute Spearman rank correlation on adapter composite scores
4. Assert `correlation > 0.8`
5. Use anchor dataset samples or mock exam records

**Files:** Created: `tests/integration/test_judge_correlation.py` (new directory if needed)
**Done when:** Spearman correlation > 0.8 on test inputs
**Verify:** `python -m pytest tests/integration/test_judge_correlation.py -v --tb=short`
**Commit:** `test(dspy): Spearman correlation test — new judge > 0.8 with old baseline`

---

### T3.10: Verify behavioral [x] invariance — trajectory output comparison
**Do:**
1. Create `tests/integration/test_trajectory_invariance.py`
2. Run `TrajectoryGenerator.generate()` with template-only path (no DSPy LM)
3. Capture output structure (turn types, turn count, error injection pattern)
4. Verify structure matches expected patterns:
   - 3-10 turns
   - OBSERVATION -> REASONING -> ACTION -> [ERROR? -> CORRECT? -> VERIFY?]
   - errors list populated when error injected
5. This proves the template fallback path is unchanged

**Files:** Created: `tests/integration/test_trajectory_invariance.py`
**Done when:** Template fallback path produces structurally identical trajectories
**Verify:** `python -m pytest tests/integration/test_trajectory_invariance.py -v --tb=short`
**Commit:** `test(dspy): behavioral invariance test — trajectory output structure preserved`

---

### T3.11: End-to-end — HardQueryBuilder [x] validation with forbidden terms
**Do:**
1. In `tests/factory/test_hard_query_builder.py`, add tests for `validate_prompt()` and `build_with_validation()`
2. Test that `validate_prompt()` returns False when forbidden terms are found
3. Test that `validate_prompt()` returns True for clean text
4. Test `build_with_validation()` succeeds when CoT output is valid
5. Test `build_with_validation()` raises ValueError after 3 retries when all outputs contain forbidden terms

**Files:** Modified: `tests/factory/test_hard_query_builder.py`
**Done when:** All 5 test cases pass
**Verify:** `python -m pytest tests/factory/test_hard_query_builder.py -v --tb=short -k validate`
**Commit:** `test(dspy): HardQueryBuilder validate_prompt and build_with_validation tests`

---

[VERIFY] Quality Checkpoint 3: All tests passing [x] All tests passing
- `python -m pytest tests/factory/test_trajectory_signature.py tests/audit/test_judge_signature.py tests/audit/test_calibration_signature.py tests/factory/test_backtracking_detector.py tests/factory/test_hard_query_builder.py tests/factory/test_trajectory_generator.py tests/test_audit_judge_submodule.py -v --tb=short` — all pass
- `python -m pytest tests/integration/ -v --tb=short` — correlation > 0.8
- No test regressions in existing suites

---

## Phase 4: Quality

*Bug fixes, dead code removal, formatting, linting, type checking.*

### T4.1: Delete dead code — frontend_taxonomy_prompts.py [x]
**Do:**
1. Delete `src/export/frontend_taxonomy_prompts.py` (verified: 0 Python imports in src/ or tests/)
2. Verify no import chains are broken:
   - `grep -rn "from src.export.frontend_taxonomy_prompts\|import frontend_taxonomy_prompts" src/ tests/` — should find nothing (beyond __pycache__ and egg-info)
3. Keep `src/export/prompts_frontend.example.yaml` (it's a documentation artifact, not code)

**Files:** Deleted: `src/export/frontend_taxonomy_prompts.py`
**Done when:** File is deleted; zero import errors; `src/export/` still has remaining files
**Verify:** `python -c "import ast; [compile(open(f).read(), f, 'exec') for f in ['src/export/chatml_exporter.py']]; print('No import errors')"`
**Commit:** `chore(dspy): delete dead code src/export/frontend_taxonomy_prompts.py (bug #7)`

---

### T4.2: Confirm bug #5 is false positive — Python vs Jinja protocol [x]
**Do:**
1. Verify the "Python vs Jinja output protocol" issue (bug #5) is a false positive
2. Check `src/factory/prompt_builder.py` and related code to confirm both use identical output format
3. Add a comment in research.md noting this was confirmed false positive

**Files:** No code changes — documentation only
**Done when:** Confirmed false positive; documented in research.md or a comment
**Verify:** Code review of relevant files
**Commit:** `docs(dspy): confirm bug #5 Python vs Jinja protocol is false positive`

---

### T4.3: Run ruff check on all changed files [x]
**Do:**
1. Run `ruff check src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py src/factory/dspy_utils.py`
2. Fix any lint errors
3. Also run on test files: `ruff check tests/factory/test_trajectory_signature.py tests/audit/test_judge_signature.py tests/audit/test_calibration_signature.py tests/factory/test_backtracking_detector.py`

**Files:** Modified: all files with lint errors
**Done when:** `ruff check` passes with zero warnings/errors on all new/modified files
**Verify:** `ruff check src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py src/factory/dspy_utils.py tests/factory/test_trajectory_signature.py tests/audit/test_judge_signature.py tests/audit/test_calibration_signature.py tests/factory/test_backtracking_detector.py`
**Commit:** `chore: ruff lint fix for dspy-integration files`

---

### T4.4: Run ruff format on all changed files [x]
**Do:**
1. Run `ruff format src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py src/factory/dspy_utils.py`
2. Verify with `ruff format --check`

**Files:** Modified: all files with formatting changes
**Done when:** `ruff format --check` reports all files already formatted
**Verify:** `ruff format --check src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py src/factory/dspy_utils.py`
**Commit:** `chore: ruff format all dspy-integration files`

---

### T4.5: Run pyright type checking on new signature files [x]
**Do:**
1. Run `pyright src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/dspy_utils.py`
2. Fix any type errors
3. Also check modified files: `pyright src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py`

**Files:** Modified: files with type errors
**Done when:** `pyright` reports zero errors on all new and modified files
**Verify:** `pyright src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py src/factory/backtracking_detector.py src/factory/dspy_utils.py src/factory/trajectory_generator.py src/audit/judge.py src/factory/hard_query_builder.py`
**Commit:** `chore: pyright type check fix for dspy-integration files`

---

### T4.6: Run full test suite — no regressions [x] [x]
**Do:**
1. Run `python -m pytest tests/ -v --tb=short` (or the project's standard test invocation)
2. Fix any regressions introduced by the refactoring
3. Ensure all existing tests still pass

**Files:** Modified: any files with regressions
**Done when:** Full test suite passes with zero regressions
**Verify:** `python -m pytest tests/ -v --tb=short`
**Commit:** `test: verify no regressions in full test suite after dspy-integration`

---

### VE1: End-to-end verification — startup
**Do:**
1. Verify all new files exist and import:
   - `python -c "from src.factory.trajectory_signature import TrajectorySignature"`
   - `python -c "from src.audit.judge_signature import JudgeSignature"`
   - `python -c "from src.audit.calibration_signature import CalibrationSignature"`
   - `python -c "from src.factory.backtracking_detector import BacktrackingDetector"`
   - `python -c "from src.factory.dspy_utils import get_predict"`
2. Verify dead code deleted:
   - `test ! -f src/export/frontend_taxonomy_prompts.py`
3. Verify signature field counts:
   - `python -c "from src.factory.trajectory_signature import TrajectorySignature; assert len(TrajectorySignature.input_fields) == 9; assert len(TrajectorySignature.output_fields) == 4"`
   - `python -c "from src.audit.judge_signature import JudgeSignature; assert 'baseline' in JudgeSignature.output_fields; assert 'adapter' in JudgeSignature.output_fields; assert 'reasoning' in JudgeSignature.output_fields"`
   - `python -c "from src.audit.calibration_signature import CalibrationSignature; assert 'parameter_target' in CalibrationSignature.input_fields; assert 'best_profile_json' in CalibrationSignature.output_fields"`

**Files:** Verification only
**Done when:** All 5 modules import; all 3 signatures have correct fields; dead code file deleted
**Verify:** Combined import check as described above
**Commit:** `verify: VE1 — all dspy signatures import and have correct fields`

---

### VE2: End-to-end verification — functional checks
**Do:**
1. Verify bug fixes:
   - `python -c "from src.audit.judge_signature import JudgeSignature; assert 'Architecture architecture' not in JudgeSignature.__doc__"`
   - `grep -rn '\$var' src/factory/trajectory_signature.py src/audit/judge_signature.py src/audit/calibration_signature.py; exit 1` (should exit 1 = no match)
   - `grep -n 'literal match' src/factory/hard_query_builder.py` (should find comment)
2. Verify BacktrackingDetector does not import dspy
3. Verify `TrajectoryGenerator.generate()` returns `AgenticTrajectory`
4. Verify `llm_judge_score()` returns `NormalizedJudgeResponse`
5. Verify `HardQueryBuilder.build()` returns string

**Files:** Verification only
**Done when:** All bug fixes verified; all function contracts preserved
**Verify:** Commands above
**Commit:** `verify: VE2 — functional checks and bug fix verification`

---

### VE3: End-to-end verification — cleanup
**Do:**
1. Clean up any temporary files or debug prints
2. Run `ruff check --select F` on all files — no unused imports
3. Run `ruff format --check` — all files formatted
4. Final test run: `python -m pytest tests/factory/test_trajectory_signature.py tests/audit/test_judge_signature.py tests/audit/test_calibration_signature.py tests/factory/test_backtracking_detector.py tests/factory/test_hard_query_builder.py tests/factory/test_trajectory_generator.py tests/test_audit_judge_submodule.py -v --tb=short`
5. Verify git status shows expected changes only

**Files:** Cleanup of any debug code
**Done when:** All checks pass; git status shows only intended changes
**Verify:** Final ruff + pytest run
**Commit:** `verify: VE3 — cleanup and final verification`

---

## Summary of File Operations

| File | Action | Purpose |
|------|--------|---------|
| `src/factory/trajectory_signature.py` | **Create** | TrajectorySignature DSPy Signature |
| `src/factory/dspy_utils.py` | **Create** | DSPy LM-aware Predict/CoT factory |
| `src/factory/backtracking_detector.py` | **Create** | BacktrackingDetector utility |
| `src/factory/trajectory_generator.py` | **Modify** | Wire TrajectorySignature with dual-path |
| `src/audit/judge_signature.py` | **Create** | JudgeSignature DSPy Signature |
| `src/audit/judge.py` | **Modify** | Wire JudgeSignature with dual-path |
| `src/audit/calibration_signature.py` | **Create** | CalibrationSignature DSPy Signature |
| `src/factory/hard_query_builder.py` | **Modify** | Replace mapping with ChainOfThought |
| `src/export/frontend_taxonomy_prompts.py` | **Delete** | Dead code (bug #7) |
| `tests/factory/test_trajectory_signature.py` | **Create** | Signature field type tests |
| `tests/audit/test_judge_signature.py` | **Create** | Signature field type tests |
| `tests/audit/test_calibration_signature.py` | **Create** | Signature field type tests |
| `tests/factory/test_backtracking_detector.py` | **Create** | Detector unit tests |
| `tests/factory/test_hard_query_builder.py` | **Modify** | Add CoT integration tests |
| `tests/factory/test_trajectory_generator.py` | **Modify** | Add DSPy integration tests |
| `tests/test_audit_judge_submodule.py` | **Modify** | Add DSPy integration tests |
| `tests/integration/test_judge_correlation.py` | **Create** | Spearman correlation test |
| `tests/integration/test_trajectory_invariance.py` | **Create** | Behavioral invariance test |

---

## Phase 5: Review Fix — Address Smart-Ralph Review Findings

*Post-completion quality pass. Addresses 5 confirmed findings from the Smart-Ralph review report (plans/dspy-integration-smart-ralph-review.md).*

### T5.1: Fix F-02 — JudgeSignature validation against correct NormalizedJudgeResponse [x]
**Do:**
1. In `src/audit/judge_signature.py`, change line 85 from:
   `from src.schemas.common import NormalizedJudgeResponse`
   to:
   `from src.audit.schema import NormalizedJudgeResponse`
2. This ensures validation uses the same strict TypedDict that the consumer (`judge.py`) uses
3. Verify import still works: `python -c "from src.audit.judge_signature import JudgeSignature; print('OK')"`

**Files:** Modified: `src/audit/judge_signature.py`
**Done when:** Validation block imports from `src.audit.schema` (the strict TypedDict version)
**Verify:** `python -c "from src.audit.judge_signature import JudgeSignature; print('OK')"`
**Commit:** `fix(dspy): validate JudgeSignature against strict NormalizedJudgeResponse from audit.schema (F-02)`

---

### T5.2: Fix F-08 — Real Spearman correlation test with stubs
**Do:**
1. Create `tests/factory/test_spearman_real.py`
2. Stub both old judge path (PromptManager-based) and new judge path (JudgeSignature-based)
3. Use identical inputs and known JSON outputs to verify `spearmanr > 0.8` between outputs
4. This tests NFR-001 compliance: correlation between old and new judge outputs

**Files:** Created: `tests/factory/test_spearman_real.py`
**Done when:** Test stubs both judge paths and verifies Spearman correlation on controlled inputs
**Verify:** `python -m pytest tests/factory/test_spearman_real.py -v --tb=short`
**Commit:** `test(dspy): real Spearman correlation test with stubbed judge outputs (F-08, NFR-001)`

---

### T5.3: Fix F-11 — Judge DSPy integration test with predictor stub
**Do:**
1. Modify `tests/audit/test_judge_dspy_integration.py` to add a real integration test
2. Mock `get_predict(JudgeSignature)` to return a predictor with JSON shaped as `NormalizedJudgeResponse`
3. Test that `llm_judge_score()` correctly parses the DSPy output and returns `NormalizedJudgeResponse`
4. This verifies the DSPy path in `llm_judge_score()` works correctly when LM IS configured

**Files:** Modified: `tests/audit/test_judge_dspy_integration.py`
**Done when:** Test mocks predictor with shaped JSON and verifies output parsing
**Verify:** `python -m pytest tests/audit/test_judge_dspy_integration.py -v --tb=short`
**Commit:** `test(dspy): integration test for Judge DSPy path with predictor stub (F-11)`

---

### T5.4: Fix F-09 — Cache dspy.Signature in HardQueryBuilder [x]
**Do:**
1. In `src/factory/hard_query_builder.py`, add module-level constant:
   `_HARD_QUERY_SIG = dspy.Signature("category: str, context: str -> abstract_objective: str")`
2. In `_transform_to_abstract()`, replace inline `dspy.Signature(...)` with `_HARD_QUERY_SIG`
3. This prevents creating a new Python class on every invocation

**Files:** Modified: `src/factory/hard_query_builder.py`
**Done when:** Signature is a module-level constant; `_transform_to_abstract()` references it
**Verify:** `python -c "from src.factory.hard_query_builder import _HARD_QUERY_SIG; print('OK')"`
**Commit:** `fix(dspy): cache HardQueryBuilder dspy.Signature as module constant (F-09)`

---

### T5.5: Fix F-03 — BacktrackingResult dead code removal
**Do:**
1. In `src/factory/backtracking_detector.py`, remove the `BacktrackingResult` dataclass (lines 15-21)
2. Update `detect()` and `detect_from_messages()` to return `BacktrackingResult` instead of tuple
3. Change return type from `tuple[bool, list[int], str]` to `BacktrackingResult`
4. Verify all callers work (grep for `detect(` references)

**Files:** Modified: `src/factory/backtracking_detector.py`
**Done when:** `BacktrackingResult` is the actual return type of `detect()` methods
**Verify:** `python -c "from src.factory.backtracking_detector import BacktrackingDetector, BacktrackingResult; r = BacktrackingDetector.detect([]); assert isinstance(r, BacktrackingResult); print('OK')"`
**Commit:** `fix(dspy): use BacktrackingResult as actual return type of detect() (F-03)`

---

### T5.6: Fix F-01 — Update stale docs: use_case → inferred_use_case
**Do:**
1. Update `specs/dspy-integration/design.md` line ~65: `use_case` → `inferred_use_case`
2. Update `specs/dspy-integration/tasks.md` line ~24: `use_case` → `inferred_use_case`
3. grep for all remaining `use_case` references in doc artifacts

**Files:** Modified: `specs/dspy-integration/design.md`, `specs/dspy-integration/tasks.md`
**Done when:** All docs reference `inferred_use_case` (not `use_case`) for the output field
**Verify:** `grep -n 'use_case' specs/dspy-integration/design.md specs/dspy-integration/tasks.md | grep -i output` should show only `inferred_use_case`
**Commit:** `docs(dspy): update stale docs use_case → inferred_use_case (F-01)`

---

### T5.7: Fix F-04 — Update epic.md Interface Contracts
**Do:**
1. Update `specs/_epics/aegf-dspy-integration/epic.md` lines ~75-91
2. Replace incorrect output field lists with actual field names from codebase
3. TrajectorySignature: `seed_id, mode, turns, errors, use_case, messages` (not `tool_usage_patterns`)
4. JudgeSignature: `baseline, adapter, reasoning` (not `coherence/overall`)
5. CalibrationSignature: match actual `CalibrationResult` schema fields

**Files:** Modified: `specs/_epics/aegf-dspy-integration/epic.md`
**Done when:** Interface Contracts match actual codebase types
**Verify:** Cross-reference against `src/factory/schema.py` and `src/audit/calibration_schema.py`
**Commit:** `docs(dspy): correct epic.md Interface Contracts to match actual types (F-04)`

---

### T5.8: Fix F-05 — Update epic.md status to complete
**Do:**
1. Update `specs/_epics/aegf-dspy-integration/epic.md` line ~6: `status: not_started` → `status: complete`
2. Update completion timestamp

**Files:** Modified: `specs/_epics/aegf-dspy-integration/epic.md`
**Done when:** epic.md status reflects completion
**Verify:** `grep 'status:' specs/_epics/aegf-dspy-integration/epic.md` shows `complete`
**Commit:** `docs(dspy): update epic.md status to complete (F-05)`

---

### T5.9: Fix F-06 + F-07 — Correct design.md pattern label and epic MIPROv2 scope
**Do:**
1. In `specs/dspy-integration/design.md` line ~200: change "(C) Parallel then switch" → "(B) Dual path with fallback"
2. In `specs/_epics/aegf-dspy-integration/epic.md` line ~50: move MIPROv2 from IN Scope to OUT of Scope

**Files:** Modified: `specs/dspy-integration/design.md`, `specs/_epics/aegf-dspy-integration/epic.md`
**Done when:** design.md correctly labels pattern as "(B)"; MIPROv2 is OUT of Scope in epic
**Verify:** `grep -n 'Parallel then switch' specs/dspy-integration/design.md` returns nothing
**Commit:** `docs(dspy): fix design.md pattern label and MIPROv2 scope (F-06, F-07)`

---

[VERIFY] Quality Checkpoint 4: All review fixes applied
- `python -m pytest tests/factory/test_spearman_real.py tests/audit/test_judge_dspy_integration.py -v --tb=short` — all pass
- `python -c "from src.audit.judge_signature import JudgeSignature; print('F-02 fix OK')"` — import from audit.schema
- `python -c "from src.factory.hard_query_builder import _HARD_QUERY_SIG; print('F-09 fix OK')"` — signature cached
- `python -c "from src.factory.backtracking_detector import BacktrackingResult; print('F-03 fix OK')"` — dataclass used as return type
- `grep -c 'use_case' specs/dspy-integration/design.md` — only `inferred_use_case` references remain
- Full suite: `python -m pytest tests/ --ignore=tests/curation --ignore=tests/unit/test_cli.py -q --tb=short` — all pass

---
