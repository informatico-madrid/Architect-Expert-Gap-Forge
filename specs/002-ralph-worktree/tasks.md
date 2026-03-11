# Tasks: Git Worktree Integration para ralph-loop

**Feature**: `002-ralph-worktree`  
**Branch**: `002-ralph-worktree`  
**File**: `.ralph/ralph-loop.sh` (818 líneas → ~1 000 líneas tras la feature)  
**Input**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/cli.md](contracts/cli.md)  
**Generated**: 2026-03-11

---

## Resumen

| Fase | Tarea | Descripción |
|------|-------|-------------|
| A0 | T00 | Self-snapshot bootstrap (FR-022) |
| A  | T01 | Scaffolding: globals + flags + help + trap EXIT |
| B  | T02 | `run_preflight_checks()` |
| C  | T03 | `check_gitignore_worktrees()` |
| D  | T04 | `get_worktree_git_dir()` + `configure_sparse_checkout()` + `generate_worktree_name()` + `init_worktree()` |
| E  | T05 | `ensure_sparse_checkout()` + llamada al inicio del loop |
| F  | T06 | `detect_and_recreate_worktree()` + llamada en el loop |
| G  | T07 | `build_work_prompt()` + cd wrappers en main loop |
| H  | T08 | Push condicional `RALPH_PUSH` (reemplaza línea 803) |
| I  | T09 | `print_merge_instructions()` + llamada al finalizar |
| J  | T10 | `detect_base_branch()` + `run_clean()` + routing en main |
| K  | T11 | `init_state()` ampliado + `main()` orquestación completa + `--resume` worktree fields |
| —  | T12 | Verificación end-to-end SC-001 a SC-007 |

**Scope acotado**: Un único archivo bash modificado (`.ralph/ralph-loop.sh`). `.gitignore` se modifica por el propio script en primera ejecución (FR-018). Sin nuevos ficheros Python.

---

## Phase A0 — Self-snapshot bootstrap

- [x] T00 [Phase A0] Self-snapshot bootstrap: protección frente a auto-modificación
  - **FR**: FR-022
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Inmediatamente después del shebang y bloque de comentarios de uso (antes de cualquier otra lógica), insertar el bloque de auto-snapshot:
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
    2. Localizar la línea donde se define `RALPH_DIR` (usar `grep -n 'RALPH_DIR'`). Modificarla para respetar `RALPH_SNAPSHOT_DIR` cuando está definido:
       ```bash
       RALPH_DIR="${RALPH_SNAPSHOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
       ```
    3. No tocar ninguna otra lógica existente.
  - **Done when**: Al ejecutar `.ralph/ralph-loop.sh --help` sin `RALPH_SNAPSHOT` definido, el proceso hace exec desde un tmpdir y termina normalmente. Dentro del proceso congelado, `printenv RALPH_SNAPSHOT` imprime `1` y `printenv RALPH_SNAPSHOT_DIR` muestra una ruta `/tmp/tmp.XXXXXX`. Al lanzar con `RALPH_SNAPSHOT=1 .ralph/ralph-loop.sh --help` no se crea ningún tmpdir adicional (no hay re-exec recursivo).
  - **Verify**: `RALPH_SNAPSHOT=1 bash .ralph/ralph-loop.sh --help > /dev/null && echo OK`
  - **Commit**: `feat(ralph): self-snapshot bootstrap to freeze runtime files (FR-022)`

---

## Phase A — Scaffolding

- [x] T01 [Phase A] Scaffolding: variables globales, flags nuevos, show_help, trap EXIT
  - **FR**: FR-014, FR-016, FR-019, FR-020, FR-022 (limpieza de RALPH_SNAPSHOT_DIR en trap)
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. En el bloque `Configuration` (tras la definición de constantes existentes), añadir las 8 nuevas variables globales:
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
    2. En `parse_args()`, añadir el manejo de los 3 flags nuevos al bloque `case "$1"`:
       ```bash
       --no-worktree)   WORKTREE_ENABLED=false; shift ;;
       --skip-preflight) SKIP_PREFLIGHT=true; shift ;;
       --clean)         CLEAN_MODE=true; CLEAN_SLUG="${2:-}"; [[ -n "${2:-}" ]] && shift; shift ;;
       ```
       También añadir `CLEAN_MODE=false` y `CLEAN_SLUG=""` en el bloque de inicialización de variables de `parse_args`.
    3. En `show_help()`, añadir las tres líneas de documentación en la sección de flags:
       ```
         --no-worktree       Run in legacy mode without git worktree
         --skip-preflight    Skip preflight checks [WARN]
         --clean [slug]      Remove merged worktrees for given spec slug
       ```
    4. Localizar el `trap EXIT` existente (o añadirlo si no existe) en `main()` y ampliarlo para limpiar también `RALPH_SNAPSHOT_DIR`:
       ```bash
       trap 'rm -f "$PROJECT_DIR/.ralph/state.json.tmp"; [[ -n "${RALPH_SNAPSHOT_DIR:-}" ]] && rm -rf "$RALPH_SNAPSHOT_DIR"' EXIT
       ```
  - **Done when**: `bash .ralph/ralph-loop.sh --help` muestra exactamente los 3 flags nuevos (`--no-worktree`, `--skip-preflight`, `--clean`). `bash -n .ralph/ralph-loop.sh` no reporta errores de sintaxis.
  - **Verify**: `.ralph/ralph-loop.sh --help | grep -cE 'no-worktree|skip-preflight|clean'` imprime `3`
  - **Commit**: `feat(ralph): add worktree flags, globals, and trap EXIT scaffold (FR-016, FR-019, FR-020)`

---

## Phase B — Preflight checks

- [x] T02 [Phase B] Implementar `run_preflight_checks()`
  - **FR**: FR-011, FR-011b, FR-012, FR-013, FR-014
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Añadir la función `run_preflight_checks()` antes de `main()` (o en el bloque de funciones auxiliares). Implementar los tres checks en el orden del pseudocódigo de plan.md Fase B:
       - **Check 0 — skip guard**: si `SKIP_PREFLIGHT=true`, `log_warn "[WARN] Preflight checks omitidos"` y `return 0`.
       - **Check 1 — worktree list trust** (FR-011b): `git -C "$PROJECT_DIR" worktree list --porcelain`; si falla, imprimir `[ERROR]` con fix de `safe.directory` y `exit 1`.
       - **Check 2 — dirty tree** (FR-011): `git -C "$PROJECT_DIR" status --porcelain`; si no vacío, imprimir lista de archivos con `head -10` y fix `git add -A && git commit` y `exit 1`.
       - **Check 3 — in-progress ops** (FR-012): iterar sobre `MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD`; si alguno existe en `$PROJECT_DIR/.git/`, imprimir `[ERROR]` con `git <op> --abort` y `exit 1`.
       - **Éxito**: `log_ok "Preflight checks: OK"`.
    2. No llamar aún a la función desde `main()` — eso se hace en T11.
  - **Done when**: Con un archivo modificado sin stagear en `$PROJECT_DIR`, ejecutar `source .ralph/ralph-loop.sh && run_preflight_checks` termina con `exit 1` y imprime `[ERROR]` listando el archivo pendiente. Con repo limpio y `SKIP_PREFLIGHT=false`, termina con `[OK] Preflight checks: OK`.
  - **Verify**: `(cd /mnt/bunker_data/ai/data_factory && touch /tmp/_dirty_test && git -C . add /tmp/_dirty_test 2>/dev/null || true; bash -c 'source .ralph/ralph-loop.sh 2>/dev/null; run_preflight_checks; echo $?' 2>&1 | grep -q 'Preflight checks: OK') && echo OK`
  - **Commit**: `feat(ralph): implement run_preflight_checks() (FR-011, FR-011b, FR-012, FR-013, FR-014)`

---

## Phase C — .gitignore check

- [x] T03 [Phase C] Implementar `check_gitignore_worktrees()`
  - **FR**: FR-018
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Añadir la función `check_gitignore_worktrees()` en el bloque de funciones auxiliares:
       ```bash
       check_gitignore_worktrees() {
           local gitignore="$PROJECT_DIR/.gitignore"
           if ! grep -qxF '.worktrees/' "$gitignore" 2>/dev/null; then
               echo '.worktrees/' >> "$gitignore"
               log_info "Añadido .worktrees/ a .gitignore"
           fi
       }
       ```
    2. No llamar aún desde `main()` — eso se hace en T11.
  - **Done when**: La función es idempotente: ejecutarla dos veces seguidas produce exactamente una línea `.worktrees/` en `.gitignore` (no duplica). Si ya existía la línea, no la añade. Si no existía, la añade con un mensaje `[INFO]`.
  - **Verify**: `grep -x '.worktrees/' /mnt/bunker_data/ai/data_factory/.gitignore | wc -l` imprime `0` antes (actual) y `1` después de una ejecución en modo worktree. Idempotencia: segunda ejecución sigue imprimiendo `1`.
  - **Commit**: `feat(ralph): implement check_gitignore_worktrees() (FR-018)`

---

## Phase D — Creación del worktree

- [x] T04 [Phase D] Implementar las 4 funciones de creación del worktree
  - **FR**: FR-001, FR-002, FR-007, FR-008, FR-009, FR-010
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. **`get_worktree_git_dir(worktree_path)`**: Lee `$1/.git` (archivo de texto), extrae la ruta real con `sed 's/^gitdir: //'`, imprime la ruta absoluta.
    2. **`configure_sparse_checkout(worktree_path)`** (FR-008, FR-009, FR-010):
       - Llamar `get_worktree_git_dir "$1"` → `git_dir`.
       - `git -C "$1" config core.sparseCheckout true`
       - `git -C "$1" config core.sparseCheckoutCone false`
       - `printf '/*\n!/specs/\n!/specs/**\n' > "$git_dir/info/sparse-checkout"`
       - `git -C "$1" read-tree -mu HEAD`
       - Añadir a `$git_dir/info/exclude` la línea `specs/` (idempotente: comprobar antes con `grep -q`).
       - Si `$1/specs/` persiste en disco: `rm -rf "$1/specs"` (FR-010).
    3. **`generate_worktree_name(slug)`** (FR-001, FR-002):
       - Construir el nombre candidato: `ralph/${slug}-$(date '+%Y%m%d_%H%M%S')`.
       - Si la rama ya existe (`git -C "$PROJECT_DIR" branch --list "$candidate"` no vacío): añadir `-$(printf '%04d' $((RANDOM % 10000)))`.
       - Imprimir el nombre final (`echo "$candidate"`).
    4. **`init_worktree(spec_dir)`** (FR-001, FR-002, FR-007, FR-008):
       - `slug=$(basename "$spec_dir")`
       - `WORKTREE_BRANCH=$(generate_worktree_name "$slug")`
       - `WORKTREE_PATH="$PROJECT_DIR/.worktrees/$(echo "$WORKTREE_BRANCH" | sed 's|ralph/||')"` 
       - `BASE_BRANCH=$(git -C "$PROJECT_DIR" branch --show-current)`
       - `WORKTREE_CREATED_AT=$(date --iso-8601=seconds)`
       - `mkdir -p "$PROJECT_DIR/.worktrees"`
       - `git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" -b "$WORKTREE_BRANCH" || { log_error "git worktree add falló"; exit 1; }`
       - `configure_sparse_checkout "$WORKTREE_PATH"`
       - Escribir los 4 campos en state.json vía `python3 "$RALPH_DIR/scripts/merge_state.py" "$PROJECT_DIR/.ralph/state.json" --set worktreePath="$WORKTREE_PATH" --set worktreeBranch="$WORKTREE_BRANCH" --set worktreeCreatedAt="$WORKTREE_CREATED_AT" --set baseBranch="$BASE_BRANCH"`
    5. No llamar aún desde `main()` — eso se hace en T11.
  - **Done when**: Llamar `init_worktree "specs/002-test"` desde el repo principal: (1) crea `.worktrees/002-test-<ts>/`, (2) `git worktree list` la muestra, (3) `ls .worktrees/002-test-<ts>/` no contiene `specs/`, (4) `cat .worktrees/002-test-<ts>/.git/info/sparse-checkout` muestra `/*\n!/specs/\n!/specs/**\n`, (5) `.ralph/state.json` contiene `worktreePath`, `worktreeBranch`, `worktreeCreatedAt`, `baseBranch`.
  - **Verify**: `git worktree list | grep -c '.worktrees/'` imprime `1` tras la llamada. `python3 -c "import json; d=json.load(open('.ralph/state.json')); print(d['worktreePath'])"` imprime la ruta del worktree.
  - **Commit**: `feat(ralph): implement worktree creation functions (FR-001, FR-002, FR-007, FR-008, FR-009, FR-010)`

---

## Phase E — ensure_sparse_checkout por iteración

- [x] T05 [Phase E] Implementar `ensure_sparse_checkout()` y llamada en el loop
  - **FR**: FR-008b
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Añadir la función `ensure_sparse_checkout(worktree_path)`:
       ```bash
       ensure_sparse_checkout() {
           local wt_path="$1"
           local git_dir
           git_dir=$(get_worktree_git_dir "$wt_path") || return 0
           local sc_file="$git_dir/info/sparse-checkout"
           local expected
           expected="$(printf '/*\n!/specs/\n!/specs/**\n')"
           local actual
           actual="$(cat "$sc_file" 2>/dev/null || true)"
           if [[ "$actual" != "$expected" ]]; then
               configure_sparse_checkout "$wt_path"
           fi
       }
       ```
    2. Localizar el bloque `while true` del main loop. Al inicio de cada iteración (justo antes de cualquier lógica de tarea), insertar la llamada condicional **desde `$PROJECT_DIR`**:
       ```bash
       if [[ "$WORKTREE_ENABLED" == "true" ]]; then
           ensure_sparse_checkout "$WORKTREE_PATH"
       fi
       ```
       Esta llamada debe preceder al `cd "$WORKTREE_PATH"` que se añadirá en T07.
  - **Done when**: Si se corrompe manualmente el archivo `<worktree-git-dir>/info/sparse-checkout` (por ejemplo borrándolo), la siguiente iteración del loop lo restaura con el contenido correcto y ejecuta `git read-tree -mu HEAD`. Si el contenido ya es correcto, la función termina sin ejecutar read-tree (verificable con `strace -e execve`).
  - **Verify**: `cat "$(cat .worktrees/$(ls .worktrees/ | head -1)/.git | sed 's/gitdir: //')/info/sparse-checkout"` muestra exactamente `/*`, `!/specs/`, `!/specs/**`.
  - **Commit**: `feat(ralph): implement ensure_sparse_checkout() per-iteration guard (FR-008b)`

---

## Phase F — Detección y recreación de worktree borrado

- [x] T06 [Phase F] Implementar `detect_and_recreate_worktree()` y llamada en el loop
  - **FR**: Edge case de spec.md (directorio del worktree borrado durante la ejecución)
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Añadir la función `detect_and_recreate_worktree()`:
       ```bash
       detect_and_recreate_worktree() {
           if [[ -n "$WORKTREE_PATH" && ! -d "$WORKTREE_PATH" ]]; then
               log_warn "[WARN] Worktree directory missing; recreating: $WORKTREE_PATH"
               git -C "$PROJECT_DIR" worktree prune
               git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH" \
                   || { log_error "No se pudo recrear el worktree"; exit 1; }
               configure_sparse_checkout "$WORKTREE_PATH"
               log_ok "Worktree recreado: $WORKTREE_PATH"
           fi
       }
       ```
    2. En el bloque `while true` del main loop, justo **después** de `ensure_sparse_checkout` (añadido en T05), insertar:
       ```bash
       if [[ "$WORKTREE_ENABLED" == "true" ]]; then
           detect_and_recreate_worktree
       fi
       ```
  - **Done when**: Al eliminar manualmente el directorio del worktree (`rm -rf .worktrees/<slug>-<ts>/`) mientras el loop está en pausa entre iteraciones, la siguiente iteración lo recrea con la misma rama, los commits previos siguen intactos en `git log`, y la ejecución continúa sin error.
  - **Verify**: `declare -F detect_and_recreate_worktree` (o `grep -q "detect_and_recreate_worktree()" .ralph/ralph-loop.sh && echo OK`)
  - **Commit**: `feat(ralph): implement detect_and_recreate_worktree() edge-case guard`

---

## Phase G — Prompt y cd wrappers

- [x] T07 [Phase G] Añadir "Working directory:" al prompt + cd wrappers en main loop
  - **FR**: FR-003, FR-017
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. En la función `build_work_prompt()`, localizar el inicio de la construcción del string del prompt. Añadir **al inicio del bloque de contexto** (solo si `WORKTREE_ENABLED=true`):
       ```bash
       if [[ "$WORKTREE_ENABLED" == "true" ]]; then
           prompt+=$'\n'"Working directory: $WORKTREE_PATH"$'\n'
       fi
       ```
    2. En el bloque `while true`, localizar la invocación de `run_work_agent` (o equivalente: claude/goose/custom). Envolver con:
       ```bash
       [[ "$WORKTREE_ENABLED" == "true" ]] && cd "$WORKTREE_PATH"
       # ... invocación existente de run_work_agent / goose / claude ...
       [[ "$WORKTREE_ENABLED" == "true" ]] && cd "$PROJECT_DIR"
       ```
    3. No modificar ninguna ruta absoluta existente en el prompt — todas las referencias a `specs/`, `src/`, `tests/` siguen siendo rutas absolutas hacia `$PROJECT_DIR` y funcionan sin cambios.
  - **Done when**: El prompt generado incluye la línea `Working directory: <ruta absoluta del worktree>` cuando `WORKTREE_ENABLED=true`. Con `--no-worktree`, el prompt es idéntico al original. Los commits del agente caen en la rama del worktree y no en la rama base.
  - **Verify**: `grep -A2 'build_work_prompt' .ralph/ralph-loop.sh | grep -q 'Working directory' && echo OK`
  - **Commit**: `feat(ralph): add working-directory line to prompt and cd wrappers (FR-003, FR-017)`

---

## Phase H — Push condicional RALPH_PUSH

- [x] T08 [Phase H] Reemplazar push incondicional (línea 803) con guard RALPH_PUSH
  - **FR**: FR-019
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Localizar la línea 803 (o actual línea equivalente): `git push origin "$current_branch" 2>/dev/null || true`.
    2. Reemplazarla íntegramente por el bloque condicional de Fase H de plan.md:
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
  - **Done when**: Con `RALPH_PUSH=false` (default), ningún `git push` se ejecuta en ningún caso. Con `RALPH_PUSH=true` y remote `origin` presente, la primera iteración usa `-u origin <branch>` y las siguientes usan `git push` sin argumentos. Sin remote `origin`, el bloque termina en silencio sin error.
  - **Verify**: `grep -c 'RALPH_PUSH' .ralph/ralph-loop.sh` imprime ≥ 3 (definición en globals T01, comprobación en este bloque, flag existente en contracts).
  - **Commit**: `feat(ralph): conditional RALPH_PUSH replaces unconditional git push (FR-019)`

---

## Phase I — print_merge_instructions

- [x] T09 [Phase I] Implementar `print_merge_instructions()` y llamada al finalizar
  - **FR**: FR-004, FR-005
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. Añadir la función `print_merge_instructions()` en el bloque de funciones auxiliares:
       ```bash
       print_merge_instructions() {
           [[ "$WORKTREE_ENABLED" != "true" || -z "$WORKTREE_BRANCH" ]] && return 0
           local slug
           slug=$(basename "$WORKTREE_PATH")
           log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
           log_info "Worktree:  $WORKTREE_PATH"
           log_info "Branch:    $WORKTREE_BRANCH"
           log_info "To merge (squash — recommended):"
           log_info "  git merge --squash $WORKTREE_BRANCH && git commit -m \"feat($slug): <description>\""
           log_info "Or (preserve full history):"
           log_info "  git merge $WORKTREE_BRANCH"
           log_info "To clean up after merge:"
           log_info "  .ralph/ralph-loop.sh --clean $slug"
           log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
       }
       ```
    2. Localizar los dos puntos de salida del main loop: (a) el exit `[OK] ALL TASKS COMPLETE` y (b) el break del safety cap `[WARN] Safety cap reached`. En ambos, añadir la llamada `print_merge_instructions` justo antes del exit/break final.
  - **Done when**: Al terminar el loop (por éxito o por cap), el terminal imprime el bloque completo con el nombre real de la rama (`ralph/<slug>-<ts>`) y los comandos de merge listos para copiar-pegar. Con `--no-worktree`, la función retorna en silencio sin imprimir nada.
  - **Verify**: `grep -c 'print_merge_instructions' .ralph/ralph-loop.sh` imprime ≥ 3 (definición + llamada en ALL TASKS COMPLETE + llamada en safety cap).
  - **Commit**: `feat(ralph): implement print_merge_instructions() at loop exit (FR-004, FR-005)`

---

## Phase J — --clean subcommand

- [x] T10 [Phase J] Implementar `detect_base_branch()` + `run_clean()` + routing en main
  - **FR**: FR-021
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. **`detect_base_branch()`**:
       ```bash
       detect_base_branch() {
           local ref
           ref=$(git -C "$PROJECT_DIR" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
           if [[ -n "$ref" ]]; then
               echo "${ref##*/}"; return 0
           fi
           for b in main master; do
               if git -C "$PROJECT_DIR" branch --list "$b" | grep -q "$b"; then
                   echo "$b"; return 0
               fi
           done
           return 1
       }
       ```
    2. **`run_clean(slug)`** (según Fase J de plan.md):
       - Si `slug` vacío: leer campo `name` de `.ralph/state.json` vía `python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" ".ralph/state.json"`.
       - Llamar `detect_base_branch` o `exit 1` con hint de `--base-branch`.
       - Iterar sobre `.worktrees/${slug}-*/`.
       - Para cada directorio: obtener su rama con `git worktree list --porcelain | awk "/^worktree.*${slug}/{f=1} f && /^branch/{print \$2; f=0}"`.
       - Clasificar con `git -C "$PROJECT_DIR" branch --merged "$base_branch"`.
       - Mergeadas: `git -C "$PROJECT_DIR" worktree remove --force "$wt_path" && git -C "$PROJECT_DIR" branch -d "$wt_branch"`.
       - No mergeadas: `read -rp "Delete unmerged worktree $wt_path? [y/N] " confirm; [[ "$confirm" == [yY] ]] && ...`.
       - Final: `git -C "$PROJECT_DIR" worktree prune`.
    3. En `main()`, al inicio (tras `parse_args`), añadir el routing:
       ```bash
       if [[ "${CLEAN_MODE:-false}" == "true" ]]; then
           run_clean "${CLEAN_SLUG:-}"
           exit 0
       fi
       ```
  - **Done when**: `.ralph/ralph-loop.sh --clean 002-test` detecta los worktrees de ese slug, imprime los mergeados y no-mergeados por separado, elimina los mergeados automáticamente y pide confirmación para los no-mergeados. Termina con `git worktree prune`. Con slug inexistente, imprime mensaje informativo y termina con exit 0.
  - **Verify**: `bash .ralph/ralph-loop.sh --clean --help 2>&1 | grep -q 'clean' && echo OK`; `declare -F run_clean 2>/dev/null || grep -q "run_clean()" .ralph/ralph-loop.sh && echo OK`
  - **Commit**: `feat(ralph): implement --clean subcommand with merged detection (FR-021)`

---

## Phase K — Orquestación final

- [x] T11 [Phase K] `init_state()` ampliado + `main()` orquestación completa + `--resume` worktree fields
  - **FR**: FR-006, FR-007, FR-015, FR-016, FR-020
  - **File**: `.ralph/ralph-loop.sh`
  - **Do**:
    1. **Ampliar `init_state()`**: después de los `--set` existentes (name, basePath, etc.), añadir escritura condicional de los 4 campos de worktree solo si `WORKTREE_ENABLED=true`:
       ```bash
       if [[ "$WORKTREE_ENABLED" == "true" ]]; then
           python3 "$RALPH_DIR/scripts/merge_state.py" "$PROJECT_DIR/.ralph/state.json" \
               --set "worktreePath=$WORKTREE_PATH" \
               --set "worktreeBranch=$WORKTREE_BRANCH" \
               --set "worktreeCreatedAt=$WORKTREE_CREATED_AT" \
               --set "baseBranch=$BASE_BRANCH"
       fi
       ```
    2. **`--resume` + restaurar worktree fields** (FR-006): en el bloque `if RESUME_MODE`, tras cargar el state.json, añadir:
       ```bash
       if [[ "$WORKTREE_ENABLED" == "true" ]]; then
           WORKTREE_PATH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('worktreePath',''))" "$PROJECT_DIR/.ralph/state.json")
           WORKTREE_BRANCH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('worktreeBranch',''))" "$PROJECT_DIR/.ralph/state.json")
           BASE_BRANCH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('baseBranch',''))" "$PROJECT_DIR/.ralph/state.json")
       fi
       ```
    3. **Ampliar `main()`** con el flujo descrito en Fase K de plan.md:
       - Después de `parse_args` y validación de agente: routing para `CLEAN_MODE` (ya hecho en T10).
       - Bloque `if RESUME_MODE`: cargar state + restaurar worktree fields.
       - Bloque `else` (nueva ejecución): `init_state` → si `WORKTREE_ENABLED`: llamar en orden `check_gitignore_worktrees`, `run_preflight_checks`, `init_worktree`.
       - Banner del loop: añadir `log_info "Worktree: $WORKTREE_PATH"` y `log_info "Branch:   $WORKTREE_BRANCH"` si `WORKTREE_ENABLED=true`.
       - En el `while true`: las llamadas de T05 (`ensure_sparse_checkout`) y T06 (`detect_and_recreate_worktree`) ya están en el loop; confirmar que están posicionadas antes del `cd "$WORKTREE_PATH"` de T07.
       - Al salir del loop: llamada a `print_merge_instructions` (añadida en T09).
    4. Verificar que el modo `--no-worktree` salta completamente el bloque de worktree y se comporta igual que el script original.
  - **Done when**: `bash -n .ralph/ralph-loop.sh` sin errores. Flujo completo: `bash .ralph/ralph-loop.sh specs/002-test-minimal` crea worktree, agente trabaja desde él, todos los commits van a la rama de worktree, la rama base no recibe commits, al finalizar se imprime `print_merge_instructions`. Con `--no-worktree`, comportamiento 100% idéntico al original.
  - **Verify**: `bash -n .ralph/ralph-loop.sh && echo "Syntax OK"`
  - **Commit**: `feat(ralph): wire main() orchestration, init_state worktree fields, --resume restore (FR-006, FR-007, FR-015, FR-016, FR-020)`

---

## Phase — End-to-End Verification

- [x] T12 [Verification] Verificación end-to-end: SC-001 a SC-007
  - **FR**: SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007
  - **File**: `.ralph/ralph-loop.sh` (solo lectura — no se modifica)
  - **Do**:
    1. **SC-001** — Ejecutar el loop con una spec de prueba mínima (2 tareas). Al finalizar: `git log main --oneline | head -5` no debe mostrar commits del agente; `git log ralph/<slug>-<ts> --oneline | head -10` sí los muestra.
    2. **SC-002** — Verificar que el historial del worktree es lineal: `git log ralph/<slug>-<ts> --oneline --graph` muestra solo commits lineales, sin merges.
    3. **SC-003** — Dentro del worktree: `git -C .worktrees/<slug>-<ts>/ status` no lista ningún archivo bajo `specs/` como modified/untracked incluso si el agente los modificó.
    4. **SC-004** — Introducir un archivo sin stagear en el repo principal: `touch /tmp/test_dirty && git add /tmp/test_dirty 2>/dev/null; bash .ralph/ralph-loop.sh specs/002-test` → debe terminar con exit 1 y `[ERROR]` visible antes de crear ningún worktree.
    5. **SC-005** — Medir el tiempo desde invocación hasta primera tarea: `time bash .ralph/ralph-loop.sh specs/002-test 2>&1 | head -5` — el overhead total de setup (preflight + worktree create + sparse-checkout) debe ser ≤ 5 segundos.
    6. **SC-006** — `pytest tests/ -x --tb=short` pasa al 100% sin ninguna regresión.
    7. **SC-007** — `bash .ralph/ralph-loop.sh --no-worktree specs/002-test` se comporta idénticamente al script original: no se crea ningún directorio en `.worktrees/`, `git worktree list` sigue mostrando solo el repo principal, todos los commits van a la rama activa.
  - **Done when**: Los 7 success criteria pasan sin excepciones en el entorno de CI local.
  - **Verify**: `pytest tests/ -x --tb=short` (SC-006 — debe ser el primer criterio que se comprueba, ya que es el más rápido y detecta regresiones Python)
  - **Commit**: `test(ralph): verify end-to-end SC-001 through SC-007`

---

## Dependency Graph

```
T00 (self-snapshot bootstrap)
 └─► T01 (globals + flags + trap)
      ├─► T02 (preflight checks)       ← independiente de T03–T06
      ├─► T03 (gitignore check)        ← independiente de T02, T04–T06
      ├─► T04 (worktree creation)      ← depende de T01; independiente de T02, T03
      │    └─► T05 (ensure_sparse)     ← depende de T04
      │         └─► T06 (recreate)     ← depende de T04, T05
      ├─► T07 (prompt + cd)            ← depende de T04; independiente de T02, T03, T05, T06
      ├─► T08 (RALPH_PUSH)             ← independiente de T02–T07
      ├─► T09 (merge instructions)     ← depende de T04
      └─► T10 (--clean subcommand)     ← depende de T01; independiente de T02–T09
           └─► T11 (main() orquesta)   ← integra T02–T10; last integration task
                └─► T12 (E2E verify)   ← depende de T11 completo
```

**Tareas paralelizables** (distintas funciones, sin dependencias mutuas):
- T02, T03 pueden implementarse en paralelo (funciones independientes).
- T07, T08, T09, T10 pueden implementarse en paralelo entre sí una vez T04 está completo.

---

## Implementation Strategy

**MVP mínimo** (loop funcional + aislamiento básico):
- T00 → T01 → T04 → T07 → T11 (sin T02, T03, T05, T06, T08, T09, T10)
- Resultado: loop crea worktree, agente trabaja desde él, commits van a la rama correcta.

**Incremento 2** (seguridad + robustez):
- Añadir T02 (preflight) + T03 (gitignore) + T05 (ensure_sparse por iteración) + T06 (recreate edge case).

**Incremento 3** (UX + push):
- Añadir T08 (RALPH_PUSH) + T09 (merge instructions al finalizar).

**Incremento 4** (limpieza + verificación):
- Añadir T10 (--clean) + T12 (E2E verification).

---

## Notes

- Todas las funciones nuevas se añaden en el bloque de funciones auxiliares (antes de `main()`), siguiendo la convención del script existente.
- El script usa `log_info`, `log_ok`, `log_warn`, `log_error` — reutilizar estas funciones existentes en todas las nuevas funciones; no usar `echo` directamente para mensajes al usuario.
- `merge_state.py` usa `os.replace` internamente → escritura atómica garantizada. El `trap EXIT` con `.ralph/state.json.tmp` es una red de seguridad adicional por robustez (FR-020), no por necesidad técnica estricta.
- La variable `CLEAN_MODE` debe inicializarse a `false` en `parse_args()` para evitar referencias a variable no definida con `set -u`.
