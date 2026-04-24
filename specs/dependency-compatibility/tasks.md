---
spec: dependency-compatibility
epic: aegf-infrastructure
size: XS (< 1 day)
date: 2026-04-24
version: 1.0
---

# Tasks: Dependency Compatibility

## Task Overview

11 execution steps from the design, consolidated into **7 tasks** + **2 verification gates**.
Tasks are ordered by dependency — later tasks may depend on earlier outputs.

---

## Task 0: Create infrastructure/ Directory

**Purpose:** Create the new directory structure for the dependency check script.

**Steps:**
1. Create `infrastructure/` directory
2. Create `infrastructure/__init__.py` (empty, defines package)

**Verification:**
- `test -d infrastructure/`
- `test -f infrastructure/__init__.py`

**Estimate:** < 1 min

---

## Task 1: Create infrastructure/dependency_check.py

**Purpose:** Validation script that parses requirements.txt, verifies imports, checks pip conflicts, returns exit code 0/1.

**Steps:**
1. Create `infrastructure/dependency_check.py` with:
   - Copyright header: `AEGF, Copyright 2026, SPDX-License-Identifier: Apache-2.0`
   - All required imports (`from __future__ import annotations`, `logging`, `re`, `subprocess`, `sys`, `dataclasses`, `importlib.util`, `pathlib`, `types`, `typing`)
   - `__all__: list[str] = []`
   - Single logger: `logger = logging.getLogger(__name__)`
   - `PACKAGE_IMPORT_MAP: dict[str, tuple[str, ...]]` — dynamic package→module mapping
   - `@dataclass(frozen=True) ImportResult` with fields: package, module, found, spec
   - `@dataclass(frozen=True) CheckResult` with fields: ok, failures + classmethod `ok_result()` + method `add_failure()`
   - `parse_requirements(path: Path) -> list[str]` — regex-based parsing
   - `_resolve_module(package_name: str) -> tuple[str, ...]` — map lookup with fallback
   - `check_imports(packages: list[str]) -> CheckResult` — find_spec loop
   - `check_pip_conflicts() -> CheckResult` — subprocess pip check
   - `main(argv: list[str] | None = None) -> int` — orchestration + logging
   - `if __name__ == "__main__": raise SystemExit(main())`
2. Run `ruff check infrastructure/dependency_check.py`
3. Run `pyright --strict infrastructure/dependency_check.py`
4. Run `python scripts/check_headers.py --check infrastructure/dependency_check.py`

**Acceptance Criteria (from requirements.md FR-3):**
- [ ] File exists at `infrastructure/dependency_check.py`
- [ ] Copyright header present
- [ ] `ruff check infrastructure/` passes with zero errors
- [ ] `pyright --strict infrastructure/dependency_check.py` passes with zero errors
- [ ] `scripts/check_headers.py --check` passes
- [ ] All public functions/methods fully type-annotated
- [ ] No import-time side effects — guarded by `if __name__ == "__main__"`
- [ ] No bare except clauses
- [ ] Single `logging.getLogger(__name__)` logger
- [ ] Exit code 0 on success, non-zero on failure
- [ ] Verifies imports: dspy, langgraph, numpy, datasets, openai (via requirements.txt parsing)
- [ ] Extensible: parses requirements.txt dynamically, not hardcoded tuples

**Verification Commands:**
```bash
ruff check infrastructure/dependency_check.py
pyright --strict infrastructure/dependency_check.py
python scripts/check_headers.py --check infrastructure/dependency_check.py
python infrastructure/dependency_check.py  # should pass (deps already installed)
```

**Estimate:** 15-20 min

---

## Task 2: Update requirements.txt

**Purpose:** Add new/runtime dependency pins, fix pre-existing bugs.

**Steps:**
1. Append to `requirements.txt`:
   ```
   # New dependencies — added for dependency-compatibility spec (2026-04-24)
   dspy==3.2.0
   langgraph==0.2.76
   openai==2.32.0

   # Bugfix: previously missing, required by src/audit/eval_bpb.py and scripts/benchmark/measure_performance.py
   numpy==2.4.4

   # Pinned to prevent 4.x API breakage (datasets 4.x changes core data format)
   datasets==2.21.0

   # Bounded ranges for known breaking-change transitive dependencies
   packaging>=25.0,<26.0
   fsspec>=2023.1.0,<2025.0.0
   ```
2. Verify: `pip install -r requirements.txt` completes with zero warnings

**Acceptance Criteria (from requirements.md FR-1):**
- [ ] `dspy==3.2.0` present
- [ ] `langgraph==0.2.76` present
- [ ] `openai==2.32.0` present
- [ ] `numpy==2.4.4` present
- [ ] `datasets==2.21.0` present
- [ ] `packaging>=25.0,<26.0` present
- [ ] `fsspec>=2023.1.0,<2025.0.0` present
- [ ] `torch` NOT in requirements.txt
- [ ] `pip install -r requirements.txt` zero version conflict warnings

**Verification Commands:**
```bash
pip install -r requirements.txt  # should complete cleanly
```

**Estimate:** 2-3 min (pip install time: 30-60s)

---

## Task 3: Update requirements-dev.txt and pyproject.toml

**Purpose:** Move openai from dev to runtime, update pyproject dependencies and coverage config.

**Steps:**
1. **requirements-dev.txt:** Remove `openai>=1.0.0` line. Keep everything else.
2. **pyproject.toml — `[project].dependencies`:** Replace with:
   ```toml
   dependencies = [
       "PyYAML>=6.0",
       "pydantic>=2.0",
       "requests>=2.28",
       "google-genai>=1.0",
       "python-dotenv>=1.0",
       "tqdm>=4.64",
       "dspy>=3.2.0,<4.0.0",
       "langgraph>=0.2.76,<1.0.0",
       "openai==2.32.0",
       "numpy==2.4.4",
       "datasets==2.21.0",
       "httpx>=0.27",
       "huggingface-hub>=0.22",
       "tiktoken>=0.7",
       "click>=8.1",
   ]
   ```
3. **pyproject.toml — `[project.optional-dependencies].dev`:** Remove `openai`:
   ```toml
   dev = [
       "pytest>=9.0",
       "pytest-cov>=7.0",
       "pytest-randomly>=3.0",
       "pytest-asyncio>=0.24",
       "psutil>=5.9",
       "ruff>=0.9",
   ]
   ```
4. **pyproject.toml — `[tool.coverage.run].source`:** Add `infrastructure`:
   ```toml
   source = ["src/audit", "src/utils", "src/factory", "src/curation", "src/discovery", "infrastructure"]
   ```

**Acceptance Criteria (from requirements.md FR-1):**
- [ ] `openai` removed from requirements-dev.txt
- [ ] `openai` NOT in pyproject.toml dev section
- [ ] All new pins present in pyproject.toml `[project].dependencies`
- [ ] `dspy` has `<4.0.0` upper bound
- [ ] `langgraph` has `<1.0.0` upper bound
- [ ] Coverage source includes `infrastructure`
- [ ] `pip install .` includes all expected dependencies

**Verification Commands:**
```bash
pip install -r requirements-dev.txt  # should complete cleanly
pip install .  # should succeed
```

**Estimate:** 5-10 min

---

## Task 4: Update scripts/check_headers.py

**Purpose:** Add `infrastructure/` to the header check include prefixes.

**Steps:**
1. Add `"infrastructure/",` to `INCLUDE_PREFIXES` tuple in `scripts/check_headers.py`

**Acceptance Criteria (from requirements.md FR-4):**
- [ ] `scripts/check_headers.py --check` passes for all new Python files

**Verification Commands:**
```bash
python scripts/check_headers.py --check
```

**Estimate:** < 1 min

---

## Task 5: Create docs/dependency-compatibility.md

**Purpose:** Single reference document covering CVEs, downgrades, install baselines, Python 3.14 caveats, version pinning rationale, optional torch, maintenance.

**Sections (from requirements.md FR-2):**
1. Full dependency tree (transitive) with table
2. CVE section — 6 litellm 1.82.6 CVEs with IDs, severity, status
3. Version pinning rationale — release cadences, why `==` pins required
4. Expected downgrades — packaging, fsspec with explanations
5. Python 3.14 caveats — tokenizers/tiktoken no wheels, Rust toolchain mitigation
6. Install baselines — measured times and disk usage
7. Optional torch — CPU-only install instructions
8. Monitoring and maintenance — how to update pins, CVE monitoring, decision gate tracking

**Acceptance Criteria (from requirements.md FR-2):**
- [ ] Document covers: full dependency tree, CVE section, Python 3.14 caveats, version pinning rationale, known risks and mitigations, installation instructions
- [ ] All 6 CVE IDs listed: GHSA-r75f-5x8p-qvmc, GHSA-jjhc-v7c2-5hh6, GHSA-v4p8-mg3p-g94g, GHSA-xqmj-j6mv-4862, GHSA-69x8-hrgq-fjj8, GHSA-53mr-6c8q-9789
- [ ] Release cadences documented (litellm 2.4 days, openai 5-7 days, dspy 1-3 months)
- [ ] Python 3.14 section with tokenizers/tiktoken caveat + Rust mitigation
- [ ] Install baselines: 30-60s no torch, 2-5 min with torch CPU; 595 MB / 2.1 GB / 3.6 GB
- [ ] Optional torch section with CPU-only install instructions
- [ ] Downgrades section for packaging and fsspec
- [ ] langchain-core exclusion list documented as known fragility

**Estimate:** 10-15 min

---

## Task 6: Final Verification Gate

**Purpose:** Run all verification commands from the design's pre-merge checklist.

**Steps:**
1. `ruff check infrastructure/` — zero errors
2. `pyright --strict infrastructure/dependency_check.py` — zero errors
3. `python scripts/check_headers.py --check` — all new files pass
4. `python infrastructure/dependency_check.py` — exit code 0
5. `pip install -r requirements.txt` — zero warnings
6. `python -c "import numpy; print(numpy.__version__)"` — succeeds
7. `python -c "import dspy; print(dspy.__version__)"` — succeeds
8. `python -c "import langgraph; print(langgraph.__version__)"` — succeeds
9. `python -c "import datasets; print(datasets.__version__)"` — succeeds

**Acceptance Criteria (from requirements.md FR-4 + FR-1):**
- [ ] `ruff check infrastructure/` passes with zero errors
- [ ] `pyright --strict infrastructure/dependency_check.py` passes with zero errors
- [ ] `scripts/check_headers.py --check` passes for all new Python files
- [ ] No bare except clauses in new code
- [ ] No import-time side effects
- [ ] `pip install -r requirements.txt` zero warnings
- [ ] numpy imports succeed in `src/audit/eval_bpb.py:30` context
- [ ] numpy imports succeed in `scripts/benchmark/measure_performance.py:34` context

**Estimate:** 5-10 min

---

## Task 7: Decision Gate Sign-off

**Purpose:** Document the human sign-off for the litellm CVE acceptance before merge.

**Steps:**
1. Add a signed decision gate section to `specs/dependency-compatibility/requirements.md` (inline in the existing Decision Gate section)
2. Record: ACCEPTED / BLOCKED / DEFERRED, signatory, date

**Acceptance Criteria (from requirements.md Decision Gate):**
- [ ] Decision recorded: ACCEPTED / BLOCKED / DEFERRED
- [ ] Re-review date recorded (if DEFERRED)
- [ ] Signed by tech lead or security lead

**Note:** This is a human-only step. The executor can create a placeholder and flag it for manual completion.

**Estimate:** < 1 min (placeholder)

---

## Execution Order

```
Task 0 (create infrastructure/)
    → Task 1 (dependency_check.py)
    → Task 2 (requirements.txt)
    → Task 3 (requirements-dev.txt + pyproject.toml)
    → Task 4 (check_headers.py)
    → Task 5 (docs/dependency-compatibility.md)
    → Task 6 (final verification)
    → Task 7 (decision gate)
```

All tasks sequential — each depends on the previous output.

---

## Quality Gates

| Gate | After | Checks |
|------|-------|--------|
| G1 | Task 1 | ruff + pyright --strict + headers + runs with exit 0 |
| G2 | Task 3 | pip install clean |
| G3 | Task 6 | Full verification suite |
