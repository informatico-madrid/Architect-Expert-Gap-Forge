# Data Model: Git Worktree Integration para ralph-loop

**Feature**: 002-ralph-worktree  
**Date**: 2026-03-11

---

## Entidades principales

### 1. WorktreeContext (estado en memoria durante ejecución del loop)

Variables bash en scope global del script:

| Variable | Tipo | Descripción |
|---|---|---|
| `WORKTREE_ENABLED` | bool (`true`/`false`) | Activado salvo que se pase `--no-worktree` |
| `WORKTREE_PATH` | string (ruta absoluta) | `.worktrees/{slug}-{YYYYMMDD_HHMMSS}/` |
| `WORKTREE_BRANCH` | string | `ralph/{slug}-{YYYYMMDD_HHMMSS}` |
| `WORKTREE_CREATED_AT` | string (ISO-8601) | Timestamp de creación del worktree |
| `BASE_BRANCH` | string | Rama base desde donde se creó (ej. `main`) |
| `SKIP_PREFLIGHT` | bool | Activado con `--skip-preflight` |
| `RALPH_PUSH` | bool (env var) | Push opt-in vía `RALPH_PUSH=true` |
| `PUSH_TRACKING_SET` | bool | `true` tras el primer `git push -u`, para hacer `git push` las siguientes |
| `RALPH_SNAPSHOT` | bool (env var) | `1` cuando el proceso corre desde snapshot en tmpdir; previene re-exec recursivo (FR-022) |
| `RALPH_SNAPSHOT_DIR` | string (ruta absoluta) | tmpdir creado por el self-snapshot; eliminado en `trap EXIT` |

---

### 2. state.json — campos nuevos (worktree)

El schema de `.ralph/state.json` se amplía con 4 campos opcionales; cuando `WORKTREE_ENABLED=false` estos campos no se escriben:

```json
{
  "worktreePath":      "/abs/path/.worktrees/001-slug-20260311_120000/",
  "worktreeBranch":    "ralph/001-slug-20260311_120000",
  "worktreeCreatedAt": "2026-03-11T12:00:00",
  "baseBranch":        "main"
}
```

| Campo | Tipo JSON | Requerido | Descripción |
|---|---|---|---|
| `worktreePath` | string | Solo si worktree activo | Ruta absoluta del directorio del worktree |
| `worktreeBranch` | string | Solo si worktree activo | Nombre completo de la rama ralph/... |
| `worktreeCreatedAt` | string | Solo si worktree activo | Timestamp ISO de cuando se creó |
| `baseBranch` | string | Solo si worktree activo | Rama base del repo en el momento de crear el worktree |

**Escritura**: vía `python3 .ralph/scripts/merge_state.py .ralph/state.json --set worktreePath=... --set worktreeBranch=... --set worktreeCreatedAt=... --set baseBranch=...`  
**Atomicidad**: garantizada por `merge_state.py` (usa `os.replace` internamente). No se require `.tmp` manual adicional en el script bash.

---

### 3. Sparse-checkout config file

Ruta: `<worktree-git-dir>/info/sparse-checkout`  
(`<worktree-git-dir>` = contenido del archivo `<WORKTREE_PATH>/.git` tras `gitdir: ` prefix)

**Contenido requerido** (exacto, línea a línea):
```
/*
!/specs/
!/specs/**
```

**Validación**: el script verifica que el contenido del archivo sea exactamente este string. Si difiere → re-escribe + `git read-tree -mu HEAD`.

---

### 4. .git/info/exclude del worktree

Ruta: `<worktree-git-dir>/info/exclude`

**Entrada añadida**:
```
# Excluded via sparse-checkout
specs/
```

El script verifica si la entrada ya existe antes de añadirla (idempotente).

---

### 5. .gitignore del proyecto

Entrada añadida por FR-018 si no existe:
```
.worktrees/
```

Verificación: `grep -qxF '.worktrees/' .gitignore`  
Acción si falta: `echo '.worktrees/' >> .gitignore`

---

### 6. Convenciones de nombrado

| Artefacto | Patrón | Ejemplo |
|---|---|---|
| Directorio worktree | `.worktrees/{slug}-{YYYYMMDD_HHMMSS}/` | `.worktrees/001-stage1-discovery-20260311_120000/` |
| Rama worktree | `ralph/{slug}-{YYYYMMDD_HHMMSS}` | `ralph/001-stage1-discovery-20260311_120000` |
| Colisión de timestamp | sufijo `-{4-digit-random}` | `ralph/001-stage1-20260311_120000-4827` |
| Timestamp format | `$(date '+%Y%m%d_%H%M%S')` | `20260311_120000` |

---

### 7. Transiciones de estado del worktree

```
[NO WORKTREE]
    │ init_worktree() — nueva ejecución
    ▼
[WORKTREE CREATED] → state.json: worktreePath, worktreeBranch, worktreeCreatedAt, baseBranch
    │ cada iteración: ensure_sparse_checkout() + cd "$WORKTREE_PATH"
    ▼
[LOOP RUNNING] → agente opera en rama ralph/...
    │ TASK_COMPLETE / ALL_TASKS_COMPLETE / max_iter / Ctrl+C
    ▼
[LOOP FINISHED] → imprime squash-merge command
    │ operador ejecuta: git merge --squash ralph/... && git commit
    ▼
[BRANCH MERGED] → operador ejecuta: ralph-loop.sh --clean <slug>
    │ --clean detecta ramas mergeadas, elimina worktrees + branches
    ▼
[CLEANED]
```

---

### 8. Función de ciclo de vida por iteración (secuencia de llamadas)

Dentro del bucle `while true`:

```
1. ensure_sparse_checkout "$WORKTREE_PATH"   ← desde $PROJECT_DIR
2. detect_and_recreate_worktree_if_missing   ← si directorio fue borrado
3. cd "$WORKTREE_PATH"
4. [build prompt + run agent]
5. cd "$PROJECT_DIR"
6. [three-layer verification]
7. [optional: git push if RALPH_PUSH=true]
8. update_state (atomic via merge_state.py)
```
