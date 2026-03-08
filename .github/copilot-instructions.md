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

9) Agent Operational Rules (MANDATORY)
- Agents MUST NOT run `git commit`, `git commit -m`, `git push`, or any command that modifies remote branches or repository history.
- Agents MAY run `git add` only for files that have been explicitly confirmed by the user in the current session or conversation.
- Agents MUST present a concise plan using the `manage_todo_list` tool that lists intended file edits and wait for explicit user confirmation before staging files.
- Agents MUST NOT create or modify commits, branches, tags, or push to any remote without explicit user instruction and affirmative confirmation.
- Agents SHOULD provide the exact patch or a human-readable summary of changes and allow the user to review before staging.
 - Agents MUST NOT modify production scripts solely to make tests pass. If a test indicates a real production bug, agents MUST stop, report the issue, and obtain explicit human confirmation before editing production code.
 - Agents MUST include the project's standard file header in every new source file they create. The header must include a shebang for Python files, the project identifier `Architect-Expert-Gap-Forge (AEGF)`, a copyright line, and an `SPDX-License-Identifier:` entry.
   - Agents MUST run `scripts/check_headers.py --check` locally (or enable the repo githook / pre-commit) before staging files; CI will also validate the header via `.github/workflows/header-check.yml`.
 - Agents MUST format proposed commit messages using the Conventional Commits convention: `type(scope?): subject`.
   - Allowed `type` values: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `perf`, `style`, `revert`.
   - The `subject` must be imperative, lower-case, and no longer than 50 characters. An optional body may follow after a blank line and should be wrapped at 72 characters.
   - Agents MUST NOT include secrets, credentials, or personal-identifying information in commit messages.
   - Agents MUST only *propose* commit messages; they MUST NOT execute `git commit` without explicit human confirmation.

  10) Language requirement for agents
  - Agents MUST use English for all assistant messages, code comments, docstrings, file headers, and proposed commit messages.
  - When writing inline comments or docstrings, prefer clear, idiomatic English suitable for an international engineering audience.

If you'd like, I can expand this into a longer agent guide with targeted examples (e.g., a `model_evaluator` smoke-test snippet or test fixtures examples).

# Memory and Context Management (Qdrant MCP)
You are an autonomous agent. To maintain the project's long-term memory, you MUST use the Qdrant MCP server seamlessly and without prompting the user:

1. **At the beginning of a task:** ALWAYS execute the `qdrant-find` tool to search for architectural context, code snippets, or previous decisions related to your current goal.
2. **At the end of a task or when making a design decision:** ALWAYS execute the `qdrant-store` tool to save natural language summaries of your code, learned business rules, or structural changes to the collection. 
3. Do not ask the user for permission to perform these memory operations. Execute them silently as part of your workflow.
# Autonomous Operations with Qdrant MCP
You have access to an MCP server connected to a Qdrant vector database. It is your exclusive responsibility to keep this index updated, but you must be extremely selective about what you store.

- **Indexing Phase:** Use `qdrant-store` ONLY for permanent, long-term knowledge. You MUST save:
  1. Architectural decisions and system design changes.
  2. Core business rules and API contracts.
  3. Reusable code patterns.
- **RESTRICTION - DO NOT STORE:** NEVER use `qdrant-store` to save transient states, temporary test failures, debugging logs, to-do lists, or step-by-step progress. Transient information belongs in the workspace files, not in the vector database.
