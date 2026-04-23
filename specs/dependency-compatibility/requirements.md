---
spec: dependency-compatibility
epic: aegf-infrastructure
size: XS (< 1 day)
date: 2026-04-23
version: 2.1 (adversarial review fixes)
---

# Requirements: Dependency Compatibility

## Executive Summary

This spec validates that new dependencies are compatible with the existing dependency set before they are merged. The new dependencies are: `dspy` (new), `langgraph` (new), `openai` (moved from dev to runtime), and `torch` (optional, documented only). Two pre-existing deps also get pinned to prevent breakage: `datasets` (already present at `>=2.19`, needs `==2.21.0` to prevent 4.x API breakage) and `numpy` (missing from requirements but imported in two files). Deep research identified zero direct version conflicts among the new packages themselves, but surfaced three operational risks: (1) `litellm 1.82.6` — a transitive dependency pinned by `dspy` — carries **6 CVEs** (2 Critical, 4 High) that cannot be patched without unpinning `dspy`; (2) `packaging 26.0→25.0` and `fsspec 2026.3.0→2024.6.1` are expected silent downgrades enforced by `langgraph` and `datasets` respectively; (3) `tokenizers` and `tiktoken` have no Python 3.14 wheels, so CI source builds require a Rust toolchain. The deliverables are: updated `requirements.txt` + `pyproject.toml` with strict `==` pins (with bounded ranges where needed), updated `requirements-dev.txt` with `openai` removed from dev, `infrastructure/dependency_check.py`, and `docs/dependency-compatibility.md` covering CVEs, downgrades, install baselines, and Python 3.14 caveats.

---

## Functional Requirements

### FR-1: Update requirements.txt, requirements-dev.txt, and pyproject.toml with strict version pins

Update all three dependency files in a single coordinated change. The strategy is exact pins (`==`) for all new and modified dependencies, and `<` upper-bound ranges only for transitive dependencies with known breaking changes.

**Acceptance Criteria:**

- [ ] `requirements.txt` contains all new/runtime dependencies at exact pins:
  ```
  dspy==3.2.0
  langgraph==0.2.76
  openai==2.32.0
  numpy==2.4.4
  datasets==2.21.0
  packaging>=25.0,<26.0
  fsspec>=2023.1.0,<2025.0.0
  ```
- [ ] `torch` is **NOT** in `requirements.txt` (documented only as optional — see Out of Scope)
- [ ] `openai` is **removed** from `requirements-dev.txt` (moved to runtime; `dspy` requires it at runtime)
- [ ] `pyproject.toml` `[project].dependencies` includes all new pins:
  `dspy==3.2.0`, `langgraph==0.2.76` (with `<1.0` upper bound to prevent major-version jumps), `openai==2.32.0`, `numpy==2.4.4`, `datasets==2.21.0`
- [ ] `pyproject.toml` dev section `["pytest-cov>=7.0", "pytest-randomly>=3.0", "pytest-asyncio>=0.24"]` is retained; `openai` is **removed** from dev
- [ ] `pip install -r requirements.txt` completes with zero version conflict warnings
- [ ] `pip install .` includes all expected dependencies (synergy between requirements.txt and pyproject.toml)
- [ ] `numpy` imports succeed in `src/audit/eval_bpb.py:30` and `scripts/benchmark/measure_performance.py:34` (fixes pre-existing `ModuleNotFoundError`)
- [ ] Expected downgrades are documented in `docs/dependency-compatibility.md`:
  - `packaging 26.0→25.0` (enforced by `langgraph<1.0` constraint)
  - `fsspec 2026.3.0→2024.6.1` (enforced by `datasets==2.21.0` pin)
- [ ] `langchain-core` is documented in `docs/dependency-compatibility.md` as working in `langgraph 0.2.76`'s exclusion list by coincidence of pip resolver — this is a known fragility to monitor

---

### FR-2: Create `docs/dependency-compatibility.md`

Produce a single reference document that serves as the authority for all dependency-related knowledge. This is an **output** of the work, not a user story.

**Acceptance Criteria:**

- [ ] Document covers: full dependency tree (transitive), CVE section, Python 3.14 CI caveats, version pinning rationale, known risks and mitigations, installation instructions
- [ ] **CVE Section:** Lists all 6 `litellm 1.82.6` CVEs with IDs:
  `GHSA-r75f-5x8p-qvmc`, `GHSA-jjhc-v7c2-5hh6`, `GHSA-v4p8-mg3p-g94g`, `GHSA-xqmj-j6mv-4862`, `GHSA-69x8-hrgq-fjj8`, `GHSA-53mr-6c8q-9789`
- [ ] **Pinning Rationale Section:** Explains release cadences — `litellm` every 2.4 days, `openai` every 5-7 days, `dspy` every 1-3 months — and why `==` pins are required
- [ ] **Python 3.14 Section:** Documents that `tokenizers` and `tiktoken` have no Python 3.14 wheels; mitigation is to add Rust to CI or pin `tiktoken<0.13.0`
- [ ] **Install Baselines Section:** States measured install times (30-60s without torch, 2-5 min with torch CPU) and disk impact (595 MB base, +1.5 GB torch CPU = 2.1 GB total, +3.0 GB torch full = 3.6 GB total)
- [ ] **Optional Torch Section:** Provides CPU-only install instructions and clarifies torch is not in default requirements.txt
- [ ] **Downgrades Section:** Explicitly documents the two expected silent downgrades (`packaging`, `fsspec`) and why they are safe

---

### FR-3: Create `infrastructure/dependency_check.py`

A validation script that verifies the dependency setup is correct before merging. Must follow project constitution conventions (strict typing, copyright header, no import-time side effects).

**Acceptance Criteria:**

- [ ] File exists at `infrastructure/dependency_check.py`
- [ ] File includes copyright header: `AEGF, Copyright 2026, SPDX-License-Identifier: Apache-2.0`
- [ ] All public functions/methods are fully type-annotated (pyright strict mode passes)
- [ ] No import-time side effects — main logic guarded by `if __name__ == "__main__":`
- [ ] No bare `except` clauses — only explicit exception types
- [ ] Module uses a single `logging.getLogger(__name__)` logger with lazy formatting
- [ ] Script exit code is `0` on success, non-zero on any conflict or import error
- [ ] Script verifies specific imports: `dspy`, `langgraph`, `numpy`, `datasets`, `openai` (torch excluded — optional dep)
- [ ] Script is extensible: parses `requirements.txt` for import verification rather than hard-coding module names
- [ ] Coverage config updated to include `infrastructure/` as a source path in `pyproject.toml`

---

### FR-4: Project constitution compliance (cross-cutting)

All new/modified files must adhere to the project constitution. This is verified via pre-commit hooks and `pyright --strict`. This FR is not a separate deliverable — it is a verification gate that applies to all new code across FR-1 through FR-3.

**Acceptance Criteria:**

- [ ] `ruff check infrastructure/` passes with zero errors
- [ ] `pyright --strict infrastructure/dependency_check.py` passes with zero errors
- [ ] `scripts/check_headers.py --check` passes for all new Python files (copyright header present)
- [ ] No new files contain bare `except` clauses (verified via `ruff` or manual review)
- [ ] No new files have import-time side effects (no network calls, no I/O at module level)

---

## Non-Functional Requirements

### NFR-1: Install time baseline
`pip install -r requirements.txt` completes within **60 seconds** on a standard network connection (without torch). With `torch` CPU: within **5 minutes**. Baseline measured on project infrastructure, April 2026.

### NFR-2: Disk space
Total installed size is documented and bounded:
- Base install (no torch): **~595 MB**
- With torch CPU: **~2.1 GB** (+1.5 GB)
- With torch full: **~3.6 GB** (+3.0 GB)

### NFR-3: Reproducibility
All production dependencies use exact version pins (`==`) unless an upper-bound range is explicitly required to prevent major-version breakage (`packaging>=25.0,<26.0`, `fsspec>=2023.1.0,<2025.0.0`). No unbounded `>=` ranges for any direct dependency.

### NFR-4: Python version compatibility
All pinned dependencies support the project's declared minimum Python version (`>=3.12` per `pyproject.toml`). Known caveat: `tokenizers` and `tiktoken` have no Python 3.14 wheels — CI requires Rust toolchain for these packages on Python 3.14.

### NFR-5: Security transparency
All known CVEs in transitive dependencies are documented and tracked. Known risk: `litellm 1.82.6` has 6 CVEs (2 Critical, 4 High). See Decision Gate below.

---

## Decision Gate: litellm CVE Acceptance

**Status:** P0 — Requires human sign-off before merge.

| Item | Detail |
|------|--------|
| Vulnerable package | `litellm==1.82.6` (transitive via `dspy==3.2.0`) |
| CVE count | 6 (2 Critical, 4 High) |
| Patched version | `litellm>=1.83.7` |
| Blocker | `dspy<=3.2.0` pins `litellm<=1.82.6` |
| Options | (A) Accept risk + monitor for dspy update; (B) Patch dspy pin manually; (C) Block merge; (D) Accept with automated CVE monitoring (GitHub Dependabot or Snyk) |
| Sign-off required by | Project security lead or tech lead |

**Decision:** [ ] ACCEPTED — [ ] BLOCKED — [ ] DEFERRED (re-review by: ____ )
**Signed by:** ____________________  **Date:** ___________

---

## Dependencies (spec-level)

| Dependency | Relationship | Notes |
|------------|-------------|-------|
| spec:baseline-measurement | Blocked by | Blocked on this spec (needs `scipy`/`numpy` from `requirements.txt`) |
| spec:prompt-externalization | Independent | Runs in parallel (no dependency) |
| spec:anchor-dataset | Blocked by | Indirectly blocked via baseline-measurement |

---

## Glossary

| Term | Definition |
|------|-----------|
| `dspy` | DSPy — prompt optimization framework by Stanford (MIPROv2) |
| `langgraph` | LangGraph — state machine framework for LLM workflows |
| `litellm` | LiteLLM — universal LLM API router supporting 100+ providers |
| `CVE` | Common Vulnerabilities and Exposures — standardized security vulnerability identifiers |
| **pinning** | Using exact version numbers (`==`) instead of ranges (`>=`) for dependency versions |
| `torch` | PyTorch — ML training framework (optional dependency, not in default requirements.txt) |
| `openai` | OpenAI Python SDK — used by both DSPy and direct API calls (moved from dev to runtime) |
| silent downgrade | A transitive dependency version that drops during install due to a new constraint (e.g., `packaging 26.0→25.0`) |

---

## Out of Scope

- DSPy model training or MIPROv2 optimization (Epic 1)
- LangGraph graph implementation (Epic 3)
- Torch GPU driver installation (optional, documented but not automated)
- Dependency update automation / Dependabot configuration (deferred to Epic 1)
- Testing the actual ML pipeline with new dependencies (Epic 1)
- Downgrading or upgrading existing non-conflicting dependencies beyond what is needed for new deps
