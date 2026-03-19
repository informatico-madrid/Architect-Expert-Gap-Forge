# Feature Specification: Fix 37 Failing Tests

**Feature Branch**: `011-fix-failing-tests`  
**Created**: 2026-03-19  
**Status**: Draft  
**Input**: User description: "Alguna spec se ha hecho mal y están fallando los tests. 37 failed, 1092 passed. Crear una spec para que todos los tests queden en verde."

## Contexto del Problema

El proyecto tiene 37 tests fallando como consecuencia de cambios recientes en la implementación que no fueron alineados con los tests existentes (o viceversa). Los fallos se agrupan en **6 causas raíz distintas** que deben resolverse de forma independiente.

### Diagnóstico: Causas Raíz

| # | Causa Raíz | Tests afectados | Archivos implicados |
|---|-----------|----------------|---------------------|
| A | `SamplingProfile` **contiene** el campo `top_p` pero los tests asumen que fue eliminado; hay que eliminarlo del schema y sus callers | 7 en `test_audit_calibration.py` + 3 en `test_inference.py` | `src/audit/calibration.py`, `src/audit/calibration_schema.py` |
| B | CLI cambió de `sys.exit()` a lanzar `CLIError`; tests esperan `SystemExit` | 2 en `test_model_evaluator_error_cases.py` + 3 en `test_model_evaluator_integration_paths.py` | `src/audit/cli.py` |
| C | `cmd_score` llama a `llm_judge_score` antes de `compute_scorecard`; tests solo mockean `compute_scorecard` | 2 en `test_model_evaluator.py` + 1 en `test_model_evaluator_integration_paths.py` | `src/audit/cli.py` |
| D | Archivo de ejemplo `configs/stage_1_discovery/examples/php_hexagonal.yaml` no existe; header del config existente no contiene texto esperado | 4 en `test_example_configs.py` | `configs/stage_1_discovery/examples/` |
| E | Tests de rutas Gemini no mockean `GOOGLE_API_KEY`; tests de inferencia Gemini necesitan mock del cliente SDK | 5 en `test_inference.py` | `src/audit/inference.py`, `tests/test_inference.py` |
| F | `test_load_master_docs_file_reading` no provee los archivos fixture esperados por el loader en la ruta `tmp_path` | 1 en `test_model_evaluator_config_and_cli.py` | `src/utils/doc_loader.py`, test correspondiente |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Eliminar `top_p` del contrato `SamplingProfile` (Priority: P1)

Un desarrollador ejecuta la suite de tests de calibración e inferencia y todos pasan; `top_p` ha sido eliminado de `SamplingProfile`, `CALIBRATION_GRID` y `VALID_PARAMETERS` en `src/audit/calibration_schema.py`, y de todos sus callers en `src/audit/calibration.py`.

**Por qué P1**: Afecta 10 tests en dos módulos críticos (`calibration` e `inference`). El campo `top_p` es parte del contrato público de la API de calibración.

**Independent Test**: `pytest tests/test_audit_calibration.py tests/test_inference.py -k "calibration or Gemini" --tb=short` — debe pasar sin errores de `TypeError: missing argument 'top_p'` ni `KeyError: 'top_p'`.

**Acceptance Scenarios**:

1. **Given** `SamplingProfile` se inicializa sin el parámetro `top_p`, **When** se ejecutan los tests de calibración, **Then** todos pasan (no `TypeError`).
2. **Given** `generate_profiles(grid)` recibe una grilla sin clave `top_p`, **When** se llama la función, **Then** no lanza `KeyError` y genera las combinaciones esperadas.
3. **Given** `VALID_PARAMETERS` en `calibration.py`, **When** se compara con el conjunto esperado en el test, **Then** los conjuntos son iguales (sin `top_p` sobrante).

---

### User Story 2 — Alinear contrato de errores CLI: `CLIError` vs `SystemExit` (Priority: P1)

Un desarrollador que ejecuta `pytest tests/test_model_evaluator_error_cases.py tests/test_model_evaluator_integration_paths.py` ve todos los tests en verde.

**Por qué P1**: Afecta el contrato de error de la CLI. La inconsistencia indica que bien (a) la CLI debe volver a lanzar `SystemExit` cuando una operación falla, o bien (b) los tests deben actualizarse para esperar `CLIError`. Se debe elegir una solución y aplicarla de forma consistente.

**Assumption**: La solución preferida es actualizar los tests para esperar `CLIError` con el mensaje correcto, ya que `CLIError` es la excepción tipada definida en el módulo y su uso es consistente en el resto de la CLI.

**Independent Test**: `pytest tests/test_model_evaluator_error_cases.py -k "propagates_error" --tb=short` — pasa sin `assert CLIError != SystemExit`.

**Acceptance Scenarios**:

1. **Given** `cmd_sample` recibe un mock que lanza `PromptGenerationError`, **When** se ejecuta, **Then** el test captura correctamente `CLIError` con el mensaje esperado.
2. **Given** `cmd_generate_exam` recibe un mock que lanza `PromptGenerationError`, **When** se ejecuta, **Then** el test captura correctamente `CLIError` con el mensaje esperado.
3. **Given** `cmd_sample` sin `--dataset` en modo generación, **When** se ejecuta, **Then** se lanza `CLIError` con mensaje `"--dataset is required"`.

---

### User Story 3 — Corregir mock de `llm_judge_score` en tests de `cmd_score` (Priority: P2)

Los tests de `TestCmdScorePhase5` pasan completamente sin hacer llamadas HTTP reales al servidor vLLM.

**Por qué P2**: Afecta 2-3 tests de scoring que son críticos para verificar la fase 5 del pipeline. El test asume que mockear `compute_scorecard` es suficiente, pero la implementación llama a `llm_judge_score` primero.

**Independent Test**: `pytest tests/test_model_evaluator.py::TestCmdScorePhase5 --tb=short` — ningún test hace conexiones HTTP reales y todos pasan.

**Acceptance Scenarios**:

1. **Given** `cmd_score` con datos de exam, baseline e adapter en disco, **When** se mockean tanto `llm_judge_score` como `compute_scorecard`, **Then** el test pasa sin `HTTPError` ni conexiones a `localhost:8000`.
2. **Given** `cmd_score` sin archivo de exam, **When** se mockean las funciones de juez, **Then** el test usa el fallback al sample sin errores.

---

### User Story 4 — Crear config de ejemplo `php_hexagonal.yaml` y corregir header (Priority: P2)

Los tests que verifican la existencia y formato de archivos de ejemplo de Stage 1 pasan sin errores de archivo no encontrado.

**Por qué P2**: Afecta 4 tests que validan que los archivos de configuración de ejemplo existen y tienen el header AEGF correcto. Son tests de validación de documentación/configuración.

**Independent Test**: `pytest tests/unit/test_example_configs.py --tb=short` — todos los 4 tests pasan (2 de existencia, 1 de keys, 1 de header).

**Acceptance Scenarios**:

1. **Given** el directorio `configs/stage_1_discovery/examples/` existe, **When** se verifica la presencia de `php_hexagonal.yaml`, **Then** el archivo existe y es YAML válido.
2. **Given** el archivo `php_hexagonal.yaml`, **When** se lee su contenido, **Then** contiene las claves requeridas por el test.
3. **Given** cualquier config de ejemplo en `configs/stage_1_discovery/examples/`, **When** se lee su header, **Then** contiene el texto `"Architect-Expert-Gap-Forge (AEGF)"`.

---

### User Story 5 — Corregir tests de Gemini que requieren `GOOGLE_API_KEY` (Priority: P2)

Los tests de rutas Gemini en `TestInferenceRouterGeminiPaths` y `TestGeminiClientWithMock` pasan sin requerir una clave API real.

**Por qué P2**: Afecta 5 tests de inferencia. Cualquier entorno CI que no tenga `GOOGLE_API_KEY` verá estos tests fallar aunque el código sea correcto.

**Independent Test**: `pytest tests/test_inference.py -k "Gemini" --tb=short` — pasan sin `OSError: Missing required environment variable: GOOGLE_API_KEY`.

**Acceptance Scenarios**:

1. **Given** no hay `GOOGLE_API_KEY` en el entorno, **When** se ejecutan los tests de `TestInferenceRouterGeminiPaths`, **Then** los tests pasan mediante mock del cliente Gemini o inyección de la variable de entorno.
2. **Given** `TestGeminiClientWithMock`, **When** se ejecuta con el SDK de Gemini mockeado, **Then** todos los tests de comportamiento del cliente pasan.

---

### User Story 6 — Corregir `test_load_master_docs_file_reading` (Priority: P3)

El test de carga de documentos maestros pasa usando fixtures de archivos en `tmp_path`.

**Por qué P3**: 1 solo test afectado. El loader busca el archivo en `tmp_path/gap_audit/HA_MASTER_GUIDE_2026.md` pero el test no lo crea ahí.

**Independent Test**: `pytest tests/test_model_evaluator_config_and_cli.py::TestLoadMasterDocsIntegration --tb=short` — pasa sin `FileNotFoundError`.

**Acceptance Scenarios**:

1. **Given** un directorio temporal con la estructura `gap_audit/HA_MASTER_GUIDE_2026.md`, **When** se llama al loader, **Then** devuelve el contenido del archivo sin lanzar `FileNotFoundError`.

---

### Edge Cases

- ¿Qué ocurre si se eliminan otros campos de `SamplingProfile` en el futuro? Los tests deben ser robustos a cambios de schema documentando los campos requeridos.
- ¿El comportamiento `CLIError` vs `SystemExit` debe ser consistente en toda la CLI o solo en los comandos afectados?
- ¿El archivo `php_hexagonal.yaml` debe ser un ejemplo real funcional o un stub mínimo que pase las validaciones?
- **[Riesgo A11] `top_p` aparece en ~171 lugares del repositorio** (`grep -rc 'top_p' src/ tests/ | awk -F: '{s+=$2}END{print s}'`). La eliminación en T002–T004 debe ser **quirúrgica**: solo `SamplingProfile`, `CALIBRATION_GRID`, `VALID_PARAMETERS` y sus callers directos en `calibration.py`. Confirmar con `grep -n 'top_p' src/audit/calibration_schema.py src/audit/calibration.py` que no queda ninguna referencia antes de ejecutar el checkpoint de T004.
- **[Riesgo E detalle] `TestGeminiClientWithMock._make_client`** instancia `GeminiClient` directamente. Si `google-genai` no está instalado en el entorno CI, `_GEMINI_AVAILABLE = False` a nivel de módulo y el constructor lanza `ImportError` antes de llegar al mock del SDK. La corrección (T010) DEBE incluir `patch('src.audit.inference._GEMINI_AVAILABLE', True)` en `_make_client`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `SamplingProfile` NO DEBE contener el campo `top_p`. Los tests son el contrato: no incluyen `top_p` en ninguna instanciación ni en `VALID_PARAMETERS`. La solución correcta es eliminar `top_p` de `calibration_schema.py` y de todos sus callers en `calibration.py`, no al revés.
- **FR-002**: `generate_profiles(grid)` DEBE manejar grillas sin clave `top_p` sin lanzar `KeyError`.
- **FR-003**: `VALID_PARAMETERS` en `calibration.py` DEBE ser el mismo conjunto que el definido como esperado en `test_audit_calibration.py::TestCalibrationPrompt::test_valid_parameters_contains_expected`.
- **FR-004**: Los tests de `cmd_sample` y `cmd_generate_exam` que prueban propagación de errores DEBEN usar `pytest.raises(CLIError)` (o la CLI debe volver a usar `sys.exit()` de forma consistente); la elección debe aplicarse a todos los tests afectados de forma uniforme.
- **FR-005**: Los tests de `TestCmdScorePhase5` DEBEN mockear `llm_judge_score` además de `compute_scorecard` para evitar llamadas HTTP reales.
- **FR-006**: El archivo `configs/stage_1_discovery/examples/php_hexagonal.yaml` DEBE existir, ser YAML válido, contener las claves requeridas y tener un header que incluya `"Architect-Expert-Gap-Forge (AEGF)"`.
- **FR-007**: Los configs de ejemplo existentes en `configs/stage_1_discovery/examples/` DEBEN tener un header que contenga `"Architect-Expert-Gap-Forge (AEGF)"`.
- **FR-008**: Los tests de `TestInferenceRouterGeminiPaths` DEBEN mockear la variable de entorno `GOOGLE_API_KEY` o el resolver del backend para no requerir credenciales reales.
- **FR-009**: `TestGeminiClientWithMock` DEBEN proveer un mock del cliente SDK de Gemini para que todos los tests de comportamiento pasen sin credenciales reales.
- **FR-010**: El test `test_load_master_docs_file_reading` DEBE crear los archivos de fixture en la ruta que el loader espera dentro de `tmp_path`.
- **FR-011**: Ningún test de la suite PUEDE realizar llamadas reales a servicios externos (HTTP, API LLM, SDK de terceros sin mock). Toda interacción con `GeminiClient`, `VLLMClient`, `llm_judge_score`, y cualquier función que abra sockets o invoque SDKs DEBE ser mockeada via `unittest.mock.patch`, `patch.dict` o `monkeypatch`. Cuando el SDK de `google-genai` no está instalado, los tests de `GeminiClient` DEBEN parchear `src.audit.inference._GEMINI_AVAILABLE = True` para poder instanciar el cliente bajo mock. Esto deriva directamente de la constitución §VI: *"CI uses local mocks for external services; avoid live external calls during CI."*

### Key Entities

- **`SamplingProfile`**: Dataclass que representa un perfil de muestreo con parámetros de temperatura, top_k, min_p. Su schema actual (con o sin `top_p`) define el contrato del sistema de calibración.
- **`CLIError`**: Excepción tipada de la CLI que indica un error operacional. Define el contrato de error hacia los callers de funciones CLI.
- **`generate_profiles(grid)`**: Función que genera todas las combinaciones de perfiles de muestreo a partir de una grilla de parámetros.
- **`VALID_PARAMETERS`**: Conjunto de nombres de parámetros válidos para el prompt de calibración.
- **`llm_judge_score`**: Función que llama al LLM juez para obtener una evaluación; debe ser mockeada en tests unitarios de `cmd_score`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La suite completa de tests produce **0 tests fallidos** (actualmente 37 fallidos de 1129 totales).
- **SC-002**: Ningún test requiere servicios externos activos (vLLM en `localhost:8000`, `GOOGLE_API_KEY` real) para ejecutarse — todos los tests que interactúan con servicios externos usan mocks.
- **SC-003**: Los tests de calibración (`test_audit_calibration.py`) pasan al 100% sin modificar la lógica de negocio de `calibration.py` — solo se alinea el schema/contrato.
- **SC-004**: Los tests de configuración de ejemplo (`test_example_configs.py`) pasan al 100% con la creación del archivo faltante y corrección de headers.
- **SC-005**: El tiempo total de ejecución de la suite de tests no aumenta más de un 10% respecto al baseline actual (~20 segundos).
- **SC-006**: Durante la ejecución completa de la suite de tests no se producen conexiones de red salientes. Verificable con: `grep -rn 'requests\.' tests/ | grep -v 'mock\|patch\|MagicMock\|#\|import'` — todo resultado DEBE estar dentro de un bloque `with patch(...)` o ser una importación.

## Assumptions

- La decisión sobre `CLIError` vs `SystemExit` se resuelve actualizando los tests para usar `CLIError`, dado que el código actual usa `CLIError` de forma consistente y es la excepción tipada correcta para este módulo. Los 5 tests que actualmente asignan `pytest.raises(SystemExit, ...)` serán actualizados a `pytest.raises(CLIError, ...)`.
- El schema actual de `SamplingProfile` en `src/audit/calibration_schema.py` **aún contiene** `top_p`; son los tests los que ya asumen que fue eliminado. La decisión correcta es hacer que el código converja con los tests (eliminar `top_p`), no modificar los tests para reintroducirlo.
- El archivo `php_hexagonal.yaml` debe ser un ejemplo mínimo pero funcional que represente una configuración típica de Stage 1 para un codebase PHP hexagonal.
- Los tests de Gemini se resuelven mediante `monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")` combinado con mock del cliente SDK, no añadiendo la clave real al entorno CI.

## Out of Scope

- No se cambia la lógica de negocio de los módulos de calibración, inferencia o CLI más allá de lo necesario para alinear el contrato de las APIs.
- No se añaden nuevas clases ni módulos de test; solo se corrigen tests existentes (cambiar asserts, añadir mocks/decoradores/parámetros) y se crean los archivos de fixtures/configuración faltantes (`php_hexagonal.yaml`, header de `multi_legacy.yaml`).
- No se modifica la configuración de pytest ni se añaden markers de skip.
