# Research — Stage 1 (Phase 0)

Fecha: 2026-03-08

Propósito: resolver las `NEEDS CLARIFICATION` del `spec.md` para permitir la implementación del refactor sin ambigüedades.

---

1) Canonical shape de `manual_module_mapping` (y overrides por repo)

- Decision: `manual_module_mapping` será un dict: `module_name -> list[str]` donde cada item es una ruta relativa o un glob (shell-style). Los `overrides` por repo usan la clave `"owner/repo": { strategy: manual_mapping, manual_module_mapping: { ... } }`.

- Rationale: formato simple, human-readable y fácil de versionar en YAML. Glob patterns permiten cubrir múltiples archivos sin listar cada uno.

- Alternatives considered:
  - Declarative JSON Schema con expresiones avanzadas (rechazado por complejidad innecesaria).
  - Tabla relacional externa (rechazado por overhead operativo).

- Example:
```yaml
manual_module_mapping:
  Billing:
    - 'src/Billing'
    - 'legacy/billing.php'
  User:
    - 'src/User/**/*.php'
overrides:
  'owner/repo-legacy':
    strategy: manual_mapping
    manual_module_mapping:
      LegacyMonolith: ['index.php', 'functions.php']
```

---

2) `master_docs_map.yaml` format (perfil -> required files)

- Decision: `master_docs_map.yaml` será un mapping: `profile -> { required: [paths], optional: [paths] }`. `production_v11.load_master_docs(gap_dir, profile)` levantará `required` y fallará si falta cualquiera; `optional` se carga si existe.

- Rationale: permite perfiles con conjuntos obligatorios y complementarios; implementable con simple YAML parsing.

- Alternatives considered:
  - Un solo listado (todos obligatorios) — insuficiente para perfiles que sólo necesitan un subset.

- Example:
```yaml
homeassistant:
  required:
    - 'home_assistant/architecture.md'
    - 'home_assistant/guidelines.md'
  optional:
    - 'home_assistant/legacy_notes.md'
php_hexagonal:
  required:
    - 'php/hexagonal_principles.md'
    - 'php/solid.md'
```

---

3) `ExtractorAdapter` API contract

- Decision: definir una interfaz (Protocol) mínima en `src/utils/extractors/base.py`:

```py
class Dependency(TypedDict):
    name: str
    type: Literal['import','require','use']
    target: str  # normalized module/path

class ParseResult(BaseModel):
    file_path: str
    dependencies: list[Dependency]
    ast: Optional[Any] = None  # adapter-specific parsed tree
    raw_text: Optional[str] = None

class ParseError(Exception):
    file_path: str
    line: Optional[int]
    error: str
    diagnosis: Optional[str]
    fix_hint: Optional[str]

class ExtractorAdapter(Protocol):
    def parse_file(self, path: Path) -> ParseResult: ...
    def extract_dependencies(self, path: Path) -> list[Dependency]: ...
```

- Rationale: small, language-agnostic surface. `ast` field is adapter-specific to allow tree-sitter or language ASTs without imposing a common AST shape.

- Alternatives considered:
  - Full AST normalization across languages (rejected — high cost and little benefit for Stage 1).

---

4) `ParseError` shape and default policy

- Decision: `ParseError` será una excepción estructurada con campos: `file_path`, `line`, `error`, `diagnosis`, `fix_hint`.

- Default runtime policy: `on_parse_error: abort` (marcar archivo `needs_manual_review` + abort repo). This is recorded in `spec.md` and implemented as default in `ProcessingConfig`. `profile` may override `on_parse_error` to `skip` or `mark_and_continue`.

- Rationale: evita ingestiones silenciosas y da trazabilidad.

- Alternatives considered:
  - Default `mark_and_continue` (rejected — risk of corrupting outputs).

---

5) Tree-sitter vs `python.ast` now or later

- Decision: Implement `python_ast_adapter` now (re-using current `ast.parse()` behaviour) to minimize risk. Design `ExtractorAdapter` so `tree-sitter` adapter can be added later behind the same interface and loaded lazily.

- Rationale: Lower risk and faster delivery. Tree-sitter will be added as optional adapter in a follow-up PR.

- Alternatives considered:
  - Immediate tree-sitter adoption (rejected due to increased dependencies and integration effort; prefer incremental approach).

---

Conclusión: Las decisiones anteriores permiten implementar el refactor sin bloqueos técnicos importantes. Paso siguiente: generar `research.md` (este archivo) y arrancar Phase 1 (data-model, contracts, quickstart) y la implementación del adapter minimal.
