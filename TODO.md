## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.


1) Mutable / non-frozen dataclasses — RESOLVED
    - Examples: `src/curation/nemo_curator_suite.py::CurationStats`, `src/discovery/processor.py::Module` / `ModuleFile` were flagged.
    - Changes made:
        - `Module` is now an immutable canonical record: converted to `@dataclass(slots=True, frozen=True)` with `files` and `neighbors` stored as tuples. Construction was adapted to build the file list and manifest before creating the frozen `Module` instance.
        - `ModuleFile` remains a mutable `@dataclass` because the processing pipeline populates/updates file `content` and roles during emission; keeping it mutable preserves the existing procedural flow without widespread refactors.
        - `CurationStats` remains mutable (not converted to frozen) because it functions as an in-place accumulator across multiple pipeline phases. This design choice is intentional and considered acceptable; if we later decide to migrate it to an immutable/builder pattern, it will be done as a separate, low-risk refactor.
    - Rationale: Applied immutability to the canonical module record where safe, and preserved mutation where it is essential to pipeline behavior. This follows the remediation guidance to "keep explicit mutable builders where justified."
    - Test status: All tests pass (263 passed) and coverage 95.73% (>= 90%). The processor smoke-test also ran successfully and generated expected `.txt` bundles.
    - Next steps (optional):
        - Introduce a `CurationStatsBuilder` or switch `CurationStats` to an immutable model with explicit functional update helpers, then migrate incrementally (low-risk PRs).

2) Unstructured `dict[str, Any]` usage
    - Widespread sites: `src/audit/*`, `src/factory/*`, `src/curation/*` (e.g., `model_evaluator`, `inference`, `production_v11`, `nemo_curator_suite`).
    - Impact: Runs counter to §2.1 (use `TypedDict` / dataclass for known schemas). Makes static analysis and refactoring harder.
    - Remediation: Introduce `TypedDict` types or small frozen dataclasses for canonical payloads (sample records, inference payload, audit report sections). Migrate incrementally with unit tests.

3) Monolith modules
    - Examples: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC).
    - Impact: Violates §3.1 guidance (modules should be small and single-responsibility). Hard to test and maintain.
    - Remediation: Split into smaller modules (sampling, baseline/adaptor inference, report generation, CLI wiring). Add typed interfaces for each submodule.

4) `src/merger/` is empty
    - Impact: README and some docs mention a merger; the folder exists but contains no implementation.
    - Remediation: Either add the intended implementation (`surgical_merge.py`) or remove the empty folder and update docs to avoid confusion.

5) Formatting tool mismatch in docs
    - `Makefile` and `README` recommend `ruff` for formatting; some docs and `AGENTS.md` historically referenced `black`.
    - Remediation: Declare canonical formatter in `pyproject.toml` and `requirements-dev.txt` (e.g., add `ruff` and optionally `black`), and add a `pre-commit` config if desired.

6) Secrets & CI behaviour
    - The repository uses `google-genai` optionally; `GOOGLE_API_KEY` controls whether the `GeminiClient` is used. CI intentionally leaves `GOOGLE_API_KEY` unset and uses local mocks/vLLM.
    - Remediation: Keep API keys out of source and document `AEGF_*` env var patterns in `configs/*.example`.

