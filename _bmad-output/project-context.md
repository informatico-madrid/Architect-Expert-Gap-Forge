---
project_name: 'data_factory'
user_name: 'Malka'
date: '2026-04-21'
sections_completed: ['technology_stack', 'critical_rules', 'patterns', 'workflow']
existing_patterns_found: 15
---

# Project Context for AI Agents — AEGF (Architect-Expert-Gap-Forge)

_Este archivo contiene reglas críticas y patrones que los agentes de IA deben seguir al implementar código en este proyecto. Se enfoca en detalles no obvios que los agentes podrían pasar por alto._

---

## Technology Stack & Versions

### Runtime Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| Python | >=3.12 | Language runtime |
| PyYAML | >=6.0 | YAML parsing for configs |
| pydantic | >=2.0 | Data validation & serialization |
| httpx | >=0.27 | Async HTTP client |
| huggingface-hub | >=0.22 | HF dataset/model operations |
| datasets | >=2.19 | HuggingFace datasets library |
| tiktoken | >=0.7 | Token counting for LLMs |
| click | >=8.1 | CLI framework |
| google-genai | >=1.0 | Gemini API backend (optional) |
| python-dotenv | >=1.0 | Environment variable loading |
| tqdm | >=4.64 | Progress bars |
| requests | >=2.28 | HTTP client (legacy sync) |

### Development Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=9.0 | Test framework |
| pytest-cov | >=7.0 | Coverage reporting |
| pytest-randomly | >=3.0 | Randomized test order |
| pytest-asyncio | >=0.24 | Async test support |
| psutil | >=5.9 | System monitoring |
| ruff | >=0.9 | Linter & formatter |
| openai | >=1.0.0 | OpenAI API client (vLLM) |
| pyright | strict mode | Type checking |

### Build & CI Tooling
- **Build:** setuptools (PEP 517)
- **Test Runner:** pytest (configured in `pyproject.toml`)
- **Coverage:** coverage.py (target >=85%, tracked modules in `[tool.coverage.run]`)
- **Linter/Formatter:** ruff
- **Type Checker:** pyright (strict mode via `pyrightconfig.json`)
- **Pre-commit:** `.pre-commit-config.yaml`

---

## Critical Implementation Rules

### 1. Constitution is Supreme
- **Canonical source:** [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- **Governance:** [`.github/agents/AEGF.agent.md`](.github/agents/AEGF.agent.md) defines the Architectural Gold Standard
- **Operations:** [`AGENTS.md`](AGENTS.md) documents project operations
- **ALWAYS read constitution before implementing changes**

### 2. File Headers Mandatory
- Every new Python source file MUST include the project header:
  ```python
  #!/usr/bin/env python3
  # -*- coding: utf-8 -*-
  #
  # Architect-Expert-Gap-Forge (AEGF)
  # Copyright (c) 2026
  # SPDX-License-Identifier: Apache-2.0
  ```
- CI checks headers via [`scripts/check_headers.py --check`](scripts/check_headers.py)

### 3. Strict Typing Required
- ALL public functions/methods must be fully type-annotated
- Use `@dataclass(slots=True, frozen=True)` for data records
- Use `TypedDict` or `pydantic.BaseModel` for structured data
- `Dict[str, Any]` is FORBIDDEN for known structures — use `TypedDict`
- Every `__init__.py` must define `__all__` with public API symbols

### 4. Immutability by Default
- Data records: frozen dataclasses or `pydantic` models with `frozen=True`
- Configuration: frozen pydantic models
- Collections: prefer `tuple` over `list`, `frozenset` over `set`
- Exception: builders, accumulators, objects with explicit lifecycle

### 5. Logging Standards
- One logger per module: `logger = logging.getLogger(__name__)`
- Use lazy formatting: `logger.info("Loaded %d records", n)` — NO f-strings in logger calls
- Lazy formatting improves performance when log level is above current

### 6. No Import-Time Side Effects
- Module imports must NOT trigger I/O, network calls, or client instantiation
- Defer all external resource creation to explicit initialization functions

### 7. Error Handling
- Explicit exceptions only — NO bare `except: pass`
- NO `SystemExit` for flow control
- Parse/validation errors must raise explicit exceptions — NO silent failures

### 8. Concurrency
- Async code uses `asyncio.TaskGroup` for structured concurrency
- Wrap blocking I/O in `asyncio.to_thread()`
- `time.sleep()` in async context is FORBIDDEN — use `asyncio.sleep()`

---

## Architecture Patterns

### Strategy + Router
- Inference backends are behind a strategy interface
- Selected by a router pattern (see `src/audit/inference.py`)
- New backends added via new classes, never by modifying existing ones (OCP)

### Prompt Externalization
- All prompt templates live under [`configs/`](configs/)
- Managed by `PromptManager` in [`src/audit/prompt_manager.py`](src/audit/prompt_manager.py)
- Never hardcode prompts in source files

### Module Architecture
- Modules should be small and single-responsibility (~400 LOC max)
- Cross-cutting concerns go to `src/utils/`
- Domain logic goes to `src/{domain}/`
- Batch operations favored over record-by-record

### Profile-Based Architecture (Stage 1 Discovery)
- Discovery engine uses YAML-driven profiles for language support
- Profiles: `homeassistant` (Python), `php_hexagonal` (PHP)
- Extractor adapters per profile in `src/utils/extractors/`
- Configuration-driven behavior, not code changes

### Extractor Adapter Pattern
- Base class: [`src/utils/extractors/base.py`](src/utils/extractors/base.py)
- Factory: [`src/utils/extractors/factory.py`](src/utils/extractors/factory.py)
- Adapters: `jinja_adapter`, `markdown_adapter`, `php_legacy_adapter`, `python_ast_adapter`, `typescript_adapter`, `yaml_adapter`
- New language support = new adapter + factory registration

---

## Project Structure

```
data_factory/
├── src/                          # Main source code
│   ├── audit/                    # Calibration, evaluation, scoring
│   ├── curation/                 # Dataset curation, dedup, quality
│   ├── discovery/                # Stage 1: repo ingestion & fragmentation
│   ├── export/                   # ChatML export, taxonomy prompts
│   ├── factory/                  # Stage 2: synthetic data factory
│   ├── merger/                   # Stage 3: merge & repair pipelines
│   ├── quantizer/                # FP8 quantization
│   ├── research/                 # Experiment orchestration
│   ├── schemas/                  # Common data schemas
│   ├── training/                 # Training config validation
│   └── utils/                    # Cross-cutting utilities
│       └── extractors/           # Language-specific extractors
├── tests/                        # Test suite (mirrors src/ structure)
│   ├── unit/                     # Pure unit tests
│   ├── integration/              # Cross-module integration tests
│   ├── e2e/                      # End-to-end tests
│   └── fixtures/                 # Test data & mocks
├── configs/                      # External configuration
│   ├── prompts/                  # System prompts
│   ├── stage_1_discovery/        # Discovery configs
│   ├── stage_2_factory/          # Factory configs & taxonomy
│   ├── stage_4_training/         # Training configs
│   ├── stage_5_evaluation/       # Evaluation configs
│   └── stage_6_calibration/      # Calibration configs
├── specs/                        # Feature specifications
├── plans/                        # Implementation plans
├── docs/                         # Documentation
├── deploy/                       # Docker deployment configs
├── _bmad/                        # BMAD workflow configuration
├── _bmad-output/                 # BMAD output artifacts
└── diagnose/                     # Diagnostic & audit scripts
```

---

## Workflow & Governance

### Git Operations
- **Git autonomy: ENABLED** — agents can commit changes
- **YOLO mode: ENABLED** — agents have high autonomy
- Commit messages follow conventional format (see `.specify/memory/workflow-stack.md`)
- Branch naming: `feat/<feature-name>`, `fix/<bug-name>`

### Testing Requirements
- **Coverage target:** >=85% for tracked modules
- **Tracked modules:** `src/audit`, `src/utils`, `src/factory`, `src/curation`, `src/discovery`
- **Excluded from coverage:** CLI entry points, deprecated code, `__init__.py`, research modules
- **Test markers:** `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Test order randomized:** `pytest-randomly` with seed="last" for reproducibility
- **Agentic tests excluded:** `tests/test_agentic_gen.py` ignored until stable

### Coverage Exclusions (Documented)
CLI modules, deprecated code, `__init__.py` re-exports, discovery ingestor (no tests yet), and research modules are excluded from coverage tracking. Each exclusion is documented in `[tool.coverage.run].omit` in `pyproject.toml`.

### BMAD Workflow Integration
- BMAD modules configured in `_bmad/{module}/config.yaml`
- Planning artifacts: `_bmad-output/planning-artifacts`
- Implementation artifacts: `_bmad-output/implementation-artifacts`
- Project knowledge: `docs/`
- PRD workflow, architecture, and story creation via BMAD skills

### Qdrant Vector Memory
- Agents MUST use `qdrant-find` before writing/modifying code (research phase)
- Agents MUST use `qdrant-store` after implementing critical code (indexing phase)
- Store only: architectural decisions, core business rules, reusable patterns
- NEVER store: transient state, test failures, to-do lists, progress

---

## Commands Reference

```bash
# Run tests
make test

# Run coverage
make coverage

# Run linter
ruff check .

# Type checking
pyright

# Install dependencies
pip install -e ".[dev]"

# BMAD workflow commands
# (via .roo/skills/bmad-*/)
```

---

## Environment Configuration

- **Environment variables:** Load from `.env` via `python-dotenv`
- **Template:** [`.env.example`](.env.example) shows required variables
- **Secrets:** Never store credentials in source — use environment variables
- **CI uses local mocks:** Avoid live external calls during CI

---

## Common Pitfalls for AI Agents

1. **DO NOT modify constitution without explicit instruction** — it is the single source of truth
2. **DO NOT add `# pragma: no cover` without justification** — each exclusion must be documented
3. **DO NOT hardcode prompts** — always externalize to `configs/`
4. **DO NOT use f-strings in logging** — use lazy formatting
5. **DO NOT skip type annotations** — strict typing is enforced
6. **DO NOT create mutable dataclasses** — use `frozen=True` by default
7. **DO NOT import-time side effects** — defer I/O to initialization
8. **DO NOT use bare except** — always specify exception types
