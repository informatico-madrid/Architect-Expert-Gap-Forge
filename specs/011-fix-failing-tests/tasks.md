---
description: "Task list for feature 011-fix-failing-tests"
---

# Tasks: Fix 37 Failing Tests

**Input**: Design documents from `/specs/011-fix-failing-tests/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label ([US1]–[US6])
- File paths are absolute from workspace root

---

## Phase 1: Setup

**Purpose**: Confirm the failing baseline before any fix is applied.

- [ ] T001 Run `PYTHONPATH=. pytest --tb=no -q 2>&1 | tail -5` in workspace root and confirm output contains `37 failed` — record exact count before touching any file

**Checkpoint**: Baseline confirmed — 37 failures across 6 independent groups.

---

## Phase 2: Foundational (Blocking Prerequisites)

No shared infrastructure changes are required. All 6 fix groups are independent — each user story can start immediately after Phase 1 is confirmed.

**Checkpoint**: All user story phases can proceed in parallel.

---

## Phase 3: User Story 1 — Eliminar `top_p` del contrato `SamplingProfile` (Priority: P1) 🎯 MVP

**Goal**: Eliminar `top_p` de `SamplingProfile`, `CALIBRATION_GRID` y `VALID_PARAMETERS` en `calibration_schema.py`; eliminar todas las referencias a `top_p` en `calibration.py`.

**Independent Test**:
```bash
PYTHONPATH=. pytest tests/test_audit_calibration.py tests/test_inference.py \
  -k "calibration or Gemini" --tb=short -q
```

### Implementation for User Story 1

- [ ] T002 [US1] Remove `top_p` field definition (and its `__post_init__` validation line + `from_dict` access) from `SamplingProfile` dataclass in `src/audit/calibration_schema.py`
- [ ] T003 [P] [US1] Remove `"top_p": [...]` entry from `CALIBRATION_GRID` dict and `"top_p"` from `VALID_PARAMETERS` set in `src/audit/calibration_schema.py`
- [ ] T004 [US1] Ejecutar primero `grep -n 'top_p' src/audit/calibration.py` para listar TODAS las referencias (se esperan: 2 instanciaciones en `generate_profiles()` + posibles líneas de print/serialización). Eliminar **todas** las referencias a `top_p` en `calibration.py` — incluyendo los dos argumentos `top_p=profile_dict["top_p"]` / `top_p=profile_dict.get("top_p", 0.9)` en `generate_profiles()` y cualquier otra línea que referencie la clave. (Depende de T002, T003 completados primero.)

**Checkpoint**: `PYTHONPATH=. pytest tests/test_audit_calibration.py --tb=short -q` → 0 failures.

---

## Phase 4: User Story 2 — Alinear contrato de errores CLI: `CLIError` vs `SystemExit` (Priority: P1)

**Goal**: Update 5 tests that assert `pytest.raises(SystemExit)` to assert `pytest.raises(CLIError)` instead.

**Independent Test**:
```bash
PYTHONPATH=. pytest tests/test_model_evaluator_error_cases.py \
  tests/test_model_evaluator_integration_paths.py \
  -k "propagates_error or requires_dataset or validates_missing" --tb=short -q
```

### Implementation for User Story 2

- [ ] T005 [P] [US2] En `tests/test_model_evaluator_error_cases.py` **líneas 279 y 328**: 
  - Línea 279: cambiar `pytest.raises(SystemExit, match="Gap analysis generation failed")` → `pytest.raises(CLIError, match="Gap analysis generation failed")`
  - Línea 328: cambiar `pytest.raises(SystemExit, match="Exam generation failed")` → `pytest.raises(CLIError, match="Exam generation failed")`
  - Verificar que `CLIError` ya está importado en la cabecera del archivo (`from src.audit.cli import CLIError`); añadirlo si falta.
- [ ] T006 [P] [US2] En `tests/test_model_evaluator_integration_paths.py`, cambiar las 3 ocurrencias de `pytest.raises(SystemExit)` a `pytest.raises(CLIError)`:
  - Línea ~230: `pytest.raises(SystemExit, match="--dataset is required")` → `pytest.raises(CLIError, match="--dataset is required")`
  - Línea ~371: `pytest.raises(SystemExit, match="validation failed")` → `pytest.raises(CLIError, match="validation failed")`
  - Línea ~906: `pytest.raises(SystemExit, match="Exam generation failed")` → `pytest.raises(CLIError, match="Exam generation failed")`
  - Añadir `from src.audit.cli import CLIError` en la sección de imports del archivo si no está presente.

**Checkpoint**: `PYTHONPATH=. pytest tests/test_model_evaluator_error_cases.py tests/test_model_evaluator_integration_paths.py --tb=short -q` → 0 failures in the 5 affected tests.

---

## Phase 5: User Story 3 — Corregir mock de `llm_judge_score` en `TestCmdScorePhase5` (Priority: P2)

**Goal**: Add `patch("src.audit.cli.llm_judge_score")` mock to both test methods in `TestCmdScorePhase5` so no real HTTP call is made.

**Independent Test**:
```bash
PYTHONPATH=. pytest tests/test_model_evaluator.py::TestCmdScorePhase5 --tb=short -q
```

### Implementation for User Story 3

- [ ] T007 [US3] En `tests/test_model_evaluator.py::TestCmdScorePhase5`: añadir mock de `src.audit.cli.llm_judge_score` a **ambos** métodos de la clase:
  - `test_scores_records_and_generates_report`
  - `test_falls_back_to_sample_when_no_exam_for_scoring`
  
  El mock debe devolver una estructura compatible con `NormalizedJudgeResponse` (TypedDict con claves `baseline`, `adapter`, `reasoning`):
  ```python
  @patch(
      "src.audit.cli.llm_judge_score",
      return_value={"baseline": {"ha_modernity": 0.8}, "adapter": {"ha_modernity": 0.9}, "reasoning": "mock"},
  )
  ```
  O como `with patch(...)` en el cuerpo del test. Añadir el parámetro del mock (`mock_judge`) a la firma del método.
  
  **Sin este mock**: `cmd_score` intenta `llm_judge_score(...)` → `InferenceRouter.professor(...)` → `VLLMClient` → `requests.post('http://localhost:8000/v1/chat/completions')` → `ConnectionRefusedError`. La tarea debe asegurarse de que CERO conexiones HTTP reales ocurran.

**Checkpoint**: `PYTHONPATH=. pytest tests/test_model_evaluator.py::TestCmdScorePhase5 --tb=short -q` → 0 failures; no `ConnectionRefusedError` or `HTTPError` in output.

---

## Phase 6: User Story 4 — Crear `php_hexagonal.yaml` y corregir header de `multi_legacy.yaml` (Priority: P2)

**Goal**: Create the missing example config file with valid AEGF header and required keys; fix the header on the existing `multi_legacy.yaml`.

**Independent Test**:
```bash
PYTHONPATH=. pytest tests/unit/test_example_configs.py --tb=short -q
```

### Implementation for User Story 4

- [ ] T008 [P] [US4] Create `configs/stage_1_discovery/examples/php_hexagonal.yaml` with full AEGF copyright header (matching `configs/stage_1_discovery/examples/homeassistant.yaml` header block) and these required keys: `profile: php_hexagonal`, `display_name`, `description`, `extractor` (with `on_parse_error: skip`), `module_discovery` (with `strategy: filesystem`)
- [ ] T009 [P] [US4] Prepend the full AEGF copyright header block to `configs/stage_1_discovery/examples/multi_legacy.yaml` so the file contains `"Architect-Expert-Gap-Forge (AEGF)"`, `"Copyright"`, and `"Apache License"` — keep all existing YAML content intact after the header

**Checkpoint**: `PYTHONPATH=. pytest tests/unit/test_example_configs.py --tb=short -q` → 0 failures; both files are valid YAML with correct headers.

---

## Phase 7: User Story 5 — Corregir tests de Gemini que requieren `GOOGLE_API_KEY` (Priority: P2)

**Goal**: Add `patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"})` to the tests in `TestInferenceRouterGeminiPaths` and `test_explicit_gemini_passes_through` that invoke `_resolve_backend("gemini")` without a key present.

**Independent Test**:
```bash
PYTHONPATH=. pytest tests/test_inference.py -k "Gemini or gemini" --tb=short -q
```

### Implementation for User Story 5

- [ ] T010 [US5] En `tests/test_inference.py`, abordar dos sub-problemas independientes:

  **Sub-problema 5a — `TestInferenceRouterGeminiPaths`**: Los tres métodos ya parchean la clase `GeminiClient` completa (`patch('src.audit.inference.GeminiClient', return_value=mock_instance)`), por lo que el `__init__` real (que chequea `GOOGLE_API_KEY`) nunca se ejecuta. **No requieren cambios** si ya pasan; verificar ejecutando el grupo en aislamiento.

  **Sub-problema 5b — `TestGeminiClientWithMock._make_client`**: Instancia `GeminiClient(model='gemini-test')` directamente. Si `google-genai` SDK no está instalado en CI, `_GEMINI_AVAILABLE = False` a nivel de módulo y el constructor lanza `ImportError` antes de alcanzar el mock del SDK. **Corrección**: añadir `patch('src.audit.inference._GEMINI_AVAILABLE', True)` envolviendo la instanciación dentro de `_make_client`:
  ```python
  with patch("src.audit.inference._GEMINI_AVAILABLE", True):
      with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-ci-key"}):
          client = GeminiClient(model="gemini-test")
  ```

  **Sub-problema 5c — `TestInferenceRouterResolveBackend::test_explicit_gemini_passes_through`**: solo devuelve el string `"gemini"`, no instancia ningún cliente. No requiere cambios.

  Verificar que `import os` y los imports de `patch.dict` están presentes en el archivo.

**Checkpoint**: `PYTHONPATH=. pytest tests/test_inference.py -k "Gemini or gemini" --tb=short -q` → 0 failures; no `EnvironmentError: Missing required environment variable: GOOGLE_API_KEY`.

---

## Phase 8: User Story 6 — Corregir `test_load_master_docs_file_reading` (Priority: P3)

**Goal**: Add `monkeypatch` parameter and `AEGF_DOC_*` env var overrides to `test_load_master_docs_file_reading` so the loader uses the files the test creates in `tmp_path` instead of the HA-specific names from `eval_config.yaml`.

**Independent Test**:
```bash
PYTHONPATH=. pytest \
  "tests/test_model_evaluator_config_and_cli.py::TestLoadMasterDocsIntegration::test_load_master_docs_file_reading" \
  --tb=short -q
```

### Implementation for User Story 6

- [ ] T011 [US6] In `tests/test_model_evaluator_config_and_cli.py::TestLoadMasterDocsIntegration::test_load_master_docs_file_reading`: add `monkeypatch` as a parameter; add these lines before the `load_master_docs()` call:
  ```python
  monkeypatch.setenv("AEGF_DOC_1", "reference_guide.md")
  monkeypatch.setenv("AEGF_DOC_2", "technical_changelog.md")
  monkeypatch.setenv("AEGF_DOC_3", "syntax_guide.md")
  ```
  so the env-var tier of the cascade resolves the files created by `tmp_path`

**Checkpoint**: `PYTHONPATH=. pytest "tests/test_model_evaluator_config_and_cli.py::TestLoadMasterDocsIntegration::test_load_master_docs_file_reading" --tb=short -q` → PASSED.

---

---

## Phase 9: Polish & Verification

- [ ] T013 [US-ALL] **Escaneo de llamadas externas sin mock**: Ejecutar el siguiente comando desde la raiz del repo y confirmar que CADA línea devuelta está dentro de un contexto `with patch(...)` o es una importación:
  ```bash
  grep -rn 'requests\.\|genai\.Client\|anthropic\.' tests/ | grep -v '#\|import\|patch\|mock\|MagicMock'
  ```
  Si hay resultados sin mock, abrir el test correspondiente y añadir el patch antes de proceder a T012.

- [ ] T012 Run the full test suite `PYTHONPATH=. pytest --tb=short -q` and verify the output shows `0 failed` (previously 37); record final count in `progress.txt` if it exists

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phases 3–8 (User Stories)**: Depend only on Phase 1 confirmation
  - All 6 story phases are **fully independent** — can proceed in parallel
  - Recommended sequential order (by risk): US4 → US2 → US5 → US6 → US3 → US1
- **Phase 9 (Polish)**: Depends on all story phases complete

### User Story Independence

| Story | Depends On | Blocks |
|-------|-----------|--------|
| US1 (P1) — calibration schema | None | Nothing |
| US2 (P1) — CLIError contract | None | Nothing |
| US3 (P2) — llm_judge_score mock | None | Nothing |
| US4 (P2) — php_hexagonal.yaml | None | Nothing |
| US5 (P2) — Gemini env mock | None | Nothing |
| US6 (P3) — doc_loader monkeypatch | None | Nothing |

### Parallel Opportunities

- **T003** can run alongside **T002** (different constants in same file — but T002 must complete first if edits are to the same dataclass body; split if using independent replace operations)
- **T005** and **T006** are fully independent (different test files) — run in parallel
- **T008** and **T009** are fully independent (different files) — run in parallel
- All of **T002–T011** can be applied by an LLM in a single pass if no merge conflicts exist

### Parallel Example: All P2 stories (US3, US4, US5)

```bash
# Worker A: US3 — T007
# Worker B: US4 — T008 + T009 (parallel within US4)
# Worker C: US5 — T010

# After all complete:
PYTHONPATH=. pytest tests/test_model_evaluator.py::TestCmdScorePhase5 \
  tests/unit/test_example_configs.py \
  tests/test_inference.py -k "Gemini or gemini" --tb=short -q
```

---

## Implementation Strategy

**MVP Scope (minimum to unblock CI)**: US1 + US2 only (fixes 15 tests, both P1).

**Full Green Suite**: Complete all 6 stories (T002–T011) in any order — all are independent.

**Recommended single-session order** (lowest risk first):

1. T008 + T009 — pure file creation/header edit, zero logic risk
2. T005 + T006 — test assertion change, mechanical substitution
3. T010 — add env mock decorator, pattern already used in `_make_client()`
4. T011 — add monkeypatch + setenv, standard pytest pattern
5. T007 — add patch decorator + mock return value
6. T002 + T003 + T004 — source code change (highest risk, run suite after)
7. T012 — final verification
