## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.

1) Monolith modules
    - Examples: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC).
    - Impact: Violates §3.1 guidance (modules should be small and single-responsibility). Hard to test and maintain.
    - Remediation: Split into smaller modules. Add typed interfaces for each submodule.

2) `src/merger/` is empty
    - Impact: README and some docs mention a merger; the folder exists but contains no implementation.
    - Remediation: Either add the intended implementation (`surgical_merge.py`) or remove the empty folder and update docs to avoid confusion.

3) Formatting tool mismatch in docs
    - `Makefile` and `README` recommend `ruff` for formatting; some docs and `AGENTS.md` historically referenced `black`.
    - Remediation: Declare canonical formatter in `pyproject.toml` and `requirements-dev.txt` (e.g., add `ruff` and optionally `black`), and add a `pre-commit` config if desired.

4) Secrets & CI behaviour
    - The repository uses `google-genai` optionally; `GOOGLE_API_KEY` controls whether the `GeminiClient` is used. CI intentionally leaves `GOOGLE_API_KEY` unset and uses local mocks/vLLM.
    - Remediation: Keep API keys out of source and document `AEGF_*` env var patterns in `configs/*.example`.

5) Default inference backend should be local vLLM
     - Detail: Make the default inference engine `vllm` (local/OpenAI-compatible HTTP) instead
        of auto-selecting `gemini`. Configuration should allow overriding via `.env` (e.g.
        `AEGF_PROFESSOR_BACKEND`) or `configs/stage_5_evaluation/eval_config.yaml`.
     - Impact: Prevent accidental use of Gemini in environments that have the SDK/API key
        available; aligns with CI expectations and local development workflows.
     - Remediation: Update the router/defaults and document the env/config option.
    
6) Refactor tests