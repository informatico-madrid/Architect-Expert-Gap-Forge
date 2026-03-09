# Implementation Plan: Stage 1 — Refactor (brownfield)

**Branch**: `001-stage1-discovery` | **Date**: 2026-03-08 | **Spec**: [specs/001-stage1-discovery/spec.md](spec.md)
**Input**: Refactor existing Stage 1 code (`src/discovery/ingestor.py`, `src/discovery/processor.py`, `src/factory/production_v11.py`) to introduce a pluggable `ExtractorAdapter` and profile-driven module mapping without breaking current behavior.

## Summary

Refactor (brownfield) of Stage 1 to decouple language parsing from the `processor` core:

- Extract parsing logic into a new `ExtractorAdapter` interface under `src/utils/extractors/` and provide a minimal `python_ast_adapter` implementation that preserves current behavior.
- Introduce `ParseError` structured exception and enforce default policy (mark file `needs_manual_review` + abort repo) while making action configurable via `profile.on_parse_error`.
- Make module discovery strategies (`manifest|directory|manual_mapping`) configurable per `profile` and support per-repo `overrides`.
- Update `production_v11.load_master_docs(gap_dir, profile)` to accept `profile` and load `master_docs_map.yaml`.

This refactor removes any silent parser fallback: the default `FR-006` behavior is to abort on `ParseError`. All tests and consumers that depended on previous fallback behavior must be audited and migrated before implementing adapter changes (see task T031).

## Technical Context

**Language/Version**: Python 3.12 (existing repo uses 3.12+)  
**Primary Dependencies**: PyYAML, pydantic, requests, pytest, ruff. Optional: `tree-sitter` (for future adapters).  
**Storage**: Local filesystem (data/raw/, data/Gap/, outputs/).  
**Testing**: `pytest` for unit/integration tests; new tests added under `tests/unit` and `tests/integration`.  
**Target Platform**: Linux servers (CI: ubuntu-latest).  
**Project Type**: CLI + library (existing code invoked as scripts and imported by pipeline).  
**Performance Goals**: Maintain current processing throughput; refactor must not add significant parse-time overhead.  
**Constraints**: Strict typing, no import-time side effects, CI coverage thresholds (see constitution).  
**Scale/Scope**: Process repos of up to ~1M LOC; changes must be resilient to vendor directories and large repos.

## Constitution Check

GATE: All proposed changes MUST comply with the repository constitution before Phase 0 research proceeds. The following checks are applied and will be re-evaluated after Phase 1 design.

- Strict typing: New modules will include type annotations and `pydantic` models where appropriate (e.g., `ParseError`, `ParseResult`, `Dependency` TypedDict). Action: add typing to new files and update `pyproject` only if needed.
- No import-time side-effects: Adapters must be instantiated via factory functions (lazy import) — do not import heavy parsers at module import time. Action: implement `get_adapter(profile)` factory in `src/utils/extractors/factory.py` using runtime imports.
- Logging: follow `logger = logging.getLogger(__name__)` and lazy formatting. Action: ensure new modules use existing logging conventions.
- Tests & coverage: add unit tests for `python_ast_adapter` and integration tests for `processor` with `homeassistant` profile. Action: add tests and run `pytest` locally before requesting merge.
- Headers & CI: new Python files must include required project header; run `scripts/check_headers.py --check` locally as part of CI checklist.

If any gate cannot be satisfied (e.g., a dependency forces import-time I/O), the plan will stop and the issue will be escalated with a mitigation proposal.

## Project Structure (selected)

This is a single Python project. Changes will be localized as follows:

``text
src/
├── discovery/
│   ├── ingestor.py            # existing
│   └── processor.py           # refactor to call adapter
├── factory/
│   └── production_v11.py      # update load_master_docs signature
├── utils/
│   └── extractors/
│       ├── __init__.py
│       ├── factory.py         # adapter factory (lazy)
│       ├── base.py            # ExtractorAdapter interface, ParseError, types
       └── python_ast_adapter.py # minimal adapter preserving current ast behavior
tests/
├── unit/
│   └── test_python_ast_adapter.py
└── integration/
    └── test_processor_profiles.py

configs/
├── stage_1_discovery/
│   ├── examples/              # new/updated profile examples
│   └── master_docs_map.yaml   # maps profiles -> required master docs
```

**Structure Decision**: Keep code colocated under `src/` and add `src/utils/extractors/` for cross-cutting adapters. The `processor` will depend only on the `base` adapter API and the lazy `factory.get_adapter()`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Import-time lazy-loading requirement | Needed to integrate optional heavy parsers (tree-sitter) without import-time I/O | Importing parser at module top-level would violate constitution (no import-time side-effects). Using factory/lazy import avoids the violation.

## Phase 0 — Research & Clarifications (deliverable: `research.md`)

Goals:

- Resolve any remaining `NEEDS CLARIFICATION` items from the spec (notably: canonical shape of `manual_module_mapping` overrides, exact set of master docs per profile, and adapter API contract). Note: `ParseError` policy has been decided (mark + abort) and documented in the spec.
- Produce `research.md` with decisions, rationale and alternatives for: adapter API, parse-result schema, master_docs_map format, and whether to include a `tree-sitter` optional adapter now or later.

Success Criteria:

- `research.md` resolves unknowns and lists concrete API signatures.

Tasks (Phase 0):

1. Enumerate any `NEEDS CLARIFICATION` in `spec.md` and produce research tasks.
2. Decide adapter API: `class ExtractorAdapter(Protocol)` with `parse_file(path: Path) -> ParseResult` and `extract_dependencies(path: Path) -> List[Dependency]`.
3. Produce `research.md` under `specs/001-stage1-discovery/`.

## Phase 1 — Design & Contracts (deliverables: `data-model.md`, `contracts/`, `quickstart.md`)

Goals:

- Define the adapter interface and types (`ParseResult`, `Dependency`, `ParseError`).
- Define config schema for `profile` including `module_heuristics`, `on_parse_error`, and `overrides`.
- Produce `data-model.md` listing entities and validation rules.

Tasks (Phase 1):

1. Write `data-model.md` with entities: `Profile`, `ManualModuleMapping`, `ParseError` and `LogicalEntity` bundle header.
2. Create `contracts/adapter.md` describing the `ExtractorAdapter` interface and examples.
3. Add `quickstart.md` showing how to run `ingestor` and `processor` with `--profile` and how to change `on_parse_error`.
4. Run `.specify/scripts/bash/update-agent-context.sh copilot` to update agent context files (as required by IMPL_PLAN). (Will run after design files are created.)

## Phase 2 — Implementation (deliverables: code changes, tests)

Goals:

- Implement `src/utils/extractors/*`, add `ParseError` class, refactor `processor.py` to use adapter factory, and update `production_v11.load_master_docs`.

Tasks (Phase 2):

1. Add `src/utils/extractors/base.py` (types + `ExtractorAdapter` Protocol + `ParseError`).
2. Add `src/utils/extractors/python_ast_adapter.py` porting existing `ast` logic from `processor._extract_local_imports` into adapter methods, preserving behaviour and tests.
3. Add `src/utils/extractors/factory.py` with `get_adapter(profile: str) -> ExtractorAdapter` performing lazy imports.
4. Modify `src/discovery/processor.py`:
   - Replace direct `ast.parse()` usage with calls to `adapter.parse_file()` / `adapter.extract_dependencies()`.
   - Read `profile` from `ProcessingConfig` and call `factory.get_adapter(profile)`.
   - Implement `on_parse_error` handling: default abort behavior (mark repo + raise) and configurable alternatives.
5. Update `src/factory/production_v11.py` to accept `profile` param in `load_master_docs` and read `configs/stage_1_discovery/master_docs_map.yaml`.
6. Add config examples in `configs/stage_1_discovery/examples/` and `master_docs_map.yaml`.
7. Add unit and integration tests and run `pytest` locally.

## Rollout & Validation

1. Run unit tests and integration tests locally; ensure `ruff` formatting and `scripts/check_headers.py --check` pass.
2. Produce `research.md`, `data-model.md` and design artifacts under `specs/001-stage1-discovery/`.
3. Execute the T031 audit to produce `specs/001-stage1-discovery/ast_fallback_audit.json` and review the list of tests that depend on legacy fallback behavior; migrate those tests to the `ParseError`-first model before implementing adapter changes.
4. Run performance benchmarks (task T032) to capture baseline throughput and latency for comparison after the refactor.
5. Create a draft PR for review. Per repository governance this PR should include design docs, tests, benchmark results, and the migration plan derived from T031.

## Stop & Report

Stop after Phase 2 planning and report back with:

- Branch name: `001-stage1-discovery`
- `plan.md` path: `specs/001-stage1-discovery/plan.md`
- Generated artifacts: `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (to be created in Phase 0/1)

---

*This plan is a brownfield refactor plan. All changes are designed to preserve current behaviour while extracting parsing into adapters and adding profile-driven configuration. Next step: run Phase 0 tasks and generate `research.md`.*
