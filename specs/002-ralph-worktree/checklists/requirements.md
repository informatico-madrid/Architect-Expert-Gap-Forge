# Specification Quality Checklist: Git Worktree Integration para ralph-loop

**Purpose**: Validar completitud y calidad de la especificación antes de pasar a planning
**Created**: 2026-03-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Spec cubre las 3 partes solicitadas: P1 worktree aislado, P2 sparse-checkout, P3 preflight checks
- Se captura el patrón de spec-kitty (worktree + .git/info/exclude + sparse-checkout) adaptado a bash sin la complejidad multi-WP
- Los flags --no-worktree, --skip-preflight y RALPH_PUSH garantizan compatibilidad y escape hatches
- Out of Scope claramente delimitado: no merge automático, no paralelismo multi-WP, no limpieza automática
- Sesión de clarificación completada (5 preguntas):
  - Q1: Ruta con timestamp para evitar colisiones → FR-001/FR-002
  - Q2: Rutas absolutas en prompt, solo línea CWD informativa → FR-017
  - Q3: Mecanismo spec-kitty completo (sparse-checkout + exclude + borrado físico) → FR-008/FR-009/FR-010
  - Q4: Push opt-in vía RALPH_PUSH=true, off por defecto → FR-019
  - Q5: cd real al worktree antes de invocar agente → FR-003
- Gaps detectados vs spec-kitty y resueltos: re-validación sparse en cada iteración (FR-008b), worktree list en preflight (FR-011b), .worktrees en .gitignore (FR-018)
- Segunda ronda de clarificación (3 preguntas adicionales):
  - Q6: Método sparse-checkout → config directo + cone false + read-tree (sin CLI de alto nivel) → FR-008 actualizado
  - Q7: Trap EXIT para atomicidad state.json → tmp+mv atómico, trap solo limpia .tmp, worktree intacto → FR-020
  - Q8: --clean con detección de ramas mergeadas → elimina auto mergeadas, confirmación para no mergeadas, git worktree prune al final → FR-021; Out of Scope actualizado
- Tercera ronda de clarificación (5 preguntas adicionales):
  - Q9: Rama base para --clean → auto-detección vía git symbolic-ref, fallback main/master → FR-021 actualizado
  - Q10: --resume con commits más recientes que state.json → rama del worktree es fuente de verdad, sin resetear → FR-006 actualizado
  - Q11: Recrear worktree borrado durante ejecución → desde rama existente ralph/slug-ts, conserva commits → edge case actualizado
  - Q12: Orden de FR-008b en iteración → desde $PROJECT_DIR antes del cd, no desde dentro del worktree → FR-008b actualizado
  - Q13: Qué imprimir al finalizar → squash-merge listo para copiar-pegar como sugerencia principal → FR-004 actualizado
- Total: 13 clarificaciones integradas. Spec lista para `/speckit.plan`
