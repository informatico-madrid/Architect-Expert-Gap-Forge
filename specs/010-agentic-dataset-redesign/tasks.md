# Tasks: Rediseño del Pipeline de Generación de Datos Sintéticos Agénticos

**Feature Branch**: `010-agentic-dataset-redesign`
**Input**: Design documents from `/specs/010-agentic-dataset-redesign/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅
**Generated**: 2026-03-19

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia de tareas incompletas)
- **[Story]**: Historia de usuario a la que pertenece la tarea ([US1]–[US5])
- Las tareas de Setup y Foundational **no** llevan etiqueta de historia

---

## Phase 1: Setup (Infraestructura Compartida)

**Purpose**: Directorios, dependencias y configuraciones de arranque.

- [ ] T001 Crear directorios de tests faltantes: `tests/factory/`, `tests/curation/`, `tests/factory/__init__.py`, `tests/curation/__init__.py`
- [ ] T002 [P] Añadir dependencias nuevas a `requirements.txt`: `httpx>=0.27`, `huggingface-hub>=0.22`, `datasets>=2.19`, `tiktoken>=0.7`, `click>=8.1` (si no están ya)
- [ ] T003 [P] Crear `configs/stage_2_factory/config.homeassistant.yaml` con bloque `teacher_model.*` y `dataset.*` de valores por defecto documentados (sin credenciales hardcodeadas)

**Checkpoint**: Directorio listo, dependencias instalables, config de ejemplo en repo.

---

## Phase 2: Foundational (Prerequisitos Bloqueantes)

**Purpose**: Código base compartido del que dependen TODAS las historias de usuario.

**⚠️ CRÍTICO**: Ninguna historia de usuario puede comenzarse hasta que esta fase esté completa.

- [ ] T004 [P] Implementar `src/factory/schema.py` — modelos Pydantic v2 inmutables **factory-specific**: `TurnType` (Enum), `TrajectoryMode` (Enum: `hard_query`/`explicit`/`no_call`), `Turn`, `SimulatedErrorType` (Enum: `tool_failure`/`wrong_result`/`cascade_failure`), `SimulatedError`, `AgenticTrajectory` (incluye campo `mode: TrajectoryMode` desde el inicio — *remedia G3*); re-exportar `DatasetRecord`, `CompositionReport` desde `src/utils/schema.py` (ver T038); incluir header AEGF
- [ ] T005 Extender `src/factory/config.py` — añadir `TeacherModelConfig` y `DatasetConfig` como `@dataclass(slots=True, frozen=True)` o modelos Pydantic; exponer función `load_teacher_config(path: Path) -> TeacherModelConfig`; importar `ConfigValidationError` desde `src/utils/exceptions.py` (ver T036); **Nota D1**: la validación de `neftune_noise_alpha` es responsabilidad exclusiva de Stage 4 — ver T030 en `src/training/config_validator.py`
- [ ] T006 [P] Extender `src/factory/checkpoint.py` — añadir clase `GenerationCheckpoint` con métodos: `mark_done(seed_id: str) -> None`, `is_done(seed_id: str) -> bool`, `resume_from(path: Path) -> GenerationCheckpoint` (carga estado de disco); asegurar persistencia atómica (write-then-rename); **Nota G2**: si Stage 3 requiere la misma lógica de reanudo, extraer la clase base genérica a `src/utils/checkpoint.py` y hacer que `src/factory/checkpoint.py` la extienda

**Checkpoint**: Schema, config y checkpoint operativos; todos los módulos US1–US5 pueden importarlos.

---

## Phase 3: User Story 1 — Trayectorias Multi-Turno con Backtracking (Priority: P1) 🎯 MVP

**Goal**: Ejecutar Stage 2 con `--mode trajectories` y obtener JSONL cuyas conversaciones tienen 3–10 turnos con al menos 1 error inyectado y 1 bloque de corrección.

**Independent Test**: `pytest tests/factory/test_trajectory_generator.py -v` sobre 100 seeds; verificar que el 100% de registros tiene `len(trajectory.turns) >= 3` y al menos 1 turno de tipo `error` + 1 de tipo `correct`.

### Tests para US1

- [ ] T011 [P] [US1] Crear `tests/fixtures/seed_examples.yaml` — 8–10 seeds HA representativas extraídas de `configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml`; prerequisito de T007 y T008 *(fixtures primero — remedia I3)*
- [ ] T007 [P] [US1] Crear `tests/factory/test_teacher_client.py` — tests unitarios con mock httpx (cubrir los tres providers del Strategy: OpenAI, Anthropic, Gemini): llamada OK, retry en 429/503, backoff exponencial (verificar sleeps con mock time), agotamiento de `max_retries` lanza `TeacherAPIError`, seeds completadas en checkpoint se omiten
- [ ] T008 [P] [US1] Crear `tests/factory/test_trajectory_generator.py` — tests unitarios: longitud de trayectoria entre 3 y 10 turnos, presencia obligatoria de turno tipo `error` + turno tipo `correct`, generación de `cascade_failure`, campo `mode: TrajectoryMode` presente, serialización a ChatML `messages[]`

### Implementación de US1

- [ ] T009 [US1] Implementar `src/factory/agentic_teacher_client.py` — **Strategy pattern** (alinea con `src/audit/inference.py`): definir `TeacherProviderStrategy` (Protocol: `async def generate(prompt: str, cfg: TeacherModelConfig) -> str`), implementaciones `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`; router `TeacherModelClient` selecciona proveedor vía `teacher_model.provider`; usar `httpx.AsyncClient` (I/O no bloqueante, `asyncio.to_thread` para wrappers síncronos); `request_delay_ms`, reintentos con backoff exponencial ante HTTP 429/500/502/503/timeout; integración con `GenerationCheckpoint`; importar `TeacherAPIError`, `ConfigValidationError` desde `src/utils/exceptions.py` (ver T036); header AEGF; sin side effects en import *(remedia C2+U2)*
- [ ] T010 [US1] Implementar `src/factory/trajectory_generator.py` — `TrajectoryGenerator`: **carga templates de turno desde `configs/stage_2_factory/prompts/trajectory_templates.yaml`** vía loader (patrón `src/audit/prompt_manager.py`; sin strings hardcodeadas en código); genera `AgenticTrajectory` con 3–10 turnos Observación→Razonamiento→Acción; inyecta `SimulatedError` con probabilidades configurables; fuerza turno de corrección tras error; serializa a lista de mensajes ChatML; header AEGF *(remedia C1)*
- [ ] T012 [US1] Añadir comando CLI `generate-trajectories` en `src/factory/agentic_cli.py` — flags: `--use-case`, `--mode trajectories`, `--config <yaml>`, `--output <jsonl>`, `--target-records <int>` (sobrescribe `dataset.target_specialized_records` del YAML; remedia A1), `--dry-run`; delega en `TrajectoryGenerator`; imprime progreso con `tqdm`

**Checkpoint**: `src/factory/agentic_cli.py generate-trajectories --use-case home_assistant --dry-run` completa sin errores; tests de US1 en verde.

---

## Phase 4: User Story 2 — Hard Queries con Objetivos Abstractos (Priority: P1)

**Goal**: Generar prompts de turno 1 que describan únicamente el estado objetivo final sin mencionar herramientas ni pasos, forzando al modelo a razonar autónomamente.

**Independent Test**: Generar 50 hard queries; validar que ningún prompt del turno 1 contiene nombres de herramientas ni verbos imperativos específicos (lista de términos prohibidos configurable).

### Tests para US2

- [ ] T013 [P] [US2] Crear `tests/factory/test_hard_query_builder.py` — tests unitarios: prompt generado no contiene términos prohibidos, descripción abstracta del objetivo, fixture de 5 seeds; test negativo: prompt con nombre de tool explícito es rechazado por el validador léxico

### Implementación de US2

- [ ] T014 [US2] Implementar `src/factory/hard_query_builder.py` — `HardQueryBuilder`: **carga templates de objetivos abstractos desde `configs/stage_2_factory/prompts/hard_query_templates.yaml`** vía loader; `FORBIDDEN_TERMS` también externalizada en el YAML (sin strings hardcodeadas); `validate_prompt(text: str) -> bool`; header AEGF *(remedia C1)*
- [ ] T015 [US2] Integrar modo `hard_query` en `src/factory/trajectory_generator.py` — cuando `mode == "hard_query"`, el turno 1 se genera via `HardQueryBuilder.build(seed)` en lugar del template explícito; añadir `mode` a `AgenticTrajectory.mode`

**Checkpoint**: `pytest tests/factory/test_hard_query_builder.py` y `test_trajectory_generator.py`en verde; US1 + US2 operativos.

---

## Phase 5: User Story 3 — Data Mixing con Datasets Ancla (Priority: P2)

**Goal**: Stage 3 descarga datasets ancla de HF Hub, normaliza a ChatML, mezcla 30/70 por tokens, desduplicata y exporta un único JSONL determinista para Axolotl.

**Independent Test**: Ejecutar Stage 3 sobre un subset de 1000 registros especializados + 500 registros Alpaca de muestra. Verificar: todos los registros tienen estructura ChatML idéntica, proporción de tokens entre 28–32% / 68–72%, 0 duplicados por hash.

### Tests para US3

- [ ] T016 [P] [US3] Crear `tests/curation/test_format_normalizer.py` — tests: Alpaca→ChatML (instruction+output), ShareGPT→ChatML (conversations[]), OpenAI Messages passthrough, registro sin `messages` ni campos Alpaca es rechazado con excepción
- [ ] T017 [P] [US3] Crear `tests/curation/test_anchor_dataset_downloader.py` — tests con mock de `huggingface_hub.snapshot_download`: parse de xlam-function-calling-60k, FineTome-100k y Magicoder; submuestreo por token_count; exporta JSONL válido
- [ ] T018 [P] [US3] Crear `tests/curation/test_dataset_mixer.py` — tests: proporción de tokens dentro de 28–32%/68–72%, mismo seed produce mismo orden (determinismo), JSONL de salida tiene 100% registros con campo `messages`, reporte de composición incluye campos obligatorios
- [ ] T019 [P] [US3] Crear `tests/curation/test_dedup_validate.py` — tests: registro duplicado entre datasets especializados y ancla es eliminado, registro etiquetado no-call con `<tool_call>` en content es descartado, log de descartes contiene `seed_id` y `reason`

### Implementación de US3

- [ ] T020 [P] [US3] Implementar `src/curation/format_normalizer.py` — `FormatNormalizer`: detecta formato (Alpaca, ShareGPT, OpenAI Messages), convierte a `DatasetRecord` con `messages: [{role, content}]`; importar `DatasetRecord` desde `src/utils/schema.py` (ver T038); importar `NormalizationError` desde `src/utils/exceptions.py` (ver T036); header AEGF *(remedia I1)*
- [ ] T021 [P] [US3] Implementar `src/curation/anchor_dataset_downloader.py` — `AnchorDatasetDownloader`: descarga datasets desde HF Hub (streaming), parsea en formato nativo, aplica submuestreo por token budget, exporta JSONL parcial; configurable via lista de `AnchorDatasetConfig`; header AEGF
- [ ] T022 [US3] Implementar `src/curation/dedup_and_validate.py` — **Nota D2**: verificar primero si `src/curation/dedup_filter.py` (existente) puede extenderse; si no, documentar en el módulo por qué se crea uno nuevo. `DedupAndValidate`: hash SHA-256 por contenido normalizado del campo `messages`; validador no-call (rechaza registros con `<tool_call>` o JSON de tool call en `content`); importar `DatasetRecord` desde `src/utils/schema.py`, `DeduplicationError` desde `src/utils/exceptions.py` (ver T036, T038); log de descartes con `reason`; header AEGF *(remedia I1+D2)*
- [ ] T023 [US3] Implementar `src/curation/dataset_mixer.py` — `DatasetMixer`: cuenta tokens con `tiktoken` modelo `cl100k_base` (**Nota U1**: aproximación rápida, drift máximo ~3% frente al tokenizador Qwen3; documentar trade-off en docstring; si se requiere exactitud usar `transformers.AutoTokenizer`), calcula factor de submuestreo para proporción configurada (por defecto 30/70), mezcla con shuffle determinista (`random.seed(cfg.shuffle_seed)`), exporta único JSONL + `CompositionReport`; importar `CompositionReport` desde `src/utils/schema.py` (ver T038); header AEGF *(remedia I1+U1)*
- [ ] T024 [US3] Añadir comando `mix-datasets` en `src/curation/curator_cli.py` — flags: `--specialized-jsonl`, `--anchor-configs <yaml>`, `--output <jsonl>`, `--seed <int>`, `--target-records <int>`, `--report <json>`; delega en `DatasetMixer`

**Checkpoint**: `python -m src.curation.curator_cli mix-datasets --specialized-jsonl data/test_spec.jsonl --anchor-configs configs/stage_3_curation/anchors.yaml --output /tmp/test_mix.jsonl` completa; reporte muestra proporciones dentro del rango.

---

## Phase 6: User Story 4 — Soporte al Formato XML de Herramientas (Priority: P2)

**Goal**: El generador puede emitir llamadas a herramientas en formato `qwen3_coder` XML, evitando errores de escape en argumentos con código PHP/YAML multilínea.

**Independent Test**: Generar 20 registros con argumentos ≥10 líneas de código; verificar que en formato `qwen3_coder` el 100% son parseables por `xml.etree.ElementTree` sin errores y sin escapes `\"`.

### Tests para US4

- [ ] T025 [P] [US4] Añadir tests XML en `tests/factory/test_trajectory_generator.py` — round-trip XML serialize→parse preserva nombre de herramienta y argumentos, argumento con código Python multilínea no requiere escaping, mismo dato en JSON y XML produce semántica idéntica

### Implementación de US4

- [ ] T026 [US4] Añadir funciones XML a `src/factory/schema.py` — `serialize_tool_call_xml(name: str, args: dict) -> str` y `parse_tool_call_xml(text: str) -> tuple[str, dict]`; usar `xml.etree.ElementTree`; format auto-selector: si `len(json.dumps(args)) > 500` → XML por defecto
- [ ] T027 [US4] Integrar parámetro `tool_format` en `src/factory/trajectory_generator.py` — leer `cfg.tool_format` (json|xml|auto); en modo `auto`, delegar en selector de `schema.py`; todos los turnos de acción del mismo registro usan el mismo formato
- [ ] T028 [P] [US4] Añadir clasificación de formato en `src/curation/dedup_and_validate.py` — detectar formato de herramienta por registro (json/xml/none), añadir `format_distribution` a `CompositionReport`

**Checkpoint**: `pytest tests/factory/test_trajectory_generator.py -k xml` en verde; `CompositionReport` incluye campo `format_distribution`.

---

## Phase 7: User Story 5 — Configuración de Entrenamiento NEFTune (Priority: P3)

**Goal**: El `axolotl.yaml` para Home Assistant incluye `neftune_noise_alpha: 10`, el rango [5,15] se valida en tiempo de carga, y el entrenamiento arranca sin errores de configuración.

**Independent Test**: Cargar config con `neftune_noise_alpha: 10` → sin error. Cargar con `neftune_noise_alpha: 20` → `ConfigValidationError` con mensaje claro antes de iniciar el entrenamiento.

### Implementación de US5

- [ ] T029 [US5] Crear `configs/stage_4_training/axolotl/config.homeassistant.yaml` — copiar de `configs/stage_4_training/axolotl/config.yaml`, añadir `neftune_noise_alpha: 10`, confirmar `num_epochs: 2`, actualizar `datasets.path` al placeholder `${STAGE3_OUTPUT_JSONL}` documentado, mantener `lora_r: 64`, `lora_alpha: 128`, `peft_use_rslora: true`
- [ ] T030 [US5] Crear `src/training/config_validator.py` — función `validate_axolotl_neftune(path: Path) -> None` que carga el YAML de Axolotl y lanza `ConfigValidationError(f"neftune_noise_alpha={v} fuera del rango [5, 15]")` si el valor no está en rango; importar `ConfigValidationError` desde `src/utils/exceptions.py` (ver T036); header AEGF; añadir test en `tests/training/test_config_validator.py` — **Nota I4+D1**: separado de `src/factory/config.py`; Stage 4 Training tiene su propio módulo de validación *(remedia I4+D1)*

**Checkpoint**: `python -c "from src.factory.config import validate_axolotl_neftune; validate_axolotl_neftune(20)"` lanza `ConfigValidationError`.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Headers AEGF, secrets management, cobertura final.

- [ ] T031 [P] (a) Crear `src/utils/logging.py` — helper `get_logger(name: str) -> logging.Logger` para imports uniformes en toda la codebase; header AEGF *(remedia G5)*. (b) Verificar y añadir headers AEGF en todos los archivos Python nuevos: `src/factory/schema.py`, `agentic_teacher_client.py`, `trajectory_generator.py`, `hard_query_builder.py`; `src/curation/dataset_mixer.py`, `anchor_dataset_downloader.py`, `format_normalizer.py`, `dedup_and_validate.py`; `src/utils/schema.py`, `exceptions.py`, `logging.py`; `src/training/config_validator.py` — usar `scripts/check_headers.py --check src/factory src/curation src/utils src/training`
- [ ] T032 [P] Crear `.env.example` en la raíz del repo con variables requeridas: `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`, `GOOGLE_API_KEY=`, `STAGE3_OUTPUT_JSONL=` (sin valores reales)
- [ ] T033 Ejecutar `pytest tests/factory/ tests/curation/ --cov=src/factory --cov=src/curation --cov-report=term-missing` y corregir gaps hasta alcanzar ≥90% de cobertura en ambos paquetes

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup)
    └─► Phase 2 (Foundational: schema.py, config.py, checkpoint.py)
            ├─► Phase 3 (US1: TeacherModelClient + TrajectoryGenerator)  [P1]
            │       └─► Phase 4 (US2: HardQueryBuilder integra en TrajectoryGenerator) [P1, depende de US1]
            │               └─► Phase 6 (US4: XML integra en TrajectoryGenerator)   [P2, depende de US1]
            ├─► Phase 5 (US3: Stage 3 Curation stack)                     [P2, independiente de US1/US2]
            └─► Phase 7 (US5: Axolotl config)                             [P3, completamente independiente]
```

**Historias verdaderamente independientes**: US3 y US5 pueden trabajarse en paralelo con US1/US2.

---

## Parallel Execution Examples

### Sprint 1 — Foundational parallelizable
```
Thread A: T004 (schema.py)          Thread B: T006 (checkpoint.py)
Thread A: T005 (config.py)          Thread B: T003 (config.homeassistant.yaml)
                  └──► Sync: Phase 2 completa
```

### Sprint 2 — US1 + US3 en paralelo (ambas independientes)
```
Thread A (US1):  T007 → T009 → T010 → T012
Thread B (US3):  T020 [P] + T021 [P] simultáneos → T022 → T023 → T024
Thread C (US3 tests): T016 [P] + T017 [P] + T018 [P] + T019 [P]
```

### Sprint 3 — US2 sobre US1, US4 sobre US1, US5 independiente
```
Thread A (US2): T013 → T014 → T015
Thread B (US4): T025 → T026 → T027 → T028
Thread C (US5): T029 → T030
```

---

## Implementation Strategy

### MVP Scope (US1 únicamente)
Entregable mínimo verificable: `TrajectoryGenerator` + `TeacherModelClient` generan JSONL de trayectorias HA con backtracking. Fases 1, 2 y 3 completas.

### Incremento 2 (US2 + US3)
Añadir hard queries y Stage 3 mixer. El modelo puede entrenarse sobre el dataset mezclado completo.

### Incremento 3 (US4 + US5)
Soporte XML robusto y config Axolotl con NEFTune. Listo para entrenamiento de producción.

---

## Phase 9: Remediations (Issues del análisis de consistencia)

**Purpose**: Tareas correctivas derivadas del análisis `/speckit.analyze`. T036 y T038 son **prerequisitos de implementación** (deben completarse antes de T009, T020, T022, T023, T030). T035 debe completarse antes de T010 y T014.

- [ ] T036 Crear `src/utils/exceptions.py` — excepciones base compartidas: `ConfigValidationError(ValueError)`, `NormalizationError(ValueError)`, `CheckpointError(IOError)`, `DeduplicationError(ValueError)`, `TeacherAPIError(RuntimeError)`; header AEGF; importar desde aquí en todos los módulos nuevos *(remedia C3: constitución §VII DRY)*
- [ ] T038 Crear `src/utils/schema.py` — entidades compartidas Factory/Curation: `Message` (`role: str`, `content: str`), `RecordMetadata` (`origin`, `type`, `use_case`, `token_count`, `format`), `DatasetRecord` (`messages: list[Message]`, `metadata: RecordMetadata`), `CompositionReport` (`records_by_origin`, `token_pct_by_origin`, `type_distribution`, `discarded_count`, `discarded_reasons`); re-exportar desde `src/factory/schema.py` y `src/curation/__init__.py`; header AEGF *(remedia I1: dependencia circular Factory←→Curation)*
- [ ] T035 [US1/US2] Crear `configs/stage_2_factory/prompts/trajectory_templates.yaml` y `configs/stage_2_factory/prompts/hard_query_templates.yaml` — templates de turno externalizados (observe/reason/act/error/correct/verify) y objectives abstractos parametrizados por `use_case`; adaptar `TrajectoryGenerator` (T010) y `HardQueryBuilder` (T014) para cargar estos templates vía loader (patrón existente en `src/audit/prompt_manager.py`) *(remedia C1: constitución §IV — prompt externalization)*
- [ ] T034 [P] [US1] Añadir tests de compatibilidad PHP Legacy en `tests/factory/test_trajectory_generator.py` — verificar que `TrajectoryGenerator` funciona con `use_case = php_legacy` sin regresión; cargar seeds desde `configs/stage_2_factory/taxonomy/`; confirmar que ningún cambio nuevo rompe el pipeline PHP existente *(remedia I2: FR-008 sin cobertura de tests)*
- [ ] T037 [P] [US3] Crear `configs/stage_3_curation/anchors.yaml` — lista de `AnchorDatasetConfig`: `Salesforce/xlam-function-calling-60k`, `FineTome-100k`, `Magicoder`; campos por entry: `hf_id`, `split`, `format` (alpaca/sharegpt/openai_messages), `token_budget_pct`; acompañar de `configs/stage_3_curation/anchors.example.yaml` sin valores reales *(remedia G1: anchors.yaml sin tarea)*
- [ ] T039 [P] Benchmark post-implementación (LOW, P3): (a) SC-008 — medir tiempo de Stage 3 con 50 000 registros, objetivo <60 s; (b) SC-006 — medir overhead de NEFTune en 100 steps vs baseline, objetivo <10%; documentar resultados en `specs/010-agentic-dataset-redesign/benchmarks.md` *(remedia G4: SC-006/SC-008 sin tareas)*

**Orden de ejecución de remediaciones**:
```
T036 (exceptions) + T038 (schema)   →  prerequisitos de T009, T020, T022, T023, T030
T035 (prompt templates)              →  prerequisito de T010, T014
T034 [P] + T037 [P] + T039 [P]      →  paralelos, sin bloquear otras tareas
```

---

## Report

| Metrica | Valor |
|---------|-------|
| Total de tareas | **39** |
| Fases | 9 (Setup · Foundational · US1–US5 · Polish · Remediations) |
| Tareas US1 (Trayectorias) | 7 (T007–T012, T034) |
| Tareas US2 (Hard Queries) | 4 (T013–T015, T035) |
| Tareas US3 (Data Mixing) | 10 (T016–T024, T037) |
| Tareas US4 (XML Format) | 4 (T025–T028) |
| Tareas US5 (NEFTune Config) | 2 (T029–T030) |
| Tareas Setup + Foundational + Polish | 9 (T001–T006, T031–T033) |
| Tareas transversales (utils/shared) | 3 (T036, T038, T039) |
| Tareas paralelizables [P] | **21** |
| MVP sugerido | Fases 1–3 + T036 + T038: T001–T012, T036, T038 |
