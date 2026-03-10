# Data Model — Stage 1

Este documento define las entidades y validaciones usadas por el refactor.

## Entities

1. Profile

- Fields:
  - `profile: str` (p.ej. `homeassistant`, `php_hexagonal`) — required
  - `extensions: list[str]` — file extensions to consider
  - `ignored_paths: list[str]` — directories/globs to ignore
  - `module_heuristics: dict` — see below
  - `master_docs_map: dict` — populated from `configs/stage_1_discovery/master_docs_map.yaml` (mapping: `profile -> { required: [paths], optional: [paths] }`)
  - `extractor_adapter: str` — adapter key used by factory
  - `on_parse_error: Literal['abort','skip','fallback']` — runtime policy

- Validation rules:
  - `profile` must be non-empty; `extensions` must contain at least one extension.
  - `on_parse_error` defaults to `abort` if omitted.

2. ManualModuleMapping

- Shape: `Dict[str, List[str]]` mapping `module_name -> [path_or_glob]`.
- Semantics: when `strategy == manual_mapping`, the mapping is authoritative for grouping.

3. ParseError

- Pydantic model / dataclass fields:
  - `file_path: str`
  - `line: Optional[int]`
  - `error: str` (original exception message)
  - `diagnosis: Optional[str]` (short analysis)
  - `fix_hint: Optional[str]` (what operator can try)
  - `adapter: Optional[str]` (identifier of the adapter that raised the error)

4. Dependency

- TypedDict fields:
  - `name: str`
  - `type: Literal['import','require','use']`
  - `target: str` (normalized module or path)

5. ParseResult

- Pydantic model fields:
  - `file_path: str`
  - `dependencies: List[Dependency]`
  - `ast: Optional[Any]`  # adapter-specific
  - `raw_text: Optional[str]`

6. Logical Entity (bundle `.txt` header)

- Required ARCH_HEADER keys (FR-007):
  - `MODULE` — bounded context name
  - `REPO_PREFIX` — e.g. `owner/repo`
  - `FILE_ROLE` — e.g. `controller`, `schema`, `utility`
  - `FRAGMENT_TYPE` — `TIPO 1|TIPO 3|TIPO 4|TIPO 5`
  - `DEPENDENCIES` — normalized list of `target`s
  - `NEIGHBORS` — related modules/files

- Validation: header must be present; `DEPENDENCIES` may be empty but must be an array.

## Config snippets

`ProcessingConfig` (pydantic) excerpt:

```py
class ProcessingConfig(BaseModel):
    profile: str
    base_dir: Path
    raw_subdir: str = 'raw'
    output_subdir: str = 'outputs'
    module_heuristics: dict
    on_parse_error: Literal['abort','skip','fallback'] = 'abort'
    overrides: Dict[str, Any] = {}
```

## Notes

- All models must be annotated and immutable where appropriate.
- Keep the adapter `ast` field intentionally untyped to allow adapter-specific ASTs.
