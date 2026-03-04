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


6) Parallelism for `model_evaluator` (workers + optional parallel judge)
    - Goal: Add configurable parallelism to speed up `generate-exam`, `baseline` and
      `adapter` stages using a worker pool. Provide an optional `--judge-workers`
      (or `--parallel-judge`) to parallelize LLM-as-Judge calls when explicitly enabled.
    - Flags: `--workers N` (default `1` for compatibility), `--judge-workers M` (default `0` = disabled).
    - Implementation notes:
       - Use `concurrent.futures.ThreadPoolExecutor` and instantiate a client per worker
         (avoid sharing `InferenceRouter` cache across threads or guard it).
       - Parallelize `generate-exam`, `baseline`, and `adapter` by submitting per-record
         tasks and collecting results (persist results from main thread to keep IO atomic).
       - Keep fail-fast semantics configurable: either cancel pending tasks on first judge
         failure or aggregate errors and fail after joining (opt-in behavior).
       - Ensure thread-safety for Gemini SDK (create one client per worker) and avoid
         race conditions when saving raw outputs (`judge_raw_{id}.txt`).
    - Tests: add smoke tests verifying behavior with `--workers>1` and `--judge-workers`.
    - Impact: significant speedups on multi-CPU hosts; increases concurrency and cost when
      using remote LLM backends — disabled by default to preserve deterministic, low-cost runs.
```
