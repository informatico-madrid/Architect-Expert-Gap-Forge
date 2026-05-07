# Spec: dependency-compatibility

**Epic:** specs/_epics/aegf-infrastructure/epic.md
**Size:** XS (< 1 day)
**Status:** pending (no dependencies) -- RUN FIRST

## BMAD Source

- **Story:** 0.4 — Dependency Compatibility (NEW in v4.0)
- **epics.md:** [`_bmad-output/planning-artifacts/epics.md:280`](../../_bmad-output/planning-artifacts/epics.md#story-04-dependency-compatibility-nueva-v40)
- **PRD:** [aegf-3-layer-prd.md](../../_bmad-output/planning-artifacts/aegf-3-layer-prd.md) — Technology stack section, DSPy/LangGraph dependency requirements
- **Technical Research:** [aegf-technology-validation-research.md](../../_bmad-output/planning-artifacts/research/aegf-technology-validation-research-2026-04-22.md) — DSPy compatibility validation
- **Sprint Status:** [sprint-status.yaml](../../_bmad-output/implementation-artifacts/sprint-status.yaml) — story 0.4, status: backlog
- **Party Mode Note:** Party Mode v4.0 Change C2 (severity 7/10, 3/4 consensus). Story 0.4 should run FIRST to fix pre-existing `numpy` bug in requirements.txt.

## Goal

As a Platform Operator, I want to validate that new dependencies (dspy, langgraph, torch, openai) are compatible with existing ones, so that the project can install and run without version conflicts.

## Acceptance Criteria

1. **No version conflicts:** Adding new dependencies to `requirements.txt` and running `pip install -r requirements.txt` reports no version conflicts:
   - `dspy==3.2.0` (DSPy MIPROv2) -- EXACT pin (rapid release cadence)
   - `langgraph==0.2.76` (Layer 2 state machine) -- EXACT pin + `<1.0` upper bound
   - `torch` -- NOT from DSPy (must be added explicitly)
   - `openai==2.32.0` (moved from dev to runtime) -- EXACT pin

2. **Tests pass:** All existing tests pass with new dependencies installed.

3. **Import works:** `python -c "import dspy; import langgraph"` succeeds without import errors.

4. **Documentation:** `docs/dependency-compatibility.md` contains:
   - Full dependency tree (see Appendix A of deep-research.md)
   - Known CVEs (litellm 1.82.6: 2 Critical + 4 High, blocked by dspy constraint)
   - Python 3.14 CI caveats (tokenizers/tiktoken no wheels)
   - Strict version pinning rationale
   - Version matrix

## Interface Contracts

### Writes
- `infrastructure/dependency_check.py` -- validates install compatibility
- `requirements.txt` -- updated with new deps, bugfix (numpy), AND strict version pins
- `pyproject.toml` -- updated to match with exact pins
- `docs/dependency-compatibility.md` -- documentation with CVEs, CI caveats, version matrix

### Reads
- Existing `requirements.txt`
- Existing `pyproject.toml`

### dependency_check.py Output
- Exit code 0 on success, non-zero on conflict
- Prints dependency tree to stdout

## Dependencies

- **None** (should be the FIRST spec to run)

## Implementation Notes (from deep research audit)

### Corrections from Spec Assumptions
- **torch is NOT from DSPy transitive deps** -- dspy 3.x removed torch entirely. Add explicitly if ML workloads needed.
- **dspy-ai is deprecated** -- use `dspy>=3.0` directly (dspy-ai==2.5.43 wraps dspy==3.2.0)
- **Version pinning CRITICAL** -- litellm releases every 2.4 days, openai every 5-7 days, dspy every 1-3 months. Use `==` exact pins, NOT `>=` ranges.

### Risk Findings
- **litellm 1.82.6 has 6 CVEs** (2 Critical + 4 High). dspy pins `litellm<=1.82.6` blocking patches. Document and accept risk or monitor dspy for constraint updates.
- **tokenizers/tiktoken have NO Python 3.14 wheels** -- CI source build failure without Rust toolchain. Pin `tiktoken<0.13.0`.
- **datasets 4.8.4 is latest** (from 2.21.0). Must pin `datasets==2.21.0` to prevent 4.x API breakage in anchor dataset downloader.
- **langchain-core 0.3.84 is in langgraph 0.2.76's exclusion list** -- works by coincidence. Pin exact versions.

### Pre-existing Bugs to Fix
- `numpy` imported by `scripts/benchmark/measure_performance.py:34` but missing from requirements.txt
- `openai>=1.0.0` only in requirements-dev.txt (must move to requirements.txt for DSPy runtime)
- Dual dependency management: `requirements.txt` (runtime) + `pyproject.toml` (build + dev) -- must reconcile both

### Transitive Dependency Risks
- `datasets==2.21.0` and `tiktoken>=0.7,<0.13` already present (satisfies anchor-dataset needs). Pin datasets `<3.0` to prevent 4.x API breakage.
- `google-genai>=1.0` already in requirements.txt as optional inference backend
- Total installed size without torch: 595 MB. With torch CPU: 2.1 GB. With torch full: 3.6 GB.
