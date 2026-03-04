## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.


1) Unstructured `dict[str, Any]` usage
    - Widespread sites: `src/audit/*`, `src/factory/*`, `src/curation/*` (e.g., `model_evaluator`, `inference`, `production_v11`, `nemo_curator_suite`).
    - Impact: Runs counter to §2.1 (use `TypedDict` / dataclass for known schemas). Makes static analysis and refactoring harder.
    - Remediation: Introduce `TypedDict` types or small frozen dataclasses for canonical payloads (sample records, inference payload, audit report sections). Migrate incrementally with unit tests.

2) Monolith modules
    - Examples: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC).
    - Impact: Violates §3.1 guidance (modules should be small and single-responsibility). Hard to test and maintain.
    - Remediation: Split into smaller modules (sampling, baseline/adaptor inference, report generation, CLI wiring). Add typed interfaces for each submodule.

3) `src/merger/` is empty
    - Impact: README and some docs mention a merger; the folder exists but contains no implementation.
    - Remediation: Either add the intended implementation (`surgical_merge.py`) or remove the empty folder and update docs to avoid confusion.

4) Formatting tool mismatch in docs
    - `Makefile` and `README` recommend `ruff` for formatting; some docs and `AGENTS.md` historically referenced `black`.
    - Remediation: Declare canonical formatter in `pyproject.toml` and `requirements-dev.txt` (e.g., add `ruff` and optionally `black`), and add a `pre-commit` config if desired.

5) Secrets & CI behaviour
    - The repository uses `google-genai` optionally; `GOOGLE_API_KEY` controls whether the `GeminiClient` is used. CI intentionally leaves `GOOGLE_API_KEY` unset and uses local mocks/vLLM.
    - Remediation: Keep API keys out of source and document `AEGF_*` env var patterns in `configs/*.example`.

