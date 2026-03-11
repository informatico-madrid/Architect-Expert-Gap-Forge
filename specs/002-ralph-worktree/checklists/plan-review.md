# Plan Review Checklist: Git Worktree Integration para ralph-loop

**Purpose**: Validar la calidad, completitud y consistencia de los requisitos antes de generar tasks.md — testear si los "requirements escritos en inglés/español" están bien redactados, sin ambigüedades y listos para implementación.
**Created**: 2026-03-11
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)
**Scope**: Pre-`/speckit.tasks` · Audiencia: revisor de spec/plan
**Depth**: Full coverage (FR-001–FR-022, 4 partes, edge cases, bootstrap safety)

---

## Completitud de Requisitos

- [ ] CHK001 - ¿Están definidos todos los requisitos para el ciclo de vida completo del worktree (creación → uso → limpieza)? [Completeness, Spec §FR-001, FR-005, FR-021]
- [ ] CHK002 - ¿Existe una FR que cubra qué debe ocurrir si `mktemp -d` falla (disco lleno, `/tmp` no escribible) en el self-snapshot? [Gap, Spec §FR-022]
- [ ] CHK003 - ¿Definen los requisitos el comportamiento cuando se pasa `--resume` y `state.json` no contiene los campos `worktreePath`/`worktreeBranch` (ejecución previa en modo `--no-worktree`)? [Gap, Spec §FR-006, FR-007]
- [ ] CHK004 - ¿Están especificados los requisitos para el caso en que `git worktree add` falla por rama ya existente (colisión de timestamp)? [Completeness, Spec §Edge Cases]
- [ ] CHK005 - ¿Existe una FR que especifique el comportamiento del flag `--clean` cuando `state.json` está ausente o corrupto (no hay slug activo del que extraer el argumento)? [Gap, Spec §FR-021]
- [ ] CHK006 - ¿Se especifica qué ocurre con el tmpdir del snapshot (`RALPH_SNAPSHOT_DIR`) si el proceso es matado con `kill -9` (SIGKILL no dispara `trap EXIT`)? [Gap, Spec §FR-022]
- [ ] CHK007 - ¿Está cubierto el requisito de qué archivos del worktree son visibles para el agente cuando sparse-checkout excluye `specs/` pero el agente necesita leer `specs/` vía ruta absoluta? [Completeness, Spec §FR-008, FR-010b]
- [ ] CHK008 - ¿Define la spec el comportamiento del flag `--auto-merge` mencionado en FR-005? (Se menciona como escape hatch pero no tiene su propia FR ni está explícitamente en Out of Scope) [Ambiguity, Spec §FR-005]

---

## Claridad y Precisión

- [ ] CHK009 - ¿Está "slug" definido explícitamente? ¿Se especifica si es el nombre del directorio de la spec (`001-stage1-discovery`), sólo el sufijo sin número (`stage1-discovery`), o el path completo? [Clarity, Spec §FR-001, FR-002]
- [ ] CHK010 - ¿Es "copia congelada" en FR-022 suficientemente preciso para implementación? ¿Está explicitado que el snapshot ocurre en tiempo de inicio antes de cualquier parsing de argumentos? [Clarity, Spec §FR-022]
- [ ] CHK011 - ¿Está cuantificado "no aumenta más de 5 segundos" de SC-005? ¿Se especifica cómo medirlo (wall clock, time builtin, desde qué punto a qué punto)? [Measurability, Spec §SC-005]
- [ ] CHK012 - ¿Es "imprimiendo un aviso visible" en FR-014 suficientemente concreto? ¿Se define el nivel de log, el prefijo `[WARN]`, destino stdout/stderr? [Clarity, Spec §FR-014]
- [ ] CHK013 - ¿Describe FR-021 con precisión cómo se obtiene la lista de worktrees activos — vía `git worktree list`, listado de `.worktrees/`, o lectura de `state.json`? [Clarity, Spec §FR-021]
- [ ] CHK014 - ¿Define FR-004 el momento exacto en que se imprime la instrucción de merge — al finalizar `DONE`, al alcanzar el cap de iteraciones, o también en errores fatales? [Clarity, Spec §FR-004]
- [ ] CHK015 - ¿Está claro en FR-022 si el `trap EXIT` del self-snapshot wrapper (antes del `exec`) también limpia el tmpdir, o si la limpieza recae 100% en el proceso del snapshot? [Clarity, Spec §FR-022]
- [ ] CHK016 - ¿Especifica FR-011b concretamente qué es un "error de trust/ownership" — un exit code no-cero de `git worktree list`, un mensaje específico en stderr, o ambos? [Clarity, Spec §FR-011b]

---

## Consistencia entre Requisitos

- [ ] CHK017 - ¿Es consistente FR-020 (trap EXIT limpia `.ralph/state.json.tmp`) con FR-022 (trap EXIT también limpia `RALPH_SNAPSHOT_DIR`)? ¿Se especifica un único `trap EXIT` que haga ambas cosas, o pueden coexistir dos traps? [Consistency, Spec §FR-020, FR-022]
- [ ] CHK018 - ¿Es consistente FR-003 (`cd "$WORKTREE_PATH"` antes del agente) con FR-008b (re-validar sparse-checkout desde `$PROJECT_DIR` antes del `cd`)? ¿Está definido el orden preciso de operaciones en cada iteración? [Consistency, Spec §FR-003, FR-008b]
- [ ] CHK019 - ¿Es consistente FR-006 (source of truth = rama del worktree en `--resume`) con FR-007 (persistir en `state.json`)? Si el worktree tiene commits más recientes, ¿qué campo de state.json se actualiza al reanudar? [Consistency, Spec §FR-006, FR-007]
- [ ] CHK020 - ¿Están alineadas las variables bash definidas en data-model.md (`RALPH_DIR`, `RALPH_SNAPSHOT`, `RALPH_SNAPSHOT_DIR`) con la pseudocódigo de FR-022 en spec.md y la Fase A0 en plan.md? [Consistency, Spec §FR-022, Plan §Fase-A0]
- [ ] CHK021 - ¿Es consistente `--auto-merge` mencionado en FR-005 con el Out of Scope que dice "Merge automático al finalizar: queda como flag `--auto-merge` opcional"? Si está Out of Scope, ¿por qué se menciona en FR-005 como si fuera in-scope? [Conflict, Spec §FR-005, §Out of Scope]
- [ ] CHK022 - ¿Coincide la lista de 5 archivos a copiar en FR-022 (spec) con la lista en Fase A0 (plan) y con la tabla de variables en data-model.md? [Consistency, Spec §FR-022, Plan §Fase-A0, data-model.md]

---

## Criterios de Aceptación — Medibilidad

- [ ] CHK023 - ¿Son todos los Success Criteria (SC-001–SC-007) verificables sin ambigüedad? ¿Puede SC-001 ("ningún commit nuevo del agente en main") detectarse con un comando git concreto como `git log main..HEAD` o `git cherry main`? [Measurability, Spec §SC-001]
- [ ] CHK024 - ¿Está SC-003 ("archivos bajo `specs/` no aparecen en `git status`") expresado de forma que un script de verificación pueda ejecutarlo automáticamente? [Measurability, Spec §SC-003]
- [ ] CHK025 - ¿Define SC-004 ("100% de los intentos bloqueados") bajo qué condiciones precisas de test? ¿Una modificación staged? ¿Sin stagear? ¿Archivos nuevos sin trackear? [Measurability, Spec §SC-004]
- [ ] CHK026 - ¿Tiene SC-006 un criterio de fallo concreto? ¿Debe `pytest tests/` pasar con exit code 0, o solo ciertos módulos? [Measurability, Spec §SC-006]

---

## Cobertura de Escenarios

- [ ] CHK027 - ¿Existe un escenario de aceptación para el flujo "primera ejecución + Ctrl+C + `--resume`"? (La US-1 cubre el happy path pero no el crash-and-resume end-to-end) [Coverage, Spec §US-1, FR-006]
- [ ] CHK028 - ¿Hay un escenario que valide el comportamiento cuando `--no-worktree` y `--resume` se pasan simultáneamente? [Coverage, Gap]
- [ ] CHK029 - ¿Existe un escenario de aceptación para el caso de bootstrap (el script implementándose a sí mismo vía RALPH_SNAPSHOT)? [Coverage, Gap, Spec §FR-022]
- [ ] CHK030 - ¿Cubren los User Stories el flujo de `--clean` como paso post-merge del operador? (Los 3 User Stories cubren creación/operación/preflight pero no el ciclo de vida completo hasta limpieza) [Coverage, Spec §FR-021]
- [ ] CHK031 - ¿Hay un escenario de aceptación para el uso de `--skip-preflight` en entorno CI? [Coverage, Gap, Spec §FR-014]

---

## Cobertura de Casos Borde

- [ ] CHK032 - ¿Define la spec el comportamiento cuando el worktree ya existe en disco (directorio `$WORKTREE_PATH` presente) pero `git worktree list` no lo reconoce (worktree huérfano)? [Edge Case, Gap, Spec §FR-010]
- [ ] CHK033 - ¿Está cubierto el caso en que `git read-tree -mu HEAD` falla durante la configuración de sparse-checkout (p.ej. conflictos de checkout)? [Edge Case, Gap, Spec §FR-008]
- [ ] CHK034 - ¿Especifica la spec el comportamiento cuando `--clean` no encuentra ningún worktree que coincida con el slug — ¿error, aviso o silencio? [Edge Case, Gap, Spec §FR-021]
- [ ] CHK035 - ¿Define la spec qué ocurre si `RALPH_SNAPSHOT_DIR` ya está definido en el entorno antes de lanzar el script (variable heredada de sesión anterior)? [Edge Case, Gap, Spec §FR-022]
- [ ] CHK036 - ¿Está cubierto el edge case de lanzar el loop cuando ya existe un worktree de la misma spec con mismo slug pero diferente timestamp (múltiples worktrees activos para el mismo slug)? [Edge Case, Spec §FR-001]

---

## Requisitos No Funcionales

- [ ] CHK037 - ¿Están los requisitos de rendimiento (SC-005: overhead ≤5s) especificados para todas las operaciones costosas, no solo para el arranque? ¿Qué ocurre con el overhead de sparse-checkout en repos grandes? [NFR, Spec §SC-005]
- [ ] CHK038 - ¿Están los requisitos de seguridad del tmpdir definidos? ¿Se especifica que `mktemp -d` crea el directorio con permisos 700 (solo el usuario)? [NFR, Security, Gap, Spec §FR-022]
- [ ] CHK039 - ¿Tiene la spec requisitos para la limpieza de tmpdir en sistemas que no persisten `/tmp` entre reinicios (e.g. sistemas con `tmpfs` de vida corta)? [NFR, Gap]
- [ ] CHK040 - ¿Están los requisitos de logging definidos de forma consistente? ¿Se especifica si los mensajes de FR-013 (preflight failures), FR-014 (`[WARN]`) y FR-022 (snapshot) van a stdout o stderr? [NFR, Clarity, Gap]

---

## Dependencias y Asunciones

- [ ] CHK041 - ¿Está validada la asunción de "git >= 2.5 disponible en PATH"? ¿Se menciona en algún preflight check, o solo en Assumptions? [Assumption, Spec §Assumptions]
- [ ] CHK042 - ¿Está documentada la dependencia de que `goose` esté disponible en el PATH del proceso snapshot? El snapshot copia los scripts pero `goose` sigue siendo una dependencia runtime no copiada. [Dependency, Gap, Spec §FR-022]
- [ ] CHK043 - ¿Está documentado que `.specify/memory/constitution.md` (leído por el agente) no forma parte del snapshot — el agente lo lee vía ruta absoluta al repo principal, que puede ser modificado? [Assumption, Spec §Assumptions, FR-022]
- [ ] CHK044 - ¿Se documenta la dependencia de `bash >= 4.x` requerida por el patrón `exec env RALPH_SNAPSHOT=1 bash ...`? [Dependency, Gap, Spec §FR-022]

---

## Trazabilidad plan.md ↔ spec.md

- [ ] CHK045 - ¿Tiene cada FR (FR-001–FR-022) al menos una tarea en la tabla T00–T12 del plan que la implemente explícitamente? [Traceability, Spec §Requirements, Plan §Tasks]
- [ ] CHK046 - ¿Está la nueva tarea T00 (Fase A0 — self-snapshot) correctamente posicionada como pre-requisito de T01 en el plan, sin dependencias circulares? [Traceability, Plan §T00, T01]
- [ ] CHK047 - ¿Se mapean los Success Criteria SC-001–SC-007 a pasos de verificación concretos en el plan (SC-007 "Verificación end-to-end" en T12)? [Traceability, Spec §SC, Plan §T12]
- [ ] CHK048 - ¿Están las variables nuevas `RALPH_SNAPSHOT` y `RALPH_SNAPSHOT_DIR` del data-model.md reflejadas en la pseudocódigo de Fase A0 del plan? [Traceability, data-model.md, Plan §Fase-A0]

---

## Ambigüedades y Conflictos Identificados

- [ ] CHK049 - ¿Se resuelve la ambigüedad de `--auto-merge` — incluirlo como FR propia (aunque sea stub) o eliminarlo de FR-005 y confirmar que es Out of Scope total? [Ambiguity, Spec §FR-005]
- [ ] CHK050 - ¿Se aclara si FR-022 aplica también cuando se llama con `--no-worktree`? (El self-snapshot protege el proceso independientemente del modo — ¿es ese el intent?) [Ambiguity, Spec §FR-022, FR-016]
- [ ] CHK051 - ¿Se resuelve si el slug en los nombres de worktree y rama incluye el número de feature (`001-stage1-discovery`) o solo la parte descriptiva (`stage1-discovery`)? Los User Stories usan `001-stage1-discovery` pero no hay definición formal. [Ambiguity, Spec §FR-001, FR-002]

## Notes

- Checklist generado en sesión 2026-03-11, previo a `/speckit.tasks`
- Items con `[Gap]` indican requisitos ausentes en la spec actual que deberían resolverse antes de implementar
- Items con `[Ambiguity]` o `[Conflict]` indican texto que necesita aclaración explícita
- Items con `[Traceability]` validan la coherencia entre artefactos (spec ↔ plan ↔ data-model)
- Prioridad de resolución sugerida: CHK008/CHK021 (conflicto --auto-merge), CHK009 (definición slug), CHK017 (trap EXIT unificado), CHK002/CHK006 (gaps FR-022)
