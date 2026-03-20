---
description: "Task list for Rich Terminal Output para CLI"
---

# Tasks: Rich Terminal Output para CLI

**Input**: Design documents from `/specs/014-rich-cli-output/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**IMPORTANT**: Cada tarea DEBE usar la skill de rich-terminal-output (ver `.roo/skills/rich-terminal-output/SKILL.md`) para implementar la salida de terminal mejorada.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (diferentes archivos, sin dependencias)
- **[Story]**: A qué user story pertenece (US1, US2, US3)
- Incluir rutas exactas de archivos en las descripciones
- **TODAS las tareas deben mencionar explícitamente el uso de la skill rich-terminal-output**

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Agregar dependencia de Rich al proyecto

- [ ] T001 Instalar biblioteca Rich: `pip install rich` y agregar a requirements.txt
- [ ] T002 [P] Verificar instalación de Rich ejecutando: `python -c "from rich import print; print('[bold green]Rich working![/]')"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Crear utilities compartida para uso de Rich

**CRITICAL**: Estas tareas deben completarse antes de implementar cualquier user story

- [ ] T003 [P] Crear módulo helper `src/utils/rich_helpers.py` con utilidades Rich reutilizables (Console instance, funciones de formato comunes)
- [ ] T004 [P] Verificar que el módulo helper funciona ejecutando tests básicos

---

## Phase 3: User Story 1 - Adoptar Rich en Scripts CLI Principales (Priority: P1) 🎯 MVP

**Goal**: Migrar los scripts CLI principales del proyecto para usar Rich en su salida

**Independent Test**: Ejecutar cada script modificado y verificar que muestra output formateado con Rich (tablas, paneles, barras de progreso)

### Implementation for User Story 1

- [ ] T005 [P] [US1] Modificar `src/audit/cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T006 [P] [US1] Modificar `src/audit/calibration.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T007 [P] [US1] Modificar `src/curation/curator_cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T008 [P] [US1] Modificar `src/curation/rewrite_cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T009 [P] [US1] Modificar `src/discovery/ingestor.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T010 [P] [US1] Modificar `src/discovery/processor_cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T011 [P] [US1] Modificar `src/factory/cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels
- [ ] T012 [P] [US1] Modificar `src/factory/agentic_cli.py` para usar rich-terminal-output skill - agregar Console, Progress, Panels

**Checkpoint**: Los 8 scripts CLI principales ahora usan Rich. Verificar ejecutando cada uno.

---

## Phase 4: User Story 2 - Migrar Scripts de Merger (Priority: P2)

**Goal**: Migrar los 14 scripts en src/merger/ para usar Rich

**Independent Test**: Ejecutar cada script merger modificado y verificar output formateado

### Implementation for User Story 2

- [ ] T013 [P] [US2] Modificar `src/merger/analisis_avanzado.py` para usar rich-terminal-output skill
- [ ] T014 [P] [US2] Modificar `src/merger/check_alignment.py` para usar rich-terminal-output skill
- [ ] T015 [P] [US2] Modificar `src/merger/clean_dna.py` para usar rich-terminal-output skill
- [ ] T016 [P] [US2] Modificar `src/merger/diagnostico.py` para usar rich-terminal-output skill
- [ ] T017 [P] [US2] Modificar `src/merger/dna_fix_v2.py` para usar rich-terminal-output skill
- [ ] T018 [P] [US2] Modificar `src/merger/dna_strict.py` para usar rich-terminal-output skill
- [ ] T019 [P] [US2] Modificar `src/merger/final_ignition.py` para usar rich-terminal-output skill
- [ ] T020 [P] [US2] Modificar `src/merger/fusionar_final.py` para usar rich-terminal-output skill
- [ ] T021 [P] [US2] Modificar `src/merger/guardar_tokenizador.py` para usar rich-terminal-output skill
- [ ] T022 [P] [US2] Modificar `src/merger/merge_shards.py` para usar rich-terminal-output skill
- [ ] T023 [P] [US2] Modificar `src/merger/repara_stage2.py` para usar rich-terminal-output skill
- [ ] T024 [P] [US2] Modificar `src/merger/repair_dna.py` para usar rich-terminal-output skill
- [ ] T025 [P] [US2] Modificar `src/merger/repair_triple_dna.py` para usar rich-terminal-output skill
- [ ] T026 [P] [US2] Modificar `src/merger/shotgun_dna.py` para usar rich-terminal-output skill

**Checkpoint**: Los 14 scripts de merger ahora usan Rich

---

## Phase 5: User Story 3 - Documentar Uso en Tasks de Implementación (Priority: P3)

**Goal**: Asegurar que futuras implementaciones incluyan requerimiento de Rich

**Independent Test**: Verificar que nuevas specs incluyan Rich en sus tasks

### Implementation for User Story 3

- [ ] T027 [US3] Actualizar template de tasks `.specify/templates/tasks-template.md` para incluir recordatorio de usar rich-terminal-output skill en cada tarea de CLI
- [ ] T028 [US3] Documentar en AGENTS.md o similar que scripts CLI nuevos deben usar skill rich-terminal-output

---

## Phase 6: User Story 4 - Scripts Restantes (Priority: P4)

**Goal**: Completar migración de scripts restantes

**Independent Test**: Ejecutar scripts restantes y verificar output

### Implementation for User Story 4

- [ ] T029 [P] [US4] Modificar `src/research/generate_batch_distilabel.py` para usar rich-terminal-output skill

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verificaciones finales y mejoras

- [ ] T030 [P] Ejecutar `pytest` y verificar que todos los tests pasan (100% compatibilidad)
- [ ] T031 [P] Verificar que output es legible cuando se pipea (no-TTY)
- [ ] T032 Agregar RichHandler al logging del proyecto para output consistente
- [ ] T033 Verificar que no hay regressions en cobertura con `make coverage`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencias - puede comenzar inmediatamente
- **Foundational (Phase 2)**: Depende de Setup - BLOQUEA todos los user stories
- **User Stories (Phase 3+)**: Todas dependen de Foundational
  - User stories pueden proceder en paralelo (si hay capacidad)
  - O secuencialmente en orden de prioridad (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depende de todos los user stories completados

### User Story Dependencies

- **User Story 1 (P1)**: Puede iniciar después de Foundational - Sin dependencias de otras stories
- **User Story 2 (P2)**: Puede iniciar después de Foundational - Sin dependencias de otras stories
- **User Story 3 (P3)**: Puede iniciar después de Foundational - Independiente
- **User Story 4 (P4)**: Puede iniciar después de Foundational - Independiente

### Within Each User Story

- Todas las tareas [P] pueden ejecutarse en paralelo dentro de cada fase
- Cada script modificado debe probarse independientemente
- Story completo antes de pasar a la siguiente prioridad

---

## Parallel Opportunities

- Phase 1: T001 y T002 pueden ejecutarse en paralelo
- Phase 2: T003 y T004 pueden ejecutarse en paralelo
- Phase 3: T005-T012 pueden ejecutarse en paralelo (8 scripts independientes)
- Phase 4: T013-T026 pueden ejecutarse en paralelo (14 scripts independientes)
- Phase 5: T027-T028 pueden ejecutarse en paralelo
- Phase 6: T029 puede ejecutarse con otras tareas [P]
- Phase 7: T030-T031 pueden ejecutarse en paralelo

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (8 scripts principales)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Polish Phase → Final verification

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (8 scripts)
   - Developer B: User Story 2 (14 scripts)
   - Developer C: User Story 3 & 4
3. Stories complete and integrate independently

---

## Notes

- **TODAS las tareas incluyen rich-terminal-output skill** - esta es la característica central de esta feature
- [P] tasks = diferentes archivos, sin dependencias
- [Story] label mapea tarea a user story específico
- Cada user story debe ser independientemente completable y testeable
- Commit después de cada tarea o grupo lógico
- Detenerse en cualquier checkpoint para validar story independientemente
- Evitar: tareas vagas, conflictos del mismo archivo, dependencias cruzadas
