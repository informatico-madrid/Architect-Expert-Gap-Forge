---
name: AEGF-Architect
description: Architectural Gold Standard — Logical compilation constraints for sovereign AI.
argument-hint: architectural task, code refactoring, logic synthesis, or quality gate request.
---

# AEGF: Architectural Gold Standard

This document codifies the **Gold Standard** of engineering for this repository. Any agent — human or synthetic — interacting with this codebase MUST treat these rules as **logical compilation constraints**. Code that violates them is not considered complete.

> *Architecture is the product. The use case is merely the validation.*

---

## § 1. FUNDAMENTAL LAWS (Non-Negotiable)

### 1.1 DRY as a Thermodynamic Law
Logic duplication is **technical debt with compound interest**. Every function, constant, pattern-list, or utility that exists in more than one file MUST be extracted to a shared module. No exceptions.

- **Verification:** Before writing a function, search whether an equivalent already exists in the codebase.
- **Remedy:** `src/utils/` for cross-cutting concerns, `src/{domain}/` for domain logic.
- **Forbidden:** Copying functions between modules "because it's easier."

### 1.2 SOLID as a Structural Constraint

| Principle | Concrete Rule |
|-----------|---------------|
| **SRP** | No module should exceed ~400 LOC without justification. If a module has more than 3 responsibilities, it must be split. |
| **OCP** | New types, backends, or strategies must be addable by creating new classes/modules, never by modifying existing ones. |
| **LSP** | Every subclass must be substitutable for its base without altering program correctness. |
| **ISP** | Abstract interfaces must be small and cohesive. Prefer N interfaces of 1-2 methods over one interface of N methods. |
| **DIP** | Domain/orchestration modules NEVER instantiate infrastructure directly. They receive abstractions via constructor or factory. |

### 1.3 Testing as an Existence Requirement
Code without tests is not finished. Every new module MUST be born with at least:
- **Unit tests** for pure functions and data transformations.
- **Integration tests** for pipelines that cross module boundaries.
- **Fixture factories** for domain entities (dataclasses, records).
- Framework: `pytest` with typed fixtures.
- **Target:** Minimum coverage 90%.
- **Coverage Integrity:** The use of `# pragma: no cover` or skipping test logic to artificially reach the target is STRICTLY PROHIBITED. 
- **Exceptions:** Coverage exclusions are only allowed for inescapable boilerplate (e.g., `if __name__ == "__main__":`) or abstract protocols. Every exclusion MUST be justified in the `<think>` block and documented with a technical comment.

---

## § 2. PYTHON STANDARDS (v3.12+)

### 2.1 Strict Typing — No Concessions
- **EVERY** function and method signature MUST be fully annotated (parameters and return type).
- Use `TypeAlias`, `Generic[T]`, `Final`, `TypedDict` to guarantee static integrity.
- `Dict[str, Any]` as a substitute for a known structure is forbidden — use `TypedDict` or `dataclass`.
- Every package's `__init__.py` MUST define `__all__` with public API symbols.
- Reference tooling: `pyright` in strict mode or `mypy --strict`.

### 2.2 Immutability by Default
- **Data records**: `@dataclass(slots=True, frozen=True)` by default. If mutation is needed, document why.
- **Configuration**: `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)` or `@dataclass(frozen=True)`.
- **Collections**: Prefer `tuple` over `list`, `frozenset` over `set`, `MappingProxyType` over `dict` for shared data.
- **Acceptable exceptions**: Builders, accumulators, and objects with explicit lifecycle (e.g., `ProgressTracker`).

### 2.3 Concurrency and I/O
- All external I/O (network, disk, APIs) must be non-blocking when the context is async.
- Use structured concurrency (`asyncio.TaskGroup`) instead of bare `asyncio.gather`.
- Legacy blocking operations (subprocess, sync HTTP) must be wrapped in `asyncio.to_thread()` or dedicated executors.
- `time.sleep()` in async context is **forbidden**. Use `asyncio.sleep()`.

### 2.4 Logging
- Use lazy formatting: `logger.info("Loaded %d records from %s", count, path)`.
- **Forbidden:** f-strings in logger calls (`logger.info(f"Loaded {count}")`).
- One logger per module: `logger = logging.getLogger(__name__)`.

---

## § 3. MODULE ARCHITECTURE

### 3.1 Logic Density Ratio
Maximize the ratio between *Architectural Intent* and *Token Footprint*:
- Prefer elegant abstractions (Decorator, ABC, Protocol) that eliminate redundancy.
- Each module should have a minimal public API and internal helpers prefixed with `_`.
- **Gold Reference:** Modules of <100 LOC with single responsibility and explicit `__all__`.

### 3.2 Layer Separation

```
configs/
  stage_1_discovery/         ← Ingestion & repo-crawling params (.yaml.example)
  stage_2_factory/
    taxonomy/                ← Domain taxonomies consumed as data (YAML per domain)
      {domain}/              ← e.g. home_assistant/, generic_domain/
  stage_3_curation/          ← NeMo Curator pipeline configs
  stage_4_training/
    axolotl/                 ← Trainer configs (.yaml + .yaml.example)
    deepspeed/               ← DeepSpeed ZeRO stage configs (.json)
  stage_5_evaluation/        ← Eval prompts (YAML) + eval pipeline config
  taxonomy/
    {domain}/                ← Extended domain-specific taxonomies

src/
  discovery/                 ← Stage 1: repo ingestion & code bundling
    ingestor.py              ← Git clone, file walking, metadata extraction
    processor.py             ← Module parsing, bundle emission
  factory/                   ← Stage 2: synthetic data generation
    production_v11.py        ← Main generation pipeline (checkpoint/resume)
    agentic_gen.py           ← Multi-turn agentic generation
    think_filter.py          ← CoT distillation with sacred constraints
  curation/                  ← Stage 3: data quality filtering
    nemo_curator_suite.py    ← NeMo Curator pipeline orchestrator
  audit/                     ← Stage 5: model evaluation pipeline
    schema.py                ← Domain dataclasses & TypedDicts
    inference.py             ← Strategy pattern: inference backends
    prompt_manager.py        ← YAML prompt loader & formatter
    model_evaluator.py       ← N-stage eval orchestrator
  research/                  ← Experimental scripts (not imported by core)
  utils/                     ← Cross-cutting: loaders, formatters, shared helpers
    doc_loader.py            ← Master docs loader (DRY canonical)
```

### 3.3 State Decoupling
- Runtime data must be encapsulated and namespaced. Unversioned mutable global registries are forbidden.
- Configuration flows in cascade: `YAML config → env vars (prefixed) → CLI args`.
- Environment variables use a consistent project prefix (e.g., `AEGF_*`).

### 3.4 Strategy Pattern for Backends
Inference engines, API clients, and external services must be abstracted behind interfaces (`abc.ABC` or `Protocol`):

```python
class BaseInferenceClient(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None, 
                 max_tokens: int = 4096, temperature: float = 0.7) -> str: ...
```

- A `Router` with caching resolves the correct client based on configuration.
- **Forbidden:** Instantiating `OpenAI(...)`, `requests.post(...)`, or SDKs directly in domain code.

### 3.5 Schema Validation
Heuristic interpretation of external data is forbidden:
- Inter-module and API communication validated with `Pydantic`, `TypedDict`, or JSON-Schema.
- Parse failure = explicit exception, never silent fallback or regex repair.
- When the backend supports it, use JSON mode (`response_mime_type`, `response_format`) instead of parsing strings.

### 3.6 Plural Operations
Prefer batch/plural design over iterative singular calls:
- Generation APIs that accept lists of inputs.
- Persistence in blocks, not record-by-record.
- Pipeline stages with intermediate persistence and resume capability.

---

## § 4. PROMPTS AND TRAINING DATA

### 4.1 Prompt Externalization
- All prompt templates MUST reside in YAML files under `configs/`.
- A centralized `PromptManager` loads, caches, and formats templates at runtime.
- **Forbidden:** Multiline prompt strings embedded in Python code.

### 4.2 Taxonomies
- Taxonomies (example types, categories, tool definitions) are defined in YAML.
- Code consumes them as data, never defines them inline.
- Adding a new type = adding a YAML entry, not modifying Python.

### 4.3 Gold Trajectory Synthesis
When generating data for SFT or evaluation:
1. **Gap Identification:** Reasoning must begin by identifying what knowledge is missing.
2. **Architectural Remediation:** The solution must represent the standard of excellence, not just "work."
3. **Auditability:** Every generated fragment must be compatible with the evaluation system's criteria.
4. **Sacred Constraints:** Document invariants that must never be violated (e.g., "NEVER modify after `</think>`").

---

## § 5. GOVERNANCE AND SECURITY

### 5.1 Secrets and Configuration
- **NEVER** persist API keys, tokens, or credentials in source code. Use environment variables.
- Configuration files with sensitive values must have a `.example` version tracked in git.
- Absolute paths from the development environment are **forbidden** in `src/` modules. Use relative or configurable paths.

### 5.2 Traceability
- Every new module must include an SPDX header with license and provenance.
- Architectural changes are documented in descriptive commits, not in generic README files.

### 5.3 Import-Time Side Effects
- **Forbidden:** Performing I/O, creating HTTP clients, or reading files at module level.
- Initialization must be explicit: constructors, factory methods, or `init()` functions.
- Exception: `logging.getLogger(__name__)` and immutable constants.

### 5.4 Error Handling
- `except Exception: pass` is **forbidden** except in documented non-critical infrastructure helpers.
- `SystemExit` is not used as flow control. Use custom domain exceptions.
- Every silenced exception must document the reason with a comment.

### 5.5 Valid Python Packages
- Every directory under `src/` containing `.py` modules MUST have an `__init__.py` with `__all__`.
- A directory without `__init__.py` is not a Python package — imports fail and the hierarchy breaks.

---

## § 6. GOLD STANDARD PATTERNS (Reference)

These patterns, already implemented in the codebase, represent the level of excellence to replicate:

| Pattern | Description | Reference |
|---------|-------------|----------|
| **Strategy + Router** | Interchangeable inference backends with automatic resolution and caching | `src/audit/inference.py` |
| **Module ≤100 LOC** | Single responsibility, minimal API, helpers with `_`, explicit `__all__` | `src/audit/prompt_manager.py`, `src/utils/doc_loader.py` |
| **Prompt Externalization** | Templates in YAML, loaded by a typed Manager | `configs/stage_*/`, `src/audit/prompt_manager.py` |
| **Sacred Constraints** | Invariants documented in docstrings that explain philosophy, not just interface | `src/factory/think_filter.py` |
| **Pipeline N-Stages** | Independent stages with intermediate persistence and resume capability | `src/audit/model_evaluator.py` |
| **Checkpoint/Resume** | Deterministic hashing for idempotency, skipping prior work | `src/factory/production_v11.py` |
| **Config Cascade** | YAML → env vars (prefixed) → CLI args | `configs/stage_5_evaluation/eval_config.yaml` |

---

## § 7. FORBIDDEN ANTI-PATTERNS

| Anti-Pattern | Description | Remedy |
|--------------|-------------|--------|
| **Monolith Module** | File >500 LOC with multiple responsibilities | Decompose into SRP modules |
| **Dict[str, Any] Abuse** | Using untyped `Dict` as a data structure | `TypedDict` or `@dataclass` |
| **Copy-Paste Inheritance** | Duplicating functions between "sibling" modules | Extract to shared module |
| **Hardcoded Infra** | API keys, URLs, absolute paths in code | Environment variables + `.example` |
| **Import-Time Side Effects** | I/O or client instantiation when importing a module | Explicit initialization |
| **Bare Except** | `except Exception: pass` without documenting why | Specific exceptions + logging |
| **SystemExit as Flow Control** | Using `raise SystemExit()` for domain errors | Custom exceptions |
| **Vibe-Coding** | Code that "works" without types, tests, or structure | The standard in this document |

---

**Status:** Operational Framework — Architectural Gold Standard v2.1