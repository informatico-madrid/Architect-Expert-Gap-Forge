# Feature Specification: Refactorización de Módulos Monolíticos

**Feature Branch**: `003-monolith-modules`  
**Created**: 2026-03-12  
**Status**: Draft  
**Input**: User description: "Tenemos un problema con los bloques o archivos monolíticos. Son muy grandes y necesitan refactorización. Siguiendo las mejores prácticas y guías del proyecto localizaremos los archivos que son realmente extensos y los vamos a refactorizar. Los archivos diana son: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC). Violación de §3.1 (módulos pequeños y responsabilidad única). Difíciles de testear y mantener. Remediation: dividir en módulos más pequeños, añadir interfaces tipadas por submódulo."

---

## Clarifications

### Session 2026-03-12

- Q: ¿Cuál es el mapa de descomposición de `production_v11.py`? → A: `prompt_builder` · `fragment_extractor` · `ldi_validator` · `checkpoint` · `pipeline_runner` · `cli`
- Q: ¿Hay un objetivo de latencia de importación para los submódulos? → A: carga diferida; sin target de ms
- Q: ¿Cuánto tiempo se mantienen los re-exports de compatibilidad en `__init__.py`? → A: eliminados en el mismo PR que la refactorización
- Q: ¿Cómo se mide el umbral de LOC y es una línea estricta? → A: orientativo; prima arquitectura limpia
- Q: ¿Cuál es el mapa de descomposición de `model_evaluator.py`? → A: `gap_generator` · `exam_builder` · `judge` · `scorecard` · `report_writer` · `cli`

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Desarrollador modifica la lógica de construcción de prompts (Priority: P1)

Un desarrollador necesita ajustar cómo se construyen los prompts del tipo "contrast" en la factory. Actualmente está obligado a navegar 2 500 líneas de `production_v11.py` mezcladas con lógica de checkpoint, extracción de fragmentos y parsing de argumentos CLI. Después de la refactorización, abre `src/factory/prompt_builder.py` (~300 LOC), localiza la función en segundos y aplica el cambio con confianza de que sólo afecta esa responsabilidad.

**Why this priority**: Es el caso de uso más frecuente y el bloqueo más doloroso del día a día. Desbloquea también la capacidad de escribir tests unitarios focalizados.

**Independent Test**: Puede validarse de forma aislada comprobando que `src/factory/prompt_builder.py` exporta los constructores de prompt documentados y que un test unitario ejercita cada tipo de prompt sin necesitar instanciar el pipeline completo.

**Acceptance Scenarios**:

1. **Given** `src/factory/production_v11.py` con >2 000 LOC, **When** se aplica la refactorización, **Then** el archivo resultante (orquestador) no supera 500 LOC y cada submodulo extraído no supera 400 LOC.
2. **Given** el módulo `prompt_builder` aislado, **When** se importa en un test sin dependencias de red ni I/O, **Then** todos los constructores de prompt retornan cadenas no vacías con los placeholders correctamente sustituidos.
3. **Given** el pipeline en ejecución real, **When** se lanza con los mismos argumentos que antes de la refactorización, **Then** el output JSONL es bit-compatible con el anterior (misma estructura de campos).

---

### User Story 2 — Desarrollador escribe tests unitarios para el evaluador de modelos (Priority: P1)

Un desarrollador quiere añadir tests para la función de puntuación del LLM judge en `src/audit/model_evaluator.py`. Hoy ese archivo mezcla carga de configuración, orquestación de subcomandos CLI, generación de exámenes, cómputo de scorecard y generación de informes. Imposible hacer un test unitario sin mockear media pipeline. Tras la refactorización, importa `src/audit/judge.py` exclusivamente y escribe tests directos contra las funciones de scoring.

**Why this priority**: Igual urgencia que P1. La baja testeabilidad de `model_evaluator.py` causa que cambios en el evaluador lleguen a producción sin cobertura.

**Independent Test**: Puede validarse comprobando que `src/audit/judge.py` puede importarse en un test que sólo mockea una función LLM y que devuelve un resultado tipado verificable.

**Acceptance Scenarios**:

1. **Given** `src/audit/model_evaluator.py` con ~1 400 LOC, **When** se aplica la refactorización, **Then** cada submodulo extraído no supera 400 LOC y el orquestador no supera 300 LOC.
2. **Given** la suite de tests existente, **When** se ejecuta `make test` tras la refactorización, **Then** todos los tests pasan sin modificación.
3. **Given** el nuevo módulo `src/audit/judge.py`, **When** se ejecuta de forma aislada con un callable LLM stub, **Then** retorna un objeto tipado con los campos `score`, `grade` y `verdict`.

---

### User Story 3 — Desarrollador identifica y corrige los demás archivos monolíticos secundarios (Priority: P2)

Tras resolver los dos archivos primarios, el equipo detecta que `src/curation/backtracking_rewriter.py` (1 539 LOC), `src/curation/nemo_curator_suite.py` (1 315 LOC), `src/discovery/processor.py` (1 227 LOC) y `src/factory/agentic_gen.py` (1 204 LOC) presentan el mismo antidafón. Esta user story cubre la aplicación del mismo patrón de extracción a esos archivos.

**Why this priority**: Son importantes pero menos urgentes que los dos archivos primarios. Pueden abordarse en una segunda pasada una vez verificado el patrón con los archivos P1.

**Independent Test**: Puede validarse ejecutando `wc -l src/**/*.py | sort -rn | head -10` y comprobando que ningún archivo supera el umbral acordado (400 LOC para módulos de dominio).

**Acceptance Scenarios**:

1. **Given** los cuatro archivos secundarios, **When** se aplica la refactorización, **Then** cada archivo original se convierte en un paquete de submódulos donde ningún submódulo supera 400 LOC.
2. **Given** los tests existentes que cubren los archivos secundarios, **When** se ejecuta `make test`, **Then** todos los tests pasan.
3. **Given** el CI con check de cabeceras, **When** se crean nuevos archivos `.py`, **Then** el CI pasa incluyendo la política de cabeceras de §V de la constitución.

---

### Edge Cases

- ¿Qué ocurre si un test existente referencia directamente una función que se mueve a otro módulo? → Los tests se actualizan al nuevo path de importación en el mismo PR. No hay período de transición: los re-exports se eliminan al completar la refactorización.
- ¿Cómo se gestiona la circularidad de importaciones al extraer submódulos dentro de un mismo paquete? → Los módulos de utilidades se extraen a `src/utils/` o a un paquete de nivel inferior (ej. `src/factory/core/`) para evitar ciclos.
- ¿Qué pasa con los scripts `legacy/` y `diagnose/` que pueden importar funciones del monolito? → Son carpetas fuera de `src/`, no forman parte del alcance formal; si importan funciones movidas, se documentan como deuda técnica en un TODO, no se refactorizan en esta feature.
- ¿Constantes y configuración global? → Se extraen a un módulo `config.py` o `constants.py` dentro del paquete, no a nivel raíz del repositorio.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada módulo fuente en `src/` cuyo tamaño o mezcla de responsabilidades dificulte su test, lectura o mantenimiento DEBE dividirse en submódulos de responsabilidad única. 400 LOC es una señal de alerta (“code smell”), no un límite estricto: un módulo puede superar ese valor si su diseño arquitectónico lo justifica. El criterio definitivo es que cada submódulo sea independientemente testeable y tenga una única razón para cambiar (SRP).
- **FR-002**: Todos los submódulos resultantes DEBEN tener interfaces públicas completamente anotadas con tipos (parámetros y valores de retorno).
- **FR-003**: Los módulos extraídos DEBEN seguir la convención de un único logger por módulo (`logger = logging.getLogger(__name__)`).
- **FR-004**: Los datos estructurados compartidos entre submódulos DEBEN definirse con contratos de tipo explícitos usando estructuras inmutables verificables en statically-typed review.
- **FR-005**: Ningún módulo importado a nivel de módulo DEBE producir I/O, llamadas de red ni instanciación de clientes (cumplimiento de §III de la constitución). No se establece un objetivo numérico de latencia de importación; el criterio es exclusivamente la ausencia de side-effects.
- **FR-006**: El comportamiento observable del pipeline (estructura del output JSONL, campos de metadatos, códigos de salida CLI) DEBE permanecer idéntico tras la refactorización.
- **FR-007**: Todos los nuevos archivos `.py` creados DEBEN incluir la cabecera del proyecto (shebang, project id, copyright, SPDX) según la política de §V de la constitución.
- **FR-008**: La cobertura de tests para los módulos refactorizados DEBE ser ≥ 90 % (en línea con el requisito CI de `src/audit` y `src/utils`).
- **FR-009**: Los paquetes refactorizados DEBEN exponer sus APIs públicas a través de `__init__.py` para preservar la compatibilidad de importación con los consumidores dentro de `src/`. Los scripts en `legacy/` y `diagnose/` quedan fuera del alcance de esta feature; si importan funciones movidas, se documentan como deuda técnica en un TODO pero no se refactorizan en este PR.
- **FR-010**: La lógica de CLI (parsing de argumentos, subcomandos) DEBE quedar en módulos separados (`cli.py`) y NO mezclada con la lógica de dominio.

### Key Entities

- **Submódulo de dominio**: Archivo con una única responsabilidad funcional (p. ej. construcción de prompts, extracción de fragmentos, validación). Independientemente testeable sin instanciar el pipeline completo. 400 LOC es una guía orientativa; lo determinante es la cohesión y la ausencia de acoplamiento innecesario.
- **Módulo orquestador**: Archivo principal del paquete que ensambla los submódulos e implementa el flujo de alto nivel. Su tamaño debe minimizarse delegando toda lógica de dominio a los submódulos.
- **Interfaz tipada**: Conjunto de definiciones de tipos que expresan el contrato público entre submódulos (qué datos entran, qué datos salen), sin exponer detalles de implementación interna.
- **Módulo CLI**: Módulo dedicado exclusivamente al parsing de argumentos y despacho de subcomandos.

#### Mapa de descomposición: `src/audit/model_evaluator.py`

| Submódulo | Responsabilidad |
|-----------|----------------|
| `gap_generator` | Generación de análisis de gaps (domain standards, reference patterns, prompts de gap analysis) |
| `exam_builder` | Construcción de preguntas de examen a partir de fragmentos y carga de configuración |
| `judge` | Scoring LLM judge: envío de inferencia, extracción de bloques de código, validación de respuesta |
| `scorecard` | Cómputo del scorecard compuesto, grade labels y veredicto final |
| `report_writer` | Generación y serialización del informe de evaluación |
| `cli` | Los 6 subcomandos CLI (`sample`, `generate-exam`, `baseline`, `adapter`, `score`, `full`) y `main()` |

| Submódulo | Responsabilidad |
|-----------|----------------|
| `prompt_builder` | Construcción de todos los mensajes de sistema y usuario por tipo de ejemplo (nominal, contrast, error-recovery, jinja, theory) |
| `fragment_extractor` | Extracción, parsing y normalización de fragmentos desde bundles, AST y texto plano |
| `ldi_validator` | Validación LDI, detección de patrones legacy y asignación de tipo de ejemplo |
| `checkpoint` | Carga, escritura y gestión de checkpoints de progreso; `AsyncFileWriter` |
| `pipeline_runner` | Loop asíncrono principal, control de workers, orquestación de pasos |
| `cli` | Parsing de argumentos CLI (`argparse`) y punto de entrada `main()` |

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras la refactorización de los archivos primarios (`production_v11.py` y `model_evaluator.py`), cada submódulo resultante tiene una única responsabilidad funcional y es independientemente testeable. Los archivos que superen 400 LOC deben justificarse con criterios arquitectónicos documentados en un comentario de cabecera.
- **SC-002**: La suite de tests completa (`make test`) pasa sin errores ni warnings nuevos tras cada fase de refactorización.
- **SC-003**: La cobertura de los módulos refactorizados en `src/audit/` y `src/factory/` es ≥ 90 %, medible con `make coverage`.
- **SC-004**: Un desarrollador nuevo puede localizar y modificar una responsabilidad concreta (p. ej. construcción de prompt "error-recovery") en menos de 2 minutos navegando la estructura de archivos resultante, sin necesidad de leer el archivo orquestador completo.
- **SC-005**: El CI (cabecera + tipos + tests) pasa limpio en todos los archivos nuevos creados.
- **SC-006**: Tras la refactorización de los cuatro archivos secundarios, ningún módulo en `src/` mezcla más de una responsabilidad funcional. Los archivos >400 LOC son la excepción justificada, no la norma.

---

## Assumptions

- Se asume que el “umbral de módulo grande” de 400 LOC es una señal de alerta orientativa (medida con `wc -l`), no una restricción absoluta. Un módulo puede superar ese valor si tiene justificación arquitectónica clara. El criterio real es SRP + testeabilidad independiente.
- Se asume que los tests existentes son suficientes para detectar regresiones de comportamiento; si algún módulo tiene cobertura < 50 % antes de la refactorización, se añadirán tests básicos de humo antes de mover el código.
- No se usan re-exports de compatibilidad transitoria. Todos los consumidores internos (tests, orquestadores) se actualizan al nuevo path de importación en el mismo PR de refactorización.
- Se asume que los archivos en `legacy/` y `diagnose/` quedan fuera del alcance de esta feature.
- Se asume que la refactorización se hace en fases independientes: primero `production_v11.py` + tests, luego `model_evaluator.py` + tests, y finalmente los archivos secundarios.
