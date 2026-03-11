# Implementation Plan: Git Worktree Integration para ralph-loop

**Branch**: `002-ralph-worktree` | **Date**: 2026-03-11 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/002-ralph-worktree/spec.md`

## Summary

Añadir soporte nativo de git worktrees al script `.ralph/ralph-loop.sh` para aislar cada ejecución del agente en su propia rama, proteger `specs/` mediante sparse-checkout (patrón spec-kitty), y añadir preflight checks de estado del repositorio. La implementación es **100% aditiva en bash puro**: un único archivo modificado (`.ralph/ralph-loop.sh`), sin nuevos ficheros Python ni dependencias externas. El modo legacy se preserva intacto con `--no-worktree`.

## Technical Context

**Language/Version**: Bash 5.x (GNU/Linux), Python 3.x (para scripts auxiliares ya existentes)  
**Primary Dependencies**: git 2.43.0 (disponible en sistema), `merge_state.py` (ya existente), `count_tasks.py` (ya existente)  
**Storage**: `.ralph/state.json` (4 campos nuevos), `.gitignore` (1 entrada nueva), `.worktrees/` (directorios temporales)  
**Testing**: pytest (tests Python existentes deben seguir pasando — SC-006); validación manual del script bash  
**Target Platform**: Linux (bash ≥ 5, git ≥ 2.5)  
**Project Type**: CLI script (bash)  
**Performance Goals**: Overhead de inicio ≤ 5 segundos vs modo legacy (SC-005)  
**Constraints**: Sin nuevas dependencias externas; sin romper ningún flujo existente; `--no-worktree` garantiza retrocompatibilidad 100%  
**Scale/Scope**: Un único archivo bash (~818 líneas → ~1000 líneas estimadas tras la feature)

## Constitution Check

*GATE: verificado antes de iniciar la implementación.*

| Regla | Estado | Notas |
|---|---|---|
| Strict typing | ✅ N/A | Bash script, no Python. Los scripts Python auxiliares no se modifican. |
| Immutability | ✅ N/A | No aplica a bash. Las variables de estado se escriben atómicamente via `merge_state.py`. |
| No import-time side-effects | ✅ N/A | No hay módulos Python nuevos. |
| Logging (un logger por módulo) | ✅ N/A | El script usa `log_info/log_ok/log_warn/log_error` ya definidos — se reutilizan. |
| Error handling explícito | ✅ APLICADO | Todos los fallos git capturan exit code; preflight termina con `exit 1` + mensaje específico. |
| No silent failures | ✅ APLICADO | Cada fallo de git (worktree add, read-tree, worktree remove) imprime mensaje y aborta limpiamente. |
| SRP | ✅ APLICADO | Cada nueva función tiene una única responsabilidad (ver sección Functions). |
| No nuevas dependencias | ✅ APLICADO | Solo bash y git (ya requeridos). |
| No código duplicado (DRY) | ✅ APLICADO | `ensure_sparse_checkout` es una función, llamada en creación Y en cada iteración. |
| Header policy | ✅ N/A | Solo se modifica el script bash existente, no se crean ficheros Python. |
| YAGNI | ✅ APLICADO | No se añade soporte multi-WP, no se añade bats, no se añade jj. |

**Veredicto**: Sin violaciones. No se necesita tabla de Complexity Tracking.

## Project Structure

### Documentation (esta feature)

```text
specs/002-ralph-worktree/
├── plan.md              ← este archivo
├── research.md          ← Phase 0, resuelto
├── data-model.md        ← Phase 1, completo
├── quickstart.md        ← Phase 1, completo
├── contracts/
│   └── cli.md           ← CLI contract completo
└── tasks.md             ← generado por /speckit.tasks (pendiente)
```

### Source Code (único archivo modificado)

```text
.ralph/
└── ralph-loop.sh        ← ÚNICO ARCHIVO A MODIFICAR

.gitignore               ← se añade .worktrees/ (por el script mismo en primera ejecución)
```

No se crean ficheros Python nuevos ni se modifican `merge_state.py` o `count_tasks.py`.

---

## Architectural Design

### Principio de diseño

**Additive-only**: todas las funciones nuevas son funciones bash separadas que el main loop llama condicionalmente. La ruta de código existente (cuando `WORKTREE_ENABLED=false`) es idéntica al script original.

### Mapa de funciones nuevas

```
ralph-loop.sh
│
├── [NUEVO] check_gitignore_worktrees()      # FR-018
├── [NUEVO] run_preflight_checks()           # FR-011, FR-011b, FR-012, FR-013, FR-014
│
├── [NUEVO] generate_worktree_name()         # FR-001, FR-002 (slug + timestamp + colisión)
├── [NUEVO] get_worktree_git_dir()           # resolve .git file → real git dir
├── [NUEVO] configure_sparse_checkout()      # FR-008 (creación inicial)
├── [NUEVO] init_worktree()                  # FR-001, FR-002, FR-007
│
├── [NUEVO] ensure_sparse_checkout()         # FR-008b (por iteración, desde $PROJECT_DIR)
├── [NUEVO] detect_and_recreate_worktree()   # edge case: directorio borrado
│
├── [NUEVO] print_merge_instructions()       # FR-004: squash-merge command al finalizar
│
├── [NUEVO] detect_base_branch()             # FR-021: auto-detect main/master
├── [NUEVO] run_clean()                      # FR-021: --clean subcommand
│
├── [MODIFICADO] parse_args()               # añadir --no-worktree, --skip-preflight, --clean
├── [MODIFICADO] show_help()                # documentar flags nuevos
├── [MODIFICADO] init_state()               # añadir baseBranch + worktree fields
├── [MODIFICADO] build_work_prompt()        # FR-017: línea "Working directory:"
├── [MODIFICADO] main()                     # orquestación nuevo flujo
└── [MODIFICADO] git push (línea 803)       # FR-019: condicionado a RALPH_PUSH
```

---

## Implementation Phases

### Fase A0 — Self-snapshot bootstrap (FR-022) ← PRIMERA FASE, antes de todo

**Objetivo**: Garantizar que el proceso bash corre desde una copia congelada de todos los archivos runtime de `.ralph/`, inmune a cualquier modificación del agente durante las iteraciones.

**Pseudocódigo** (al inicio del script, inmediatamente después del shebang y los comentarios de uso):
```bash
# Self-snapshot: protección frente a auto-modificación (FR-022)
if [[ "${RALPH_SNAPSHOT:-0}" != "1" ]]; then
    _snap_dir=$(mktemp -d)
    cp "$0"                                         "$_snap_dir/ralph-loop.sh"
    cp "$(dirname "$0")/recipes/ralph-work.yaml"    "$_snap_dir/ralph-work.yaml"
    cp "$(dirname "$0")/recipes/ralph-review.yaml"  "$_snap_dir/ralph-review.yaml"
    mkdir -p "$_snap_dir/scripts"
    cp "$(dirname "$0")/scripts/merge_state.py"     "$_snap_dir/scripts/merge_state.py"
    cp "$(dirname "$0")/scripts/count_tasks.py"     "$_snap_dir/scripts/count_tasks.py"
    export RALPH_SNAPSHOT=1
    export RALPH_SNAPSHOT_DIR="$_snap_dir"
    exec bash "$_snap_dir/ralph-loop.sh" "$@"
fi
# Llegamos aquí solo cuando RALPH_SNAPSHOT=1 (proceso congelado)
```

Las variables `RALPH_DIR` definidas en el bloque Configuration deben respetar `RALPH_SNAPSHOT_DIR` si está definido:
```bash
RALPH_DIR="${RALPH_SNAPSHOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
```

El `trap EXIT` de Fase A también debe limpiar `$RALPH_SNAPSHOT_DIR`:
```bash
trap 'rm -f "$PROJECT_DIR/.ralph/state.json.tmp"; [[ -n "${RALPH_SNAPSHOT_DIR:-}" ]] && rm -rf "$RALPH_SNAPSHOT_DIR"' EXIT
```

**Nota estructura del snapshot**: `$_snap_dir/recipes/` no existe — los yaml se copian directamente a `$_snap_dir/`. El `RALPH_DIR` apunta a `$_snap_dir`; las referencias a `$RALPH_DIR/recipes/ralph-work.yaml` y `$RALPH_DIR/recipes/ralph-review.yaml` deben buscar en `$RALPH_DIR/ralph-work.yaml` **ó** crear la estructura `$_snap_dir/recipes/` en el cp. **Decisión de implementación**: crear `$_snap_dir/recipes/` y `$_snap_dir/scripts/` para preservar las rutas relativas existentes sin modificarlas.

**Pseudocódigo corregido** (con estructura de directorios):
```bash
if [[ "${RALPH_SNAPSHOT:-0}" != "1" ]]; then
    _snap_dir=$(mktemp -d)
    mkdir -p "$_snap_dir/recipes" "$_snap_dir/scripts"
    _self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cp "$_self_dir/ralph-loop.sh"              "$_snap_dir/ralph-loop.sh"
    cp "$_self_dir/recipes/ralph-work.yaml"    "$_snap_dir/recipes/ralph-work.yaml"
    cp "$_self_dir/recipes/ralph-review.yaml"  "$_snap_dir/recipes/ralph-review.yaml"
    cp "$_self_dir/scripts/merge_state.py"     "$_snap_dir/scripts/merge_state.py"
    cp "$_self_dir/scripts/count_tasks.py"     "$_snap_dir/scripts/count_tasks.py"
    export RALPH_SNAPSHOT=1
    export RALPH_SNAPSHOT_DIR="$_snap_dir"
    exec bash "$_snap_dir/ralph-loop.sh" "$@"
fi
```

**Verificación**: ejecutar el script; verificar que `RALPH_SNAPSHOT=1` y `RALPH_SNAPSHOT_DIR=/tmp/tmp.XXXX` están definidos dentro del loop. Al terminar, el tmpdir debe estar eliminado.

---

### Fase A — Scaffolding y flags

**Objetivo**: Añadir variables globales y flags nuevos sin cambiar comportamiento actual.

**Cambios**:
1. Añadir al bloque `Configuration` (respetando override de `RALPH_SNAPSHOT_DIR`):
   ```bash
   WORKTREE_ENABLED=true
   SKIP_PREFLIGHT=false
   RALPH_PUSH="${RALPH_PUSH:-false}"
   PUSH_TRACKING_SET=false
   WORKTREE_PATH=""
   WORKTREE_BRANCH=""
   WORKTREE_CREATED_AT=""
   BASE_BRANCH=""
   ```
2. Ampliar `parse_args()`: manejar `--no-worktree` (→ `WORKTREE_ENABLED=false`), `--skip-preflight` (→ `SKIP_PREFLIGHT=true`), `--clean [slug]` (→ `CLEAN_MODE=true; CLEAN_SLUG="$2"`)
3. Actualizar `show_help()` con los 3 flags nuevos
4. Añadir `trap EXIT` al inicio de `main()`:
   ```bash
   trap 'rm -f "$PROJECT_DIR/.ralph/state.json.tmp"' EXIT
   ```

**Verificación**: `--help` muestra los flags nuevos; script sin flags sigue funcionando igual.

---

### Fase B — Preflight checks (FR-011, FR-011b, FR-012)

**Función `run_preflight_checks()`**:

```bash
run_preflight_checks() {
    if [[ "$SKIP_PREFLIGHT" == "true" ]]; then
        log_warn "[WARN] Preflight checks omitidos"
        return 0
    fi

    # FR-011b: worktree list trust check (también detecta dirty indirectamente)
    local wt_out
    wt_out=$(git -C "$PROJECT_DIR" worktree list --porcelain 2>&1)
    if [[ $? -ne 0 ]]; then
        log_error "git worktree list falló (posible safe.directory error)"
        log_info  "Fix: git config --global --add safe.directory $PROJECT_DIR"
        exit 1
    fi

    # FR-011: dirty working tree
    local dirty
    dirty=$(git -C "$PROJECT_DIR" status --porcelain 2>&1)
    if [[ -n "$dirty" ]]; then
        log_error "Hay archivos sin commit en el repo principal:"
        echo "$dirty" | head -10 >&2
        log_info  "Fix: git add -A && git commit -m 'wip: save work before ralph'"
        exit 1
    fi

    # FR-012: in-progress git operations
    for sentinel in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD; do
        if [[ -f "$PROJECT_DIR/.git/$sentinel" ]]; then
            local op="${sentinel//_HEAD/}"
            log_error "${op} en curso detectado (.git/${sentinel})"
            log_info  "Fix: git ${op,,} --abort"
            exit 1
        fi
    done

    log_ok "Preflight checks: OK"
}
```

**Verificación**: script con archivo sin commit → `[ERROR]` + exit 1, sin crear worktree.

---

### Fase C — .gitignore check (FR-018)

**Función `check_gitignore_worktrees()`**:

```bash
check_gitignore_worktrees() {
    local gitignore="$PROJECT_DIR/.gitignore"
    if ! grep -qxF '.worktrees/' "$gitignore" 2>/dev/null; then
        echo '.worktrees/' >> "$gitignore"
        log_info "Añadido .worktrees/ a .gitignore"
    fi
}
```

Llamada una vez en `main()` antes de `init_worktree()`.

---

### Fase D — Creación del worktree (FR-001 a FR-003, FR-007, FR-008, FR-009, FR-010)

**Función `get_worktree_git_dir(worktree_path)`**:
- Lee `$worktree_path/.git` (archivo, no directorio en worktrees)
- Extrae el path real: `sed 's/^gitdir: //'`
- Retorna la ruta absoluta del git dir del worktree

**Función `configure_sparse_checkout(worktree_path)`** (FR-008, FR-009, FR-010):
1. `get_worktree_git_dir` → `git_dir`
2. `git -C $worktree_path config core.sparseCheckout true`
3. `git -C $worktree_path config core.sparseCheckoutCone false`
4. `printf '/*\n!/specs/\n!/specs/**\n' > $git_dir/info/sparse-checkout`
5. `git -C $worktree_path read-tree -mu HEAD`
6. Añadir `specs/` a `$git_dir/info/exclude` si no está (idempotente)
7. `rm -rf $worktree_path/specs` si persiste tras sparse (FR-010)

**Función `generate_worktree_name(slug)`** (FR-001, FR-002):
- Construye `ralph/${slug}-$(date '+%Y%m%d_%H%M%S')`
- Si la rama ya existe: añade `-$(printf '%04d' $((RANDOM % 10000)))`

**Función `init_worktree(spec_dir)`**:
1. `slug=$(basename "$spec_dir")`
2. `WORKTREE_BRANCH=$(generate_worktree_name "$slug")`
3. `WORKTREE_PATH="$PROJECT_DIR/.worktrees/$(echo "$WORKTREE_BRANCH" | sed 's|ralph/||')"`
4. `BASE_BRANCH=$(git -C "$PROJECT_DIR" branch --show-current)`
5. `mkdir -p "$(dirname "$WORKTREE_PATH")"`
6. `git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" -b "$WORKTREE_BRANCH"` o exit 1
7. `configure_sparse_checkout "$WORKTREE_PATH"`
8. `update_state --set worktreePath=... --set worktreeBranch=... --set worktreeCreatedAt=... --set baseBranch=...`

**Verificación**: `.worktrees/slug-ts/` existe; `specs/` ausente del worktree; `git worktree list` la muestra.

---

### Fase E — `ensure_sparse_checkout` por iteración (FR-008b)

**Función `ensure_sparse_checkout(worktree_path)`**:
- `get_worktree_git_dir` → si falla, return (no worktree)
- Compara contenido de `$git_dir/info/sparse-checkout` con el string esperado
- Si difiere o no existe: llama `configure_sparse_checkout "$worktree_path"`

Llamada al **inicio de cada iteración del loop**, antes del `cd "$WORKTREE_PATH"`.

---

### Fase F — Detección y recreación de worktree borrado (edge case)

**Función `detect_and_recreate_worktree()`**:
- Si `[[ ! -d "$WORKTREE_PATH" ]]`:
  - `git worktree prune` para limpiar referencias huérfanas
  - `git worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH"` (la rama ya existe con commits)
  - `configure_sparse_checkout "$WORKTREE_PATH"`

---

### Fase G — Prompt y cd (FR-003, FR-017)

**`build_work_prompt()`**: añadir al inicio del prompt (si `WORKTREE_ENABLED=true`):
```
Working directory: $WORKTREE_PATH
```

**Main loop**: envolver `run_work_agent` con:
```bash
[[ "$WORKTREE_ENABLED" == "true" ]] && cd "$WORKTREE_PATH"
agent_output=$(run_work_agent ...)
[[ "$WORKTREE_ENABLED" == "true" ]] && cd "$PROJECT_DIR"
```

---

### Fase H — Push condicional (FR-019)

Reemplaza la línea 803 (`git push origin "$current_branch" 2>/dev/null || true`):

```bash
if [[ "${RALPH_PUSH:-false}" == "true" ]]; then
    if git -C "$PROJECT_DIR" remote get-url origin &>/dev/null; then
        local push_branch
        if [[ "$WORKTREE_ENABLED" == "true" ]]; then
            push_branch="$WORKTREE_BRANCH"
        else
            push_branch=$(git -C "$PROJECT_DIR" branch --show-current)
        fi
        if [[ "$PUSH_TRACKING_SET" != "true" ]]; then
            git -C "$PROJECT_DIR" push -u origin "$push_branch" 2>/dev/null || true
            PUSH_TRACKING_SET=true
        else
            git -C "$PROJECT_DIR" push 2>/dev/null || true
        fi
    fi
fi
```

---

### Fase I — print_merge_instructions (FR-004)

**Función `print_merge_instructions()`**: imprime al finalizar el loop (éxito o cap):
- Worktree path y branch
- Comando squash-merge listo para copiar-pegar
- Alternativa con merge regular
- Comando `--clean` sugerido

Llamada al final de `main()`, tanto en el exit 0 de "ALL TASKS COMPLETE" como en el break del safety cap.

---

### Fase J — `--clean` subcommand (FR-021)

**Función `detect_base_branch()`**:
1. `git symbolic-ref refs/remotes/origin/HEAD` → extrae nombre
2. Fallback: probar `main`, luego `master`
3. Si ninguno → retorna string vacío (el caller aborta con hint)

**Función `run_clean(slug)`**:
1. Si slug vacío → leer `state.json` campo `name`
2. `detect_base_branch` o exit 1 con hint
3. Iterar sobre `.worktrees/${slug}-*/`
4. Por cada una: obtener branch via `git worktree list --porcelain`
5. `git branch --merged $base_branch` → clasificar
6. Mergeadas: `git worktree remove --force` + `git branch -d`
7. No mergeadas: pedir confirmación interactiva
8. Final: `git worktree prune`

---

### Fase K — Integración en `main()` (orquestación final)

El nuevo flujo de `main()`:

```
parse_args
validate agent (existente)
if CLEAN_MODE → run_clean "$CLEAN_SLUG"; exit 0

if RESUME_MODE:
    cargar state.json
    restaurar WORKTREE_PATH, WORKTREE_BRANCH, BASE_BRANCH desde state
else:
    init_state
    if WORKTREE_ENABLED:
        check_gitignore_worktrees
        run_preflight_checks
        init_worktree

[banner display — añadir worktree info si WORKTREE_ENABLED]

while true:
    [safety cap y all-done check — idénticos]
    
    if WORKTREE_ENABLED:
        ensure_sparse_checkout "$WORKTREE_PATH"    ← desde $PROJECT_DIR
        detect_and_recreate_worktree
    
    [build prompt — con Working directory: si WORKTREE_ENABLED]
    
    if WORKTREE_ENABLED: cd "$WORKTREE_PATH"
    run_work_agent ...
    if WORKTREE_ENABLED: cd "$PROJECT_DIR"
    
    [three-layer verification — idéntico]
    [push condicional RALPH_PUSH — Fase H]
    [update state — idéntico]
    sleep 2

# Al salir del loop (cualquier razón):
print_merge_instructions
```

---

## Non-Functional Requirements

### SC-005: Overhead ≤ 5s
- `git worktree add`: ~0.5s
- `configure_sparse_checkout`: ~0.5s  
- `run_preflight_checks`: ~0.3s  
- **Total estimado**: ~1.3s ✅

### SC-006: pytest sin regresiones
No se modifica ningún fichero Python. Verificación: `pytest tests/ -x --tb=short`.

---

## Sequence of Implementation Tasks

Orden recomendado para `/speckit.tasks`:

| # | Fase | Descripción |
|---|---|---|
| T00 | A0 | Self-snapshot bootstrap: cp `.ralph/` runtime files → tmpdir + exec con RALPH_SNAPSHOT=1 (FR-022) |
| T01 | A | Scaffolding: variables globales nuevas + flags + show_help + trap EXIT (incluye limpieza RALPH_SNAPSHOT_DIR) |
| T02 | B | `run_preflight_checks()` (dirty tree + merge/rebase + worktree list trust) |
| T03 | C | `check_gitignore_worktrees()` |
| T04 | D | `get_worktree_git_dir()` + `configure_sparse_checkout()` + `generate_worktree_name()` + `init_worktree()` |
| T05 | E | `ensure_sparse_checkout()` + llamada al inicio del loop |
| T06 | F | `detect_and_recreate_worktree()` + llamada en el loop |
| T07 | G | `build_work_prompt()` modified + cd wrappers en main loop |
| T08 | H | Push condicional RALPH_PUSH (reemplaza línea 803) |
| T09 | I | `print_merge_instructions()` + llamada al finalizar |
| T10 | J | `detect_base_branch()` + `run_clean()` + routing en main |
| T11 | K | `init_state()` ampliado + `main()` orquestación completa + resume worktree fields |
| T12 | — | Verificación end-to-end: SC-001 a SC-007 |
