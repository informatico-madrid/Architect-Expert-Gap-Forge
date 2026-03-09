# Checklist: Refactor — Capa de Abstracción de Lenguaje (Stage 1)

**Purpose**: Validar la calidad y completitud de los requisitos para el refactor hacia una capa de abstracción de lenguaje (`ExtractorAdapter`) y la configuración por `profile`.
**Created**: 2026-03-08
**Feature**: [spec.md](specs/001-stage1-discovery/spec.md)

## Requirement Completeness

- [ ] CHK001 - ¿Está definido qué archivos y lenguajes cubre cada `profile` con ejemplos concretos? [Completeness, Spec §FR-001]
- [ ] CHK002 - ¿Incluye cada `profile` el nombre del `extractor_adapter` y una referencia a su implementación objetivo? [Completeness, Spec §FR-005]
- [ ] CHK003 - ¿Se ha especificado la `strategy` de detección de módulos por profile y los parámetros requeridos para cada estrategia? [Completeness, Spec §FR-008]
- [ ] CHK004 - ¿Están versionados y accesibles los `examples/<profile>.yaml` para los perfiles en scope? [Completeness, Spec §FR-011]
- [ ] CHK005 - ¿Se listan claramente los `master_docs` obligatorios y opcionales por profile en `master_docs_map.yaml`? [Completeness, Spec §FR-009]

## Requirement Clarity

- [ ] CHK006 - ¿Está cuantificada y ejemplificada la política por defecto y las alternativas para `on_parse_error` (`abort|skip|mark_and_continue`)? [Clarity, Spec §FR-006]
- [ ] CHK007 - ¿Se define con precisión la forma y campos de `ParseError` (`file_path`, `line`, `error`, `diagnosis`, `fix_hint`)? [Clarity, Spec §FR-006]
- [ ] CHK008 - ¿El formato de `manual_module_mapping` (rutas vs globs) y su semántica están documentados? [Clarity, Spec Assumptions]
- [ ] CHK009 - ¿Están especificados con ejemplos los campos obligatorios del `[ARCH_HEADER]` y el formato de `DEPENDENCIES`? [Clarity, Spec §FR-007]
- [ ] CHK010 - ¿La API del adapter (ParseResult, Dependency) está documentada con tipos y ejemplos? [Clarity, contracts/adapter.md]

## Requirement Consistency

- [ ] CHK011 - ¿Son consistentes los nombres y claves entre `profile`, `master_docs_map.yaml` y `examples/<profile>.yaml`? [Consistency, Spec §FR-001 §FR-009]
- [ ] CHK012 - ¿Se ha definido la precedencia entre `.gitignore` y `profile.ignored_paths` (qué tiene prioridad)? [Consistency, Spec §FR-010]
- [ ] CHK013 - ¿Los formatos de logging, error structure y métricas de `ParseError` son uniformes entre adapters? [Consistency, Spec §FR-006, contracts/adapter.md]

## Acceptance Criteria Quality

- [ ] CHK014 - ¿Los Success Criteria (SC-001..SC-004) están asociados a pruebas automatizadas y son cuantificables? [Acceptance Criteria, Spec §SC-001 §SC-004]
- [ ] CHK015 - ¿Cada requisito FR tiene al menos una métrica verificable (p. ej. %detección de dependencias, latencia por archivo)? [Measurability, Spec §SC-002]
- [ ] CHK016 - ¿Está definido el comportamiento exacto y el mensaje de error cuando falta un `master_doc` obligatorio (FileNotFoundError)? [Acceptance Criteria, Spec §FR-009 §SC-003]
- [ ] CHK017 - ¿Se definieron criterios de rollback o re-procesado para repos que abortan por `ParseError`? [Acceptance Criteria, Spec §FR-006]

## Scenario Coverage

- [ ] CHK018 - ¿La spec cubre los cuatro tipos de escenarios: Primario, Alterno, Excepción y Recuperación? [Coverage, Spec overall]
- [ ] CHK019 - ¿Se documenta la semántica y precedencia de `overrides` por repo en `profile`? [Coverage, Spec §FR-008]
- [ ] CHK020 - ¿Están definidos los criterios para repos grandes o con dependencias vendor-heavy (umbral, skip, streaming)? [Coverage, Assumptions]
- [ ] CHK021 - ¿Está descrito el comportamiento ante rate-limit de GitHub (backoff, logs, reintento)? [Coverage, User Story 1]

## Edge Case Coverage

- [ ] CHK022 - ¿Se han especificado requisitos para archivos parcialmente corruptos (encoding, EOF) y su tratamiento? [Edge Case, Spec §FR-006]
- [ ] CHK023 - ¿Qué debe ocurrir si una entrada en `manual_module_mapping` referencia rutas inexistentes? (error vs advertencia) [Edge Case, Spec §FR-008]
- [ ] CHK024 - ¿Cómo se debe manejar un repositorio con múltiples lenguajes/mezcla de extensiones? ¿Perfil por defecto o multi-profile? [Edge Case, Spec §FR-002]
- [ ] CHK025 - ¿Se ha definido un requisito para tamaño máximo de bundle y reglas de truncado/fragmentación? [Edge Case, Assumptions]

## Non-Functional Requirements

- [ ] CHK026 - ¿Se han cuantificado los objetivos de rendimiento (throughput, p95) o se han establecido límites operacionales aceptables? [Non-Functional, Constitution & Spec]
- [ ] CHK027 - ¿Se especifican requisitos de observabilidad: métricas por repo, contador de `ParseError`, tiempos por etapa y exportación de métricas? [Non-Functional, Spec §SC-004]
- [ ] CHK028 - ¿Se documentan requisitos de seguridad para acceso a master_docs y GitHub tokens (rotación, scopes mínimos)? [Non-Functional, Constitution]
- [ ] CHK029 - ¿Se exige compatibilidad con `.gitignore` y definiciones claras para exclusión de `vendor`/`node_modules`? [Non-Functional, Spec §FR-010]

## Dependencies & Assumptions

- [ ] CHK030 - ¿Están listadas las dependencias opcionales (p. ej. `tree-sitter`) y la política de carga perezosa (lazy)? [Dependencies, research.md]
- [ ] CHK031 - ¿Se documentaron las suposiciones clave sobre la estructura de repos (manifest presence) y el impacto si faltan? [Assumptions, Spec Assumptions]
- [ ] CHK032 - ¿Está definido el ciclo de vida/versionado de los `master_docs` y cómo se actualizan en producción? [Dependencies, Spec §FR-009]
- [ ] CHK033 - ¿Existe un plan de pruebas de integración por profile (repos ejemplo, criterios de aceptación y dataset de test)? [Dependencies, Spec §SC-002]

## Ambiguities & Conflicts

- [ ] CHK034 - ¿Se han listado y priorizado términos vagos (p. ej. “rápido”, “prominent”) para convertirlos en métricas? [Ambiguity, Spec Assumptions]
- [ ] CHK035 - ¿Se detectaron conflictos entre `overrides` por repo y heurísticas globales y se documentó la resolución? [Conflict, Spec §FR-008]
- [ ] CHK036 - ¿Hay trazabilidad mínima (IDs) entre requisitos, criterios de aceptación y tests automatizados? [Traceability, Spec overall]

---

**Uso**: Esta checklist está pensada para revisión de `spec.md` y artefactos asociados antes de implementar el refactor. Marcar cada `CHK###` cuando la revisión documentada lo confirme.
