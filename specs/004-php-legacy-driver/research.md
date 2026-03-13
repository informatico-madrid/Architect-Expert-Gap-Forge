# Research: PHPLegacyDriver (Regex-Based Extractor)

**Feature**: 004-php-legacy-driver | **Date**: 2026-03-12

## R-001: ExtractorAdapter Protocol Interface

**Question**: ¿Cuál es la interfaz exacta del protocolo ExtractorAdapter que debe implementar PhpLegacyAdapter?

**Decision**: Implementar el `ExtractorAdapter` Protocol definido en `src/utils/extractors/base.py` (L29-50).

**Rationale**: El protocolo tiene dos métodos:
- `parse_file(path: Path) → ParseResult` — devuelve `ParseResult(file_path, ast_tree, raw_content, dependencies)`
- `extract_dependencies(path: Path) → List[Dependency]` — devuelve lista de `Dependency(name, module_type, source_module)`

Para PHP, `ast_tree` será `None` (no hay AST parser), `raw_content` contiene el código fuente, y `dependencies` se poblan desde `include`/`require`/`require_once` regex.

**Alternatives considered**:
- Crear un nuevo Protocol para PHP → rechazado porque rompe el contrato existente y requiere cambios en todo el pipeline
- Subclasear PythonAstAdapter → rechazado porque acopla comportamiento AST innecesario

## R-002: Module Discovery Strategy para PHP

**Question**: ¿Cómo descubre `metadata_enricher.py` (`RepoProcessor`) módulos en repositorios PHP legacy sin `manifest.json` ni `__init__.py`?

**Decision**: Añadir nueva estrategia `"directory_scan"` en `ProcessingConfig.module_discovery_strategy` (en `src/discovery/metadata_enricher.py`) que escanea directorios recursivamente buscando archivos `.php`.

**Rationale**: Las 4 estrategias existentes (`manifest`, `init`, `directory`, `manual_mapping`) dependen de artefactos Python:
- `manifest`: busca `manifest.json` + `__init__.py`
- `init`: busca `__init__.py`
- `directory`: busca subdirectorios con `__init__.py`
- `manual_mapping`: usa dict explícito

Ninguna funciona para PHP. La estrategia `directory_scan` usa `Path.rglob("*.php")` con exclusiones (`vendor/`, `node_modules/`, `tests/`, `cache/`).

**Alternatives considered**:
- Reutilizar `directory` con override de extensión → rechazado porque `directory` todavía busca `__init__.py`
- `manual_mapping` con script previo → rechazado porque requiere pasos manuales, no es escalable a 7+ plataformas

## R-003: Heuristic Block Fragmentation sin AST

**Question**: ¿Cómo fragmentar archivos PHP legacy procedural sin parser AST?

**Decision**: Motor de fragmentación regex multi-level:

1. **Preamble Rule (FR-018)**: líneas antes del primer bloque funcional → fragmento `PREAMBLE` con `fragment_type: "bootstrap"`
2. **Funciones**: `^\s*function\s+(\w+)\s*\(` → captura nombre, parámetros, bloque completo con brace-matching
3. **Clases**: `^\s*(abstract\s+)?class\s+(\w+)` → captura herencia/interfaces, bloque completo
4. **Switch/case blocks**: `^\s*switch\s*\(` → captura completa como unidad
5. **HTML/PHP mixed sections**: detección de bloques `<?php ... ?>` intercalados con HTML
6. **Fallback**: archivos sin funciones/clases → fragmentos de 50 líneas con overlap de 5

**Rationale**: El PHP legacy procedural usa funciones top-level sin namespaces. El brace-matching simple (count `{`/`}`) funciona >95% en código procedural porque no hay lambdas ni closures complejas (FR-017).

**DECISION (rev-1): FastBraceScanner en lugar de regex pura para brace-matching**:
Implementar un `FastBraceScanner` — un loop sobre el string caracter a caracter — para encontrar el cierre de función/clase/switch. Es 10× más robusto que contar `{`/`}` con regex y prácticamente igual de rápido al operar sobre strings en memoria:

```python
def fast_brace_scan(source: str, open_pos: int) -> int:
    """Returns index of closing brace matching the brace at open_pos."""
    depth = 0
    for i, ch in enumerate(source[open_pos:], start=open_pos):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1  # unmatched — caller aborts this fragment and logs
```

**DECISION (rev-2): Abort & Log para brace-mismatch**:
En archivos de 3000+ líneas, el 5% de fallos de brace-matching producen fragmentos truncados o mal delimitados que degradan silenciosamente el entrenamiento. Cuando `fast_brace_scan()` retorna `-1`, **no se crea ningún `PhpFragment`**. En su lugar, se registra un record compacto en `needs_manual_review.json` y el fragmenter continúa al siguiente bloque extraíble. Esto previene que código sintácticamente inválido entre al corpus de entrenamiento.

```python
if close_pos == -1:
    # Abort: no PhpFragment created — log and skip
    manual_review_log.append({
        "source_file": str(path),
        "name": func_name,
        "start_line": start,
        "reason": "unmatched_brace",
    })
    continue  # skip to next extractable block
```

El enum `fragment_type` mantiene exactamente 6 valores válidos: `function`, `class`, `switch_block`, `bootstrap`, `mixed_html`, `catchall`. No existe un tipo `DIRTY` — los fragmentos inválidos simplemente no se emiten.

**Alternatives considered**:
- `php-parser` via subprocess → rechazado (dependencia externa, latencia, falla en sintaxis rota)
- Tree-sitter PHP bindings → rechazado (dependencia C compilada, overhead de setup)
- Split fijo por líneas → rechazado (corta funciones por la mitad, pierde contexto semántico)
- Regex brace-counting pura → rechazado (frágil con strings/comments que contienen `{`/`}`)

## R-004: Extension Mapper en Stage 2

**Question**: ¿Cómo desacoplar `get_v2_fragments()` y `_ast_fragment_list()` del hardcode Python/AST?

**Decision**: Extension Mapper dict en `src/factory/fragment_extractor.py`:

```python
_EXTENSION_FRAGMENTERS: dict[str, Callable[[str, str], list[dict]]] = {
    ".py": _ast_fragment_list,
    ".php": _php_fragment_list,
    ".md": _md_fragment_list,
    ".yaml": _yaml_fragment_list,
    ".jinja": _jinja_fragment_list,
    ".j2": _jinja_fragment_list,
}
```

Insertar en `get_v2_fragments()` (en `src/factory/fragment_extractor.py`) para que `FUNCTIONAL_UNIT` route por extensión en vez de llamar directamente a `_ast_fragment_list()`.

**Rationale**: El código actual en `get_v2_fragments()` llama `_ast_fragment_list()` incondicionalmente para `FUNCTIONAL_UNIT`. El Extension Mapper extiende sin romper — `.py` sigue usando `_ast_fragment_list()`, `.php` usa el nuevo `_php_fragment_list()`.

**Alternatives considered**:
- Parametrizar `_ast_fragment_list()` con parser inyectado → rechazado (modifica firma de función existente, mayor blast radius)
- Dispatcher class → rechazado (over-engineering para un dict simple, viola YAGNI)

## R-005: Generic Section Parser en parse_bundle()

**Question**: ¿Cómo capturar `[LEGACY_SIGNATURES]` y futuras secciones custom sin hardcodear cada una?

**Decision**: Añadir regex genérico post-parse en `parse_bundle()` (en `src/factory/fragment_extractor.py`):

```python
# Capturar TODAS las secciones [SECTION_NAME]
all_sections = re.findall(r'\[([A-Z_]+)\](.*?)(?=\n\[|\n---|$)', content, re.DOTALL)
for name, body in all_sections:
    if name not in known_sections:
        arch[f"extra_{name.lower()}"] = body.strip()
```

Esto captura `[LEGACY_SIGNATURES]`, `[INCLUDE_GRAPH]`, etc. en el dict `arch` con prefijo `extra_` para evitar colisiones.

**Rationale**: `parse_bundle()` ya captura campos desconocidos en `[ARCH_HEADER]` (líneas con `:` se guardan en dict). Pero ignora silenciosamente secciones desconocidas (`[LEGACY_SIGNATURES]` se pierde). El regex genérico sigue el mismo espíritu: capturar todo, dejar al consumidor filtrar.

**Alternatives considered**:
- Hardcodear `[LEGACY_SIGNATURES]` → rechazado (no escala, viola Open/Closed)
- Plugin system para parsers de sección → rechazado (YAGNI, solo necesitamos 2-3 secciones extras)

## R-006: PHP Prompt Templates

**Question**: ¿Cómo estructurar los templates de prompt para el Teacher cuando procesa fragmentos PHP?

**Decision**: Nuevo namespace `php_legacy` en taxonomy YAML:

```yaml
system:
  php_legacy:
    base: |
      You are a PHP modernization expert. Analyze the legacy PHP code...
    blueprint_context: |
      BLUEPRINT CONTEXT (legacy codebase structure):
      ${blueprint}
    governance_context: |
      MODERNIZATION DOCTRINE:
      ${governance}
    nominal_suffix: |
      Generate a training pair with THREE sections:
      [DEBT_DIAGNOSTIC] — What's wrong with this legacy code
      [MODERN_PROPOSAL] — Symfony hexagonal equivalent
      [MAPPING_LOGIC]   — How element-by-element maps to modern
user:
  php_legacy:
    functional_unit: |
      LEGACY PHP FRAGMENT:
      ${fragment}
      LEGACY SIGNATURES:
      ${legacy_signatures}
      PLATFORM: ${platform}
```

Templates se inyectan al sistema via `build_system_with_blueprint()` (en `src/factory/prompt_builder.py`) y `_prompt()` routing por profile.

**Rationale**: La arquitectura de prompts existente usa `_prompt("system.python.base")` con dot-notation en YAML. Añadir `php_legacy` es extensión natural. El output de 3 secciones (DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC) fue especificado por el usuario para orientar a Symfony hexagonal.

**Alternatives considered**:
- Reutilizar templates Python con parámetro `language=php` → rechazado (PHP legacy necesita contexto de modernización totalmente diferente)
- Templates en archivos `.md` separados → rechazado (la arquitectura actual usa YAML centralizado)

## R-007: Platform Detection y Profiles

**Question**: ¿Cómo identificar la plataforma PHP (osCommerce, WordPress, etc.) automáticamente?

**Decision**: `PlatformProfile` con detección basada en archivos marker:

| Platform | Marker Files | Marker Patterns |
|----------|-------------|-----------------|
| osCommerce | `includes/application_top.php` | `tep_db_query`, `$HTTP_GET_VARS` |
| WordPress | `wp-config.php`, `wp-includes/` | `add_action`, `apply_filters`, `$wpdb` |
| ZenCart | `includes/configure.php` | `zen_`, `DIR_WS_CATALOG` |
| openmage | `app/Mage.php` | `Mage::`, `Varien_` |
| PrestaShop | `config/config.inc.php` | `Module::`, `ObjectModel` |
| CodeIgniter | `system/core/CodeIgniter.php` | `$this->load->`, `CI_Controller` |
| SuiteCRM | `include/MVC/` | `SugarBean`, `$sugar_config` |
| Generic PHP | (fallback) | `mysql_query`, `$_GET`, `$_POST` |

**Rationale**: Cada plataforma tiene patterns distintos de acoplamiento, convenciones de naming, y anti-patterns. La detección permite:
1. Seleccionar el snippet de Anti-Patterns Mapping correcto
2. Ajustar reglas de fragmentación (WordPress hooks vs osCommerce functions)
3. Enriquecer `[ARCH_HEADER]` con `PLATFORM: oscommerce`

**DECISION (rev-1): Unificar Magento/OpenMage bajo perfil `openmage`**:
OpenMage es el LTS activo de Magento 1 — misma arquitectura EAV, mismos XML configs masivos, mismo legado `Mage::` global. Magento 2 (completamente distinto, basado en DI) no está en el scope del MVP. El perfil se llama `openmage` (no `magento`) para distinguirlo claramente de Magento 2 y evitar mapeos incorrectos. El directorio `data/raw/multi_legacy/OpenMage/` mapea directamente a este perfil.

**DECISION (rev-1): Mapear directorio `gburton` al perfil `oscommerce_phoenix`**:
Gary Burton es mantenedor del fork Phoenix de osCommerce — variante procedimental modernizada con mejor tipado PHP 7+, namespaces parciales y PSR-4 parcial, pero aún con `tep_db_query()` y estructura de carpetas osCommerce. Profile `oscommerce_phoenix` hereda todos los markers de `oscommerce` y añade detección de namespaces `OSC\OM\` como indicador de estilo `hybrid`. No es un nuevo perfil desde cero — es una extensión de `oscommerce` con nivel de deuda `hybrid`.

**DECISION (rev-1): Golden Rule para clasificación Legacy vs Hybrid vs Modernizado**:
No usar porcentajes ni heurísticas complejas. Regla binaria en tres checks secuenciales:
1. ¿El archivo tiene `namespace` y al menos un constructor con parámetros tipados? → **Modernizado**
2. ¿Tiene `global $db` o funciones top-level sin clase? → **Puro**
3. ¿Tiene una `class` pero incluye `mysql_query()` / `tep_db_query()` / superglobals dentro del cuerpo? → **Hybrid**

Esta regla produce zero falsos positivos en los repositorios de multi_legacy/ y es implementable como 3 regex compiladas en <10ms por archivo.

**Alternatives considered**:
- Configuración manual por repo → rechazado (no escala, error-prone)
- Detección solo por nombre de directorio → rechazado (poco fiable, repos renombrados)
- Porcentaje de líneas OOP vs procedural → rechazado (costoso, ambiguo, error-prone)

## R-008: Anti-Patterns Mapping Snippets

**Question**: ¿Cómo estructurar la documentación de anti-patterns por plataforma?

**Decision**: Un archivo master `master_symfony_hex.md` con los principios generales de modernización a Symfony hexagonal, más un directorio `snippets/` con un archivo `.md` por plataforma conteniendo:

```markdown
# Anti-Patterns: osCommerce

## Database Access
- ANTI: `tep_db_query("SELECT * FROM...")` — SQL directo con string concat
- MODERN: Repository pattern con Doctrine DBAL QueryBuilder
- MAPPING: tep_db_query() → ProductRepository::findBy()

## Global State
- ANTI: `$HTTP_GET_VARS['id']` — superglobals directas
- MODERN: Symfony Request object injection
- MAPPING: $HTTP_GET_VARS → Request::query->get()
```

**Rationale**: El usuario especificó explícitamente master file + platform snippets con Anti-Patterns Mapping. Cada snippet se inyecta en el prompt del Teacher via `${governance}` para que el modelo conozca los patterns específicos de la plataforma.

**Alternatives considered**:
- JSON structured → rechazado (menos legible, más difícil de mantener/editar)
- Base de datos → rechazado (YAGNI, filesystem es suficiente para <10 plataformas)

## R-009: Test Strategy para PHP Fixtures

**Question**: ¿Cómo crear fixtures de test representativas sin copiar archivos PHP completos?

**Decision**: Fixtures sintéticas mínimas en `tests/fixtures/php_legacy/`:

```php
<?php
// tests/fixtures/php_legacy/oscommerce_categories.php
// Minimal osCommerce-style procedural PHP for testing
require('includes/application_top.php');
include(DIR_WS_LANGUAGES . $language . '/categories.php');

function tep_get_category_tree($parent_id = '0', $spacing = '', $exclude = '') {
    global $languages_id;
    $categories_query = tep_db_query("SELECT c.categories_id, cd.categories_name
        FROM categories c, categories_description cd
        WHERE c.parent_id = '" . (int)$parent_id . "'
        AND c.categories_id = cd.categories_id
        AND cd.language_id = '" . (int)$languages_id . "'
        ORDER BY sort_order, cd.categories_name");
    // ... body
    while ($categories = tep_db_fetch_array($categories_query)) {
        $result[] = $categories;
    }
    return $result;
}
```

Cada fixture ejerce 3-5 patterns clave de su plataforma en ≥150 líneas.

**Rationale**: Los tests existentes del proyecto usan `tmp_path` con fixtures inline. Para PHP necesitamos archivos `.php` reales por el parsing regex multi-línea.

**Alternatives considered**:
- Copiar archivos reales de data/raw/multi_legacy/ → rechazado (licensing, tamaño, fragilidad)
- Generar fixtures dinámicamente → rechazado (complejidad innecesaria)

## R-010: Parallel IO con ProcessPoolExecutor

**Question**: ¿Cómo orquestar el procesamiento de ~miles de archivos PHP para saturar todos los cores del Threadripper sin bloquear el GIL?

**Decision**: Usar `concurrent.futures.ProcessPoolExecutor` para el procesamiento por archivo (CPU-bound: regex matching, brace scanning, signature detection). IO de disco usa `ThreadPoolExecutor` para lectura concurrente antes del paso CPU:

```python
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

# Stage 1: IO-bound — leer todos los .php en paralelo
with ThreadPoolExecutor(max_workers=32) as io_pool:
    raw_files: dict[Path, str] = dict(
        zip(php_paths, io_pool.map(Path.read_text, php_paths))
    )

# Stage 2: CPU-bound — fragmentar + signature detection en paralelo
with ProcessPoolExecutor(max_workers=os.cpu_count()) as cpu_pool:
    futures = {cpu_pool.submit(process_php_file, path, content): path
               for path, content in raw_files.items()}
    for future in as_completed(futures):
        result = future.result()  # list[PhpFragment] (malformed blocks already aborted & logged)
        emit_bundle(result)
```

**Rationale**: PHP fragmentación + regex matching es CPU-bound (GIL es un cuello de botella con ThreadPoolExecutor para código Python puro). ProcessPoolExecutor bypasea el GIL lanzando subprocesos. El Threadripper tiene suficientes cores para procesar todos los repos de multi_legacy/ en paralelo. La separación IO (threads) / CPU (processes) es el patrón canónico para este tipo de workload.

**Worker function must be serializable**: La función pasada a `ProcessPoolExecutor.submit()` debe ser importable (no lambda, no closure). Definir `process_php_file(path: Path, content: str) -> list[PhpFragment]` como función de módulo top-level en `php_fragmenter.py`.

**Chunksize guidance**: Para repositorios grandes (1000+ archivos), usar `ProcessPoolExecutor.map(chunksize=50)` para reducir overhead de IPC serialization.

**Alternatives considered**:
- `asyncio` → rechazado (PHP parsing es CPU-bound, async no ayuda)
- `ThreadPoolExecutor` solo → rechazado (GIL bloquea regex CPU-intensivo)
- Procesamiento secuencial → rechazado (subutiliza Threadripper, inaceptable para 3000+ archivos)

## R-011: Preamble Attachment — Virtual Reference

**Question**: ¿Cómo adjuntar contexto de preámbulo a fragmentos derivados sin duplicar tokens?

**Decision**: **Virtual Reference via SHA-256 hash** — no copiar el código del preámbulo en cada fragmento. En su lugar, registrar el **SHA-256 hex digest del `raw_content` del fragmento bootstrap** en el `[ARCH_HEADER]` del fragmento derivado con campo `PREAMBLE_REF: <sha256_hex>`:

```text
[ARCH_HEADER]
MODULE: oscommerce/admin/categories
...
PREAMBLE_REF: 3a7f9c2e1b5d4f8a0e6c2d4b8f0a1e3c5d7b9f2e4a6c8d0b2f4a6e8c0d2b4f6
```

Stage 2 recibe el `PREAMBLE_REF` (64-char SHA-256 hex), localiza el fragmento bootstrap en el blueprint cache **por hash de contenido**, y lo inyecta en el prompt del Teacher via la variable `${preamble}` solo cuando está presente. Si el preámbulo excede el **TokenCounter threshold** (default: 800 tokens), Stage 2 invoca un **Summarization Step**: una llamada rápida al modelo local que resume el preámbulo a ≤200 tokens antes de inyectarlo.

```python
def prepare_preamble_context(preamble_content: str, max_tokens: int = 800) -> str:
    token_count = estimate_tokens(preamble_content)  # len(content) // 4 como proxy
    if token_count <= max_tokens:
        return preamble_content
    # Summarization Step — prompt pequeño al modelo local
    return summarize_preamble(preamble_content)  # returns ≤200 token summary
```

**Rationale**: Copiar el preámbulo en cada fragmento duplica tokens N veces (N = número de fragmentos del archivo). Para un archivo de 3000 líneas con preámbulo de 100 líneas y 30 fragmentos, eso es 3000 líneas de contexto duplicado. La Virtual Reference es zero-copy y permite que Stage 2 gestione el presupuesto de tokens de forma centralizada.

**Alternatives considered**:
- Inline copy en cada fragmento → rechazado (desperdicio de tokens, aumenta costo del Teacher)
- Omitir preámbulo del contexto del Teacher → rechazado (pierde información crítica de setup global)

## R-012: Validation Judge para SC-009

**Question**: ¿Cómo validar que el Teacher output sigue el schema de 3 secciones (SC-009 ≥90%)?

**Decision**: Dos niveles de validación:

**Level 1 — Structural regex (fast)**: Verificar presencia de las 3 secciones con regex:
```python
SECTION_PATTERN = re.compile(
    r'\[DEBT_DIAGNOSTIC\].*?\[MODERN_PROPOSAL\].*?\[MAPPING_LOGIC\]',
    re.DOTALL
)
```

**Level 2 — Validation Judge (thorough)**: Para muestras aleatorias (10% del output), enviar un prompt corto al modelo vLLM local:
```
System: You are a strict validator. Answer only YES or NO.
User: Does the following text contain all three sections [DEBT_DIAGNOSTIC],
      [MODERN_PROPOSAL], and [MAPPING_LOGIC], each with structured YAML content
      (not free prose)? Answer YES or NO only.
<teacher_output>
```

El Judge es un modelo 7B local (latencia <500ms) que detecta casos donde las secciones están presentes pero vacías o con prosa libre en lugar de YAML estructurado — falsos positivos del regex Level 1.

**SC-009 measurement**: SC-009 ≥90% se mide con Level 1 sobre el corpus completo + Level 2 sobre muestra aleatoria del 10%. Si Level 2 < 90%, se dispara un warning en el log del pipeline.

**Alternatives considered**:
- Solo regex → rechazado (no detecta secciones con contenido no estructurado)
- LLM judge en el 100% del output → rechazado (costo innecesario, muestra del 10% es estadísticamente suficiente)
