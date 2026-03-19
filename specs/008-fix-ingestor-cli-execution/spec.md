# Feature Specification: Fix Ingestor CLI Execution

**Feature Branch**: `008-fix-ingestor-cli-execution`
**Created**: 2026-03-19
**Status**: Draft
**Input**: "El ingestor falla al ejecutarse desde la terminal con `python3 -m src.discovery.ingestor` por ModuleNotFoundError y FileNotFoundError. Debe funcionar desde la raíz del proyecto sin PYTHONPATH, en terminal manual y en CI/CD (GitHub Actions)."

## Resumen ejecutivo

`src/discovery/ingestor.py` no puede ejecutarse desde la terminal sin configuración especial de `PYTHONPATH`.
Hay **dos causas raíz independientes**:

1. **`ModuleNotFoundError: No module named 'src'`** — pytest usa `--import-mode=importlib` (en `pyproject.toml`) que añade automáticamente la raíz del proyecto a `sys.path`. La terminal directa no lo hace. Al ejecutar `python3 -m src.discovery.ingestor` desde la raíz del proyecto, Python SÍ añade el CWD a `sys.path[0]`, pero `from src.utils.metrics import get_metrics` (línea 31 del ingestor) falla si se intenta importar el módulo fuera de la raíz.

2. **`FileNotFoundError` en la ruta del config** — `open(args.config, "r")` (línea 560) abre la ruta tal cual se pasa, que al ser relativa (`configs/...`) falla si el CWD no es la raíz del proyecto.

**Solución mínima**: añadir un constante `PROJECT_ROOT` a nivel de módulo (pura computación, sin efectos laterales de I/O) y resolver la ruta del config a absoluta dentro de `main()` antes de abrirla. Crear `src/discovery/__main__.py` con importación relativa para habilitar `python3 -m src.discovery.ingestor`. Añadir un paso CI/CD en `.github/workflows/python-tests.yml` que valide la ejecución directa sin `PYTHONPATH`.

**Alcance del fix**: ejecución desde la **raíz del proyecto** sin PYTHONPATH. Ejecución desde un directorio arbitrario externo (p.ej. `/tmp`) está fuera de alcance: requeriría instalar el paquete (`pip install -e .`).

## Clarifications

- `os.chdir()` a nivel de módulo queda **excluido** de la solución: viola la constitución §III "No import-time side-effects". El `chdir`, si se necesitase, solo sería válido dentro de `main()`, pero la solución preferida es resolución de ruta absoluta sin cambiar CWD.
- `__main__.py` debe usar **importación relativa** (`from .ingestor import main`) para que funcione con `python3 -m src.discovery.ingestor`. La importación absoluta (`from src.discovery.ingestor import main`) solo funciona si `src` ya está en `sys.path`.
- El flag `--dry-run` existente en el ingestor se usará en el paso CI/CD para evitar clones de red reales.

## User Scenarios & Testing *(mandatorio)*

### User Story 1 — Ejecución manual desde terminal (Priority: P0)

Como desarrollador que configura un pipeline de ingesta PHP, quiero ejecutar `python3 -m src.discovery.ingestor --config configs/stage_1_discovery/examples/php_hexagonal.yaml --dry-run` desde la raíz del proyecto sin exportar `PYTHONPATH`, para que cualquier colaborador pueda lanzar el ingestor con `git clone` + `pip install -r requirements.txt`.

**Independent Test**: Desde una sesión de shell limpia (sin `PYTHONPATH` en el entorno):
```bash
cd /mnt/bunker_data/ai/data_factory
unset PYTHONPATH
source .venv/bin/activate
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/examples/php_hexagonal.yaml --dry-run
echo "Exit code: $?"
```

**Acceptance Scenarios**:

1. **Given** el CWD es la raíz del proyecto y `PYTHONPATH` no está exportado,  
   **When** se ejecuta `python3 -m src.discovery.ingestor --config configs/stage_1_discovery/examples/php_hexagonal.yaml --dry-run`,  
   **Then** el proceso termina con exit code 0 sin `ModuleNotFoundError` ni `FileNotFoundError`.

2. **Given** la ruta del config es relativa (`configs/stage_1_discovery/examples/php_hexagonal.yaml`),  
   **When** se procesa el argumento `--config` dentro de `main()`,  
   **Then** la ruta se resuelve a absoluta usando `PROJECT_ROOT` antes de `open()`, y la apertura del fichero no lanza `FileNotFoundError`.

3. **Given** se pasa una ruta de config absoluta (`/ruta/absoluta/config.yaml`),  
   **When** se procesa el argumento `--config`,  
   **Then** la ruta absoluta se usa tal cual sin modificación.

---

### User Story 2 — Tests unitarios sin PYTHONPATH (Priority: P0)

Como ingeniero de QA, quiero que todos los tests existentes del ingestor sigan pasando en una sesión de terminal normal (sin `--import-mode=importlib` explícito ni `PYTHONPATH` exportado manualmente), para que los tests sean reproducibles en cualquier entorno developer.

**Independent Test**:
```bash
cd /mnt/bunker_data/ai/data_factory
unset PYTHONPATH
source .venv/bin/activate
# pytest usa --import-mode=importlib declarado en pyproject.toml
pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v
echo "Exit code: $?"
```

**Acceptance Scenarios**:

1. **Given** pytest ejecuta con la configuración de `pyproject.toml` (que incluye `--import-mode=importlib`),  
   **When** se añade `PROJECT_ROOT` como constante de módulo a `ingestor.py`,  
   **Then** los 21 tests existentes (11 unit + 10 integration) pasan sin errores.

2. **Given** `PROJECT_ROOT` se calcula en tiempo de importación del módulo,  
   **When** pytest importa `ingestor` durante la colección de tests,  
   **Then** no se produce ningún efecto lateral de I/O (no `os.chdir()`, no escritura de ficheros, no llamadas de red) — solo computación de path.

---

### User Story 3 — CI/CD GitHub Actions certifica ejecución directa (Priority: P0)

Como mantenedor del repositorio, quiero que el workflow `.github/workflows/python-tests.yml` incluya un paso que ejecute `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` **sin** `PYTHONPATH` en el entorno, para que ningún PR rompa la ejecución directa del CLI sin que CI lo detecte.

**Independent Test** (validación del workflow tras el cambio):
1. Hacer push en una rama con los cambios implementados
2. Verificar que el job `test` de `python-tests.yml` completa todos sus steps, incluyendo el nuevo step "Verify direct CLI execution"
3. Verificar que el step NO tiene `env: PYTHONPATH: ...`

**Acceptance Scenarios**:

1. **Given** el workflow `python-tests.yml` incluye el step "Verify direct CLI execution",  
   **When** GitHub Actions ejecuta ese step en ubuntu-latest con Python 3.12 y 3.13,  
   **Then** el comando `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` termina con exit code 0 en ambas versiones.

2. **Given** el step de verificación CLI no tiene `env: PYTHONPATH` configurado,  
   **When** el step se ejecuta,  
   **Then** el CLI encuentra el módulo `src` via `sys.path` (añadido automáticamente por `-m` cuando CWD = raíz del repo en GitHub Actions checkout).

3. **Given** los tests pytest ya pasan en CI (step existente sin cambios),  
   **When** se añade el nuevo step CLI,  
   **Then** los tests pytest siguen pasando sin modificación del step existente.

---

## Requisitos (testables) *(mandatorio)*

### Requisitos funcionales

- **FR-001 (PROJECT_ROOT constante)**: `ingestor.py` debe declarar una constante `PROJECT_ROOT: Path` a nivel de módulo calculada como `Path(__file__).resolve().parent.parent.parent`. Esta constante es **pura computación** (sin I/O), compatible con la constitución §III.

- **FR-002 (Resolución de ruta de config)**: Dentro de `main()`, antes de `open(args.config)`, la ruta del config debe resolverse: si es relativa, se convierte a absoluta con `PROJECT_ROOT / args.config`; si es absoluta, se usa tal cual.

- **FR-003 (Sin PYTHONPATH en ejecución desde raíz)**: `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` ejecutado desde la raíz del proyecto, sin `PYTHONPATH` exportado, debe completar con exit code 0.

- **FR-004 (`__main__.py` con importación relativa)**: Crear `src/discovery/__main__.py` que use `from .ingestor import main` para habilitar `python3 -m src.discovery.ingestor`. Debe incluir header AEGF completo.

- **FR-005 (Retrocompatibilidad de tests)**: Los 21 tests existentes (11 unit `test_ingestor_profile_filter.py` + 10 integration `test_ingestor_git_recovery.py`) deben continuar pasando sin cambios en los propios tests.

- **FR-006 (Sin efectos laterales de importación)**: La adición de `PROJECT_ROOT` a nivel de módulo NO debe introducir efectos de I/O en tiempo de importación. Prohibido: `os.chdir()`, escritura de ficheros, llamadas de red, lectura de ficheros —exclusivamente en el nivel de módulo.

- **FR-007 (CI/CD — step de verificación CLI)**: El workflow `.github/workflows/python-tests.yml` debe incluir un nuevo step "Verify direct CLI execution" que ejecute `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` sin variable de entorno `PYTHONPATH`. Este step debe correr en ambas versiones de la matrix (3.12 y 3.13).

- **FR-008 (CI/CD — no PYTHONPATH en workflow)**: El workflow modificado no debe añadir `PYTHONPATH` como variable de entorno en ningún step nuevo ni en el step existente de tests.

- **FR-009 (Documentación)**: El README **y** `docs/ORCHESTRATION_QUICKSTART.md` deben documentar el comando correcto de ejecución (`python3 -m src.discovery.ingestor`) sin referencias a `PYTHONPATH`. Si existe documentación con `PYTHONPATH`, debe eliminarse.

### Restricciones (hard constraints)

- **C-001**: No usar `os.chdir()` a nivel de módulo — viola constitución §III.
- **C-002**: No añadir `PYTHONPATH` a scripts de automatización, README ni workflow CI.
- **C-003**: `__main__.py` debe usar importación relativa, no absoluta, para evitar dependencia circular con `sys.path`.
- **C-004**: La solución no debe requerir `pip install -e .` para funcionar desde la raíz del proyecto.

## Success Criteria *(medibles y verificables)*

| # | Criterio | Verificación |
|---|----------|-------------|
| AC-1 | `python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml` desde raíz sin `PYTHONPATH` → exit code 0 | `unset PYTHONPATH && python3 -m src.discovery.ingestor --dry-run --config configs/stage_1_discovery/examples/php_hexagonal.yaml; echo $?` |
| AC-2 | 21 tests existentes siguen pasando en terminal sin `PYTHONPATH` explícito | `unset PYTHONPATH && pytest tests/unit/test_ingestor_profile_filter.py tests/integration/test_ingestor_git_recovery.py -v` → 21 passed |
| AC-3 | `python-tests.yml` contiene step "Verify direct CLI execution" sin `PYTHONPATH` | `grep -A5 "Verify direct CLI" .github/workflows/python-tests.yml` no contiene `PYTHONPATH` |
| AC-4 | GitHub Actions pasa el nuevo step en Python 3.12 y 3.13 | Badge verde en PR; ambas matrix entries completadas |
| AC-5 | No hay `os.chdir()` a nivel de módulo en `ingestor.py` | `grep -n "^os.chdir\|^    os.chdir" src/discovery/ingestor.py` → sin resultados |
| AC-6 | `__main__.py` usa importación relativa | `grep "from .ingestor import main" src/discovery/__main__.py` → match |