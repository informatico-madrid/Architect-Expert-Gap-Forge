# Contract: ExtractorAdapter

Location: `src/utils/extractors/base.py` (interface) and `src/utils/extractors/factory.py` (lazy instantiation)

## Purpose

Definir la API mínima que el `processor` usa para parsear archivos y extraer dependencias, sin imponer una forma AST única.

## Interface (Python sketch)

```py
from typing import Protocol, TypedDict, List, Optional
from pathlib import Path

class Dependency(TypedDict):
    name: str
    type: str  # 'import' | 'require' | 'use'
    target: str

class ParseResult(BaseModel):
    file_path: str
    dependencies: List[Dependency]
    ast: Optional[Any] = None
    raw_text: Optional[str] = None

class ParseError(Exception):
    file_path: str
    line: Optional[int]
    error: str
    diagnosis: Optional[str]
    fix_hint: Optional[str]

class ExtractorAdapter(Protocol):
    def parse_file(self, path: Path) -> ParseResult: ...
    def extract_dependencies(self, path: Path) -> List[Dependency]: ...
```

## Behavioural contracts

- `parse_file` must raise `ParseError` on parse failures.
- `extract_dependencies` may call `parse_file` or parse incrementally; result should be stable and idempotent.
- Implementations MUST NOT perform network I/O at import time; heavy parsers must be imported lazily inside factory.

## Example adapter: python_ast_adapter

- `parse_file` uses `ast.parse()` to obtain imports and returns a `ParseResult` with `dependencies` containing entries of type `import` and normalized `target` values.
- On `SyntaxError` or `ValueError` the adapter raises `ParseError` with `diagnosis` describing probable cause and `fix_hint` recommending `python -m pyflakes` or similar.

## Example JSON schema for ParseResult (for logs)

```json
{
  "file_path": "src/foo/bar.py",
  "dependencies": [
    {"name":"os","type":"import","target":"os"}
  ],
  "ast": null,
  "raw_text": null
}
```

## Versioning & Compatibility

- This contract is v1 for the refactor. Future adapters (tree-sitter) must implement the same surface; `ast` is adapter-specific.

## Adapter identifiers & factory contract

- **Canonical adapter identifiers (v1):**
  - `python_ast` — builtin Python `ast`-based adapter (recommended for `homeassistant`).
  - `tree_sitter` — generic tree-sitter backed adapter (language-specific grammars required).
  - `php_native` — PHP parsing adapter (native/externally provided parser).
  - `generic_regex` — best-effort regex-based extractor (fallback for tiny profiles; use only for simple heuristics).

Adapters MUST expose their identifier (string) and implement the `ExtractorAdapter` surface.

### Factory contract (`get_adapter`)

The adapter factory lives in `src/utils/extractors/factory.py` and exposes the function:

```py
def get_adapter(profile: str) -> ExtractorAdapter:
    """Resolve an `ExtractorAdapter` for a given `profile`.

    Resolution strategy (v1):
      1. Read mapping in `configs/stage_1_discovery/profile_adapters.yaml` if present.
      2. Fall back to an internal mapping table: e.g. {'homeassistant': 'python_ast', 'php_hexagonal': 'php_native'}.
      3. Lazy-import the adapter implementation from `src.utils.extractors.<identifier>_adapter`.

    The function MUST perform lazy imports (no heavy imports at module import time) and raise `RuntimeError` with a clear message if no adapter is found.
    """

```

## Testing guidance

- Unit tests must feed representative files and verify `dependencies` and raised `ParseError` shape.
- Integration tests should confirm `processor` uses adapter outputs to populate `DEPENDENCIES` in bundles.
