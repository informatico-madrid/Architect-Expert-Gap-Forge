# Quickstart: Git Worktree Integration

**Feature**: 002-ralph-worktree | **Branch**: `002-ralph-worktree`

---

## Uso básico (modo worktree — nuevo comportamiento por defecto)

```bash
# Lanzar ralph-loop con worktree aislado (nuevo default)
.ralph/ralph-loop.sh specs/001-stage1-discovery

# Al terminar, el script imprime:
#   Worktree: .worktrees/001-stage1-discovery-20260311_120000/
#   Branch:   ralph/001-stage1-discovery-20260311_120000
#
#   To merge:
#     git merge --squash ralph/001-stage1-discovery-20260311_120000 && git commit -m "feat(001-stage1-discovery): <descripción>"
#   Or (preserve full history):
#     git merge ralph/001-stage1-discovery-20260311_120000
```

---

## Modo legacy (sin worktree)

```bash
# Comportamiento original — sin aislamiento de rama
.ralph/ralph-loop.sh specs/001-stage1-discovery --no-worktree
```

---

## Reanudar una ejecución interrumpida

```bash
# Reutiliza el worktree y rama registrados en .ralph/state.json
.ralph/ralph-loop.sh --resume
```

---

## Limpiar worktrees tras merge

```bash
# Limpiar worktrees de un slug específico (detecta los ya mergeados automáticamente)
.ralph/ralph-loop.sh --clean 001-stage1-discovery

# Limpiar el slug activo en state.json
.ralph/ralph-loop.sh --clean
```

---

## Omitir preflight checks (escape hatch para CI)

```bash
.ralph/ralph-loop.sh specs/001-stage1-discovery --skip-preflight
# [WARN] Preflight checks omitidos
```

---

## Push automático a origin (opt-in)

```bash
RALPH_PUSH=true .ralph/ralph-loop.sh specs/001-stage1-discovery
# Hace git push -u origin <branch> en la primera iteración,
# luego git push en las siguientes.
# Sin efecto si no hay remote origin configurado.
```

---

## Variables de entorno (nuevas)

| Variable | Default | Descripción |
|---|---|---|
| `RALPH_PUSH` | `false` | `true` para activar push automático al worktree branch |

---

## Flags nuevos

| Flag | Descripción |
|---|---|
| `--no-worktree` | Desactiva worktree; comportamiento legacy idéntico al original |
| `--skip-preflight` | Omite todos los preflight checks (con `[WARN]` visible) |
| `--clean [slug]` | Limpia worktrees mergeados del slug dado (o el activo en state.json) |

---

## Flujo completo típico

```bash
# 1. Desde rama main, lanzar el loop
git checkout main
.ralph/ralph-loop.sh specs/002-ralph-worktree

# El script automáticamente:
#   - Verifica repo limpio (preflight)
#   - Añade .worktrees/ a .gitignore si falta
#   - Crea .worktrees/002-ralph-worktree-20260311_120000/
#   - Crea rama ralph/002-ralph-worktree-20260311_120000
#   - Configura sparse-checkout (excluye specs/)
#   - Por cada iteración: cd al worktree, agente trabaja, cd de vuelta

# 2. Tras terminar, el operador mergea:
git merge --squash ralph/002-ralph-worktree-20260311_120000
git commit -m "feat(002-ralph-worktree): git worktree integration"

# 3. Limpiar worktrees residuales:
.ralph/ralph-loop.sh --clean 002-ralph-worktree
```

---

## Preflight checks — errores comunes

| Error | Causa | Remediación |
|---|---|---|
| `Hay archivos sin commit` | `git status --porcelain` devuelve líneas | `git add -A && git commit -m "wip"` |
| `Merge/rebase en curso` | `.git/MERGE_HEAD` o `REBASE_HEAD` existe | `git merge --abort` o `git rebase --abort` |
| `safe.directory error` | Propiedad del repo es de otro usuario (Docker) | `git config --global --add safe.directory <path>` |
