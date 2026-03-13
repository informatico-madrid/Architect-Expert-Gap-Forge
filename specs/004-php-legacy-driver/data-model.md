# Data Model: PHPLegacyDriver

**Feature**: 004-php-legacy-driver | **Date**: 2026-03-12

## Taxonomy

### LEGACY_ACTION — What the code *does* (business intent of the fragment)

Used in `PhpFragment.legacy_action` to classify the **functional intent** of the fragment:

| Value | Meaning |
|-------|---------|
| `DB_ACCESS` | Reads or writes persistent data (queries, ORM calls, file storage) |
| `ROUTING` | Dispatches user requests to handlers (switch on `$_GET['action']`, URL routing) |
| `AUTH_SESSION` | Manages authentication, sessions, user identity |
| `OUTPUT_RENDER` | Produces HTML/JSON/XML output (templates, `echo`, view rendering) |
| `FILE_IO` | File system operations (`fopen`, `file_get_contents`, uploads) |
| `BUSINESS_LOGIC` | Domain operations that don't fit the above (calculations, transforms, validations) |

### SIGNATURE_CATEGORY — What the code *has wrong* (technical debt smell)

Used in `LegacySignature.category` to classify the **technical debt pattern** detected. Values use explicit `_SMELL` / `_POLLUTION` / `_VULN` suffixes to prevent any confusion with the business-intent enum above:

| Value | Meaning | Drives |
|-------|---------|--------|
| `PERSISTENCE_SMELL` | Direct DB access: `mysql_query`, `tep_db_query`, `$wpdb->query` | DEBT_DIAGNOSTIC |
| `STATE_POLLUTION` | Global state leak: `global $var`, `$_SESSION`, `$_COOKIE`, `$GLOBALS` | DEBT_DIAGNOSTIC |
| `MODULE_LINK_SMELL` | Coupling via include/require chains | DEBT_DIAGNOSTIC |
| `SECURITY_VULN` | Injection vectors: SQL concat, `echo $_GET`, `eval()`, dynamic `include($var)` | DEBT_DIAGNOSTIC |
| `CONSTANT_POLLUTION` | Magic constants: `define()`, `DIR_WS_*`, inline config literals | DEBT_DIAGNOSTIC |
| `MODERN_HYBRID` | Hybrid OOP in procedural file: `namespace`, `use`, class with constructor DI | DEBT_DIAGNOSTIC |

**Key distinction** — a single match `tep_db_query("SELECT..." . $id)` produces:
- `PhpFragment.legacy_action = "DB_ACCESS"` — the fragment *does* database work → drives MODERN_PROPOSAL
- `LegacySignature(category="PERSISTENCE_SMELL")` + `LegacySignature(category="SECURITY_VULN")` — two simultaneous debt patterns → drive DEBT_DIAGNOSTIC

The two enums are **never mixed in the same field** and answer orthogonal questions.

## Entities

### PhpFragment

Unidad atómica de código PHP extraída por el fragmenter heurístico.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True, slots=True)
class PhpFragment:
    """Fragmento de código PHP extraído heurísticamente."""

    name: str                    # Nombre del fragmento (función/clase/preamble_N)
    fragment_type: str           # "function" | "class" | "switch_block" | "bootstrap"
                                 # | "mixed_html" | "catchall"
    source_file: Path            # Ruta del archivo fuente
    start_line: int              # Línea inicio (1-based)
    end_line: int                # Línea fin (1-based)
    raw_content: str             # Código fuente completo del fragmento
    legacy_action: str           # LEGACY_ACTION — business intent (see Taxonomy above)
    preamble_ref: str | None     # SHA-256 hex digest of the bootstrap fragment's raw_content
                                 # from the same source file; None for bootstrap fragments themselves
                                 # Stage 2 uses this hash to locate the preamble in blueprint cache
    dependencies: tuple[str, ...]          # Rutas de archivos include/require detectados
    platform_hints: tuple[str, ...]        # Patterns de plataforma encontrados
    file_style: str = "LEGACY_PURE"        # "LEGACY_PURE" | "LEGACY_MODERNIZED" | "HYBRID"
    implicit_deps: tuple[ImplicitDependency, ...] = field(default_factory=tuple)
    # ↑ Typed dependencies with confidence; populated by detect_implicit_deps()
    # ImplicitDependency from php_fragmenter (defined below)
    signatures: tuple[LegacySignature, ...] = field(default_factory=tuple)
    # ↑ Populated by scan_signatures() (Phase 4 / US2); LegacySignature from php_signatures
```

**Invariantes**:
- `start_line <= end_line`
- `fragment_type` ∈ `{"function", "class", "switch_block", "bootstrap", "mixed_html", "catchall"}`
- `legacy_action` ∈ `{"DB_ACCESS", "ROUTING", "AUTH_SESSION", "OUTPUT_RENDER", "FILE_IO", "BUSINESS_LOGIC"}`
- `file_style` ∈ `{"LEGACY_PURE", "LEGACY_MODERNIZED", "HYBRID"}`
- `dependencies` contains only include/require **file paths** (not variable names)
- `implicit_deps` contains `ImplicitDependency` instances (sorted by `target_symbol`); 80% heuristic — not exhaustive
- `fragment_type == "bootstrap"` implies `preamble_ref is None` (a preamble does not reference itself)
- `preamble_ref` when set is a 64-character lowercase hex string (SHA-256 of the bootstrap fragment's `raw_content`)
- Immutable (frozen dataclass, `slots=True`)

**Brace failure / parse-abort behavior**: When `FastBraceScanner` returns `-1` (unmatched brace — common in osCommerce files with braces embedded inside HTML conditionals), **no PhpFragment is created**. The fragmenter writes a compact record `{source_file, name, start_line, reason: "unmatched_brace"}` directly to `needs_manual_review.json` and continues to the next extractable block. This prevents syntactically invalid code from entering the training corpus.

### LegacySignature

Firma semántica de un anti-pattern de deuda técnica detectado en el código.

```python
@dataclass(frozen=True, slots=True)
class LegacySignature:
    """Firma de un anti-pattern de deuda técnica detectado."""

    pattern_name: str       # Nombre del patrón (e.g., "direct_sql_concat")
    category: str           # SIGNATURE_CATEGORY — technical debt smell (see Taxonomy above)
    matched_text: str       # Texto exacto matcheado por regex
    line_number: int        # Línea donde se encontró (1-based)
    severity: str           # "critical" | "warning" | "info"
    modern_equivalent: str  # Hint de modernización (e.g., "QueryBuilder")
```

**Invariantes**:
- `severity` ∈ `{"critical", "warning", "info"}`
- `category` ∈ `{"PERSISTENCE_SMELL", "STATE_POLLUTION", "MODULE_LINK_SMELL", "SECURITY_VULN", "CONSTANT_POLLUTION", "MODERN_HYBRID"}`
- A single fragment carries a list of `LegacySignature` instances; multiple categories are permitted on the same fragment
- Immutable (frozen dataclass)

### IncludeGraph

Grafo de dependencias entre archivos PHP vía `include`/`require`.

```python
@dataclass(frozen=True, slots=True)
class IncludeEdge:
    """Arista del grafo de includes."""

    source_file: str       # Archivo que hace el include
    target_file: str       # Archivo incluido
    include_type: str      # "include" | "require" | "include_once" | "require_once"
    line_number: int       # Línea del include statement

@dataclass(frozen=True, slots=True)
class IncludeGraph:
    """Grafo dirigido de dependencias include/require."""

    edges: tuple[IncludeEdge, ...]  # Aristas del grafo
    entry_points: tuple[str, ...]   # Archivos sin incoming edges (raíces)

    def neighbors(self, file: str) -> tuple[str, ...]:
        """Archivos directamente incluidos por `file`."""
        return tuple(e.target_file for e in self.edges if e.source_file == file)

    def reverse_neighbors(self, file: str) -> tuple[str, ...]:
        """Archivos que incluyen a `file`."""
        return tuple(e.source_file for e in self.edges if e.target_file == file)
```

**Invariantes**:
- Grafo dirigido, puede tener ciclos (PHP permite includes circulares con `_once`)
- `include_type` ∈ `{"include", "require", "include_once", "require_once"}`
- Immutable (frozen dataclass)

### PlatformProfile

Perfil de detección de plataforma PHP.

```python
from dataclasses import dataclass, field
from types import MappingProxyType

@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Perfil de detección y configuración para una plataforma PHP legacy."""

    name: str                              # "oscommerce" | "oscommerce_phoenix" | "wordpress" |
                                           # "zencart" | "openmage" | "prestashop" |
                                           # "codeigniter" | "suitecrm" | "generic_php"
    marker_files: tuple[str, ...]          # Archivos que identifican la plataforma
    marker_patterns: tuple[str, ...]       # Patterns regex en código fuente
    exclude_dirs: tuple[str, ...]          # Directorios a excluir del scan
    snippet_path: str                      # Ruta al snippet de anti-patterns
    signature_patterns: dict[str, str] = field(default_factory=dict)
    # ↑ Declared as dict for ergonomic construction; coerced to MappingProxyType in __post_init__

    def __post_init__(self) -> None:
        # Bypass frozen=True to swap the dict for an immutable MappingProxyType.
        # After this point the field is read-only — MappingProxyType raises TypeError on mutation.
        object.__setattr__(self, 'signature_patterns', MappingProxyType(self.signature_patterns))
```

**Invariantes**:
- `name` es lowercase, sin espacios
- `marker_files` son rutas relativas al root del repo
- `marker_patterns` son regex válidos
- `signature_patterns` es `MappingProxyType[str, str]` en runtime (immutable, raises `TypeError` on `__setitem__`)
- All regex values in `signature_patterns` must compile (`re.compile(v)` must not raise)
- Immutable (frozen dataclass — `MappingProxyType` closes the dict escape hatch)

**Platform registry** (canonical names):

| `name` | Source directory | Notes |
|--------|-----------------|-------|
| `oscommerce` | `multi_legacy/osCommerce/` | Classic procedural |
| `oscommerce_phoenix` | `multi_legacy/gburton/` | OSC fork, hybrid typing |
| `wordpress` | `multi_legacy/WordPress/` | Hook-based |
| `zencart` | `multi_legacy/zencart/` | OSC-derived |
| `openmage` | `multi_legacy/OpenMage/` | Magento 1 LTS (EAV, XML config) |
| `prestashop` | `multi_legacy/PrestaShop/`, `multi_legacy/PrestaShopCorp/` | Same profile, two repos |
| `codeigniter` | `multi_legacy/bcit-ci/` | MVC lite |
| `suitecrm` | `multi_legacy/salesagility/` | SugarCRM fork |
| `generic_php` | (fallback) | No platform markers found |

### ImplicitDependency

Dependencia implícita detectada en un fragmento (variable usada sin asignación local).

```python
@dataclass(frozen=True, slots=True)
class ImplicitDependency:
    """Variable implícita usada en un fragmento PHP sin asignación local."""

    target_symbol: str      # Variable referenciada (e.g., "$languages_id")
    dependency_type: str    # "global_var" | "constant" | "function_call" | "class_instantiation"
    confidence: float       # 0.0-1.0: 1.0 for known-set matches, 0.8 for frequency-scan matches
```

**Invariantes**:
- `0.0 <= confidence <= 1.0`
- `dependency_type` ∈ `{"global_var", "constant", "function_call", "class_instantiation"}`
- `target_symbol` starts with `$` for variables, no prefix for constants/functions
- Immutable (frozen dataclass)

## Entity Relationships

```text
PlatformProfile ──detects──▶ Repository (data/raw/multi_legacy/*)
     │
     ├── guides ──▶ PhpFragmenter (exclusions, patterns)
     │
     └── selects ──▶ Anti-Pattern Snippet (configs/doctrine/*)

PhpFragment ◀──produces── PhpFragmenter
     │
     ├── contains ──▶ LegacySignature (0..N per fragment)
     │
     └── references ──▶ ImplicitDependency (0..N per fragment)

IncludeGraph ◀──builds── IncludeGraphBuilder
     │
     └── provides ──▶ NEIGHBORS field in [ARCH_HEADER]

PhpFragment + LegacySignature + IncludeGraph
     │
     └── assembles ──▶ Bundle .txt ([ARCH_HEADER] + [MODULE_MAP] + [LEGACY_SIGNATURES])
            │
            └── consumed by ──▶ Stage 2 (src/factory/fragment_extractor.py + pipeline_runner.py)
```

## State Transitions

### Fragment Lifecycle

```text
Raw .php file
  │ [fragmenter: regex split]
  ▼
PhpFragment (fragment_type assigned)
  │ [signature engine: pattern matching]
  ▼
PhpFragment + LegacySignature[] (legacy_action + category assigned)
  │ [include graph: dependency resolution]
  ▼
PhpFragment enriched (dependencies + platform_hints filled)
  │ [bundle assembler: ARCH_HEADER generation]
  ▼
Bundle .txt section (ready for Stage 2)
```

### Platform Detection Flow

```text
Repository root
  │ [scan marker_files]
  ▼
Candidate profiles (0..N matches)
  │ [score by marker_patterns in sample files]
  ▼
Selected PlatformProfile (highest match count)
  │ [fallback: "generic_php" if no match]
  ▼
Active profile (used for fragmentation + prompt selection)
```

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| PhpFragment | raw_content | Non-empty, must contain at least one PHP token |
| PhpFragment | fragment_type | Must be in 6-value enum set: `{"function", "class", "switch_block", "bootstrap", "mixed_html", "catchall"}` |
| PhpFragment | legacy_action | Must be in 6-value LEGACY_ACTION set |
| PhpFragment | preamble_ref | If set, must be 64-char lowercase hex (SHA-256); must resolve to a `bootstrap` fragment for the same `source_file` |
| LegacySignature | category | Must be in 6-value SIGNATURE_CATEGORY set |
| LegacySignature | matched_text | Must be substring of parent fragment's raw_content |
| LegacySignature | line_number | Must be within parent fragment's [start_line, end_line] |
| IncludeEdge | target_file | Path normalized, no `..` traversal outside repo |
| PlatformProfile | marker_patterns | Must compile as valid regex |
| PlatformProfile | signature_patterns | All regex values must compile |
| ImplicitDependency | confidence | Float in [0.0, 1.0] |
