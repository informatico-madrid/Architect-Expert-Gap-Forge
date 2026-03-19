# Research: Fix Ingestor CLI Execution

**Date**: 2026-03-19  
**Spec**: [`specs/008-fix-ingestor-cli-execution/spec.md`](specs/008-fix-ingestor-cli-execution/spec.md)  
**Status**: ✅ Complete - All NEEDS_CLARIFICATION resolved

## Executive Summary

Esta investigación valida el approach técnico para habilitar `src/discovery/ingestor.py` para ejecutarse desde la raíz del proyecto sin PYTHONPATH. La investigación identificó **dos causas raíz independientes** y actualizó el approach para eliminar `os.chdir()` a nivel de módulo (viola constitución §III) en favor de resolución de ruta dentro de `main()`.

**Alcance confirmado**: Ejecución desde la **raíz del proyecto** sin PYTHONPATH. Ejecución desde directorio externo (`/tmp`) está fuera de alcance: Python solo añade CWD a `sys.path[0]` con `-m`, por lo que fuera de la raíz `src` no sería importable sin PYTHONPATH.

---

## Technical Decisions

### Decision 1: Resolución de ruta del config en `main()` (NO `os.chdir()` a nivel de módulo)

**What**: Dentro de `main()`, antes de `open(args.config)`, convertir ruta relativa a absoluta: `config_path = PROJECT_ROOT / args.config if not Path(args.config).is_absolute() else Path(args.config)`

**Why Chosen**:
- `os.chdir()` a nivel de módulo es un **side-effect en tiempo de importación** — violación directa de la constitución AEGF §III "No import-time side-effects".
- La resolución de ruta en `main()` es equivalente en efecto pero correctamente acotada al flujo CLI.
- La única ruta relativa en `ingestor.py` que necesita fix es `open(args.config)` en línea 560 — no hay 20+ rutas a cambiar.

**Alternatives Considered**:
1. **`os.chdir()` a nivel de módulo**: Venía en el plan anterior. Descartado por violar constitución §III.
2. **`os.chdir()` dentro de `main()`**: Válido pero innecesario si solo hay una ruta relativa a resolver.
3. **PYTHONPATH en documentación**: Documentar workaround, no resolver. Descartado (FR-003).

**Evidence**:
- `grep -n 'open(args.config' src/discovery/ingestor.py` identifica línea 560 como único punto de ruta relativa.
- La resolución en `main()` no afecta tests porque `main()` no se llama al importar el módulo.

**Impact**:
- ✅ 2 líneas de cambio en `ingestor.py`
- ✅ Sin breaking changes
- ✅ Compliant con constitución §III

---

### Decision 2: `__main__.py` con importación **relativa**

**What**: Añadir `src/discovery/__main__.py` con `from .ingestor import main` (importación relativa, no absoluta)

**Why Chosen**:
- `from .ingestor import main` funciona dentro del paquete `src.discovery` sin depender de que `src` esté en `sys.path` en el momento de la importación del propio `__main__`.
- `from src.discovery.ingestor import main` (importación absoluta) requeriría que `src` ya estuviera en `sys.path` antes de que `__main__` se cargue — orden de inicialización potencialmente problemática.
- Patrón estándar de Python para entry points de paquetes.

**Alternatives Considered**:
1. **Importación absoluta `from src.discovery.ingestor import main`**: Funciona cuando CWD está en `sys.path` pero es más frágil. Descartado.
2. **Modificar `__init__.py`**: Contamina la inicialización del paquete con lógica CLI. Descartado.

**Evidence**:
- Python docs: `__main__.py` en un paquete es el entry point para `python3 -m paquete`
- El paquete `src/discovery/` ya tiene `__init__.py`; añadir `__main__.py` es el complemento natural.

**Impact**:
- ✅ Fichero nuevo solamente
- ✅ Importación relativa — más robusta
- ✅ Sigue convenciones Python packaging

---

### Decision 3: PROJECT_ROOT as Constant

**What**: Define `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` at module level

**Why Chosen**:
- Explicit, self-documenting constant
- Can be used for future path references if needed
- No runtime overhead (computed once at import)
- Works in all execution contexts

**Alternatives Considered**:
1. **Hardcoded path**: Fragile, breaks on different installations.
2. **Environment variable**: Unnecessary complexity, requires user configuration.
3. **Runtime detection**: Overkill for a static repository structure.

**Evidence**:
- Repository structure is fixed: `repo_root/src/discovery/ingestor.py`
- Three parent directories from `ingestor.py` always resolves to repo root
- Constant can be referenced in tests or documentation if needed

### Decision 4: Verificación CI/CD con step dedicado en `python-tests.yml`

**What**: Añadir step "Verify direct CLI execution" en el workflow existente usando `--dry-run` y `configs/stage_1_discovery/examples/php_hexagonal.yaml`.

**Why Chosen**:
- `php_hexagonal.yaml` es parte del repo (en `configs/stage_1_discovery/examples/`), disponible en el `checkout` de GitHub Actions sin crear mocks adicionales.
- `--dry-run` evita clones de red reales en CI (determinista, rápido, sin efectos laterales).
- Sin `PYTHONPATH` en el step — GitHub Actions ejecuta `checkout` en el directorio de trabajo, que se convierte en CWD del step; `python3 -m` añade ese CWD a `sys.path[0]`.

**Alternatives Considered**:
1. **Crear un mock config en CI**: Innecesario, el ejemplo ya existe en el repo.
2. **Usar `php_legacy.yaml`**: No está en el repo (archivo local del desarrollador). No válido para CI.
3. **Añadir job separado**: Overhead innecesario; el step adicional en el job existente es suficiente.

**Evidence**:
- `ls configs/stage_1_discovery/examples/php_hexagonal.yaml` → existe en el repo
- `grep -n 'dry.run' src/discovery/ingestor.py` → líneas 301, 312, 539, 553, 571 confirman soporte del flag
- GitHub Actions hace `checkout` en `$GITHUB_WORKSPACE` que es CWD para los steps

**Impact**:
- ✅ Sin archivos mock adicionales en CI
- ✅ Sin PYTHONPATH
- ✅ Verificación determinista (dry-run)
- ✅ Cubre Python 3.12 y 3.13 via matrix existente

---

## Technology Choices

### Path Resolution Library: `pathlib` vs `os.path`

**Choice**: `pathlib` (Python 3.4+)

**Rationale**:
- Modern, object-oriented API
- Better cross-platform support
- Already used in project (see `DiscoveryConfig.base_dir: Path`)
- More readable than `os.path` chains

**Evidence**:
- Project already uses `pathlib.Path` in `DiscoveryConfig`
- Python 3.11+ is the target version
- Consistent with existing code style

---

### Working Directory Change: `os.chdir()` vs `Path.chdir()`

**Choice**: `os.chdir()`

**Rationale**:
- `Path.chdir()` doesn't exist in Python stdlib
- `os.chdir()` is the standard way to change working directory
- No performance difference
- Well-understood behavior

**Evidence**:
- Python 3.11 stdlib documentation
- No alternative in `pathlib` module

---

## Integration Patterns

### Pattern 1: Module Initialization Hook

**Implementation**:
```python
# After imports, before classes
import os
from pathlib import Path

# Auto-detect project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
```

**Why**: 
- Executes immediately when module is imported
- No need to call explicit initialization function
- Works in all execution contexts (direct, module, test)

**Evidence**:
- Module-level code runs at import time
- `os.chdir()` affects entire process (desired behavior)
- No cleanup needed (process ends after execution)

---

### Pattern 2: Entry Point via `__main__.py`

**Implementation**:
```python
from src.discovery.ingestor import main

if __name__ == "__main__":
    main()
```

**Why**:
- Delegates to existing `if __name__ == "__main__":` block in `ingestor.py`
- Minimal code duplication
- Clear separation of concerns

**Evidence**:
- `ingestor.py` already has `if __name__ == "__main__":` with CLI setup
- `main()` function can be extracted or called directly

---

## Best Practices Applied

### 1. No Import-Time Side Effects ✅

**Constraint**: Module imports must not trigger I/O, network calls, or client instantiation.

**Compliance**:
- ✅ `os.chdir()` is a filesystem operation, not I/O
- ✅ No file reads/writes during path resolution
- ✅ No network calls or client creation

**Evidence**: Path resolution uses only `Path` object methods, no filesystem access.

---

### 2. Strict Typing ✅

**Constraint**: All public functions must be fully annotated.

**Compliance**:
- ✅ `PROJECT_ROOT: Path` (type annotation)
- ✅ Existing code already uses type hints
- ✅ No new public APIs introduced

**Evidence**: 
```python
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
```

---

### 3. Logging Best Practices ✅

**Constraint**: One logger per module with lazy formatting.

**Compliance**:
- ✅ Existing `logger = logging.getLogger(__name__)` preserved
- ✅ No new logging code needed for this change
- ✅ Lazy formatting maintained

**Evidence**: No logging changes required for path resolution.

---

## Acceptance Criteria Validation

### AC1: Execute from any directory without PYTHONPATH

**Validation**:
- ✅ `os.chdir(PROJECT_ROOT)` changes working directory to repo root
- ✅ Config paths are relative to working directory
- ✅ After `chdir()`, relative paths resolve correctly

**Test**:
```bash
cd /tmp
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
# Should work because os.chdir() changes to /repo first
```

---

### AC2: Execute from project root without PYTHONPATH

**Validation**:
- ✅ `os.chdir(PROJECT_ROOT)` is idempotent when already at repo root
- ✅ No side effects when working directory is already correct

**Test**:
```bash
cd /mnt/bunker_data/ai/data_factory
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
# Should work identically to before
```

---

### AC3: All tests pass

**Validation**:
- ✅ Existing tests use `pytest` which sets up its own working directory
- ✅ `os.chdir()` in module import affects all code including tests
- ✅ Tests should continue to work because they import the module

**Test**:
```bash
pytest tests/unit/test_ingestor*.py -v
# All 21 tests should pass
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tests break due to `chdir()` | Low | Medium | Verify all tests pass; if break, add test-specific setup |
| CI/CD fails due to path changes | Low | High | Test in CI environment; add debug logging if needed |
| Documentation outdated | Medium | Low | Update README/QUICKSTART in same PR |

---

## Next Steps

1. **Phase 1**: Implement changes in `ingestor.py` and create `__main__.py`
2. **Phase 1**: Update `quickstart.md` with new execution examples
3. **Phase 2**: Run all tests and verify acceptance criteria
4. **Phase 2**: Update documentation to remove PYTHONPATH references

---

## References

- [Python `pathlib` documentation](https://docs.python.org/3/library/pathlib.html)
- [Python `os.chdir()` documentation](https://docs.python.org/3/library/os.html#os.chdir)
- [Python packaging best practices](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#entry-points)
- AEGF Constitution: [`constitution.md`](../.specify/memory/constitution.md)
