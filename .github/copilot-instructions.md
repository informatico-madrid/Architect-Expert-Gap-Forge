# AEGF — Copilot instructions (brief)

Purpose: quickly orient coding agents to become productive in this repository.

1) High-level architecture (quick read)
- Main pipeline: Discovery → Factory → Curation → Training → Quality Gate (Audit) → Merger.
- Key directories: `src/discovery/`, `src/factory/`, `src/curation/`, `src/audit/`, `src/utils/`, `configs/`, `data/Gap/`, `tests/`.

2) Files to read first (in this order)
- `src/audit/inference.py` — Router and `GeminiClient` / `VLLMClient` implementations (how the backend is chosen: presence of `google-genai` + `GOOGLE_API_KEY`).
- `src/audit/model_evaluator.py` — CLI orchestrator (commands: `sample|baseline|adapter|score|full`, use `--validate` for a smoke test).
- `src/audit/prompt_manager.py` — loads `configs/stage_5_evaluation/eval_prompts.yaml` (script will fail if missing).
- `src/utils/doc_loader.py` — master-doc resolution (env `AEGF_DOC_1..3` or `configs/stage_5_evaluation/eval_config.yaml`).
- `configs/stage_5_evaluation/` and `data/Gap/` — prompt templates and master docs required for real runs.
- `tests/conftest.py` and `tests/test_doc_loader.py` — show how tests create fixtures and the exact filenames they expect.

3) Quick development commands & flows
```bash
make test           # run pytest (fast)
make coverage       # run pytest + coverage (fails if < 90% on src/audit, src/utils)
make fmt            # format with ruff
make lint           # run pyright (optional)

# Evaluator (smoke / validate):
python -m src.audit.model_evaluator full \
  --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \
  --base-model qwen3-30b-a3b-thinking-fp8 --adapter-model platinum_adapter --validate

# Generator example:
python src/factory/production_v11.py --gap-dir data/Gap --test 10
```

4) Project-specific conventions & patterns
- Prompts are externalized: all templates live under `configs/*` and are loaded by `PromptManager`.
- Master documents (`data/Gap/`) are the single source of truth for injected context; `doc_loader` will raise if they are missing.
- Backend router: instantiate `GeminiClient` only if `google-genai` is available and `GOOGLE_API_KEY` is set; default to `VLLMClient` otherwise.
- Avoid external calls in CI — tests use local mocks/fixtures; the CI workflow creates minimal mock YAMLs when required.

5) External integrations to know
- vLLM endpoint: `AEGF_VLLM_API_URL` (default `http://localhost:8000/v1`).
- Gemini (optional): `google-genai` SDK + `GOOGLE_API_KEY` — used as a teacher/judge fallback.
- NeMo Curator / datasketch: optional imports in `src/curation/nemo_curator_suite.py` (guarded with try/except).

6) Practical tips for agents
- If you change prompt YAMLs, run the evaluator with `--validate` for a quick, low-cost check.
- To avoid external API costs, stub or mock `src.audit.inference` in CI or local runs.
- Prefer `TypedDict` or `@dataclass(slots=True, frozen=True)` for stable payload types when adding APIs.
- Before editing CI/tests, inspect `tests/conftest.py` to see which files and env vars the tests expect.

7) Known gotchas
- Several folders under `src/` (`discovery`, `factory`, `curation`) lack `__init__.py` — import behavior may differ between `importlib` and `-m src` modes.
- Large, monolithic modules exist (`src/factory/production_v11.py`, `src/audit/model_evaluator.py`) — consider refactoring into smaller units when editing.
- Coverage thresholds: `Makefile` and `pyproject.toml` use 90% for tracked modules;
8) Governance references
- Follow the Architectural Gold Standard in `.github/agents/AEGF.agent.md` and the operational notes in `AGENTS.md`. The `processor` collects repository governance files (e.g., `AGENTS.md`, `CLAUDE.md`) and injects them as high-authority prompts (TIPO 5).

If you'd like, I can expand this into a longer agent guide with targeted examples (e.g., a `model_evaluator` smoke-test snippet or test fixtures examples).

