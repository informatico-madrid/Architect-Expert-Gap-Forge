# Implementation Plan: Fix Ingestor CLI Execution

**Branch**: `008-fix-ingestor-cli-execution` | **Date**: 2026-03-19 | **Spec**: [`specs/008-fix-ingestor-cli-execution/spec.md`](specs/008-fix-ingestor-cli-execution/spec.md)
**Input**: Feature specification from `/specs/008-fix-ingestor-cli-execution/spec.md`

## Summary

**Primary Requirement**: Habilitar `src/discovery/ingestor.py` para ejecutarse desde la **raíz del proyecto** sin PYTHONPATH, tanto en terminal manual como en CI/CD (GitHub Actions), resolviendo dos causas raíz independientes:
1. `ModuleNotFoundError` — se resuelve ejecutando con `python3 -m` desde la raíz (Python añade CWD a `sys.path[0]`)
2. `FileNotFoundError` — se resuelve convirtiendo la ruta relativa del config a absoluta dentro de `main()`

**Technical Approach**:
1. Añadir constante `PROJECT_ROOT: Path` a nivel de módulo (pura computación, sin I/O — compliant con constitución §III)
2. Dentro de `main()`, resolver ruta del config a absoluta usando `PROJECT_ROOT` si es relativa
3. Crear `src/discovery/__main__.py` con **importación relativa** `from .ingestor import main`
4. Añadir step "Verify direct CLI execution" en `.github/workflows/python-tests.yml` sin `PYTHONPATH`
5. Actualizar documentación eliminando referencias a `PYTHONPATH`

**EXCLUIDO**: `os.chdir()` a nivel de módulo — viola constitución §III (side-effect en tiempo de importación). Si fuese necesario, solo dentro de `main()`, pero la solución correcta es resolución de ruta absoluta.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic V2, PyYAML, python-dotenv, requests  
**Storage**: File system (YAML configs, Git repositories)  
**Testing**: pytest (unit tests in `tests/unit/`)  
**Target Platform**: Linux server (CI/CD environment)  
**Project Type**: CLI tool / Data pipeline utility  
**Performance Goals**: Fast execution (<1s for config loading), minimal overhead from path resolution  
**Constraints**: Must maintain backward compatibility with existing tests, no PYTHONPATH required  
**Scale/Scope**: Single module fix affecting CLI execution path, ~25 lines of code changes (ingestor.py: ~15 lines, __main__.py: ~10 lines)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate Verification

| Gate | Requirement | Status | Notes |
|------|-------------|--------|-------|
| **Header Policy** | New files must include AEGF header | ✅ PASS | `__main__.py` will include full header |
| **No Import-Time Side Effects** | Module imports must not trigger I/O | ✅ PASS | `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` es pura computación de path (no I/O). `os.chdir()` a nivel de módulo está **prohibido** y excluido del diseño. |
| **Logging** | One logger per module with lazy formatting | ✅ PASS | Existing pattern to preserve |
| **Strict Typing** | All public functions must be annotated | ✅ PASS | Existing code already typed |
| **No Silent Failures** | Parse/validation errors must raise exceptions | ✅ PASS | Existing error handling preserved |
| **Security** | No credentials in source | ✅ PASS | GITHUB_TOKEN via env var only |

**Result**: ✅ All gates pass. No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/008-fix-ingestor-cli-execution/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (technical research)
├── data-model.md        # Phase 1 output (data models)
├── quickstart.md        # Phase 1 output (usage guide)
├── tasks.md             # Phase 2 output (task breakdown)
└── spec.md              # Source specification
```

### Source Code Changes

```text
src/discovery/
├── __main__.py          # NEW: Module entry point
├── ingestor.py          # UPDATED: Add PROJECT_ROOT, path conversion
└── __pycache__/         # Compiled bytecode

configs/
└── stage_1_discovery/
    └── examples/php_hexagonal.yaml  # Existing config used for CI/CD dry-run (no changes)

tests/
└── unit/
    └── test_ingestor*.py  # Existing tests (no changes needed)
```

**Structure Decision**: Minimal changes to existing structure. Only add `__main__.py` and modify `ingestor.py`. No new directories required.

## Implementation Phases

### Phase 0: Research & Clarification ✅ COMPLETE

**Objective**: Resolver incógnitas técnicas y validar el approach.

**Tasks**:
1. **Verificar cálculo de PROJECT_ROOT** — Confirmar que `Path(__file__).resolve().parent.parent.parent` resuelve a la raíz del repo desde `src/discovery/ingestor.py` ✅ (3 niveles: `discovery` → `src` → raíz)
2. **Confirmar comportamiento de `python3 -m`** — Cuando se ejecuta `python3 -m src.discovery.ingestor` desde la raíz del proyecto, Python añade CWD a `sys.path[0]`, lo que hace `src` importable. Verificado contra docs Python 3.12.
3. **Identificar todas las rutas relativas** — `grep -n 'open(args.config' src/discovery/ingestor.py` → línea 560: única ruta relativa a resolver.
4. **Verificar tests existentes** — 21 tests no dependen de CWD; pasan con `--import-mode=importlib`. Sigue siendo válido tras añadir `PROJECT_ROOT`.

**Decisión clave**: NO usar `os.chdir()` a nivel de módulo. Solo resolver ruta del config a absoluta dentro de `main()`.

**Success Criteria**:
- ✅ research.md creado con hallazgos
- ✅ Todas las incógnitas resueltas
- ✅ Approach validado

### Phase 1: Design & Contracts ✅ COMPLETE

**Objective**: Documentar interfaces, contracts y data model. Artefactos producidos: `research.md`, `contracts/cli-interface.md`, `data-model.md`, `quickstart.md`.

**Tasks**:
1. **Añadir constante `PROJECT_ROOT`** en `ingestor.py` a nivel de módulo (después de imports, antes de clases): `PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent`
2. **Resolver ruta del config en `main()`** — NO a nivel de módulo. Solo dentro de la función `main()`: `config_path = PROJECT_ROOT / args.config if not Path(args.config).is_absolute() else Path(args.config)`
3. **Crear `__main__.py`** con importación **relativa**: `from .ingestor import main` + guard `if __name__ == "__main__": main()`
4. **Añadir step CI/CD** en `.github/workflows/python-tests.yml`: step "Verify direct CLI execution" que ejecute `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` sin `PYTHONPATH`
5. **Actualizar quickstart.md** con comandos correctos y sin referencias a PYTHONPATH
6. **Actualizar documentación** para eliminar cualquier referencia a `PYTHONPATH`

**Data Model Changes**: Ninguno — solo cambios en path resolution y entry point.

**Interface Contracts**:
- CLI interface sin cambios (mismos args, mismo comportamiento)
- Nueva interfaz de módulo habilitada: `python3 -m src.discovery.ingestor`
- Workflow CI actualizado: nuevo step de verificación CLI sin PYTHONPATH

### Phase 2: Implementation & Testing ⏳ PENDING

**Objective**: Implementar cambios en código y CI/CD, y verificar todos los criterios de aceptación.

**Tasks**:
1. **T01 — Añadir `PROJECT_ROOT` a `ingestor.py`**: Constante a nivel de módulo usando `Path(__file__).resolve().parent.parent.parent`. Sin `os.chdir()`.
2. **T02 — Resolver ruta config en `main()`**: Convertir `args.config` a absoluta usando `PROJECT_ROOT` si es relativa, antes de `open()`.
3. **T03 — Crear `src/discovery/__main__.py`**: Con header AEGF, importación relativa `from .ingestor import main`, guard `if __name__ == "__main__": main()`.
4. **T04 — Actualizar `.github/workflows/python-tests.yml`**: Añadir step "Verify direct CLI execution" después del step de tests existente. Sin `PYTHONPATH`. Usar `--dry-run` y `configs/stage_1_discovery/examples/php_hexagonal.yaml`.
5. **T05 — Actualizar documentación**: Eliminar referencias a `PYTHONPATH` en README/quickstart. Documentar `python3 -m src.discovery.ingestor`.

**Acceptance Criteria**:
- ✅ AC-1: `unset PYTHONPATH && python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` → exit code 0
- ✅ AC-2: `unset PYTHONPATH && pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v` → 21 passed
- ✅ AC-3: Step CI/CD presente en `python-tests.yml` sin `PYTHONPATH`
- ✅ AC-4: GitHub Actions badge verde en Python 3.12 y 3.13
- ✅ AC-5: `grep -n "^os.chdir" src/discovery/ingestor.py` → sin resultados a nivel de módulo
- ✅ AC-6: `grep "from .ingestor import main" src/discovery/__main__.py` → match

## Verification Strategy

### Verification Manual (terminal local)
```bash
cd /mnt/bunker_data/ai/data_factory
source .venv/bin/activate

# Verificación AC-1: CLI directo sin PYTHONPATH
unset PYTHONPATH
python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml
echo "AC-1 exit code: $?"   # debe ser 0

# Verificación AC-2: Tests existentes sin PYTHONPATH
unset PYTHONPATH
pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v
echo "AC-2 exit code: $?"   # debe ser 0, 21 passed

# Verificación AC-5: Sin os.chdir a nivel de módulo
grep -n "^os.chdir" src/discovery/ingestor.py && echo "FALLO" || echo "AC-5 OK"

# Verificación AC-6: __main__.py con importación relativa
grep "from .ingestor import main" src/discovery/__main__.py && echo "AC-6 OK" || echo "FALLO"
```

### Verification CI/CD (GitHub Actions)
```bash
# Verificación AC-3: step presente en workflow
grep -A10 "Verify direct CLI" .github/workflows/python-tests.yml
# Debe mostrar el comando con --dry-run y sin PYTHONPATH

# Verificación AC-4: revisar badge o logs de GitHub Actions
# Ambas matrix entries (3.12, 3.13) deben mostrar  ✅ "Verify direct CLI execution"
```

### Checklist de verificación pre-merge
- [ ] AC-1: CLI sin PYTHONPATH → exit code 0
- [ ] AC-2: 21 tests pasan sin PYTHONPATH
- [ ] AC-3: `python-tests.yml` tiene step sin PYTHONPATH
- [ ] AC-4: GitHub Actions verde en 3.12 y 3.13
- [ ] AC-5: Sin `os.chdir` a nivel de módulo
- [ ] AC-6: `__main__.py` usa importación relativa

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Romper tests existentes | Baja | Alta | No modificar lógica de tests; solo añadir `PROJECT_ROOT` constante y resolver path en `main()` |
| `python -m` sin funcionar en CI | Baja | Alta | Verificar localmente con `unset PYTHONPATH` antes del PR; el step CI usa `--dry-run` |
| `php_hexagonal.yaml` falta en CI | Baja | Media | El archivo está en `configs/stage_1_discovery/examples/` y es parte del repo; disponible en el `checkout` de GA |
| `os.chdir()` introducido accidentalmente | Media | Alta | AC-5 lo detecta con `grep`; revisión de PR debe rechazar cualquier `os.chdir` a nivel de módulo |

## Rollback Plan

If issues arise:
1. Revert `ingestor.py` to previous commit
2. Remove `__main__.py`
3. Restore PYTHONPATH documentation
4. Create new spec for alternative approach

## Dependencies

- **External**: None (pure Python stdlib + existing deps)
- **Internal**: `src/discovery/ingestor.py`, `tests/unit/test_ingestor*.py`
- **Configuration**: `configs/stage_1_discovery/*.yaml`

## Notes

- **Backward Compatibility**: Existing pytest tests continue to work without changes
- **Developer Experience**: Removes setup friction (no PYTHONPATH needed)
- **Production Ready**: Works in CI/CD, local dev, and any environment
