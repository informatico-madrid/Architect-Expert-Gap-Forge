# Research: Git Worktree Integration para ralph-loop

**Feature**: 002-ralph-worktree  
**Date**: 2026-03-11  
**Status**: Complete — todos los unknowns resueltos

---

## 1. Versión de git disponible

**Decision**: git 2.43.0 (sistema)  
**Rationale**: Supera con creces el mínimo requerido (git ≥ 2.5 para `git worktree`; ≥ 2.37 para cone mode). `git worktree add`, `git worktree remove`, `git worktree list --porcelain`, `git worktree prune` están todos disponibles.  
**Alternatives considered**: N/A — el sistema tiene git moderno.

---

## 2. Método de configuración de sparse-checkout

**Decision**: Config directo (no CLI de alto nivel) — igual que spec-kitty.  
**Rationale**: `git sparse-checkout init` en git ≥ 2.37 activa `core.sparseCheckoutCone=true` por defecto, lo que ignora silenciosamente las negaciones `!/specs/`. La secuencia segura es:
```bash
git -C "$WORKTREE_PATH" config core.sparseCheckout true
git -C "$WORKTREE_PATH" config core.sparseCheckoutCone false
printf '/*\n!/specs/\n!/specs/**\n' > "$GIT_DIR/info/sparse-checkout"
git -C "$WORKTREE_PATH" read-tree -mu HEAD
```
**Alternatives considered**: `git sparse-checkout set --no-cone` — descartado porque requiere git ≥ 2.37 explícitamente y el flag `--no-cone` no está disponible en versiones intermedias.

---

## 3. Schema actual de state.json y API de merge_state.py

**Decision**: Añadir 4 campos nuevos a state.json via `merge_state.py --set`:
- `worktreePath` (string): ruta absoluta del worktree activo
- `worktreeBranch` (string): nombre de la rama ralph/...
- `worktreeCreatedAt` (string): timestamp ISO de creación
- `baseBranch` (string): rama base desde donde se creó el worktree (para --clean)

**Rationale**: `merge_state.py` ya tiene escritura atómica real (`os.replace`) — no hace falta implementar la atomicidad manualmente dentro del script bash; simplemente invocar `python3 merge_state.py --set worktreePath=...` es suficiente y thread-safe. El `trap EXIT` del FR-020 solo necesita eliminar el `.tmp` si existe, pero dado que `merge_state.py` ya usa `os.replace`, el riesgo de `.tmp` huérfano es mínimo. Se mantiene igualmente por robustez.

**Alternatives considered**: Escribir campos directamente con `jq` — descartado porque `jq` puede no estar disponible; `merge_state.py` es la vía canónica del proyecto.

**Schema actual completo** (campos existentes + nuevos marcados con `NEW`):
```json
{
  "awaitingApproval": false,
  "basePath": "specs/001-...",
  "baseBranch": "main",           // NEW
  "featureId": 1,
  "fixTaskMap": {},
  "globalIteration": 0,
  "lastReviewAt": 0,
  "maxFixTasksPerOriginal": 3,
  "maxGlobalIterations": 100,
  "maxTaskIterations": 5,
  "name": "001-...",
  "phase": "execution",
  "recoveryMode": true,
  "reviewInterval": 5,
  "taskIndex": 0,
  "taskIteration": 1,
  "totalTasks": 0,
  "worktreeBranch": "ralph/001-...-20260311_120000",  // NEW
  "worktreeCreatedAt": "2026-03-11T12:00:00",         // NEW
  "worktreePath": "/abs/path/.worktrees/001-...-ts/"  // NEW
}
```

---

## 4. Infraestructura de tests para bash

**Decision**: No existe test suite de bash en el proyecto. El SC-006 exige que `pytest tests/` siga pasando; tests del script bash se validan manualmente o mediante un test de integración end-to-end.  
**Rationale**: El proyecto usa pytest solo para código Python en `src/`. El script `.ralph/ralph-loop.sh` no tiene cobertura automatizada hoy — esto no cambia con esta feature. Las verificaciones de no-regresión se realizan ejecutando el loop con `--no-worktree` tras la implementación.  
**Alternatives considered**: Añadir bats (Bash Automated Testing System) — descartado, fuera del scope de esta feature (YAGNI).

---

## 5. Estado de .gitignore — entrada .worktrees/

**Decision**: `.worktrees/` NO figura en `.gitignore` actualmente. FR-018 exige que el script lo añada automáticamente en la primera ejecución.  
**Rationale**: Se verifica con `grep -q "^\.worktrees" .gitignore` y se añade con `echo '.worktrees/' >> .gitignore` seguido de un commit automático si el worktree mode está activo.  
**Alternatives considered**: Requerir que el operador lo añada manualmente — descartado, el autoñadir es menos friction y más seguro.

---

## 6. Rama base del proyecto

**Decision**: El repo local no tiene `refs/remotes/origin/HEAD` configurado (no hay remote activo). El fallback de FR-021 aplica: intentar `main`, luego `master`. La rama actual es `002-ralph-worktree`; la rama base del proyecto es `main`.  
**Rationale**: El script debe detectar esto silenciosamente y usar `main` como default, sin fallar.  
**Alternatives considered**: Requerir `--base-branch` siempre — descartado, demasiada fricción para el caso normal.

---

## 8. Self-snapshot bootstrap: protección contra auto-modificación

**Decision**: Implementar self-snapshot completo al inicio del script. Los archivos a copiar al tmpdir son: `ralph-loop.sh`, `recipes/ralph-work.yaml`, `recipes/ralph-review.yaml`, `scripts/merge_state.py`, `scripts/count_tasks.py`. El script redefine `RALPH_DIR=$tmpdir` y hace `exec env RALPH_SNAPSHOT=1 bash "$tmpdir/ralph-loop.sh" "$@"`. La variable `RALPH_SNAPSHOT=1` previene re-exec recursivo. El tmpdir se elimina en `trap EXIT`.

**Rationale**: Bash lee `ralph-loop.sh` secuencialmente del disco durante la ejecución; modificaciones al archivo en iteraciones posteriores (el caso exacto del bootstrap que implementa esta feature) pueden afectar el proceso en marcha. Los subprocesos de goose lanzan un nuevo binario y leen los recipes del disco en cada iteración — sin snapshot, verían la versión parcialmente implementada de `ralph-work.yaml` o `ralph-review.yaml` si el agente los modifica durante el run.

**Alternatives considered**:
- Solo snapshot de `ralph-loop.sh`: descartado, los recipes de goose son subprocesos que leen del disco cada iteración — misma clase de riesgo.
- Confiar en que bash parsea todo al inicio: no formalmente garantizado; comportamiento dependiente de versión. Descartado.
- Documentar como riesgo aceptable con `--no-worktree` bootstrap: descartado, FR-022 es más seguro y costo de implementación es ~10 líneas.

---

## 7. Comportamiento del git push existente (línea 803)

**Decision**: La línea actual `git push origin "$current_branch" 2>/dev/null || true` debe moverse/adaptarse: en modo worktree, empuja la rama del worktree (`$WORKTREE_BRANCH`) solo si `RALPH_PUSH=true`; en modo legacy (`--no-worktree`), mantiene el comportamiento actual.  
**Rationale**: La línea en línea 803 siempre pushea independientemente de `RALPH_PUSH` — esto es un bug latente que se corrige al refactorizar. En modo worktree sin `RALPH_PUSH=true`, no se debe pushear nada.  
**Alternatives considered**: Mantener la línea actual y añadir condición extra — descartado, resulta en lógica duplicada.
