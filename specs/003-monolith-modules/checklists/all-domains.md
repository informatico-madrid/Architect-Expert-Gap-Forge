# All-Domain Specification Quality Checklist: Refactorización de Módulos Monolíticos

**Purpose**: Validate completeness, clarity, consistency, measurability, and coverage of all requirements across every quality dimension — prior to task generation  
**Created**: 2026-03-12  
**Feature**: [spec.md](../spec.md) · [research.md](../research.md) · [data-model.md](../data-model.md)  
**Scope**: All domains — Functional · Architecture · Data Model · Non-Functional · Testing · Security · Edge Cases · Dependencies · CLI · Documentation

---

## Requirement Completeness

- [ ] CHK001 — ¿Están documentados los requisitos de refactorización para los **4 archivos secundarios** (backtracking_rewriter, nemo_curator_suite, processor, agentic_gen) con el mismo nivel de detalle que los primarios? La US3 los menciona pero no tiene mapa de descomposición. [Completeness, Spec §US3, Gap]
- [ ] CHK002 — ¿Define la spec los requisitos para actualizar las **importaciones en los 16 archivos de test** de `production_v11` y los **7 archivos de test** de `model_evaluator`? El edge case lo menciona pero no está en los Functional Requirements. [Completeness, Gap]
- [ ] CHK003 — ¿Existe un requisito explícito para el **módulo `config.py`** (constantes, `TaxonomyState`, singletons lazy) dentro de cada paquete? El data-model lo documenta pero FR-001–FR-010 no lo mencionan directamente. [Completeness, data-model.md, Gap]
- [ ] CHK004 — ¿Están cubiertos los requisitos para la **formalización de tipos existentes** (`ExamRecord`, `NormalizedJudgeResponse`, `ScoreCard`) que hoy son dicts anónimos en `model_evaluator.py`? El data-model los lista pero la spec no los menciona como requisito funcional. [Completeness, data-model.md §Estado de transición, Gap]
- [ ] CHK005 — ¿Existe un requisito para que **`agentic_gen.py`** (1 204 LOC, excluido de cobertura en `pyproject.toml`) sea incluido en la métrica de cobertura tras su refactorización? [Completeness, Spec §FR-008, Gap]

---

## Requirement Clarity

- [ ] CHK006 — ¿Es "responsabilidad única" definible de forma objetiva, o depende de criterio subjetivo del revisor? ¿Hay ejemplos negativos (qué NO cuenta como SRP) documentados en la spec? [Clarity, Spec §FR-001, Ambiguity]
- [ ] CHK007 — ¿Está clarificado qué se entiende por **"interfaces públicas completamente anotadas"** (FR-002)? ¿Incluye métodos privados con `_` prefijo? ¿Parámetros `**kwargs`? [Clarity, Spec §FR-002, Ambiguity]
- [ ] CHK008 — ¿Define FR-006 ("comportamiento observable idéntico") qué ocurre si hay **diferencias en ordering de campos** en el JSONL de salida que el pipeline actual genera de forma no determinista? [Clarity, Spec §FR-006, Ambiguity]
- [ ] CHK009 — ¿Está especificado el formato exacto del **`# ARCH-NOTE:`** que deben incluir los archivos >400 LOC como justificación? ¿Quién lo aprueba? [Clarity, Spec §SC-001, research.md §Decision 5, Ambiguity]
- [ ] CHK010 — ¿Define FR-010 qué se considera "lógica de dominio" (i.e., qué NO debe estar en `cli.py`)? Sin esta definición, la frontera entre `pipeline_runner.main_async()` y `cli.main()` puede ser ambigua. [Clarity, Spec §FR-010, Ambiguity]

---

## Requirement Consistency

- [ ] CHK011 — ¿Son consistentes FR-001 (SRP + testeabilidad como criterio) y SC-001 (archivos que superen 400 LOC deben justificarse)? El plan muestra que `pipeline_runner.py` (~400 LOC) y `cli.py` de `model_evaluator` (~420 LOC) están en el límite — ¿el criterio aplicado es el mismo en ambos? [Consistency, Spec §FR-001 vs §SC-001, research.md §Decision 1]
- [ ] CHK012 — ¿Son consistentes FR-008 (cobertura ≥ 90 % para módulos refactorizados) y la exclusión actual de `agentic_gen.py` en `pyproject.toml`? Si `agentic_gen.py` se refactoriza en Fase C, ¿debe eliminarse su exclusión del coverage? [Consistency, Spec §FR-008, pyproject.toml]
- [ ] CHK013 — ¿Es consistente la US1 (dice que el output JSONL debe ser "bit-compatible") con la decisión de formalizar `GeneratedSample` como `TypedDict`? Un `TypedDict` con campos new puede producir output con campos adicionales si se serializa sin filtrar. [Consistency, Spec §US1 SC3, data-model.md §GeneratedSample]
- [ ] CHK014 — ¿Son consistentes los umbrales de LOC entre la spec (400 para submódulos, 500 para orquestador en SC-001) y el plan (que elimina el límite del orquestador)? La spec original SC-001 habló de "500 LOC para orquestador" pero luego se eliminó al actualizar. ¿Está alineado con el plan? [Consistency, Spec §SC-001 vs plan.md]

---

## Acceptance Criteria Quality

- [ ] CHK015 — ¿Es el criterio "en menos de 2 minutos" (SC-004) objetivamente medible? ¿Bajo qué condiciones (IDE, familiaridad con el proyecto, tamaño del repo)? [Measurability, Spec §SC-004, Ambiguity]
- [ ] CHK016 — ¿Define SC-002 ("make test pasa sin errores ni warnings nuevos") cómo se distinguen **warnings preexistentes** de warnings introducidos por la refactorización? [Measurability, Spec §SC-002]
- [ ] CHK017 — ¿Son los acceptance scenarios de US2 suficientemente específicos para los campos `score`, `grade` y `verdict` del módulo `judge.py`? ¿Están sus rangos de valores documentados? [Acceptance Criteria, Spec §US2 SC3, data-model.md §NormalizedJudgeResponse]
- [ ] CHK018 — ¿Tiene SC-003 ("cobertura ≥ 90 % en `src/audit/` y `src/factory/`") un criterio de evaluación por **submódulo individual** o sólo agregado por paquete? Diferencia importante: un submódulo puede tener 0 % si los tests importan del monolito todavía. [Measurability, Spec §SC-003, Acceptance Criteria]

---

## Scenario Coverage

- [ ] CHK019 — ¿Está cubierto el escenario de **refactorización parcialmente completada** (Fase A terminada, Fase B en progreso)? ¿El pipeline sigue funcionando de punta a punta con un paquete refactorizado y otro no? [Coverage, Spec §US1, Edge Case]
- [ ] CHK020 — ¿Está cubierto el escenario de **CI fallando en check de cabeceras** (§V de la constitución) sobre un fichero nuevo que no tiene la cabecera correcta? ¿Hay un test específico para esto o sólo se detecta en CI? [Coverage, Spec §FR-007, Spec §SC-005]
- [ ] CHK021 — ¿Están cubiertos los escenarios de **recuperación de checkpoint** en el nuevo diseño donde `checkpoint.py` es un módulo separado? La lógica de checkpoint es crítica para la resiliencia del pipeline. [Coverage, data-model.md §CheckpointSet, Spec §US1]
- [ ] CHK022 — ¿Existe un escenario que cubra la **ejecución del pipeline completo end-to-end** (`make run` o equivalente) tras la refactorización, no sólo la suite de tests unitarios? [Coverage, Spec §SC-002, quickstart.md]

---

## Edge Case Coverage

- [ ] CHK023 — ¿Está definido qué ocurre si **`load_taxonomy()` se llama múltiples veces** en el nuevo diseño con `TaxonomyState` inmutable? ¿Se lanza una excepción, se ignora, o se retorna el estado existente? [Edge Case, data-model.md §TaxonomyState, Spec §FR-004]
- [ ] CHK024 — ¿Está especificado el comportamiento cuando el **singleton lazy** de `PromptManager` o `InferenceRouter` en `src/audit/config.py` falla durante la inicialización? ¿Excepción explícita o degradación silenciosa? [Edge Case, data-model.md §Decision 3, Spec §FR-005]
- [ ] CHK025 — ¿Están documentados los requisitos para el caso donde un **submódulo nuevo importa un símbolo que aún no ha sido movido** durante el proceso de refactorización incremental? ¿Se permite importar del monolito temporalmente? [Edge Case, Spec §US1, quickstart.md]
- [ ] CHK026 — ¿Está cubierto el edge case en `ldi_validator.py` donde `assign_example_type()` recibe un fragmento con **todos los tipos ya agotados en el checkpoint**? ¿La distribución 50/30/20 puede producir starvation? [Edge Case, research.md §LDI_VALIDATOR, Spec §FR-001]

---

## Non-Functional Requirements

- [ ] CHK027 — ¿Están definidos los requisitos de **tiempo de arranque del pipeline** tras la refactorización? La eliminación de side-effects de import-time puede cambiar (mejorar o aumentar) el tiempo del primer `import`. [Non-Functional, Spec §FR-005, research.md §Decision 3]
- [ ] CHK028 — ¿Están especificados los requisitos de **uso de memoria** para `TaxonomyState` inmutable frente a los globales mutables actuales? Una frozen dataclass con listas grandes puede tener overhead de copia. [Non-Functional, data-model.md §TaxonomyState, Gap]
- [ ] CHK029 — ¿Existe un requisito de **compatibilidad de señales del proceso** (SIGINT, SIGTERM) en el nuevo `pipeline_runner.py`? El monolito actual maneja la interrupción mediante el contexto async; ¿esto se preserva explícitamente? [Non-Functional, Spec §FR-006, Gap]
- [ ] CHK030 — ¿Están definidos requisitos de **mantenibilidad medible a futuro** (ej. límite de imports por módulo, profundidad máxima de la cadena de llamadas) para prevenir que los nuevos submódulos vuelvan a crecer? [Non-Functional, Spec §FR-001, Gap]

---

## Architecture & Design Requirements

- [ ] CHK031 — ¿Está documentado el **orden de dependencia** entre los 7 submódulos de `src/factory/` para guiar al implementador en el orden correcto de extracción? (mencionado en quickstart.md pero ¿está en la spec como requisito?) [Architecture, quickstart.md, research.md §Decision 1]
- [ ] CHK032 — ¿Define la spec el patrón de **inyección de dependencias** para `TaxonomyState` — específicamente, ¿en qué nivel del call stack se instancia y cómo llega a `prompt_builder` y a `pipeline_runner`? [Architecture, data-model.md §TaxonomyState, Spec §FR-004]
- [ ] CHK033 — ¿Está documentado si el nuevo `src/audit/config.py` debe usar **`importlib` lazy loading** u otro mecanismo para diferir `PromptManager` e `InferenceRouter`? El "singleton lazy" está en el research pero no en la spec. [Architecture, research.md §Decision 2, Gap]
- [ ] CHK034 — ¿Define la spec cómo se gestionan los **workers async** (`asyncio.TaskGroup` vs `asyncio.gather`) en el nuevo `pipeline_runner.py`? La constitución (§III) requiere `asyncio.TaskGroup` para concurrencia estructurada. [Architecture, Spec §FR-005, constitution §III]

---

## Data Model Requirements

- [ ] CHK035 — ¿Está especificado si `TaxonomyState` debe ser un `@dataclass(frozen=True)` o un `TypedDict` inmutable? Tienen semánticas distintas de validación en runtime vs. static analysis. [Data Model, data-model.md §TaxonomyState, Spec §FR-002]
- [ ] CHK036 — ¿Están definidos los **valores permitidos** (enums o Literals) para `ExampleTypeAssignment.example_type` ("nominal" | "contrast" | "error_recovery") y `difficulty` ("easy" | "medium" | "hard" | None)? [Data Model, data-model.md §ExampleTypeAssignment, Clarity]
- [ ] CHK037 — ¿Está especificado si `ExamRecord` debe ir en `src/audit/schema.py` (existente) o en el nuevo `src/audit/config.py`? El data-model dice "formalizar en `src/audit/schema.py`" pero no está en FR. [Data Model, data-model.md §Estado de transición, Gap]
- [ ] CHK038 — ¿Están definidos los **campos mandatorios vs. opcionales** de `NormalizedJudgeResponse.baseline` y `.adapter`? La regla de "mismas claves de dimensión" está en data-model.md pero no como FR con excepción explícita. [Data Model, data-model.md §Reglas de validación, Spec §FR-004]

---

## Testing Requirements

- [ ] CHK039 — ¿Define la spec los requisitos de **tests de integración** que validen que el pipeline de extremo a extremo produce el mismo output antes y después de la refactorización? Los tests unitarios garantizan partes; un test e2e garantiza la composición. [Testing, Spec §SC-002, Gap]
- [ ] CHK040 — ¿Están especificados los requisitos de **fixtures compartidas** entre los 16 archivos de test de `production_v11`? Si se actualiza el módulo, ¿se consolidan las fixtures o se actualizan independientemente? [Testing, Spec §FR-008, tests/fixtures/production_v11_mocks.py]
- [ ] CHK041 — ¿Existe un requisito para que el **test de regresión de cobertura** se ejecute incrementalmente (tras cada submódulo extraído) y no sólo al final de la Fase A o Fase B? [Testing, Spec §FR-008, SC-003]
- [ ] CHK042 — ¿Están definidos los requisitos para **testear los nuevos tipos formalizados** (`TaxonomyState`, `LDIResult`, `ExamRecord`, etc.)? ¿Se necesitan tests de schema específicos o se cubren implícitamente? [Testing, data-model.md §Estado de transición, Gap]

---

## Security Requirements

- [ ] CHK043 — ¿Define la spec cómo el nuevo `src/audit/config.py` carga credenciales de entorno (API keys)? El `load_dotenv()` actual se mueve a `cli.py`; ¿está documentado que las API keys nunca deben estar en `CFG` (cargada desde YAML)? [Security, Spec §FR-005, constitution §VI]
- [ ] CHK044 — ¿Están definidos los requisitos para que el nuevo `AsyncFileWriter` en `checkpoint.py` no exponga **rutas de escritura arbitrarias** vía argumentos CLI? [Security, research.md §CHECKPOINT, OWASP: Path Traversal]
- [ ] CHK045 — ¿Define la spec los requisitos para que **`run_inference()`** en `judge.py` no exponga datos del modelo ni respuestas del LLM en logs a nivel DEBUG sin sanitización? [Security, research.md §judge, constitution §VI]

---

## CLI & Interface Requirements

- [ ] CHK046 — ¿Está especificado si los **6 subcomandos de `model_evaluator`** (`sample`, `generate-exam`, `baseline`, `adapter`, `score`, `full`) deben mantener sus nombres exactos y flags en el nuevo `cli.py`? FR-006 cubre output observable pero ¿cubre la interfaz CLI? [CLI, Spec §FR-006, Spec §FR-010]
- [ ] CHK047 — ¿Está documentado el requisito de **punto de entrada en `pyproject.toml`** o `setup.py`? Si `main()` se mueve a `cli.py`, el entry point debe actualizarse. [CLI, Spec §FR-009, Gap]
- [ ] CHK048 — ¿Define la spec el comportamiento de `cli.py` cuando se invoca con **argumentos desconocidos**? Hereda el comportamiento de `argparse`, ¿pero está documentado como requisito explícito? [CLI, Spec §FR-010, Edge Case]

---

## Dependencies & Assumptions

- [ ] CHK049 — ¿Está validada la assumption de que **ningún módulo en `src/` importa directamente `production_v11` o `model_evaluator`**? El research menciona "verificado con grep" pero no como pre-condición documentada en la spec. [Assumption, Spec §Assumptions, research.md §Decision 4]
- [ ] CHK050 — ¿Está documentada la dependencia de `production_v11.py` en **`think_filter.py`** (import dinámico opcional)? Si `think_filter.py` no está presente, ¿el nuevo `pipeline_runner.py` debe degradar gracefully igual que el monolito? [Dependency, research.md §Side-effects, Spec §FR-006]
- [ ] CHK051 — ¿Define la spec qué ocurre con la assumption "los tests existentes son suficientes para detectar regresiones" si se detecta durante la refactorización que un submódulo tiene **< 50 % de cobertura**? La spec dice "añadir tests básicos de humo" pero no lo eleva a FR. [Assumption, Spec §Assumptions, Gap]
- [ ] CHK052 — ¿Está validada la assumption de que **`legacy/` y `diagnose/` no importan** `production_v11` ni `model_evaluator`? Esto está en Assumptions pero no verificado con evidencia en research.md. [Assumption, Spec §Assumptions, research.md §Decision 4]

---

## Documentation Requirements

- [ ] CHK053 — ¿Define la spec los requisitos para **actualizar el docstring del módulo** en cada nuevo submódulo? FR-007 cubre la cabecera AEGF pero no los docstrings de módulo que describen la responsabilidad. [Documentation, Spec §FR-007, Gap]
- [ ] CHK054 — ¿Existe un requisito para actualizar el **README o METHODOLOGY.md** del proyecto reflejando la nueva estructura de paquetes tras la refactorización? [Documentation, Gap]
- [ ] CHK055 — ¿Está especificado si el **`# ARCH-NOTE:`** en archivos >400 LOC debe incluir la fecha, el autor, y/o referencia a esta feature? [Documentation, research.md §Decision 5, Clarity]

---

## Ambiguities & Conflicts

- [ ] CHK056 — **Conflicto potencial**: SC-001 dice "archivos que superen 400 LOC deben justificarse con criterios arquitectónicos", pero `cli.py` de `model_evaluator` se estima en ~420 LOC (research.md). ¿Se considera el CLI parte del dominio o infraestructura? Si es infraestructura, ¿el umbral aplica? [Conflict, Spec §SC-001, research.md §Decision 2]
- [ ] CHK057 — **Ambigüedad**: La spec dice que el orquestador "debe delegar toda la lógica de dominio a los submódulos" (plan.md §Key Entities), pero `pipeline_runner.main_async()` contiene lógica de orquestación de alto nivel que podría considerarse dominio. ¿Está la frontera clara? [Ambiguity, plan.md §Key Entities, data-model.md §pipeline_runner]
- [ ] CHK058 — **Ambigüedad**: FR-009 dice que los paquetes deben exponer APIs públicas via `__init__.py` "para preservar compatibilidad de importación", pero la spec también dice "eliminados en el mismo PR". ¿Qué se expone exactamente en `__init__.py` — la nueva API o la antigua? [Ambiguity, Spec §FR-009 vs §Assumptions]
- [ ] CHK059 — **Conflicto potencial**: El plan dice `production_v11.py` se **elimina** al final de la Fase A, pero si los tests de integración end-to-end aún no cubren todos los submódulos, eliminar el monolito antes de tener tests completos aumenta el riesgo. ¿Hay una pre-condición de cobertura mínima para el DELETE? [Conflict, quickstart.md §Fase A, Spec §FR-008]

---

## Notes

- Checklist generado: 2026-03-12. Cubre todos los dominios con foco en **calidad de los requisitos escritos**, no en verificación de implementación.
- 59 ítems en 13 categorías. Prioridad alta (bloquean implementación): CHK001–CHK005, CHK006, CHK010, CHK019, CHK039, CHK049, CHK052, CHK058–CHK059.
- Prioridad media (mejoran claridad): CHK007–CHK009, CHK011–CHK014, CHK015–CHK018, CHK032–CHK034.
- Prioridad baja (nice-to-have para producción): CHK028–CHK030, CHK043–CHK045, CHK053–CHK055.
