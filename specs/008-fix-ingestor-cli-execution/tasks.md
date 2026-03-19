---
description: "Task list for 008-fix-ingestor-cli-execution"
---

# Tasks: Fix Ingestor CLI Execution

**Input**: Design documents from `/specs/008-fix-ingestor-cli-execution/`
**Spec**: [`spec.md`](spec.md) | **Plan**: [`plan.md`](plan.md)
**Generated**: 2026-03-19

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no incomplete task dependencies)
- **[US1/US2/US3]**: User story this task belongs to
- No test tasks — tests are verification checkpoints; the 21 existing tests must pass, no new test code needed.

---

## Phase 1: Foundational (Blocking Prerequisite)

**Purpose**: Añadir la constante `PROJECT_ROOT` a `ingestor.py`. Este cambio es el prerequisito común para US1 (CLI funciona) y US2 (tests siguen pasando), ya que habilita la resolución de rutas sin `os.chdir()` a nivel de módulo.

**⚠️ CRÍTICO**: US1 y US2 no pueden implementarse hasta que este cambio esté completo.

- [ ] T001 Añadir constante `PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent` en `src/discovery/ingestor.py` a nivel de módulo, después de los imports, antes de las clases — sin añadir `os.chdir()` ni ningún efecto lateral de I/O

**Checkpoint**: `python3 -c "from pathlib import Path; p=Path('src/discovery/ingestor.py'); print(p.resolve().parent.parent.parent)"` debe devolver la raíz del repo.

---

## Phase 2: User Story 1 — Ejecución Manual desde Terminal (P0)

**Goal**: `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` funciona desde la raíz del proyecto sin `PYTHONPATH`.

**Independent Test**:
```bash
unset PYTHONPATH && python3 -m src.discovery.ingestor \
  --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml
echo $?   # debe ser 0
```

- [ ] T002 [P] [US1] Resolver ruta del config a absoluta dentro de `main()` en `src/discovery/ingestor.py`: antes de `open(args.config)`, añadir `config_path = PROJECT_ROOT / args.config if not Path(args.config).is_absolute() else Path(args.config)` y usar `config_path` en `open()`
- [ ] T003 [P] [US1] Crear `src/discovery/__main__.py` con header AEGF completo, importación relativa `from .ingestor import main` y guard `if __name__ == "__main__": main()`

> **T002 y T003 son paralelos** — afectan archivos diferentes (`ingestor.py` línea 560 vs nuevo `__main__.py`).

---

## Phase 3: User Story 2 — Tests Unitarios sin PYTHONPATH (P0)

**Goal**: Los 21 tests existentes siguen pasando tras los cambios de Phase 1 y 2, sin ningún efecto lateral de importación.

**Independent Test**:
```bash
unset PYTHONPATH && pytest \
  tests/unit/test_ingestor_profile_filter.py \
  tests/integration/test_ingestor_git_recovery.py -v
# Resultado esperado: 21 passed, 0 failed
```

- [ ] T004 [US2] [VERIFY] Ejecutar `unset PYTHONPATH && pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v` y confirmar 21 passed; si algún test falla, corregir el cambio en `ingestor.py` (T001/T002) sin revertir la solución
- [ ] T005 [US2] [VERIFY] Confirmar que no hay `os.chdir` en scope de módulo: `grep -n "^os\.chdir\|^    os\.chdir" src/discovery/ingestor.py` → sin resultados fuera de funciones

> **T004 y T005 son paralelos** entre sí, pero deben ir después de completar T001–T003.

---

## Phase 4: User Story 3 — CI/CD GitHub Actions Certifica Ejecución Directa (P0)

**Goal**: `.github/workflows/python-tests.yml` incluye un step que ejecuta el CLI directamente sin `PYTHONPATH`, cubriendo Python 3.12 y 3.13.

**Independent Test**:
```bash
# Verificar que el step está presente y no tiene PYTHONPATH
grep -A10 "Verify direct CLI" .github/workflows/python-tests.yml
# Debe incluir: python3 -m src.discovery.ingestor --dry-run
# No debe incluir: PYTHONPATH
```

- [ ] T006 [US3] Añadir step "Verify direct CLI execution" en `.github/workflows/python-tests.yml` después del step existente de tests, sin variable de entorno `PYTHONPATH`, usando `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml`
- [ ] T007 [US3] [VERIFY] Confirmar que el workflow modificado no tiene `PYTHONPATH` en ningún step nuevo: `grep -n "PYTHONPATH" .github/workflows/python-tests.yml` → solo puede aparecer en comentarios, nunca como variable de entorno añadida por esta feature

---

## Phase 5: Polish & Documentación

**Purpose**: Eliminar referencias a `PYTHONPATH` en documentación y confirmar el comando correcto en quickstart.

- [ ] T008 Buscar y eliminar referencias a `PYTHONPATH` en `docs/ORCHESTRATION_QUICKSTART.md` y `README.md`; documentar el comando correcto `python3 -m src.discovery.ingestor`
- [ ] T009 [VERIFY] Ejecutar `grep -rn "PYTHONPATH" docs/ README.md` → sin resultados (o solo contexto histórico en comentarios)

---

## Dependency Graph

```
T001 (PROJECT_ROOT)
├── T002 [US1] (path resolution in main)   ─┐ paralelo
├── T003 [US1] (__main__.py)               ─┘
│
├──▶ T004 [US2] (VERIFY 21 tests pass)     ─┐ paralelo
│   └── T005 [US2] (VERIFY no os.chdir)   ─┘
│
└──▶ T006 [US3] (CI/CD workflow step)
     └── T007 [US3] (VERIFY no PYTHONPATH in workflow)

T008 (docs) ──▶ T009 (VERIFY docs clean)
```

US1 y US3 dependen de T001.
US2 verifica que T001 no introdujo regresiones.
US3 (T006) puede trabajarse en paralelo con US1 (T002/T003) — archivo diferente.

---

## Parallel Execution Examples

### Máximo paralelismo (después de T001):

```
Terminal 1: T002 — editar ingestor.py línea 560 (path resolution en main)
Terminal 2: T003 — crear src/discovery/__main__.py
Terminal 3: T006 — editar .github/workflows/python-tests.yml
```

### Tras completar T001–T003:
```
Terminal 1: T004 — pytest (verification)
Terminal 2: T005 — grep os.chdir (verification)
Terminal 3: T007 — grep PYTHONPATH en workflow
```

---

## Implementation Strategy

**MVP**: US1 + US2 = T001 → T002 + T003 → T004 + T005

Con solo 5 tareas (T001–T005), el CLI funciona en terminal local y los tests existentes siguen pasando. Esto valida la solución core antes de tocar CI/CD.

**Full feature**: Añadir T006 + T007 + T008 + T009 para certificar en CI/CD y limpiar docs.

---

## Acceptance Criteria (resumen)

| AC | Comando de verificación | Resultado esperado |
|----|------------------------|--------------------|
| AC-1 | `unset PYTHONPATH && python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` | exit code 0 |
| AC-2 | `unset PYTHONPATH && pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v` | 21 passed |
| AC-3 | `grep -A10 "Verify direct CLI" .github/workflows/python-tests.yml` | step presente, sin PYTHONPATH |
| AC-4 | GitHub Actions PR badge | verde en Python 3.12 y 3.13 |
| AC-5 | `grep -n "^os\.chdir" src/discovery/ingestor.py` | sin resultados a nivel de módulo |
| AC-6 | `grep "from .ingestor import main" src/discovery/__main__.py` | match |
