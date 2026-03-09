# Feature Specification: Stage 1 — Discovery, Processor y Master Documents (Language‑Agnostic)

**Feature Branch**: `001-stage1-discovery`  
**Created**: 2026-03-08  
**Status**: Draft  
**Input**: "Evolución a motor agnóstico de lenguaje para Stage 1 (Discovery, Processor, Master Docs)."

## Resumen ejecutivo

Esta especificación redefine Stage 1 para que sea **agnóstico respecto al lenguaje**. El Stage 1 debe seguir proporcionando las mismas garantías (descubrimiento fiable, empaquetado por módulo y documentos maestros de gobernanza), pero soportando múltiples perfiles de uso: p. ej. `homeassistant` (Python), `php_hexagonal` (PHP legacy → Hexagonal), y otros por añadir.

Piezas principales:

- `ingestor.py` (Discovery): descubre y sincroniza repositorios según un YAML de configuración que incluye un `profile` (indica el caso de uso y filtros por lenguaje/paths).
- `processor.py` (Processor): transforma los clones en `Logical Entity` bundles (`.txt`) siguiendo reglas definidas por el `profile` y usando un **Extractor Plugable** para analizar código y extraer dependencias/entidades.
- `production_v11` (Factory loader): carga dinámicamente los Master Documents (gap context) basados en el `profile` activo y los inyecta en los prompts.

Objetivo: que con un cambio de `--config` o `profile` el pipeline adapte su extracción y empaque a otro lenguaje sin modificar código core.

## Clarifications

### Session 2026-03-08

- Nota: La política canónica sobre fallos de parseo está definida en la sección **FR-006** (Prohibición de fallback silencioso / Política por defecto ante ParseError). Consulte FR-006 para la definición normativa de la conducta por defecto y las opciones configurables (`on_parse_error`).

## User Scenarios & Testing *(mandatorio)*

### User Story 1 — Ingestar repositorios (Priority: P1)

Como operador del pipeline, quiero que Stage 1 descubra y sincronice repositorios (modo `static` o `dynamic`) en `data/raw/{category}/{owner}/{repo}` usando un `profile` que filtre por lenguaje y paths relevantes, para que Stage 2 reciba materia prima consistente por caso de uso.

**Independent Test**: Ejecutar `python src/discovery/ingestor.py --config configs/stage_1_discovery/examples/<profile>.yaml --dry-run` y verificar que la lista de repos devuelta coincide con filtros del `profile`; ejecutar sin `--dry-run` y comprobar que las rutas clonadas existen y contienen `.git`.

**Acceptance Scenarios**:
1. **Given** un `profile: homeassistant` en la configuración, **When** se ejecuta la ingesta, **Then** se incluyen repositorios Python relevantes y se clonan bajo `data/raw/<category>`.
2. **Given** un `profile: php_hexagonal`, **When** se ejecuta la ingesta, **Then** se incluyen repositorios PHP legacy (p. ej. que contienen `composer.json` o extensiones `.php`) y se clonan.
3. **Given** que GitHub devuelve 403 por rate-limit, **When** el ingestor detecta `X-RateLimit-Reset`, **Then** duerme hasta el reset + 5s y reintenta (log explicado).

---

### User Story 2 — Emitir paquetes por módulo (Priority: P1)

Como arquitecto del dataset, quiero que `processor.py` analice cada repositorio según su `profile`, agrupe artefactos en módulos/contextos delimitados y emita bundles tipados (`TIPO 1`, `TIPO 3`, `TIPO 4`, `TIPO 5`) incluyendo metadatos de dependencias extraídos por el extractor plugable.

**Acceptance Scenarios (Agnóstico)**:

- **Escenario A (Python / Home Assistant)**: Dado un repo Python HA, el procesador genera `MODULE_BLUEPRINT` con imports Python, `VOCABULARY` desde `const.py` y `SCHEMA` desde `services.yaml` cuando correspondan.
- **Escenario B (PHP legacy → Hexagonal)**: Dado un repo PHP, el procesador genera `MODULE_BLUEPRINT` con `DEPENDENCIES` (sentencias `use`, `require`, `include`) y agrupa controladores/modelos en bounded contexts.
- **Comportamiento esperado**: Cambiar el `profile` en la configuración (o pasar `--profile`) modifica únicamente el extractor y las reglas, sin tocar la lógica core de emisión de bundles.

---

### User Story 3 — Carga dinámica de Master Documents (Priority: P2)

Como mantenedor del pipeline, quiero que los Master Documents se carguen dinámicamente en función del `profile` activo (p. ej. `homeassistant` → HA docs; `php_hexagonal` → Hexagonal/SOLID docs), para que los prompts de Stage 2 reciban la doctrina adecuada.

**Acceptance Scenarios**:
1. **Given** `profile: homeassistant` y `gap_dir` configurado, **When** se inicia `production_v11`, **Then** se cargan los ficheros mapeados por perfil y se inyectan en los prompts; si falta un fichero obligatorio, se lanza `FileNotFoundError` con mensaje claro.
2. **Given** `profile: php_hexagonal`, **When** se inicia la fábrica, **Then** se cargan los documentos maestros definidos por ese profile.

---

## Requisitos (testables) *(mandatorio)*

### Requisitos funcionales

- **FR-001 (Profile en configuración)**: `DiscoveryConfig` y `ProcessingConfig` deben aceptar un `profile` (ej. `homeassistant`, `php_hexagonal`) y `--profile` debe poder sobrescribirlo en CLI. Los `examples/<profile>.yaml` deben estar versionados en `configs/stage_1_discovery/examples/`.
- **FR-002 (Descubrimiento agnóstico)**: El sistema debe soportar `mode: static` y `mode: dynamic` y aplicar filtros definidos por `profile` (extensiones, paths, heurísticas de lenguaje).  
- **FR-003 (Sincronización Git)**: El ingestor debe clonar con `git clone --depth 1` y actualizar con `git pull --ff-only`.

	- **Recuperación segura:** en caso de fallo del `pull`, se intentará una secuencia controlada: `fetch` + comprobación de ancestry (verificar que el commit remoto incluye el antiguo HEAD en su historia) y solo entonces `reset --hard` hacia el commit remoto.
	- **Política de retry:** máximo **3** intentos por operación (pull → fetch+reset), con backoff exponencial (1s, 2s, 4s) antes de declarar fallo y reportar el repositorio para revisión manual.
	- **Criterios de abort:** si la comprobación de ancestry falla (historia divergente sin ancestro común detectable) o los intentos se agotan, marcar el trabajo como `needs_manual_review` y fallar el procesamiento del repositorio.
- **FR-004 (Backoff por rate-limit)**: Manejo automático de 403 y `X-RateLimit-Reset` con logging y reintentos controlados.
- **FR-005 (Extractor Plugable)**: Introducir una interfaz `ExtractorAdapter` configurada por `profile` que implemente `extract_dependencies(path: Path) -> List[Dependency]` y `parse_file(path: Path) -> ParseResult` para el lenguaje objetivo (Tree‑sitter o adaptadores específicos). El `processor` debe usar el adapter indicado por el `profile`.
- **FR-006 (Prohibición de fallback silencioso / Política por defecto ante ParseError)**: Si el extractor falla al parsear un archivo, NO se debe aplicar un fallback heurístico silencioso. El extractor debe levantar una excepción `ParseError` con estructura documentada (`file_path`, `line`, `error`, `diagnosis`, `fix_hint`, `adapter`) y registrar el evento en el informe de ejecución.

	- **Política por defecto (normativa):** marcar el archivo como `needs_manual_review` y **abortar el procesamiento del repositorio actual**. Este proyecto **elimina** la práctica de preservar silent fallbacks: la compatibilidad hacia atrás se conseguirá migrando los tests y consumidores (ver tarea T031), no manteniendo comportamiento silencioso.

	- **Configurabilidad:** la acción ante `ParseError` debe ser configurable vía `profile` con la opción `on_parse_error` que acepta valores literales `abort`, `skip`, `mark_and_continue`. Si se selecciona una opción distinta a `abort`, el informe de ejecución deberá incluir todos los `ParseError` ocurridos y métricas por repo (contador, ejemplos, trazas) para auditoría.
	- **Forma de `ParseError`:** La excepción `ParseError` será estructurada y su forma normativa contiene: `file_path: str`, `line: int | None`, `error: str`, `diagnosis: str | None`, `fix_hint: str | None`, `adapter: str`.
    - Nota: `TIPO 2` se considera obsoleto en esta versión (su contenido se pliega en `MODULE_BLUEPRINT` / `TIPO 4`).
	- **Compatibilidad:** los consumidores que todavía produzcan/lean `TIPO 2` deben mapearlo a `TIPO 4` durante la ventana de deprecación. Timeline de deprecación: soporte mantenido por una ventana de 90 días desde la fusión de este refactor; después de ese periodo, `TIPO 2` será eliminado.
- **FR-007 (Bundles tipados agnósticos)**: El processor debe emitir `.txt` con `[ARCH_HEADER]` estándar que incluya al menos: `MODULE`, `REPO_PREFIX`, `FILE_ROLE`, `FRAGMENT_TYPE`, `DEPENDENCIES` (lista de dependencias normalizadas), `NEIGHBORS`.

### Fragment Types (TIPO 1..5)

Para eliminar ambigüedades las emisiones `.txt` y el campo `FRAGMENT_TYPE` se normalizan en los siguientes tipos (valores aceptados):

- `TIPO 1` — `FUNCTIONAL_UNIT`: Unidad funcional emparejada con su(s) prueba(s). Se emite como par (código + test) y suele saltarse la regla de tamaño (`MIN_SIZE`) para preservar utilidades con tests. Produce dos artefactos (logic + test) cuando procede.
- `TIPO 3` — `LOGIC_ONLY`: Fragmentos de lógica individuales (archivo de código o chunk AST) que no tienen tests detectados y pasan los umbrales de tamaño/pureza. Se generan skeletons AST-chunked y metadata de contexto.
- `TIPO 4` — `MODULE_BLUEPRINT`: Blueprint de módulo/paquete que agrupa archivos ancla (manifiestos, `README`, `const.*`, `schema*`) y provee contexto arquitectónico para los fragmentos del módulo.
- `TIPO 5` — `GOVERNANCE_RULES`: Reglas a nivel de repo/paquete (normas de estilo, hojas de ruta de CI, ejemplos de configuración) que se emiten como artefactos de gobernanza y van al `governance_cache`.

- Nota: `TIPO 2` se considera obsoleto en esta versión (su contenido se pliega en `MODULE_BLUEPRINT` / `TIPO 4`).
- **FR-008 (Detección de módulos configurable)**: La estrategia de agrupación de archivos en módulos/bounded contexts debe ser declarativa y leída desde la configuración del `profile`. El `processor` debe soportar al menos tres estrategias seleccionables por `profile`:

	- `strategy: manifest` — detectar módulos a partir de manifestos o archivos ancla (p. ej. `manifest.json`, `composer.json`, `package.json`).
	- `strategy: directory` — agrupar por reglas de directorio (p. ej. `app/`, `src/`, `controllers/`) tal como declaradas en la configuración del `profile`.
	- `strategy: manual_mapping` — usar una tabla explícita de mapeo `manual_module_mapping` definida en el `profile.yaml` que asigna rutas/archivos concretos a nombres de bounded context.

	La configuración debe permitir overrides por repositorio (por ejemplo, un bloque `overrides: { 'owner/repo': { strategy: manual_mapping, manual_module_mapping: {...} } }`). El `processor` no debe asumir una estructura por defecto más allá de la estrategia declarada; cuando `strategy` sea `manual_mapping` la información del YAML es normativa.
- **FR-009 (Governance bundles dinámicos)**: `production_v11.load_master_docs(gap_dir, profile)` debe cargar el conjunto de documentos maestros mapeados por profile desde `configs/stage_1_discovery/master_docs_map.yaml` o equivalente; si falta un documento obligatorio por profile, lanzar `FileNotFoundError`.
    - **Profile**: Identificador de caso de uso que declara: lenguaje principal, extractor adapter, `master_docs_map`, `extensions`, `ignored_paths` y, opcionalmente, `module_heuristics` o `manual_module_mapping`.
    - La configuración por `profile` define: `extensions`, `module_heuristics`, `ignored_paths`, `master_docs_map`, `extractor_adapter`.

    - **Precedencia de exclusión (FR-010):** cuando exista conflicto entre el `.gitignore` del repositorio y `profile.ignored_paths`, el archivo del repositorio (`.gitignore`) tiene prioridad. Se añadirá una prueba unitaria que valide esta regla (ver T028/T029 para harness y validación).
- **FR-010 (Filtros de relevancia)**: Excluir paths por `.gitignore` y por reglas de `profile` (p. ej. `/vendor`, `node_modules`) durante el procesamiento.
- **FR-011 (Ejemplos versionados)**: Incluir ejemplos de configuración por profile en `configs/stage_1_discovery/examples/` versionados en git para referencia del usuario.

### Entidades clave

- **Profile**: Identificador de caso de uso que declara: lenguaje principal, extractor adapter, `master_docs_list`, `extensions`, `ignored_paths` y, opcionalmente, `module_heuristics` o `manual_module_mapping`.

	- `manual_module_mapping` (opcional): un bloque de configuración que permite declarar explícitamente qué archivos o rutas pertenecen a cada `Bounded Context` cuando las heurísticas automáticas no son fiables. Diseñado para repositorios legacy que carecen de estructura clara.
- **ExtractorAdapter**: Implementación por lenguaje encargada de parsear archivos y devolver dependencias estructuradas.
- **Logical Entity (.txt)**: Paquete emitido que contiene código, `[ARCH_HEADER]` y secciones de contexto.
- **ParseError**: Error estructurado lanzado por el extractor en caso de fallo en parsing.

## Success Criteria *(medibles y verificables)*

- **SC-001**: Cambiar `--config` o `--profile` (por ejemplo entre `homeassistant` y `php_hexagonal`) produce bundles `.txt` cuyos `DEPENDENCIES` reflejan el lenguaje objetivo sin modificación del core del `processor`.
- **SC-002**: En tests de integración (5 repositorios por profile), el extractor identifica al menos el 90% de las dependencias esperadas para cada lenguaje (imports/use/require).
    - **Reference corpus & recall (SC-002 clarification):** Se definirá un corpus de referencia en `tests/fixtures/reference_corpus/<profile>/` con 5 repositorios por profile y un archivo `gold_dependencies.json` que contiene el conjunto esperado de dependencias por archivo. La métrica canónica será `recall@N` (N=5,10): para cada archivo, tomar las N dependencias extraídas por el extractor y medir cuántas aparecen en la lista esperada; agregación a nivel repo y profile. SC-002 exige recall >= 90% sobre la agregación del corpus en `recall@10`.
- **SC-003**: Los `master_docs` mapeados por `profile` se cargan correctamente y, si falta alguno, la ejecución falla con `FileNotFoundError` claramente documentado.
- **SC-004**: En caso de parse failure el sistema registra un `ParseError` estructurado y la política configurada decide (abort, skip, mark) sin silencios.
- **SC-005 (Performance benchmarks)**: Antes de merge debe existir un benchmark reproducible que capture:
	- Throughput baseline: `files/hour/worker` para repos de tamaño típico. Objetivo MVP: **>= 1000 files/hour/worker** en condiciones de CI para repos pequeños/medianos.
	- Latency per-file: mean < 200ms, P95 < 1s (archivo pequeño, < 1k LOC).
	- Repos por hora: objetivo operativo: procesar **>= 10 repos/hour** para un worker en carga media.
	- Estas métricas deben ser capturadas por T032 y comparadas contra el baseline previo al refactor.

## Assumptions (decisiones tomadas / valores por defecto)

- La configuración por `profile` define: `extensions`, `module_heuristics`, `ignored_paths`, `master_docs_list`, `extractor_adapter`.
- El pipeline respeta el `.gitignore` original del repo como primera fuente para excluir vendor/ dependencias externas y evita procesar `node_modules`, `vendor`, etc.
- Ejemplo de configuración por profile debe estar versionado en `configs/stage_1_discovery/examples/<profile>.yaml` para facilitar adopción.

- El `profile.yaml` puede incluir un bloque opcional `manual_module_mapping` para casos en los que la detección automática falle. Ejemplo esquemático:

```yaml
profile: php_hexagonal
extensions: ['.php']
ignored_paths: ['vendor', 'node_modules']
module_heuristics:
	strategy: directory
	directories: ['app', 'src']
manual_module_mapping:
	'Billing':
		- 'src/Billing'
		- 'legacy/billing.php'
	'User':
		- 'src/User'
overrides:
	'owner/repo-legacy':
		strategy: manual_mapping
		manual_module_mapping:
			'LegacyMonolith': ['index.php', 'functions.php']
```

Esta sección permite al operador declarar, por profile o por repositorio, el agrupamiento exacto de archivos en `Bounded Contexts` cuando las heurísticas no sean suficientes.

## How to test locally (comandos rápidos)

1. Ejecutar discovery con profile de ejemplo:

```bash
python src/discovery/ingestor.py --config configs/stage_1_discovery/examples/homeassistant.yaml --dry-run
```

2. Ejecutar processor con profile PHP:

```bash
python src/discovery/processor.py --config configs/stage_1_discovery/examples/php_hexagonal.yaml
```

3. Cargar master docs dinámicos (ejemplo unit test):

```python
from pathlib import Path
from src.factory import production_v11
production_v11.load_master_docs(Path('data/Gap'), profile='php_hexagonal')
```

## Notas para refactor futuro

- Extraer `ExtractorAdapter` en `src/utils/extractors/` con adaptadores: `python_ast_adapter`, `tree_sitter_adapter`, `php_neon_adapter`, etc., y una fábrica que los instancie según `profile`.
- Migrar umbrales y patrones a `configs/stage_1_discovery/policy.yaml` y exponer overrides por CLI.
- Asegurar tests unitarios para cada adapter y pruebas de integración por profile.

---

*Especificación actualizada para soportar múltiples lenguajes y perfiles de uso. Este refactor **no preservará** silent fallbacks: la compatibilidad hacia atrás se logrará mediante migración de tests y consumidores (ver tarea T031). `production_v11.load_master_docs` deberá aceptar `profile` y usar `configs/stage_1_discovery/master_docs_map.yaml`.*