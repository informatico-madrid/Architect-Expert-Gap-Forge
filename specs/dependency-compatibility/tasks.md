# Tasks: Dependency Compatibility (v3.0 with Quality Gates)

## Summary

XS spec — all deliverables already committed to branch `rfactory-factory-frameworks`.
Tasks are verification-only with adversarial quality gates.
14 tasks + 5 quality gates = 19 items total.

## Quality Gate Protocol

Each QG task spawns a DIFFERENT adversarial review sub-agent whose ONLY mission is to FIND REASONS TO REJECT.

**QG Verdicts:**
- `APPROVE` — deliverables pass all checks. Continue to next task.
- `REJECT` — UNDO to last passing task. Re-verify with sub-agent's specific recommendations. Max 2 retries.
- `ESCALATE` — repeated rejection after 2 retries. Human review required.

**Sub-Agent Rotation:**
| Gate | Reviewer Role | Focus |
|------|--------------|-------|
| QG-01 | Product reviewer | Version pin rationale, missing packages, cross-file conflicts |
| QG-02 | Architecture reviewer | Bounded ranges, coverage config, ruff + headers |
| QG-03 | Code quality reviewer | Copyright, typing, dataclasses, exception handling |
| QG-04 | Research reviewer | Documentation sections, CVE accuracy, decision gate |
| QG-05 | Chief reviewer (final) | Full AC coverage, integration correctness, undo/redo audit |

**UNDO + REDO Flow:**
1. QG verdict = REJECT
2. Read sub-agent findings for specific recommendations
3. Re-verify last task from the rejected gate's phase with recommendations applied
4. Re-submit to QG
5. Max 2 retries before ESCALATE

## AC Coverage Matrix

| AC Source | Verified By |
|-----------|-------------|
| FR-1: requirements.txt pins | T-01, QG-01 |
| FR-1: torch NOT in requirements.txt | T-01, T-13 |
| FR-1: openai removed from dev | T-02 |
| FR-1: pyproject.toml deps + coverage | T-04, T-05, QG-02 |
| FR-2: docs sections + CVE IDs | T-09, T-10, QG-04 |
| FR-2: langchain-core documented | T-10 |
| FR-2: expected downgrades documented | T-10 |
| FR-3: dependency_check.py structure | T-07, T-08, QG-03 |
| FR-3: script runs exit 0 | T-08 |
| FR-4: ruff check passes | T-06, QG-02 |
| FR-4: check_headers passes | T-05 |
| NFR-1: import verification | T-03, QG-01 |
| NFR-4: Python 3.14 caveats | T-10, QG-04 |
| Decision Gate: documented | T-11, QG-04, QG-05 |

---

## Phase 1: Requirements Files

- [x] 01: [VERIFY] requirements.txt version pins
- [x] 02: [VERIFY] requirements-dev.txt
- [x] 03: [VERIFY] import success
- [x] QG-01: [QUALITY] Adversarial Review — Requirements Files (Product Reviewer) — **APPROVED**

---

- [x] 04: [VERIFY] pyproject.toml dependencies
- [x] 05: [VERIFY] headers and coverage config
- [x] 06: [VERIFY] ruff compliance
- [x] QG-02: [QUALITY] Adversarial Review — pyproject.toml and Tooling (Architecture Reviewer) — **APPROVED**

---

- [x] 07: [VERIFY] script structure
- [x] 08: [VERIFY] script execution
- [x] QG-03: [QUALITY] Adversarial Review — dependency_check.py (Code Quality Reviewer) — **APPROVED**

---

- [x] 09: [VERIFY] documentation sections
- [x] 10: [VERIFY] CVE IDs and langchain-core documentation
- [x] 11: [VERIFY] decision gate documentation
- [x] QG-04: [QUALITY] Adversarial Review — Documentation (Research Reviewer) — **APPROVED**

---

- [x] 12: [VERIFY] pip install cleanliness
- [x] 13: [VERIFY] torch documented as optional
- [x] 14: [VERIFY] final integration — run full dependency check
- [x] QG-05: [QUALITY] Final Adversarial Review (Chief Reviewer) — **APPROVED**

---

## Detailed Task Definitions

### T-01: Verify requirements.txt Version Pins

**Do:**
```bash
# Exact pins for new/moved packages
grep -q 'dspy==3.2.0' requirements.txt
grep -q 'langgraph==0.2.76' requirements.txt
grep -q 'openai==2.32.0' requirements.txt
grep -q 'numpy==2.4.4' requirements.txt
grep -q 'datasets==2.21.0' requirements.txt

# Bounded ranges for transitive deps
grep -q 'packaging>=25.0,<26.0' requirements.txt
grep -q 'fsspec>=2023.1.0,<2025.0.0' requirements.txt

# torch NOT in requirements.txt
! grep -q 'torch' requirements.txt
```

**Files:** requirements.txt

**Done when:** All greps return exit 0, torch absent.

**Verify:** `grep 'dspy\|langgraph\|openai\|numpy\|datasets\|packaging\|fsspec' requirements.txt && ! grep -q 'torch' requirements.txt && echo T-01_PASS`

**Commit:** `spec(dependency-compatibility): verify requirements.txt pins`

---

### T-02: Verify requirements-dev.txt

**Do:**
```bash
# openai removed from dev
! grep -q 'openai' requirements-dev.txt

# Runtime deps pulled in via requirements.txt
grep -q '-r requirements.txt' requirements-dev.txt

# Dev deps retained
grep -q 'pytest-cov' requirements-dev.txt
grep -q 'pytest-randomly' requirements-dev.txt
grep -q 'pytest-asyncio' requirements-dev.txt
grep -q 'ruff' requirements-dev.txt
```

**Files:** requirements-dev.txt

**Done when:** openai absent, dev deps retained, runtime deps pulled in.

**Verify:** `! grep -q 'openai' requirements-dev.txt && grep -q 'pytest-cov' requirements-dev.txt && echo T-02_PASS`

**Commit:** `spec(dependency-compatibility): verify requirements-dev.txt`

---

### T-03: Verify Import Success

**Do:**
```bash
python -c "import numpy; print(numpy.__version__)"
python -c "import dspy; print(dspy.__version__)"
python -c "import langgraph; print(langgraph.__version__)"
python -c "import datasets; print(datasets.__version__)"
python -c "import openai; print(openai.__version__)"
```

**Files:** (runtime verification — no file changes)

**Done when:** All imports succeed with no errors, version printed.

**Verify:** `python -c "import numpy; import dspy; import langgraph; import datasets; import openai; print('ALL_IMPORTS_OK')"`

**Commit:** `spec(dependency-compatibility): verify imports`

---

### QG-01: Adversarial Review — Requirements Files (Product Reviewer)

**Do:** Spawn an adversarial reviewer agent. Give it requirements.txt, requirements-dev.txt, requirements.md v2.1. Ask it to verify what T-01/T-02/T-03 actually check:

1. Cross-check each version pin in requirements.txt against requirements.md AC (7 pins + torch absent)
2. Verify no conflicting ranges between requirements.txt and pyproject.toml
3. Verify openai is properly moved from dev→runtime (absent in dev, present in runtime)

**Review checklist (map each to a verified task):**
- T-01: 7 version pins match requirements.txt (dspy==3.2.0, langgraph==0.2.76, openai==2.32.0, numpy==2.4.4, datasets==2.21.0, packaging>=25.0,<26.0, fsspec>=2023.1.0,<2025.0.0)
- T-01: torch is NOT in requirements.txt
- T-02: openai is NOT in requirements-dev.txt
- T-02: pytest-cov, pytest-randomly, pytest-asyncio, ruff retained in dev
- T-03: All 5 imports succeed (numpy, dspy, langgraph, datasets, openai)

**Reject if:** Any checklist item fails against the actual file contents.

**Commit:** (none — review only)

---

### T-04: Verify pyproject.toml Dependencies

**Do:**
```bash
# New deps present with correct version constraints
grep -q 'dspy>=3.2.0,<4.0.0' pyproject.toml
grep -q 'langgraph>=0.2.76,<1.0.0' pyproject.toml
grep -q 'openai==2.32.0' pyproject.toml
grep -q 'numpy==2.4.4' pyproject.toml
grep -q 'datasets==2.21.0' pyproject.toml
```

**Files:** pyproject.toml

**Done when:** All 5 new deps present with correct constraints.

**Verify:** `grep 'dspy\|langgraph\|openai\|numpy\|datasets' pyproject.toml && echo T-04_PASS`

**Commit:** `spec(dependency-compatibility): verify pyproject.toml deps`

---

### T-05: Verify Headers and Coverage Config

**Do:**
```bash
# Coverage source includes infrastructure
grep -q '"infrastructure"' pyproject.toml

# Dev section retains pytest deps
grep -q 'pytest-cov' pyproject.toml
grep -q 'pytest-randomly' pyproject.toml
grep -q 'pytest-asyncio' pyproject.toml

# check_headers passes
python scripts/check_headers.py --check
```

**Files:** pyproject.toml, scripts/check_headers.py

**Done when:** Coverage includes infrastructure, headers check passes.

**Verify:** `python scripts/check_headers.py --check && grep -q '"infrastructure"' pyproject.toml && echo T-05_PASS`

**Commit:** `spec(dependency-compatibility): verify headers and coverage`

---

### T-06: Verify Ruff Compliance

**Do:**
```bash
ruff check infrastructure/
```

**Files:** infrastructure/

**Done when:** ruff exits 0 with no violations.

**Verify:** `ruff check infrastructure/ && echo T-06_PASS`

**Commit:** `spec(dependency-compatibility): verify ruff compliance`

---

### QG-02: Adversarial Review — pyproject.toml and Tooling (Architecture Reviewer)

**Do:** Spawn an adversarial reviewer agent. Give it pyproject.toml, requirements.txt, requirements.md v2.1. Ask it to verify what T-04/T-05/T-06 actually check:

1. Cross-check each dependency in pyproject.toml against requirements.txt pins
2. Verify bounded ranges in pyproject.toml match requirements.txt
3. Verify check_headers.py and ruff pass

**Review checklist (map each to a verified task):**
- T-04: dspy>=3.2.0,<4.0.0 present in pyproject.toml
- T-04: langgraph>=0.2.76,<1.0.0 present in pyproject.toml
- T-04: openai==2.32.0 present in pyproject.toml
- T-04: numpy==2.4.4 present in pyproject.toml
- T-04: datasets==2.21.0 present in pyproject.toml
- T-05: "infrastructure" in coverage source list
- T-05: pytest-cov, pytest-randomly, pytest-asyncio in dev section
- T-05: scripts/check_headers.py --check exits 0
- T-06: ruff check infrastructure/ exits 0

**Reject if:** Any checklist item fails against the actual file contents.

**Commit:** (none — review only)

---

### T-07: Verify Script Structure

**Do:**
```bash
# Key attributes per FR-3
grep -q '__all__: list\[str\] = \[\]' infrastructure/dependency_check.py
grep -q 'if __name__ == "__main__":' infrastructure/dependency_check.py
grep -q 'logger = logging.getLogger(__name__)' infrastructure/dependency_check.py
grep -q '@dataclass(frozen=True)' infrastructure/dependency_check.py
grep -q 'OPTIONAL_PACKAGES' infrastructure/dependency_check.py

# Copyright header
grep -q 'AEGF' infrastructure/dependency_check.py
grep -q 'Copyright 2026' infrastructure/dependency_check.py
grep -q 'SPDX-License-Identifier: Apache-2.0' infrastructure/dependency_check.py

# No bare except
! grep -q '^except:' infrastructure/dependency_check.py || grep -q 'except (FileNotFoundError' infrastructure/dependency_check.py
```

**Files:** infrastructure/dependency_check.py, infrastructure/__init__.py

**Done when:** All structural checks pass, copyright present, no bare except.

**Verify:** `grep -q 'if __name__ == "__main__":' infrastructure/dependency_check.py && grep -q 'SPDX-License-Identifier: Apache-2.0' infrastructure/dependency_check.py && ! grep -q '^except:' infrastructure/dependency_check.py && echo T-07_PASS`

**Commit:** `spec(dependency-compatibility): verify script structure`

---

### T-08: Verify Script Execution

**Do:**
```bash
# Run the script — must exit 0
python infrastructure/dependency_check.py

# Verify numpy imports in existing source (bugfix)
grep -n 'import numpy' src/audit/eval_bpb.py
grep -n 'import numpy' scripts/benchmark/measure_performance.py
```

**Files:** infrastructure/dependency_check.py

**Done when:** Script runs exit 0, numpy imports verified in source.

**Verify:** `python infrastructure/dependency_check.py && echo T-08_PASS`

**Commit:** `spec(dependency-compatibility): verify script execution`

---

### QG-03: Adversarial Review — dependency_check.py (Code Quality Reviewer)

**Do:** Spawn an adversarial reviewer agent. Give it infrastructure/dependency_check.py, requirements.md FR-3. Ask it to verify what T-07/T-08 actually check:

1. Read the actual file and confirm each structural property T-07 greps for is genuinely present
2. Verify the script exit 0 (T-08) against the actual behavior
3. Check that each grep pattern in T-07 actually matches real content in the file

**Review checklist (map each to a verified task):**
- T-07: `__all__: list[str] = []` present
- T-07: `if __name__ == "__main__":` guard present
- T-07: `logger = logging.getLogger(__name__)` single logger present
- T-07: `@dataclass(frozen=True)` present (2 frozen dataclasses)
- T-07: `OPTIONAL_PACKAGES` frozenset present
- T-07: Copyright header: AEGF, Copyright 2026, SPDX-License-Identifier: Apache-2.0
- T-07: No bare `except:` clauses (only explicit exception types like FileNotFoundError, TimeoutExpired)
- T-08: `python infrastructure/dependency_check.py` exits 0
- T-08: numpy imports verified in src/audit/eval_bpb.py and scripts/benchmark/measure_performance.py

**Reject if:** Any checklist item doesn't match actual file content, or script doesn't exit 0.

**Commit:** (none — review only)

---

### T-09: Verify Documentation Sections

**Do:**
```bash
# All required sections present
grep -q '## 2. CVE and Security' docs/dependency-compatibility.md
grep -q '## 3. Version Pinning Rationale' docs/dependency-compatibility.md
grep -q '## 4. Expected Downgrades' docs/dependency-compatibility.md
grep -q '## 5. Python 3.14 Caveats' docs/dependency-compatibility.md
grep -q '## 6. Installation Instructions' docs/dependency-compatibility.md
grep -q '## 7. Installation Baselines' docs/dependency-compatibility.md || grep -q '## 7. Baseline' docs/dependency-compatibility.md
grep -q '## 8. Optional: Torch' docs/dependency-compatibility.md
```

**Files:** docs/dependency-compatibility.md

**Done when:** All 7 required sections present.

**Verify:** `grep -q '## 2. CVE and Security' docs/dependency-compatibility.md && grep -q '## 3. Version Pinning Rationale' docs/dependency-compatibility.md && grep -q '## 8. Optional: Torch' docs/dependency-compatibility.md && echo T-09_PASS`

**Commit:** `spec(dependency-compatibility): verify documentation sections`

---

### T-10: Verify CVE IDs and Langchain-Core Documentation

**Do:**
```bash
# All 6 CVE IDs present
CVE_MISSING=0
for cve in GHSA-r75f-5x8p-qvmc GHSA-jjhc-v7c2-5hh6 GHSA-v4p8-mg3p-g94g GHSA-xqmj-j6mv-4862 GHSA-69x8-hrgq-fjj8 GHSA-53mr-6c8q-9789; do
  grep -q "$cve" docs/dependency-compatibility.md || CVE_MISSING=1
done
if [ "$CVE_MISSING" -eq 1 ]; then
  echo "FAIL: one or more CVE IDs missing from docs"
  exit 1
fi

# langchain-core fragility documented
grep -q 'langchain-core' docs/dependency-compatibility.md

# Expected downgrades documented
grep -qi 'downgrad' docs/dependency-compatibility.md
```

**Files:** docs/dependency-compatibility.md

**Done when:** All 6 CVE IDs present, langchain-core documented, downgrades documented.

**Verify:** `python -c "
cves = ['GHSA-r75f-5x8p-qvmc','GHSA-jjhc-v7c2-5hh6','GHSA-v4p8-mg3p-g94g','GHSA-xqmj-j6mv-4862','GHSA-69x8-hrgq-fjj8','GHSA-53mr-6c8q-9789']
text = open('docs/dependency-compatibility.md').read()
missing = [c for c in cves if c not in text]
assert not missing, f'Missing CVEs: {missing}'
print('ALL_CVES_PRESENT')
"`

**Commit:** `spec(dependency-compatibility): verify CVEs and langchain-core`

---

### T-11: Verify Decision Gate Documentation

**Do:**
```bash
# Decision gate documented in requirements.md
grep -q 'Decision Gate' specs/dependency-compatibility/requirements.md
grep -q 'P0' specs/dependency-compatibility/requirements.md

# Decision gate documented in docs
grep -q 'Decision Gate' docs/dependency-compatibility.md
grep -q 'P0' docs/dependency-compatibility.md
```

**Files:** specs/dependency-compatibility/requirements.md, docs/dependency-compatibility.md

**Done when:** P0 decision gate documented in both locations.

**Verify:** `grep -q 'Decision Gate' specs/dependency-compatibility/requirements.md && grep -q 'P0' docs/dependency-compatibility.md && echo T-11_PASS`

**Commit:** `spec(dependency-compatibility): verify decision gate documented`

---

### QG-04: Adversarial Review — Documentation (Research Reviewer)

**Do:** Spawn an adversarial reviewer agent. Give it docs/dependency-compatibility.md, requirements.md, research findings from .progress.md. Ask it to verify what T-09/T-10/T-11 actually check:

1. Read the actual docs/dependency-compatibility.md and confirm each section T-09 greps for exists
2. Read the actual docs and confirm each CVE ID T-10 checks for is present
3. Verify decision gate P0 documented in both requirements.md and docs/ (T-11)

**Review checklist (map each to a verified task):**
- T-09: "## 2. CVE and Security" section present
- T-09: "## 3. Version Pinning Rationale" section present
- T-09: "## 4. Expected Downgrades" section present
- T-09: "## 5. Python 3.14 Caveats" section present
- T-09: "## 6. Installation Instructions" section present
- T-09: "## 7. Installation Baselines" OR "## 7. Baseline" section present
- T-09: "## 8. Optional: Torch" section present
- T-10: All 6 CVE IDs present (GHSA-r75f-5x8p-qvmc, GHSA-jjhc-v7c2-5hh6, GHSA-v4p8-mg3p-g94g, GHSA-xqmj-j6mv-4862, GHSA-69x8-hrgq-fjj8, GHSA-53mr-6c8q-9789)
- T-10: "langchain-core" present in docs
- T-10: "downgrad" (case-insensitive) present in docs
- T-11: Decision Gate + P0 in specs/dependency-compatibility/requirements.md
- T-11: Decision Gate + P0 in docs/dependency-compatibility.md

**Reject if:** Any checklist item doesn't match actual file content.

**Commit:** (none — review only)

---

### T-12: Verify pip Install Cleanliness

**Do:**
```bash
pip install -r requirements.txt 2>&1 | tee /tmp/pip-install.log
# Check for version conflict warnings (not just exit code)
if grep -qi 'conflict\|incompatible\|requires.*but' /tmp/pip-install.log; then
  echo "FAIL: version conflicts detected"
  exit 1
fi
echo "No version conflicts"
```

**Files:** requirements.txt (runtime verification)

**Done when:** No version conflict warnings in pip output.

**Verify:** `pip install -r requirements.txt 2>&1 | tee /tmp/pip-install.log && ! grep -qi 'conflict\|incompatible\|requires.*but' /tmp/pip-install.log && echo T-12_PASS`

**Commit:** `spec(dependency-compatibility): verify clean install`

---

### T-13: Verify Torch Documented as Optional

**Do:**
```bash
# Torch should NOT be in requirements.txt (only documented as optional)
! grep -q 'torch' requirements.txt

# Torch SHOULD be documented as optional in docs
grep -q 'torch' docs/dependency-compatibility.md
grep -q 'optional' docs/dependency-compatibility.md
```

**Files:** requirements.txt, docs/dependency-compatibility.md

**Done when:** torch absent from requirements.txt, documented as optional in docs.

**Verify:** `! grep -q 'torch' requirements.txt && grep -q 'torch' docs/dependency-compatibility.md && echo T-13_PASS`

**Commit:** `spec(dependency-compatibility): verify torch documented as optional`

---

### T-14: Final Integration — Run Full Dependency Check

**Do:**
```bash
# Run the complete validation script
python infrastructure/dependency_check.py

# Verify ruff still passes
ruff check infrastructure/

# Verify all imports still work
python -c "import numpy; import dspy; import langgraph; import datasets; import openai; print('FINAL_IMPORTS_OK')"
```

**Files:** infrastructure/dependency_check.py

**Done when:** All three checks pass (script, ruff, imports).

**Verify:** `python infrastructure/dependency_check.py && ruff check infrastructure/ && python -c "import numpy; import dspy; import langgraph; import datasets; import openai" && echo T-14_PASS`

**Commit:** `spec(dependency-compatibility): final integration verification`

---

### QG-05: Final Adversarial Review (Chief Reviewer)

**Do:** Spawn an adversarial review agent as the final gate. Give it:
- requirements.md v2.1 (all FR + NFR)
- All 14 task results
- All QG-01 through QG-04 verdicts

Ask it to:
1. Cross-check each FR/AC against the specific tasks that verify it (AC Coverage Matrix)
2. Verify no tasks were skipped or falsely marked complete
3. Confirm P0 decision gate human sign-off requirement is documented (not that it's signed — sign-off requires human)

**Review checklist (map each FR to verified tasks):**
- FR-1 (requirements pins): T-01, T-04, T-12 all pass
- FR-1 (torch absent): T-01 passes
- FR-1 (openai removed from dev): T-02 passes
- FR-1 (numpy imports in source): T-08 passes
- FR-2 (docs sections + CVE): T-09, T-10 pass
- FR-2 (langchain-core documented): T-10 passes
- FR-2 (expected downgrades documented): T-10 passes
- FR-3 (dependency_check.py structure): T-07 passes
- FR-3 (script exit 0): T-08 passes
- FR-3 (extensible requirements.txt parsing): T-07 checks PACKAGE_IMPORT_MAP
- FR-3 (no bare except): T-07 passes
- FR-3 (single logger): T-07 checks logger pattern
- FR-4 (ruff check): T-06 passes
- FR-4 (check_headers): T-05 passes
- Decision Gate P0 documented: T-11 passes

**Reject if:** Any FR has no corresponding passing task, or any QG verdict is not APPROVE.

**Commit:** (none — review only)

---

## Execution Order

All QG tasks are sequential gatekeepers. Tasks within a phase can run in any order, but QG must APPROVE before the next phase starts.

| Task | What it checks | Estimated time |
|------|---------------|----------------|
| T-01 | requirements.txt pins | 10s |
| T-02 | requirements-dev.txt | 5s |
| T-03 | Import verification | 10s |
| **QG-01** | Adversarial: requirements | 30s |
| T-04 | pyproject.toml deps | 10s |
| T-05 | Headers + coverage | 10s |
| T-06 | Ruff compliance | 10s |
| **QG-02** | Adversarial: pyproject + tooling | 30s |
| T-07 | Script structure | 10s |
| T-08 | Script execution | 15s |
| **QG-03** | Adversarial: code quality | 45s |
| T-09 | Docs sections | 5s |
| T-10 | CVE IDs + langchain-core | 10s |
| T-11 | Decision gate docs | 5s |
| **QG-04** | Adversarial: documentation | 30s |
| T-12 | pip install clean | 60s |
| T-13 | Torch documented as optional | 5s |
| T-14 | Full integration | 30s |
| **QG-05** | Adversarial: final review | 60s |

## Notes

- **pyright --strict:** Not verified — not installed in this venv. Design ran 0 errors on initial check.
- **Unit tests:** Not included — XS spec, coverage target deferred (documented in QG-05).
- **Decision gate:** litellm CVE acceptance requires human sign-off before merge. Documented in both requirements.md and docs/.
- **Torch:** Optional dependency — not in requirements.txt, documented as optional in docs/ section 8 (T-13 verifies this).
