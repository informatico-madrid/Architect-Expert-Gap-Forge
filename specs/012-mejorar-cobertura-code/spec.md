# Feature Specification: Mejorar Cobertura de Código

**Feature Branch**: `[012-mejorar-cobertura-code]`  
**Created**: 2026-03-19  
**Status**: Draft  
**Input**: User description: "mejorar cobertura de código para alcanzar 90%+ en todos los módulos de src/"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aumentar cobertura de módulos con 0% cobertura (P1)

**Descripción**: Los desarrolladores necesitan que todos los módulos del sistema tengan tests que cubran al menos el 90% del código para garantizar la fiabilidad y mantenibilidad del proyecto.

**Por qué esta prioridad**: Los módulos sin cobertura (0%) representan un riesgo crítico de calidad - cualquier cambio en código no testado puede introducir bugs sin detección automática.

**Test independiente**: Se puede ejecutar `pytest --cov=src/audit/eval_bpb` y verificar que la cobertura sea >= 90% sin necesidad de otros módulos.

**Escenarios de aceptación**:

1. **Dado** que existe el archivo `src/audit/eval_bpb.py` con funciones de cálculo de BPB, **cuando** se ejecutan los tests unitarios, **entonces** la cobertura de código debe ser >= 90%.

2. **Dado** que existe el archivo `src/utils/logging.py`, **cuando** se ejecutan los tests, **entonces** la función `get_logger()` debe estar cubierta.

3. **Dado** que existe el archivo `src/utils/cache_reset.py`, **cuando** se ejecutan los tests, **entonces** la función `reset_all_caches()` debe estar cubierta.

---

### User Story 2 - Mejorar cobertura de módulos con baja cobertura (P2)

**Descripción**: Los módulos con cobertura entre 20-70% necesitan tests adicionales para alcanzar el objetivo del 90%.

**Por qué esta prioridad**: Los módulos con baja cobertura tienen áreas no testadas que pueden contener bugs críticos en flujos de trabajo importantes.

**Test independiente**: Se puede verificar la cobertura de cada módulo individualmente con `pytest --cov=src/curation/anchor_dataset_downloader`.

**Escenarios de aceptación**:

1. **Dado** que `anchor_dataset_downloader.py` tiene 20% de cobertura, **cuando** se añaden tests para las funciones de descarga y parseo, **entonces** la cobertura debe aumentar a >= 90%.

2. **Dado** que `dedup_and_validate.py` tiene 40% de cobertura, **cuando** se añaden tests para las funciones de detección de herramientas y deduplicación, **entonces** la cobertura debe aumentar a >= 90%.

3. **Dado** que `format_normalizer.py` tiene 54% de cobertura, **cuando** se añaden tests para todas las rutas de conversión (Alpaca, ShareGPT, OpenAI), **entonces** la cobertura debe aumentar a >= 90%.

---

### User Story 3 - Mejorar cobertura de módulos con cobertura media (P3)

**Descripción**: Los módulos con cobertura entre 70-90% necesitan tests adicionales para alcanzar el objetivo del 90%.

**Por qué esta prioridad**: Aunque estos módulos tienen cierta cobertura, aún tienen áreas no testadas que pueden contener bugs.

**Test independiente**: Se puede verificar la cobertura de cada módulo individualmente.

**Escenarios de aceptación**:

1. **Dado** que `agentic_teacher_client.py` tiene 78% de cobertura, **cuando** se añaden tests para las rutas de error y timeout, **entonces** la cobertura debe aumentar a >= 90%.

2. **Dado** que `factory/config.py` tiene 69% de cobertura, **cuando** se añaden tests para todas las rutas de configuración, **entonces** la cobertura debe aumentar a >= 90%.

3. **Dado** que `python_ast_adapter.py` tiene 71% de cobertura, **cuando** se añaden tests para las rutas de fallback regex, **entonces** la cobertura debe aumentar a >= 90%.

---

### Edge Cases

- Qué pasa cuando el tokenizador tiktoken no está disponible
- Qué pasa cuando los archivos de fixture no existen en el sistema de archivos
- Qué pasa cuando los datos de entrada tienen formato inválido
- Cómo maneja el sistema los errores de red al descargar datasets de HuggingFace
- Qué pasa cuando hay registros con contenido extremadamente largo
- Cómo se comportan las funciones de hash con caracteres Unicode especiales

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE tener tests unitarios que cubran al menos el 90% del código en todos los módulos de `src/`.

- **FR-002**: El sistema DEBE usar mocks y fixtures para todos los servicios externos (HuggingFace Hub, APIs de inferencia, etc.).

- **FR-003**: El sistema DEBE tener fixtures en `tests/fixtures/` para datos de prueba que actualmente están en carpetas ignoradas por `.gitignore`.

- **FR-004**: El sistema DEBE proporcionar fixtures reutilizables para cada tipo de dato (DatasetRecord, SampleRecord, ScoreCard, etc.).

- **FR-005**: El sistema DEBE incluir tests para todas las rutas de error y casos límite en los módulos críticos.

- **FR-006**: El sistema DEBE mantener los tests independientes y ejecutables sin dependencias de red.

- **FR-007**: El sistema DEBE documentar en los tests los supuestos sobre el comportamiento esperado.

### Key Entities *(include if feature involves data)*

- **DatasetRecord**: Representa un registro de dataset con mensajes en formato ChatML y metadatos de origen.

- **AnchorDatasetConfig**: Configuración para datasets de anclaje desde HuggingFace Hub.

- **DedupAndValidate**: Proceso de deduplicación y validación de registros.

- **FormatNormalizer**: Normalizador que convierte entre diferentes formatos de dataset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La cobertura total de código debe ser >= 90% según pytest-cov.

- **SC-002**: Todos los archivos en `src/` deben tener cobertura >= 90% excepto aquellos explícitamente excluidos.

- **SC-003**: Los tests deben ejecutarse en menos de 30 segundos sin dependencias de red.

- **SC-004**: El 100% de las funciones públicas en los módulos críticos deben tener al menos un test unitario.

- **SC-005**: No debe haber archivos de fixture en `.gitignore` que sean necesarios para los tests.

## Assumptions

- pytest y pytest-cov están disponibles en el entorno de desarrollo.

- Los fixtures pueden almacenarse en `tests/fixtures/` sin problemas de tamaño.

- Los mocks son suficientes para simular servicios externos sin necesidad de fixtures reales.

- El objetivo del 90% de cobertura es aplicable a todos los módulos de producción.

## Notes

- Los módulos con 0% de cobertura son prioridad máxima.

- Los fixtures deben seguir el patrón existente del proyecto (fixtures en `tests/fixtures/`).

- Los tests deben ser deterministas y no depender de estados externos.
