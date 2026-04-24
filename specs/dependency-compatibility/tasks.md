# Tasks: Dependency Compatibility

## Summary

XS spec — all deliverables already committed to branch `rfactory-factory-frameworks`.
Tasks are verification-only. Consolidated into **7 tasks** (no redundancy).

## AC Coverage Matrix

| AC Source | Verified By |
|-----------|-------------|
| FR-1: requirements.txt pins | T-01 |
| FR-1: torch NOT in requirements.txt | T-01 |
| FR-1: pip install zero warnings | T-03 |
| FR-1: openai removed from dev | T-01 |
| FR-1: pyproject.toml deps + coverage | T-02 |
| FR-2: docs sections + CVE IDs | T-03 |
| FR-2: langchain-core documented | T-03 |
| FR-3: dependency_check.py — copyright, typing, no side effects | T-01 |
| FR-3: script runs exit 0 | T-01 |
| FR-3: extensible (requirements.txt parsing) | T-01 |
| FR-3: no bare except | T-01 |
| FR-3: single logger | T-01 |
| FR-4: ruff check passes | T-01 |
| FR-4: check_headers passes | T-02 |
| FR-4: pyright --strict | SKIPPED (not installed in venv — noted in design) |
| Decision Gate: documented | T-07 |

---

## T-01: Verify Core Deliverables

**Do:** Run a single consolidated verification script covering all core deliverables:

```bash
# requirements.txt — all pins present, torch absent
grep -q 'dspy==3.2.0' requirements.txt
grep -q 'langgraph==0.2.76' requirements.txt
grep -q 'openai==2.32.0' requirements.txt
grep -q 'numpy==2.4.4' requirements.txt
grep -q 'datasets==2.21.0' requirements.txt
grep -q 'packaging>=25.0,<26.0' requirements.txt
grep -q 'fsspec>=2023.1.0,<2025.0.0' requirements.txt
! grep -q 'torch' requirements.txt

# requirements-dev.txt — openai absent
! grep -q 'openai' requirements-dev.txt

# dependency_check.py — key attributes
grep -q '__all__: list\[str\] = \[\]' infrastructure/dependency_check.py
grep -q 'if __name__ == "__main__":' infrastructure/dependency_check.py
grep -q 'logger = logging.getLogger(__name__)' infrastructure/dependency_check.py
! grep -q 'except:' infrastructure/dependency_check.py || grep -q 'except (FileNotFoundError' infrastructure/dependency_check.py
grep -q '@dataclass(frozen=True)' infrastructure/dependency_check.py
grep -q 'OPTIONAL_PACKAGES' infrastructure/dependency_check.py

# ruff
ruff check infrastructure/

# script execution
python infrastructure/dependency_check.py
```

**Files:** requirements.txt, requirements-dev.txt, infrastructure/dependency_check.py

**Done when:** All commands return exit code 0.

**Commit:** `spec(dependency-compatibility): verify core deliverables`

---

## T-02: Verify pyproject.toml and Headers

**Do:**

```bash
# pyproject.toml — new deps
grep -q 'dspy>=3.2.0,<4.0.0' pyproject.toml
grep -q 'langgraph>=0.2.76,<1.0.0' pyproject.toml
grep -q 'openai==2.32.0' pyproject.toml
grep -q 'numpy==2.4.4' pyproject.toml
grep -q 'datasets==2.21.0' pyproject.toml

# coverage source includes infrastructure
grep -q '"infrastructure"' pyproject.toml

# dev section retains pytest deps
grep -q 'pytest-cov' pyproject.toml
grep -q 'pytest-randomly' pyproject.toml
grep -q 'pytest-asyncio' pyproject.toml

# check_headers passes
python scripts/check_headers.py --check
```

**Files:** pyproject.toml, scripts/check_headers.py

**Done when:** All commands return exit code 0.

**Commit:** `spec(dependency-compatibility): verify pyproject.toml and headers`

---

## T-03: Verify Documentation

**Do:**

```bash
# docs sections present
grep -q '## 2. CVE and Security' docs/dependency-compatibility.md
grep -q '## 3. Version Pinning Rationale' docs/dependency-compatibility.md
grep -q '## 4. Expected Downgrades' docs/dependency-compatibility.md
grep -q '## 5. Python 3.14 Caveats' docs/dependency-compatibility.md
grep -q '## 6. Installation Instructions' docs/dependency-compatibility.md
grep -q '## 7. Baselines Medidos' docs/dependency-compatibility.md || grep -q '## 7. Installation Baselines' docs/dependency-compatibility.md
grep -q '## 8. Optional: Torch' docs/dependency-compatibility.md

# All 6 CVE IDs
for cve in GHSA-r75f-5x8p-qvmc GHSA-jjhc-v7c2-5hh6 GHSA-v4p8-mg3p-g94g GHSA-xqmj-j6mv-4862 GHSA-69x8-hrgq-fjj8 GHSA-53mr-6c8q-9789; do
  grep -q "$cve" docs/dependency-compatibility.md || echo "MISSING: $cve"
done

# langchain-core fragility documented
grep -q 'langchain-core' docs/dependency-compatibility.md
```

**Files:** docs/dependency-compatibility.md

**Done when:** All commands return exit code 0, no MISSING output.

**Commit:** `spec(dependency-compatibility): verify documentation`

---

## T-04: Verify Import Success

**Do:**

```bash
python -c "import numpy; print(numpy.__version__)"
python -c "import dspy; print(dspy.__version__)"
python -c "import langgraph; print(langgraph.__version__)"
python -c "import datasets; print(datasets.__version__)"
python -c "import openai; print(openai.__version__)"
```

**Files:** (runtime verification)

**Done when:** All imports succeed with no errors.

**Commit:** `spec(dependency-compatibility): verify imports`

---

## T-05: Install Verification

**Do:**

```bash
pip install -r requirements.txt 2>&1 | tee /tmp/pip-install.log
# Check for version conflict warnings (not just exit code)
grep -i 'conflict\|incompatible\|requires.*but' /tmp/pip-install.log && echo "WARNINGS FOUND" || echo "NO CONFLICTS"
```

**Files:** requirements.txt (runtime verification)

**Done when:** No version conflict warnings in pip output.

**Commit:** `spec(dependency-compatibility): verify clean install`

---

## T-06: Decision Gate Check

**Do:**

```bash
grep -q 'Decision Gate' specs/dependency-compatibility/requirements.md
grep -q 'P0' specs/dependency-compatibility/requirements.md
grep -q 'Decision Gate' docs/dependency-compatibility.md
grep -q 'P0' docs/dependency-compatibility.md
echo "Decision gate documented"
```

**Files:** specs/dependency-compatibility/requirements.md, docs/dependency-compatibility.md

**Done when:** All greps pass. Decision gate requires manual sign-off (accept/block/defer) before merge.

**Commit:** `spec(dependency-compatibility): verify decision gate documented`

---

## Execution Order

All tasks independent (no dependencies between them). Run in any order.

| Task | What it checks | Estimated time |
|------|---------------|----------------|
| T-01 | Core deliverables (pins, script attrs, ruff, execution) | 30s |
| T-02 | pyproject.toml, headers | 10s |
| T-03 | Documentation sections + CVEs + langchain-core | 10s |
| T-04 | Import verification (numpy, dspy, langgraph, datasets, openai) | 10s |
| T-05 | Clean pip install (no warnings) | 30-60s |
| T-06 | Decision gate documentation | 5s |

## Notes

- **pyright --strict:** Not verified — not installed in this venv. Design ran 0 errors on initial check.
- **Unit tests:** Not included — XS spec, POC-first approach defers testing.
- **Decision gate:** litellm CVE acceptance requires human sign-off before merge. Documented in both requirements.md and docs/.
