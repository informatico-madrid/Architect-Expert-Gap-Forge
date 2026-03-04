## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.

1) Missing package initializers
    - Affected paths: `src/discovery/`, `src/factory/`, `src/curation/` — each contains Python modules but no `__init__.py` file.
    - Impact: Import-time package resolution can fail in some import modes; contravenes §5.5 of the Gold Standard.
    - Remediation: Add `__init__.py` to each folder and export a minimal `__all__` list for public API symbols.

2) Mutable / non-frozen dataclasses
    - Examples: `src/curation/nemo_curator_suite.py::CurationStats`, `src/discovery/processor.py::Module` / `ModuleFile` are declared with `@dataclass` but not `frozen=True`.
    - Impact: Violates §2.2 (Immutability by default). Mutable records increase cognitive load and risk of subtle state bugs.
    - Remediation: Convert canonical records to `@dataclass(slots=True, frozen=True)` or `pydantic.BaseModel` with `ConfigDict(frozen=True)`, and keep explicit mutable builders where justified.

3) Unstructured `dict[str, Any]` usage
    - Widespread sites: `src/audit/*`, `src/factory/*`, `src/curation/*` (e.g., `model_evaluator`, `inference`, `production_v11`, `nemo_curator_suite`).
    - Impact: Runs counter to §2.1 (use `TypedDict` / dataclass for known schemas). Makes static analysis and refactoring harder.
    - Remediation: Introduce `TypedDict` types or small frozen dataclasses for canonical payloads (sample records, inference payload, audit report sections). Migrate incrementally with unit tests.

4) Monolith modules
    - Examples: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC).
    - Impact: Violates §3.1 guidance (modules should be small and single-responsibility). Hard to test and maintain.
    - Remediation: Split into smaller modules (sampling, baseline/adaptor inference, report generation, CLI wiring). Add typed interfaces for each submodule.

5) `src/merger/` is empty
    - Impact: README and some docs mention a merger; the folder exists but contains no implementation.
    - Remediation: Either add the intended implementation (`surgical_merge.py`) or remove the empty folder and update docs to avoid confusion.

6) Formatting tool mismatch in docs
    - `Makefile` and `README` recommend `ruff` for formatting; some docs and `AGENTS.md` historically referenced `black`.
    - Remediation: Declare canonical formatter in `pyproject.toml` and `requirements-dev.txt` (e.g., add `ruff` and optionally `black`), and add a `pre-commit` config if desired.

7) Secrets & CI behaviour
    - The repository uses `google-genai` optionally; `GOOGLE_API_KEY` controls whether the `GeminiClient` is used. CI intentionally leaves `GOOGLE_API_KEY` unset and uses local mocks/vLLM.
    - Remediation: Keep API keys out of source and document `AEGF_*` env var patterns in `configs/*.example`.

---

## ✅ Actionable Next Steps (recommended, small PRs)
- Add `__init__.py` to `src/discovery`, `src/factory`, `src/curation` with minimal `__all__` exports. (low friction)
- Replace canonical mutable dataclasses with `@dataclass(slots=True, frozen=True)` for records; provide small mutable builder classes where mutation is essential.
- Introduce a `src/audit/types.py` containing `TypedDict` definitions used by `model_evaluator` and `inference` (migrate incrementally).
- Split `production_v11.py` and `model_evaluator.py` into smaller modules and add focused unit tests for each piece.
- Decide whether `src/merger/` should be implemented or removed; update `README.md` accordingly.
- Add `ruff` to `requirements-dev.txt` (and `pyproject.toml` tool config) to make formatting reproducible.

---

If you want, I can:
- implement the easy fixes now (add `__init__.py` files + `__all__`),
- create a starter `TypedDict` file for `model_evaluator` payloads, and
- stage the changes for review.
