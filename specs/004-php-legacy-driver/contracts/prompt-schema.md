# Contract: PHP Teacher Prompt Output Schema

**Feature**: 004-php-legacy-driver | **Date**: 2026-03-12

## Overview

Schema de output que el Teacher (Gemini) debe producir al procesar fragmentos PHP legacy. Define las 3 secciones obligatorias y su contenido esperado.

## Output Schema

```text
[DEBT_DIAGNOSTIC]
<Análisis del deuda técnica del fragmento legacy>

[MODERN_PROPOSAL]
<Código Symfony/hexagonal equivalente>

[MAPPING_LOGIC]
<Mapeo elemento-por-elemento de legacy → moderno>
```

## Section Specifications

### [DEBT_DIAGNOSTIC]

**Propósito**: Identificar y catalogar los problemas del código legacy.

**Contenido esperado**:
- Clasificación de anti-patterns encontrados (referencia a LEGACY_SIGNATURES del bundle)
- Impacto de seguridad (SQL injection, XSS, etc.)
- Problemas de mantenibilidad (acoplamiento, globals, etc.)
- Violations de SOLID/Clean Architecture
- Severidad general: CRITICAL / HIGH / MEDIUM / LOW

**Formato**:
```text
[DEBT_DIAGNOSTIC]
SEVERITY: HIGH
ANTI_PATTERNS:
  - direct_sql_concat: SQL injection risk via string concatenation in tep_db_query()
  - global_state: 3 global variables used ($languages_id, $currencies, $messageStack)
  - mixed_concerns: Database access + HTML rendering in same function
SECURITY:
  - SQL injection: unparameterized query at line 15
  - XSS: unescaped output at line 28
MAINTAINABILITY:
  - Coupling: direct DB access without abstraction layer
  - No error handling on database operations
```

### [MODERN_PROPOSAL]

**Propósito**: Código Symfony hexagonal equivalente funcional.

**Contenido esperado**:
- Clase(s) PHP moderna(s) con namespaces PSR-4
- Inyección de dependencias via constructor
- Repository pattern para acceso a datos
- Type hints estrictos (PHP 8.1+)
- Arquitectura hexagonal: Domain / Application / Infrastructure layers

**Formato**:
```php
[MODERN_PROPOSAL]
// Domain Layer
namespace App\Domain\Catalog\Entity;

final class Category
{
    public function __construct(
        private readonly int $id,
        private readonly string $name,
        private readonly ?int $parentId = null,
    ) {}

    // ... getters
}

// Application Layer
namespace App\Application\Catalog\Query;

final class GetCategoryTreeHandler
{
    public function __construct(
        private readonly CategoryRepositoryInterface $categoryRepo,
    ) {}

    public function __invoke(GetCategoryTreeQuery $query): array
    {
        return $this->categoryRepo->findTreeByParent($query->parentId);
    }
}

// Infrastructure Layer
namespace App\Infrastructure\Persistence\Doctrine;

final class DoctrineCategoryRepository implements CategoryRepositoryInterface
{
    public function findTreeByParent(?int $parentId): array
    {
        return $this->createQueryBuilder('c')
            ->where('c.parentId = :parentId')
            ->setParameter('parentId', $parentId)
            ->orderBy('c.sortOrder', 'ASC')
            ->getQuery()
            ->getResult();
    }
}
```

### [MAPPING_LOGIC]

**Propósito**: Correspondencia elemento-por-elemento entre legacy y moderno.

**Contenido esperado**:
- Cada constructo legacy → su equivalente moderno
- Cambios de responsabilidad (quién hace qué)
- Migraciones de estado (globals → DI, direct SQL → Repository)
- Transformaciones de tipo (array loosely typed → typed entities)

**Formato**:
```text
[MAPPING_LOGIC]
ELEMENT_MAP:
  tep_db_query("SELECT...") → DoctrineCategoryRepository::findTreeByParent()
  global $languages_id → LanguageContext::getCurrentLanguageId() (injected)
  tep_db_fetch_array($query) → Doctrine getResult() + Category entity mapping
  $categories_query (raw SQL string) → QueryBuilder with parameterized query
  function tep_get_category_tree() → GetCategoryTreeHandler::__invoke()
  require('application_top.php') → Symfony kernel auto-wiring
RESPONSIBILITY_SHIFT:
  - DB access: function body → Infrastructure Repository
  - Input sanitation: (int) cast → Symfony ParamConverter + type declaration
  - Output: direct array return → DTO/ViewModel transformation
PATTERN_MIGRATION:
  - Procedural function → CQRS Query Handler
  - Global variable → Constructor injection
  - Direct SQL → Doctrine QueryBuilder
```

## Validation Rules

1. Output MUST contain all 3 sections in order: DEBT_DIAGNOSTIC, MODERN_PROPOSAL, MAPPING_LOGIC
2. MODERN_PROPOSAL MUST contain valid PHP 8.1+ syntax
3. MAPPING_LOGIC MUST reference specific elements from the input fragment
4. DEBT_DIAGNOSTIC MUST include SEVERITY classification
5. Sections are delimited by `[SECTION_NAME]` markers (same regex as bundle parser)

### Strict Structured Format Rule

**DEBT_DIAGNOSTIC and MAPPING_LOGIC MUST use YAML key-value format — not free prose.**

Free prose inside diagnostic sections is the leading cause of Stage 3 automation failure. The Teacher is instructed to use the following literal structure with no deviations:

- `DEBT_DIAGNOSTIC`: Top-level keys `SEVERITY`, `ANTI_PATTERNS`, `SECURITY`, `MAINTAINABILITY`. Each value is a YAML list. No narrative paragraphs.
- `MAPPING_LOGIC`: Top-level keys `ELEMENT_MAP`, `RESPONSIBILITY_SHIFT`, `PATTERN_MIGRATION`. Each entry is a YAML mapping or list.
- `MODERN_PROPOSAL`: Free-form PHP code block only — no YAML, no prose outside of code comments.

**Invalid** (will fail SC-009 Level 2 validation):
```text
[DEBT_DIAGNOSTIC]
This code has several issues. The main problem is that it uses direct SQL...
```

**Valid**:
```yaml
[DEBT_DIAGNOSTIC]
SEVERITY: HIGH
ANTI_PATTERNS:
  - direct_sql_concat: SQL injection risk in tep_db_query() at line 15
SECURITY:
  - SQL injection: unparameterized query concatenates $parent_id
MAINTAINABILITY:
  - No abstraction layer between controller and database
```

The `system.php_legacy.nominal_suffix` template MUST include an explicit instruction:

```
IMPORTANT: DEBT_DIAGNOSTIC and MAPPING_LOGIC must use strict YAML key-value
format. Do NOT write prose paragraphs. Use list items under each key.
```

## Validation Judge (SC-009)

SC-009 requires ≥90% of Teacher outputs to follow this 3-section YAML schema. Validation uses two levels:

**Level 1 — Structural regex** (applied to 100% of output):
```python
_SECTION_RE = re.compile(
    r'\[DEBT_DIAGNOSTIC\].*?\[MODERN_PROPOSAL\].*?\[MAPPING_LOGIC\]',
    re.DOTALL,
)
```
Pass/fail per output record.

**Level 2 — Validation Judge** (applied to random 10% sample):
A short prompt sent to the local vLLM instance (7B model, <500ms latency):

```
System: You are a strict validator. Answer only YES or NO.
User: Does the following text contain all three sections [DEBT_DIAGNOSTIC],
      [MODERN_PROPOSAL], and [MAPPING_LOGIC], where DEBT_DIAGNOSTIC and
      MAPPING_LOGIC use YAML key-value format (not free prose)? YES or NO:
<teacher_output_here>
```

If Level 2 pass rate < 90% on the sample, the pipeline logs a `WARNING: SC-009 degradation detected` and halts Stage 2 output for that batch.

## Integration with Stage 2

El Teacher output se parsea por Stage 2 para generar pares de entrenamiento:
- **Input**: Fragmento legacy PHP (del bundle), enriquecido con `${legacy_signatures}`, `${preamble}` (vía `PREAMBLE_REF`), `${platform}`
- **Output**: Las 3 secciones concatenadas

El prompt template (`system.php_legacy.nominal_suffix`) instruye al Teacher a producir este formato exacto. El parseo del output reutiliza el generic section parser de `parse_bundle()`.
