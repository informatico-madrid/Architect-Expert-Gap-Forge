# Feature Specification: Git Worktree Integration para ralph-loop

**Feature Branch**: `002-ralph-worktree`  
**Created**: 2026-03-11  
**Status**: Draft  
**Input**: Añadir soporte git worktree al ralph-loop: worktree aislado por ejecución, symlink de memory, sparse-checkout para excluir specs/, y preflight checks de rama limpia

## Resumen ejecutivo

El bucle de automatización `ralph-loop.sh` ejecuta actualmente todas las tareas en la rama activa del repositorio principal, sin aislamiento de rama. Esto genera ruido en el historial de git, riesgo de conflictos entre ejecuciones paralelas, y ausencia de red de seguridad ante cambios que rompen el proyecto. Esta feature añade tres mejoras al script `.ralph/ralph-loop.sh` inspiradas en el patrón de worktrees de spec-kitty, sin tocar el resto del proyecto y manteniendo compatibilidad total con el flujo actual.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Worktree aislado por ejecución de ralph-loop (Priority: P1)

El operador lanza `ralph-loop.sh specs/001-stage1-discovery` desde la rama `main`. El script detecta que no existe todavía un worktree para esta ejecución, crea automáticamente un git worktree en `.worktrees/001-stage1-discovery/` con una rama dedicada `ralph/001-stage1-discovery-<timestamp>`, y el agente IA realiza todos sus commits ahí. Al finalizar (o si se interrumpe), el operador puede fusionar o revisar esa rama sin que `main` esté contaminada.

**Why this priority**: Es el cambio de mayor impacto y es la base sobre la que se construyen P2 y P3. Sin aislamiento de rama, todo el historial de git del proyecto queda mezclado con los commits del agente, dificultando revisiones y rollbacks.

**Independent Test**: Ejecutar `ralph-loop.sh` sobre una spec de prueba mínima de 2 tareas y verificar que al terminar: (1) la rama `main` no tiene commits nuevos del agente, (2) existe `.worktrees/001-stage1-discovery/` con una rama propia llena de commits, (3) el agente completó las tareas correctamente desde ese contexto.

**Acceptance Scenarios**:

1. **Given** que `main` está limpia y no existe `.worktrees/001-stage1-discovery/`, **When** se ejecuta `ralph-loop.sh specs/001-stage1-discovery`, **Then** el script crea el worktree, el agente trabaja en él y la rama `main` no recibe ningún commit directo del agente.
2. **Given** que ya existe un worktree de una ejecución anterior incompleta, **When** se lanza el loop con `--resume`, **Then** el script reutiliza el worktree existente en lugar de crear uno nuevo.
3. **Given** que el loop completa todas las tareas, **When** el script termina, **Then** imprime la ruta exacta del worktree y el nombre de la rama para que el operador pueda hacer el merge manualmente.
4. **Given** que el loop necesita ser abortado (Ctrl+C), **When** el operador interrumpe, **Then** el worktree persiste para inspección y no se realiza ningún merge automático no solicitado.

---

### User Story 2 - Sparse-checkout excluye specs/ del worktree (Priority: P2)

El agente IA que corre dentro del worktree no puede accidentalmente modificar los archivos de especificación en `specs/`. El script configura sparse-checkout en el worktree para que la carpeta `specs/` exista como referencia de lectura pero los cambios allí hechos por el agente no se incluyan en los commits del worktree.

**Why this priority**: Sin esta protección, el agente podría modificar el `tasks.md` o el `spec.md` de la feature que está implementando y corromper el estado de planificación. Los archivos de spec son de sólo lectura para el agente.

**Independent Test**: Lanzar una ejecución de ralph-loop y verificar que: (1) el agente puede leer `specs/001-stage1-discovery/tasks.md` desde el worktree, (2) si el agente escribe en `specs/` dentro del worktree, ese cambio no aparece en `git status` de la rama del worktree.

**Acceptance Scenarios**:

1. **Given** un worktree recién creado, **When** el agente crea o modifica cualquier archivo bajo `specs/` dentro del worktree, **Then** ese cambio no queda rastreado por git en esa rama (aparecerá como no-rastreado o excluido).
2. **Given** el worktree configurado, **When** el agente ejecuta cualquier lectura de archivos bajo `specs/`, **Then** puede leerlos (el contenido está disponible), no hay error de archivo no encontrado.
3. **Given** que el operador hace `git status` dentro del worktree, **When** el agente ha modificado archivos de `specs/`, **Then** esos archivos no aparecen ni en staged ni en unstaged (están excluidos por `.git/info/exclude`).

---

### User Story 3 - Preflight checks: rama limpia antes de arrancar (Priority: P3)

Antes de crear el worktree o ejecutar el primer ciclo, el script verifica el estado del repositorio principal: no hay cambios sin commit, no hay un rebase/merge en curso, y se tiene la rama `main` actualizada. Si algo falla, el script informa el problema concreto con el comando para resolverlo y no arranca.

**Why this priority**: Crear un worktree desde un repo principal con cambios sin commit o en mitad de un rebase produce estados inconsistentes difíciles de depurar. Esta guardia es de bajo coste y evita la mayoría de errores de configuración.

**Independent Test**: Introducir un archivo sin commit en el repo principal y ejecutar `ralph-loop.sh`. El script debe negarse a arrancar con un mensaje claro listando los archivos pendientes y el comando `git add && git commit` sugerido.

**Acceptance Scenarios**:

1. **Given** que hay archivos modificados sin stagear en el repo principal, **When** se lanza `ralph-loop.sh`, **Then** el script imprime la lista de archivos pendientes y termina con código de error, sin crear el worktree.
2. **Given** que hay un rebase o merge en curso en el repo principal, **When** se lanza `ralph-loop.sh`, **Then** el script detecta el estado `MERGE_HEAD` o `REBASE_HEAD` y termina con un mensaje específico sobre cómo resolverlo.
3. **Given** que el repo está limpio (sin cambios pendientes, sin rebase en curso), **When** se lanza `ralph-loop.sh`, **Then** los preflight checks pasan en silencio y el loop arranca normalmente.
4. **Given** que se usa el flag `--skip-preflight`, **When** se lanza el loop, **Then** los preflight checks se omiten (escape hatch para CI o casos excepcionales), con un aviso visible en el log.

---

### Edge Cases

- ¿Qué ocurre si `.worktrees/` no existe cuando el script intenta crear el worktree? El script debe crear el directorio automáticamente.
- ¿Qué ocurre si la rama `ralph/<slug>-<timestamp>` ya existe por colisión de timestamp (mismo segundo)? El script debe añadir un sufijo de 4 dígitos aleatorios (`-XXXX`) para garantizar unicidad en esa situación excepcional.
- ¿Qué ocurre si `git worktree add` falla por falta de permisos o disco lleno? El script debe capturar el error, mostrarlo y abortar limpiamente sin dejar estado inconsistente.
- ¿Qué ocurre si el agente borra accidentalmente el directorio del worktree durante su ejecución? El script debe detectar la ausencia del worktree en la siguiente iteración y recrearlo con `git worktree add <mismo-path> <misma-rama-ralph/...>` — la rama con los commits del agente sigue existiendo; solo se recrea el directorio físico. Los commits previos se conservan intactos.
- ¿Qué ocurre con el flag `--resume` cuando el worktree fue borrado manualmente? El script debe detectarlo, avisar, y ofrecer recrearlo antes de continuar.
- ¿Qué ocurre si se lanza el loop desde dentro del propio worktree (no desde el repo principal)? Los preflight checks deben detectar el contexto y operar sobre el repo principal raíz.
- ¿Qué ocurre si el agente modifica `ralph-loop.sh` en disco mientras el proceso está en ejecución (el caso normal de bootstrap: implementarse a sí mismo)? Sin protección, bash puede leer partes del script modificadas en iteraciones posteriores. El self-snapshot (FR-022) elimina este riesgo haciendo `exec` desde una copia congelada en tmpdir antes de iniciar el loop.
- ¿Qué ocurre si el agente modifica `recipes/ralph-work.yaml` o `ralph-review.yaml` durante su ejecución? Goose lanza un subprocess nuevo en cada iteración y lee el recipe del disco en ese momento — vería la versión parcialmente implementada. El self-snapshot de FR-022 cubre también estos archivos: `RALPH_DIR` apunta al tmpdir, por lo que goose lee la copia congelada del recipe durante todo el run.

## Requirements *(mandatory)*

### Functional Requirements

#### Parte 1: Worktree aislado por ejecución

- **FR-001**: El script DEBE crear un git worktree en `.worktrees/{feature-slug}-{YYYYMMDD_HHMMSS}/` al inicio de cada ejecución nueva (no-resume). La ruta incluye timestamp para garantizar unicidad y permitir múltiples ejecuciones consecutivas sin limpieza manual previa.
- **FR-002**: La rama del worktree DEBE seguir el mismo patrón que el directorio: `ralph/{feature-slug}-{YYYYMMDD_HHMMSS}`, garantizando que ruta de worktree y nombre de rama son siempre consistentes entre sí.
- **FR-003**: El script DEBE hacer `cd "$WORKTREE_PATH"` inmediatamente antes de invocar al agente, de modo que el proceso del agente (claude/goose/custom) hereda CWD=worktree. Tras la invocación, el script vuelve a `$PROJECT_DIR`. Esto garantiza que todas las operaciones git del agente sin directorio explícito (git status, git add, git commit) operan sobre la rama del worktree, no sobre main.
- **FR-004**: Al finalizar el loop (por éxito, error, o cap de iteraciones), el script DEBE imprimir la ruta del worktree, la rama creada, y el comando de merge sugerido listo para copiar-pegar:
  ```
  git merge --squash ralph/<slug>-<ts> && git commit -m "feat(<slug>): <descripción>"
  ```
  Con nota de que `git merge ralph/<slug>-<ts>` también funciona si se quiere preservar el historial completo de commits del agente. El squash es el camino sugerido para mantener `main` limpio.
- **FR-005**: El worktree DEBE persistir tras la finalización del loop; el script no realiza merge ni borrado automático a menos que el operador pase un flag explícito `--auto-merge`.
- **FR-006**: El flag `--resume` DEBE reutilizar el worktree existente registrado en `.ralph/state.json`, sin crear uno nuevo. La rama del worktree es la fuente de verdad: el script retoma desde el estado guardado en `state.json` sin modificar ni reescribir los commits ya existentes en la rama. Si el worktree tiene commits más recientes que el último estado registrado (crash entre commit y actualización de state), el agente continúa sobre esos commits tal como están.
- **FR-007**: El script DEBE persistir la ruta y nombre de la rama del worktree en `.ralph/state.json` para soporte de `--resume`.

#### Parte 2: Mecanismo de protección de specs/ en el worktree

- **FR-008**: Tras crear el worktree, el script DEBE configurar sparse-checkout replicando exactamente el patrón de spec-kitty (immune a cambios de cone-mode por versión de git): (1) `git config core.sparseCheckout true`, (2) `git config core.sparseCheckoutCone false` (desactiva el cone mode que ignora negaciones en git ≥ 2.37), (3) escribir el archivo `.git/info/sparse-checkout` directamente con contenido `/*\n!/specs/\n!/specs/**\n`, (4) `git read-tree -mu HEAD` para aplicar el filtro. **No usar** el CLI de alto nivel `git sparse-checkout init/set`, que puede activar cone mode por defecto y anular silenciosamente las negaciones.
- **FR-008b**: Al inicio de **cada iteración del loop**, el script DEBE re-validar y re-aplicar la configuración de sparse-checkout **desde `$PROJECT_DIR`** (antes del `cd "$WORKTREE_PATH"`), ejecutando los pasos de FR-008 sobre el worktree si detecta que la configuración falta o es incorrecta. Esto garantiza que cuando el agente arranca, su CWD ya es el worktree correctamente configurado. Patrón tomado de `_ensure_sparse_checkout()` de spec-kitty.
- **FR-009**: El script DEBE añadir `specs/` al archivo `.git/info/exclude` del worktree como segunda capa de protección, impidiendo que cualquier archivo bajo `specs/` aparezca en `git status` aunque sobreviva en disco.
- **FR-010**: Si tras la configuración de sparse-checkout la carpeta `specs/` persiste en el worktree (worktree huérfano o fallo de sparse), el script DEBE eliminarla físicamente (`rm -rf`).
- **FR-010b**: El agente DEBE acceder a los archivos de specs exclusivamente mediante rutas absolutas al repo principal (acordado en FR-017 / Q2). No se crean symlinks hacia `specs/` en el worktree.

#### Parte 3: Preflight checks

- **FR-011**: Antes de crear el worktree, el script DEBE verificar que no existen archivos modificados sin commit en el repo principal (`git status --porcelain`).
- **FR-011b**: El preflight DEBE ejecutar `git worktree list --porcelain` para detectar errores de trust/ownership del repositorio (`safe.directory`, frecuente en Docker o cuando el repo es propiedad de otro usuario). Si falla, mostrar el comando `git config --global --add safe.directory <path>` como remediación.
- **FR-012**: El script DEBE verificar que no hay un rebase, merge, o cherry-pick en curso (ausencia de `.git/MERGE_HEAD`, `.git/REBASE_HEAD`, `.git/CHERRY_PICK_HEAD`).
- **FR-013**: Si algún preflight check falla, el script DEBE imprimir el problema específico y el comando sugerido para resolverlo, y terminar con código de salida no-cero sin haber creado el worktree.
- **FR-014**: El flag `--skip-preflight` DEBE omitir todos los preflight checks, imprimiendo un aviso visible `[WARN] Preflight checks omitidos`.

#### Parte 4: Bootstrap safety — protección contra auto-modificación

- **FR-022**: Al iniciarse, el script DEBE detectar si ya está corriendo desde un snapshot temporal (variable de entorno `RALPH_SNAPSHOT=1`). Si NO está en modo snapshot, DEBE:
  1. Copiar `ralph-loop.sh` + `recipes/ralph-work.yaml` + `recipes/ralph-review.yaml` + `scripts/merge_state.py` + `scripts/count_tasks.py` a un directorio temporal (`mktemp -d`).
  2. Re-exportar `RALPH_DIR` apuntando al tmpdir.
  3. Hacer `exec env RALPH_SNAPSHOT=1 bash "$tmpdir/ralph-loop.sh" "$@"` para substituir el proceso actual por la copia congelada.
  
  Esto garantiza que aunque el agente modifique cualquiera de esos archivos durante las iteraciones (especialmente `ralph-loop.sh` cuando se implementa a sí mismo), el proceso en ejecución permanece completamente inmune: opera desde los bits del snapshot, no desde los archivos modificados en disco. El `exec` elimina el proceso shell intermedio — solo existe el proceso del snapshot.

  Si `RALPH_SNAPSHOT=1` ya está definido, el script omite el paso de snapshot (evita re-exec recursivo) y continúa normalmente.

  El tmpdir del snapshot se elimina en el `trap EXIT` junto con `.ralph/state.json.tmp`.

#### Compatibilidad y no-regresión

- **FR-015**: Toda la funcionalidad existente del ralph-loop (state machine JSON, tres capas de verificación, recovery mode, retry limits, soporte para claude/goose/custom) DEBE seguir funcionando exactamente igual que antes.
- **FR-016**: El flag `--no-worktree` DEBE permitir ejecutar el loop en modo legacy (sin worktree, comportamiento original), para casos donde el repo no tiene soporte git completo o en entornos CI simplificados.
- **FR-017**: El prompt enviado al agente DEBE incluir una línea informativa `Working directory: <ruta absoluta del worktree>` al inicio de la sección de contexto. Todas las referencias a archivos en el prompt (specs, tests, src) DEBEN seguir usando rutas absolutas, idénticas a las actuales — funcionan sin cambios porque el worktree comparte el mismo filesystem. El `cd` real del proceso es el mecanismo de aislamiento (FR-003); la línea en el prompt es solo informativa.
- **FR-018**: El script DEBE verificar que `.worktrees/` figura en el `.gitignore` del proyecto y, si no está, añadirlo automáticamente antes de crear el primer worktree. Esto evita que `git add -A` desde el repo principal incluya accidentalmente los worktrees.
- **FR-019**: El push de la rama del worktree a origin está **desactivado por defecto**. Si la variable de entorno `RALPH_PUSH=true` está definida Y existe un remote `origin` configurado, el script DEBE hacer push al final de cada iteración con detección automática de tracking (`git push -u origin <branch>` la primera vez, `git push` las siguientes). Si no hay remote, el push se omite silenciosamente.
- **FR-020**: El script DEBE escribir `.ralph/state.json` de forma atómica: primero escribe a `.ralph/state.json.tmp` y luego ejecuta `mv .ralph/state.json.tmp .ralph/state.json`. DEBE instalar un `trap EXIT` mínimo que elimine `.ralph/state.json.tmp` si existe al salir (evita dejar un write parcial en caso de Ctrl+C o error). El worktree persiste intacto en disco para inspección; el trap no toca el worktree ni ejecuta `git worktree prune`.
- **FR-021**: El flag `--clean [<slug>]` DEBE limpiar los worktrees de una spec concluida. Comportamiento:
  1. Detecta todas las ramas `ralph/<slug>-*` bajo `.worktrees/` para el slug indicado (o el slug activo en `.ralph/state.json` si no se pasa argumento).
  2. Clasifica cada worktree en **mergeado** o **no mergeado** usando `git branch --merged <base-branch>`. La rama base se auto-detecta con `git symbolic-ref refs/remotes/origin/HEAD` (extrae el nombre, ej. `main`); fallback: probar `main`, luego `master`. Si ninguno existe, abortar con mensaje de error e instrucción de usar `--base-branch <branch>`.
  3. Elimina automáticamente los worktrees mergeados: `git worktree remove <path> --force` + `git branch -d <branch>`.
  4. Para worktrees no mergeados: lista su path y rama, pide confirmación explícita antes de borrar.
  5. Al finalizar ejecuta `git worktree prune` para limpiar referencias huérfanas.
  Este comportamiento replica el patrón de spec-kitty (`remove_worktree=True` por defecto en `merge`, `delete_branch=True` por defecto): una vez que la rama de la spec llega a main, todos los worktrees generados por esa spec son residuos y deben limpiarse.

### Key Entities

- **Worktree**: Directorio git aislado en `.worktrees/{feature-slug}/` vinculado a una rama propia. Tiene su propio índice pero comparte el objeto store con el repo principal.
- **Rama de trabajo**: Rama con patrón `ralph/{slug}-{timestamp}` donde el agente hace todos sus commits durante la ejecución del loop.
- **Workspace metadata**: Entrada en `.ralph/state.json` que registra `worktreePath`, `worktreeBranch`, `worktreeCreatedAt` para soporte de resume y trazabilidad.
- **Preflight result**: Resultado de los checks previos: lista de archivos pendientes, estado de rebase/merge, y flag de éxito/fallo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras una ejecución completa de ralph-loop con worktree activado, la rama `main` (u otra base) no contiene ningún commit nuevo del agente — todos los commits están en la rama `ralph/...`.
- **SC-002**: El historial de git del worktree es lineal y trazable: cada tarea completada genera al menos un commit con mensaje descriptivo en la rama de trabajo.
- **SC-003**: Los archivos bajo `specs/` del worktree no aparecen en `git status` dentro del worktree, incluso si el agente los modificó, garantizando que los cambios de spec no contaminan la rama de trabajo.
- **SC-004**: Cuando el repo principal tiene cambios sin commit, el 100% de los intentos de lanzar ralph-loop son bloqueados por los preflight checks con un mensaje accionable.
- **SC-005**: El tiempo de inicio del loop (desde invocación hasta primera tarea) no aumenta más de 5 segundos respecto al modo legacy (el overhead de crear el worktree es imperceptible para el usuario).
- **SC-006**: Todos los tests existentes del proyecto (`pytest tests/`) siguen pasando después de la implementación (no-regresión total).
- **SC-007**: Al ejecutar con `--no-worktree`, el comportamiento es idéntico al loop original, sin diferencias observables.

## Assumptions

- El repo del proyecto tiene git >= 2.5 (soporte básico de `git worktree`) disponible en el PATH.
- El operador es responsable del merge final de la rama de trabajo a `main` o la rama base — el loop no hace merge automático por defecto.
- La carpeta `.worktrees/` es añadida al `.gitignore` del proyecto por el script (FR-018); si ya figura, el script lo detecta y no duplica la entrada.
- El agente (claude/goose) puede operar correctamente con un CWD diferente al raíz del proyecto; el contexto correcto se provee mediante el prompt actualizado.
- Los symlinks de `.specify/memory/` al worktree (patrón de spec-kitty) quedan fuera del scope de esta feature para mantener el alcance mínimo; podrán añadirse como mejora posterior. El agente lee la constitution vía ruta absoluta al repo principal.

## Clarifications

### Session 2026-03-11

- Q: Colisión de worktree — ¿ruta fija o con timestamp cuando ya existe un worktree anterior sin `--resume`? → A: Ruta con timestamp `.worktrees/{slug}-{YYYYMMDD_HHMMSS}/`; cada ejecución nueva crea su propio directorio único (Opción B)
- Q: ¿Rutas en el prompt del agente cuando opera desde el worktree — absolutas o relativas al worktree? → A: Rutas absolutas para todo; solo se añade una línea informativa de CWD al prompt; no se reescriben referencias existentes (Opción A)
- Q: ¿Mecanismo para proteger `specs/` — solo `.git/info/exclude` o mecanismo completo de spec-kitty (sparse-checkout + exclude + borrado físico)? → A: Mecanismo completo de spec-kitty: sparse-checkout elimina `specs/` del worktree físicamente, `.git/info/exclude` como capa adicional, borrado físico si persiste como huérfano; agente lee specs vía rutas absolutas al repo principal (Opción A)
- Q: ¿Push del worktree branch a origin — activo por defecto, opt-in o eliminado? → A: Opt-in vía `RALPH_PUSH=true`; desactivado por defecto; push solo si hay remote `origin` configurado; omisión silenciosa si no hay remote (Opción B)
- Q: ¿CWD del proceso agente — `cd` real al worktree o solo informar en el prompt? → A: `cd` real antes de invocar al agente y `cd` de vuelta al terminar; el proceso del agente hereda CWD=worktree garantizando que git commit aterriza en la rama correcta (Opción A)
- Q: ¿Método de implementación de sparse-checkout — CLI de alto nivel o config directo como spec-kitty? → A: Replicar exactamente spec-kitty: `git config core.sparseCheckoutCone false` + escribir `.git/info/sparse-checkout` directamente + `git read-tree -mu HEAD`; no usar `git sparse-checkout init/set` (cone mode rompe negaciones en git ≥ 2.37) (Opción A)
- Q: ¿Trap EXIT/SIGINT para integridad de state.json al interrumpir? → A: Trap mínimo solo para atomicidad: escribir siempre a `.ralph/state.json.tmp` y mover atómicamente con `mv`; trap EXIT elimina el .tmp si existe; el worktree persiste intacto, sin `git worktree prune` automático (Opción B)
- Q: ¿Flag `--clean` para limpiar worktrees tras merge? → A: Opción B con detección inteligente de ramas mergeadas: `--clean [slug]` detecta ramas `ralph/<slug>-*` mergeadas en la rama base (`git branch --merged`) y las elimina automáticamente (worktree + branch); pide confirmación para no mergeadas; finaliza con `git worktree prune`. Replica el patrón de spec-kitty `merge --remove-worktree --delete-branch` (ambos `True` por defecto).
- Q: ¿Cómo determina `--clean` la rama base para clasificar worktrees como mergeados? → A: Auto-detección vía `git symbolic-ref refs/remotes/origin/HEAD`; fallback a `main` luego `master`; si ninguno existe, abortar con hint de `--base-branch <branch>` (Opción A)
- Q: ¿Qué hace `--resume` si el worktree tiene commits más recientes que el state.json (crash entre commit y write)? → A: La rama del worktree es fuente de verdad; `--resume` retoma desde `state.json` sin tocar commits existentes en la rama; el agente continúa sobre lo ya hecho sin resetear ni advertir (Opción A)
- Q: ¿Cómo se recrea el worktree si el agente lo borra durante la ejecución? → A: Recrear desde la rama existente `ralph/slug-ts` con `git worktree add <mismo-path> <misma-rama>`; los commits del agente se conservan; solo se restaura el directorio físico (Opción A)
- Q: ¿Cuándo exactamente se ejecuta la re-validación de sparse-checkout (FR-008b) en cada iteración? → A: Desde `$PROJECT_DIR` antes del `cd "$WORKTREE_PATH"`, al inicio de cada iteración; cuando el agente arranca su CWD ya es el worktree correctamente configurado (Opción A)
- Q: ¿Qué imprime el script al finalizar para guiar al operador en el merge? → A: Comando squash-merge listo para copiar-pegar (`git merge --squash ralph/... && git commit`) con nota de que merge regular también funciona; squash es el sugerido para mantener `main` limpio (Opción B)
- Q: ¿Puede ralph-loop.sh implementarse a sí mismo de forma segura si el agente modifica el script o los recipes durante las iteraciones bootstrap? → A: No sin protección; bash puede leer partes del archivo modificadas y los subprocesos de goose ven la versión parcialmente implementada de los yaml. Solución: self-snapshot completo al inicio — copiar ralph-loop.sh + recipes/*.yaml + scripts/*.py a un tmpdir, redefinir RALPH_DIR al tmpdir, y hacer exec desde la copia congelada (FR-022). Solo un exec; variable RALPH_SNAPSHOT=1 previene re-exec recursivo. tmpdir eliminado en trap EXIT (Opción A)
- Q: ¿El self-snapshot debe cubrir solo ralph-loop.sh o también los archivos de recipes y scripts? → A: Snapshot completo de todos los archivos runtime de .ralph/: ralph-loop.sh + recipes/ralph-work.yaml + recipes/ralph-review.yaml + scripts/merge_state.py + scripts/count_tasks.py. Los subprocesos de goose/python lanzan binary nuevo y leen del disco cada vez — si el agente modifica un recipe a mitad de iteración, la siguiente invocación de goose ve la versión parcial. Con RALPH_DIR apuntando al tmpdir, todos los subprocesos leen la versión congelada durante todo el run (Opción A completo)

## Out of Scope

- Ejecución paralela de múltiples worktrees (un worktree por WP al estilo spec-kitty): queda para una feature posterior.
- Merge automático al finalizar: queda como flag `--auto-merge` opcional, pero no es el comportamiento por defecto.
- Soporte para Jujutsu (jj) como VCS alternativo.
- Rotación automática de worktrees sin intervención del operador (la limpieza manual explícita con `--clean` sí está en scope — FR-021).
