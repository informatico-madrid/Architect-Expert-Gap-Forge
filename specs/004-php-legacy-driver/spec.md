# Feature Specification: PHPLegacyDriver (Regex-Based Extractor)

**Feature Branch**: `004-php-legacy-driver`
**Created**: 2026-03-12
**Status**: Draft
**Input**: Implementación del PHPLegacyDriver — All-Terrain Engine para extracción de código PHP legacy procedural (2000-2010) mediante regex, con etiquetado semántico de categorías, detección de dependencias implícitas, y generación de ARCH_HEADER compatible con el pipeline Stage 2.

## Clarifications

### Session 2026-03-12

- Q: ¿Cómo se resuelve la contradicción entre compatibilidad 100% Stage 2 (FR-004) y las extensiones IMPLICIT_DEPS/[LEGACY_SIGNATURES]? → A: Evolución del contrato — Stage 2 se actualiza con cambios mínimos: parser genérico de secciones (`\[(\w+)\]`), routing por extensión de archivo (eliminar AST lock), e inyección de [LEGACY_SIGNATURES] en el prompt del Teacher. Se añade categoría MODERN_REFERENCE para código PHP híbrido (OOP + procedural). Retrocompatible con bundles Python existentes.
- Q: ¿BaseAdapter compartido (herencia) o Protocol independiente para unificar la interfaz Python/PHP? → A: Protocol + dispatch con Extension Mapper. El acoplamiento ocurre en el schema del bundle (.txt), no en jerarquía de clases. `get_v2_fragments()` usa un diccionario de extensión → función de fragmentación (no if/else hardcodeado) para ser extensible a futuros lenguajes.
- Q: ¿Cuál es la unidad de fragmentación para PHP procedural sin AST (archivos de 1000+ líneas con switch/case)? → A: Bloque funcional heurístico — fragmentar por `function`, `case` de switch, o bloque `<?php ?>` significativo. Regla del Preámbulo obligatoria: capturar el bloque de setup inicial del archivo y adjuntarlo a cada fragmento derivado. Cases >500 líneas se sub-chunkean manteniendo encabezado. Cada fragmento lleva `LEGACY_ACTION: nombre_del_case` en su metadata.
- Q: ¿Reutilizar prompt templates de Python/HA o crear templates dedicados para PHP legacy? → A: Templates PHP dedicados (`system.php_legacy.*`, `user.php_legacy.*`) con inyección de doctrina (archivos maestros, al igual que HA). Output del Teacher en 3 secciones: DEBT_DIAGNOSTIC (firmas e impacto), MODERN_PROPOSAL (interfaces de dominio/Ports y DTOs para arquitectura hexagonal), MAPPING_LOGIC (transición de estado global a contexto inyectado Symfony). Objetivo: dataset que entrene al modelo como experto en modernización empresarial PHP legacy → Symfony hexagonal.
- Q: ¿Doctrina de destino única o parametrizada por plataforma de origen? → A: Master file único de arquitectura hexagonal Symfony + snippets por plataforma origen con Anti-Patterns Mapping completo. Los snippets no son solo listas de funciones → destino (ej. `tep_db_query` → Doctrine), sino mapeos de anti-patrones completos incluyendo estado global → servicio moderno (ej. `global $customer_id` → `UserInterface`/`TokenStorage`, `$_SESSION['cart']` → `CartService` inyectado).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Extracción de fragmentos PHP legacy (Priority: P1)

Un operador del pipeline ejecuta el processor sobre un repositorio PHP legacy (osCommerce, ZenCart, WordPress) clonado en `data/raw/multi_legacy/`. El PHPLegacyDriver recorre cada archivo `.php`, extrae los fragmentos de lógica de negocio mediante patrones regex, y genera bundles `.txt` con el formato ARCH_HEADER + contenido, idéntico en estructura a los bundles que produce el adaptador Python existente.

**Why this priority**: Sin esta capacidad base, ninguna de las demás funcionalidades tiene valor. Es el núcleo del driver: leer PHP → emitir bundles compatibles con Stage 2.

**Independent Test**: Procesar un archivo PHP representativo de osCommerce (≥2000 líneas) y verificar que se emiten bundles `.txt` válidos con secciones [ARCH_HEADER] parseables por Stage 2.

**Acceptance Scenarios**:

1. **Given** un repositorio osCommerce clonado en `data/raw/multi_legacy/osCommerce/`, **When** el processor se ejecuta con profile `php_legacy`, **Then** se generan bundles `.txt` en el directorio de salida con [ARCH_HEADER] válido.
2. **Given** un archivo PHP de 2000+ líneas con PHP mezclado con HTML/JavaScript, **When** el driver lo procesa, **Then** extrae exclusivamente los bloques de lógica PHP ignorando el markup HTML/JS inline.
3. **Given** un archivo PHP que contiene funciones globales (sin clases), **When** el driver lo procesa, **Then** cada función se extrae como un fragmento independiente con tipo LOGIC_ONLY o FUNCTIONAL_UNIT.

---

### User Story 2 — Etiquetado semántico de patrones de deuda técnica (Priority: P1)

El driver clasifica cada patrón regex detectado en una categoría semántica: PERSISTENCE (acceso a BD), STATE (estado global/sesión), MODULE_LINK (dependencias de includes), SECURITY_SMELL (vectores de inyección SQL), y CONSTANT_DEF (defines y constantes). Estas categorías se incluyen en una sección [LEGACY_SIGNATURES] dentro de cada bundle, proporcionando al Teacher contexto sobre la naturaleza del código legacy.

**Why this priority**: El etiquetado semántico es lo que diferencia este driver de un simple grep. Sin él, el modelo no puede aprender qué tipo de deuda técnica está viendo.

**Independent Test**: Procesar un archivo PHP con `mysql_query()`, `global $db`, `include('file.php')`, y `$_SESSION` → verificar que [LEGACY_SIGNATURES] contiene entradas categorizadas correctamente.

**Acceptance Scenarios**:

1. **Given** un archivo PHP con llamadas `mysql_query()`, `tep_db_query()`, y `$wpdb->query()`, **When** el driver lo procesa, **Then** la sección [LEGACY_SIGNATURES] lista cada match con categoría PERSISTENCE.
2. **Given** un archivo PHP con `global $currencies`, `$_SESSION['cart']`, y `tep_session_register()`, **When** el driver lo procesa, **Then** la sección [LEGACY_SIGNATURES] lista cada match con categoría STATE.
3. **Given** un archivo PHP con `include(DIR_WS_INCLUDES . 'header.php')`, **When** el driver lo procesa, **Then** la sección [LEGACY_SIGNATURES] lista cada match con categoría MODULE_LINK y captura la ruta del archivo incluido.

---

### User Story 3 — Detección de dependencias implícitas (Priority: P2)

El driver analiza cada fragmento extraído e identifica variables usadas con prefijo `$` que no fueron asignadas dentro del fragmento. Estas variables representan dependencias implícitas inyectadas por includes previos o por el scope global, y se listan como `IMPLICIT_DEPS` en el ARCH_HEADER para dar contexto completo al Teacher.

**Why this priority**: Las dependencias implícitas son el mayor obstáculo para entender código PHP procedural. Sin ellas, los fragmentos quedan descontextualizados.

**Independent Test**: Extraer una función que use `$languages_id` y `$db` sin declararlas localmente → verificar que ambas aparecen en `IMPLICIT_DEPS`.

**Acceptance Scenarios**:

1. **Given** un fragmento PHP que usa `$languages_id`, `$currencies`, y `$db`, y ninguna de estas variables está asignada dentro del fragmento, **When** el driver analiza el fragmento, **Then** el ARCH_HEADER incluye `IMPLICIT_DEPS: ['$languages_id', '$currencies', '$db']`.
2. **Given** un fragmento PHP donde `$query` se asigna localmente (`$query = ...`) pero `$db` no, **When** el driver analiza el fragmento, **Then** solo `$db` aparece en `IMPLICIT_DEPS`.

---

### User Story 4 — Reconstrucción del grafo de módulos (Priority: P2)

El driver construye un grafo de dependencias entre archivos basándose en las cadenas `include`/`require` detectadas. Este grafo permite a Stage 2 entender la arquitectura implícita del sistema legacy: qué archivos dependen de cuáles, qué archivos son "hubs" (incluidos por muchos), y qué archivos son hojas.

**Why this priority**: Sin el grafo de módulos, es imposible generar MODULE_BLUEPRINT (TIPO 4) para repositorios PHP, y Stage 2 pierde contexto arquitectónico.

**Independent Test**: Procesar 5 archivos PHP interconectados por includes → verificar que el grafo resultante refleja las dependencias reales.

**Acceptance Scenarios**:

1. **Given** un repositorio donde `application_top.php` es incluido por 20+ archivos, **When** el driver procesa el repositorio, **Then** `application_top.php` se identifica como hub y se emite un bundle TIPO 4 (MODULE_BLUEPRINT) que lo documenta como anchor del módulo.
2. **Given** un archivo con `require(DIR_WS_FUNCTIONS . 'general.php')`, **When** el driver resuelve la dependencia, **Then** el grafo registra un arco desde el archivo hacia `includes/functions/general.php` (resolviendo la constante `DIR_WS_FUNCTIONS` si está definida).

---

### User Story 5 — Compatibilidad multi-plataforma (Priority: P3)

El driver reconoce patrones idiomáticos específicos de cada plataforma legacy: prefijos `tep_` para osCommerce, `$wpdb->` para WordPress, `zen_` para ZenCart, `Mage::` para Magento. Los patrones se organizan en perfiles de plataforma, permitiendo detección precisa sin falsos positivos entre plataformas.

**Why this priority**: Los repositorios en `data/raw/multi_legacy/` cubren 7+ plataformas. Sin perfiles específicos, los patrones de una plataforma generarían ruido en otra.

**Independent Test**: Procesar un archivo osCommerce con `tep_db_query()` y un archivo WordPress con `$wpdb->prepare()` → verificar que cada uno usa el perfil correcto y no genera falsos positivos.

**Acceptance Scenarios**:

1. **Given** un archivo de osCommerce con `tep_db_query($query)`, **When** el driver lo procesa con auto-detección de plataforma, **Then** se identifica como osCommerce y el patrón se categoriza como PERSISTENCE con subtipo `tep_db`.
2. **Given** un archivo de WordPress con `$wpdb->prepare()`, **When** el driver lo procesa, **Then** se identifica como WordPress y el patrón se categoriza como PERSISTENCE con subtipo `wpdb`.
3. **Given** un archivo genérico con `mysql_query()` sin marcadores de plataforma, **When** el driver lo procesa, **Then** se clasifica como `generic_php` y el patrón se categoriza igualmente como PERSISTENCE.

---

### Edge Cases

- **PHP mezclado con HTML/JavaScript**: El driver debe extraer solo bloques `<?php ... ?>` y funciones PHP, ignorando HTML, CSS y JavaScript inline. Los fragments emitidos contienen exclusivamente lógica PHP.
- **Archivos con eval() y código dinámico**: Se detecta `eval()` como un SECURITY_SMELL y se marca el fragmento completo como potencialmente incompleto. El contenido del `eval()` se captura como string literal sin intentar parsearlo.
- **Includes con rutas dinámicas**: Cuando un include usa expresiones como `include($var . 'file.php')`, el driver marca la dependencia como `UNRESOLVED` en el grafo y registra la expresión original para revisión manual.
- **Archivos mayores de 10,000 líneas**: Se aplica chunking automático para que ningún fragmento exceda el tamaño máximo compatible con la ventana de contexto del modelo.
- **Archivos con encoding no-UTF8**: El driver intenta decodificar como latin-1 como fallback, registrando un warning. Los archivos completamente ilegibles se saltan con un registro en `needs_manual_review.json`.
- **Archivos sin etiqueta de apertura `<?php`**: Se tratan como archivos de template puro y se excluyen del procesamiento de lógica, pero se pueden registrar como MODULE_LINK targets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE implementar un adaptador `PhpLegacyAdapter` que cumpla el protocolo `ExtractorAdapter` existente, registrándose en el factory de adaptadores con el profile `php_legacy`.
- **FR-002**: El sistema DEBE extraer fragmentos de código PHP de archivos `.php` utilizando patrones regex, sin depender de un parser AST de PHP.
- **FR-003**: El sistema DEBE clasificar cada patrón detectado en exactamente una categoría semántica: PERSISTENCE, STATE, MODULE_LINK, SECURITY_SMELL, CONSTANT_DEF, o MODERN_REFERENCE. La categoría MODERN_REFERENCE captura usos de clases OOP, namespaces (`use`), y patrones modernos encontrados en código legacy híbrido (ej. `use OSC\OM\Registry` en osCommerce v4, clases con herencia en ZenCart reciente).
- **FR-004**: El sistema DEBE generar bundles `.txt` con formato [ARCH_HEADER] compatible con el parser `parse_bundle()` de Stage 2, incluyendo MODULE, REPO_PREFIX, FILE_ROLE, FRAGMENT_TYPE, LOCAL_IMPORTS, DEPENDENCIES, NEIGHBORS, e IMPLICIT_DEPS. El parser `parse_bundle()` de Stage 2 DEBE ser actualizado para capturar secciones adicionales como `[LEGACY_SIGNATURES]` mediante un loop genérico de descubrimiento de secciones (`\[(\w+)\]`), en lugar del allowlist rígido actual.
- **FR-005**: El sistema DEBE añadir una sección [LEGACY_SIGNATURES] en cada bundle, listando todos los patrones de deuda técnica detectados con su categoría, línea, y texto original del match. El parser de Stage 2 DEBE reconocer y capturar esta sección, y `get_v2_fragments()` DEBE inyectar su contenido en el bloque de contexto del prompt del Teacher para que el modelo reciba información sobre la naturaleza de la deuda técnica del código fuente.
- **FR-006**: El sistema DEBE detectar variables implícitas (usadas con `$` pero no asignadas localmente) y listarlas como `IMPLICIT_DEPS` en el ARCH_HEADER.
- **FR-007**: El sistema DEBE detectar cadenas `include`/`require`/`include_once`/`require_once` y construir un grafo de dependencias entre archivos para el repositorio procesado.
- **FR-008**: El sistema DEBE procesar archivos donde PHP está mezclado con HTML/JavaScript, extrayendo exclusivamente los bloques de lógica PHP.
- **FR-009**: El sistema DEBE soportar perfiles de plataforma (osCommerce, WordPress, ZenCart, Magento, CodeIgniter, Joomla, SuiteCRM) con patrones regex específicos de cada una, además de un perfil genérico.
- **FR-010**: El sistema DEBE auto-detectar la plataforma de un repositorio basándose en marcadores de directorio y archivos canónicos (ej. `includes/configure.php` para osCommerce, `wp-config.php` para WordPress).
- **FR-011**: El sistema DEBE aplicar chunking a archivos que excedan el tamaño máximo de fragmento, asegurando que cada chunk sea procesable dentro de la ventana de contexto del modelo.
- **FR-012**: El sistema DEBE registrar archivos problemáticos (encoding, parse failures, eval dinámico) en `needs_manual_review.json`, siguiendo el mismo formato que el processor actual.
- **FR-013**: El sistema DEBE procesar todo localmente sin conexiones de red externas (soberanía de datos).
- **FR-014**: El sistema DEBE categorizar los patrones de seguridad detectados por tipo: SQL injection vectors (`mysql_query` con concatenación de variables), XSS potencial (`echo $_GET`/`$_POST` sin sanitizar), y file inclusion dinámica.
- **FR-015**: Stage 2 (`get_v2_fragments()` en production_v11.py) DEBE implementar un Extension Mapper — un diccionario que asocie extensiones de archivo a funciones de fragmentación (`.py` → `ast.parse()`, `.php` → regex fragmenter). Este patrón elimina el AST lock actual y permite extensión futura a otros lenguajes sin modificar la lógica de dispatch.
- **FR-016**: El sistema DEBE distinguir entre código PHP 'Legacy Puro' (procedural: funciones globales, mysql_*, includes directos) y 'Legacy Modernizado' (OOP: clases con herencia, namespaces `use`, patrones Registry/Factory). Los archivos mixtos se etiquetan como `hybrid` y emiten firmas de ambos tipos.
- **FR-017**: El fragmentador PHP DEBE usar una estrategia heurística de bloques funcionales: detectar `function nombre()`, bloques `case` dentro de `switch`, y bloques `<?php ?>` significativos como unidades de fragmentación independientes. Archivos sin ninguno de estos delimitadores se fragmentan por tamaño con solapamiento de contexto.
- **FR-018**: El fragmentador PHP DEBE implementar la Regla del Preámbulo (Preamble Rule): capturar el bloque de código al inicio del archivo (antes del primer `switch`/`function`/bloque lógico principal) que contiene includes, asignaciones de variables críticas, y setup global. Este preámbulo se adjunta virtualmente o se referencia en el [ARCH_HEADER] de cada fragmento derivado del mismo archivo, garantizando que ninguna acción pierda el contexto de inicialización.
- **FR-019**: Cada fragmento generado desde un bloque `case` DEBE incluir en su ARCH_HEADER el campo `LEGACY_ACTION: nombre_del_case` para mantener siempre un mapeo arquitectónico entre el fragmento y la intención de negocio original. Si un `case` individual excede 500 líneas, se aplica sub-chunking por tamaño conservando el encabezado del case original como contexto.
- **FR-020**: El sistema DEBE crear prompt templates dedicados para PHP legacy (`system.php_legacy.context`, `system.php_legacy.doctrine`, `user.php_legacy.fragment`) que inyecten archivos maestros de doctrina (guía de modernización, patrones hexagonales, referencia Symfony) de la misma forma que los templates Python/HA inyectan la doctrina Home Assistant. Los templates DEBEN instruir al Teacher a actuar como experto en modernización empresarial PHP legacy → arquitectura hexagonal Symfony.
- **FR-021**: La respuesta del Teacher para fragmentos PHP DEBE seguir un esquema de 3 secciones obligatorias: (1) **DEBT_DIAGNOSTIC** — lista de firmas de deuda técnica detectadas y su impacto en mantenibilidad; (2) **MODERN_PROPOSAL** — definición de la Interfaz de Dominio (Port) y DTOs necesarios para reemplazar la lógica procedural con arquitectura hexagonal; (3) **MAPPING_LOGIC** — explicación de cómo transicionar del estado global detectado (`$GLOBALS`, `$_SESSION`, variables implícitas) al contexto inyectado de Symfony (Dependency Injection Container, Services).
- **FR-022**: Los templates PHP DEBEN recibir como contexto enriquecido: el contenido de [LEGACY_SIGNATURES], el campo `LEGACY_ACTION`, las `IMPLICIT_DEPS`, y el preámbulo del archivo, para que el Teacher tenga toda la información necesaria sobre la deuda técnica antes de generar su propuesta de modernización.
- **FR-023**: El sistema DEBE mantener un master file único de doctrina que defina la arquitectura hexagonal Symfony de destino: Ports (interfaces de dominio), Adapters (implementaciones de infraestructura), DTOs, Doctrine ORM como persistencia, Symfony DI Container como inyección de dependencias, y Event Dispatcher como bus de eventos. Este master se inyecta en el system prompt del Teacher para todos los fragmentos PHP, análogamente al master guide de Home Assistant para Python.
- **FR-024**: El sistema DEBE mantener snippets de plataforma por cada origen legacy (osCommerce, WordPress, ZenCart, Magento, CodeIgniter, Joomla, SuiteCRM, generic) que contengan Anti-Patterns Mapping completos. Cada snippet DEBE mapear no solo APIs de persistencia (`tep_db_query` → `Doctrine Repository`, `$wpdb->query` → `Doctrine QueryBuilder`) sino también anti-patrones de estado global (`global $customer_id` → `UserInterface`/`TokenStorage`, `$_SESSION['cart']` → `CartService` inyectado, `$_GET/$_POST` sin sanitizar → `Request` object con validación), patrones de modularidad (`include`/`require` chains → Service autowiring, `define()` constants → `.env` parameters), y patrones de seguridad (`mysql_query` con concat → parameterized queries, `echo $_GET` → Twig auto-escaping). El snippet de la plataforma detectada se inyecta junto al master en el prompt del Teacher.

### Key Entities

- **PhpFragment**: Fragmento de código PHP extraído. Atributos principales: contenido, archivo fuente, rango de líneas, tipo TIPO, categoría de plataforma (osCommerce/WordPress/ZenCart/generic).
- **LegacySignature**: Patrón de deuda técnica detectado. Atributos: categoría semántica (PERSISTENCE/STATE/MODULE_LINK/SECURITY_SMELL/CONSTANT_DEF/MODERN_REFERENCE), texto del match, número de línea, regex que lo detectó, y clasificación de estilo del archivo (legacy_pure/legacy_modern/hybrid).
- **IncludeGraph**: Grafo dirigido de dependencias entre archivos dentro de un repositorio. Nodos = archivos PHP, arcos = relaciones include/require. Permite identificar hubs (archivos incluidos por muchos) y hojas.
- **PlatformProfile**: Colección de patrones regex específicos de una plataforma. Incluye marcadores de detección automática y patrones idiomáticos propios.
- **ImplicitDependency**: Variable usada en un fragmento sin asignación local. Atributos: nombre de variable, línea de primera aparición, frecuencia de uso en el fragmento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El extractor procesa archivos PHP de 2000+ líneas en menos de 5 segundos por archivo, de forma síncrona.
- **SC-002**: Los bundles generados son parseables por `parse_bundle()` de Stage 2 sin errores — el 100% de los bundles emitidos pasan validación.
- **SC-003**: Los fragmentos generados tienen un tamaño máximo compatible con la ventana de contexto del modelo (verificable contra el límite configurado).
- **SC-004**: La detección de categorías semánticas tiene una precisión ≥95% sobre los archivos de test representativos (3 archivos: uno osCommerce, uno WordPress, uno ZenCart).
- **SC-005**: El grafo de dependencias include/require reconstruido cubre ≥90% de las relaciones reales verificables manualmente en los repositorios de test.
- **SC-009**: Las respuestas del Teacher para fragmentos PHP siguen el esquema de 3 secciones (DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC) en ≥90% de las muestras generadas, validable por parsing estructural del output.
- **SC-006**: En archivos con PHP mezclado con HTML/JavaScript, el driver extrae ≥95% de las firmas de lógica de negocio (funciones, queries, globals) sin incluir markup en los fragmentos emitidos.
- **SC-007**: El driver soporta los 7 repositorios de `data/raw/multi_legacy/` (osCommerce, WordPress, ZenCart, OpenMage, PrestaShop, CodeIgniter, SalesAgility) sin errores fatales — los archivos problemáticos se registran en `needs_manual_review.json`.
- **SC-008**: Los tests unitarios e integración cubren ≥90% del código del driver, con al menos 3 fixtures representativos (uno por plataforma principal).

## Assumptions

- Los repositorios PHP legacy están previamente clonados en `data/raw/multi_legacy/` y son accesibles localmente.
- El protocolo `ExtractorAdapter` existente es suficientemente flexible para acomodar un driver regex-based sin modificar la interfaz.
- Los archivos PHP legacy usan encoding UTF-8 o latin-1 (ISO-8859-1); otros encodings se consideran edge cases.
- Las constantes de ruta (`DIR_WS_INCLUDES`, `DIR_FS_CATALOG`, etc.) se resuelven best-effort — las que no puedan resolverse se marcan como UNRESOLVED.
- El parser de Stage 2 (`parse_bundle()` y `get_v2_fragments()`) será actualizado con cambios mínimos para soportar secciones extensibles y routing por extensión de archivo. Estos cambios son retrocompatibles con los bundles Python existentes.
- El chunking de archivos grandes sigue la misma estrategia de tamaño máximo definida en la configuración del processor existente.

## Scope Boundaries

**Incluido en el MVP**:
- Extracción regex de fragmentos PHP de las 7 plataformas en multi_legacy
- Clasificación semántica en 6 categorías (PERSISTENCE, STATE, MODULE_LINK, SECURITY_SMELL, CONSTANT_DEF, MODERN_REFERENCE)
- Sección [LEGACY_SIGNATURES] en los bundles, reconocida y capturada por Stage 2
- Detección de IMPLICIT_DEPS por análisis de variables
- Grafo de dependencias include/require a nivel de repositorio
- Auto-detección de plataforma
- Separación de PHP vs HTML/JS en archivos mixtos
- Distinción Legacy Puro vs Legacy Modernizado vs Hybrid para código PHP con OOP parcial
- Fragmentación heurística por bloques funcionales con Preamble Rule y LEGACY_ACTION
- Refactor mínimo de Stage 2: extensión del parser para secciones genéricas y routing por extensión de archivo
- Prompt templates PHP dedicados con inyección de doctrina y output 3-secciones (DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC) orientados a modernización Symfony hexagonal
- Master file de doctrina Symfony hexagonal + snippets de plataforma con Anti-Patterns Mapping completos
- Tests con fixtures de osCommerce, WordPress, y ZenCart

**Excluido del MVP**:
- Parsing AST de PHP (nikic/php-parser o similar) — se usa exclusivamente regex
- Transformación o modernización automática del código PHP (el Teacher propone, no ejecuta)
- Ejecución del código PHP o resolución dinámica de includes en runtime
- Integración con Stage 3 (curation) o Stage 4 (training) — el scope termina en la generación de bundles y prompts compatibles con Stage 2
