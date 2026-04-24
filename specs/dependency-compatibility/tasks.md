# Tasks: Dependency Compatibility

## Phase 1: Verify Core Implementation (POC)

Focus: Prove all deliverables exist and work. Code is already committed; verify acceptance criteria via automated commands.

- [ ] 1.1 [VERIFY] Verify dependency_check.py passes ruff
  - **Do**: Run ruff on the infrastructure/ directory
  - **Verify**: `ruff check infrastructure/ && echo PASS`
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: Zero lint errors
  - **Commit**: `chore(spec): verify ruff on dependency_check`
  - _Requirements: FR-4, AC (ruff check infrastructure/)_

- [ ] 1.2 [VERIFY] Verify dependency_check.py runs and exits 0
  - **Do**: Run the script; confirm all imports resolve and pip check passes
  - **Verify**: `python infrastructure/dependency_check.py 2>&1 | grep -q "OK: All dependency checks passed" && echo PASS`
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: Exit code 0, stdout contains "OK: All dependency checks passed"
  - **Commit**: `chore(spec): verify dependency_check.py runs`
  - _Requirements: FR-3, AC (exit code 0 success, non-zero on failure)_

- [ ] 1.3 [VERIFY] Verify requirements.txt pins match FR-1
  - **Do**: Check exact pins for all new dependencies via grep
  - **Verify**: `grep -c 'dspy==3.2.0' requirements.txt && grep -c 'langgraph==0.2.76' requirements.txt && grep -c 'openai==2.32.0' requirements.txt && grep -c 'numpy==2.4.4' requirements.txt && grep -c 'datasets==2.21.0' requirements.txt && grep -c 'packaging>=25.0,<26.0' requirements.txt && grep -c 'fsspec>=2023.1.0,<2025.0.0' requirements.txt && echo PASS`
  - **Files**: requirements.txt
  - **Done when**: All 7 pins present, grep returns 1 for each
  - **Commit**: `chore(spec): verify requirements.txt pins`
  - _Requirements: FR-1, AC (all exact pins)_

- [ ] 1.4 [VERIFY] Verify requirements-dev.txt has no openai
  - **Do**: Confirm openai is absent from requirements-dev.txt
  - **Verify**: `! grep -q 'openai' requirements-dev.txt && echo PASS`
  - **Files**: requirements-dev.txt
  - **Done when**: No openai line in dev requirements
  - **Commit**: `chore(spec): verify openai removed from dev`
  - _Requirements: FR-1, AC (openai removed from requirements-dev.txt)_

- [ ] 1.5 [VERIFY] Verify pyproject.toml has correct deps and coverage config
  - **Do**: Check new deps in [project].dependencies and coverage source includes infrastructure/
  - **Verify**: `grep -q 'dspy>=3.2.0,<4.0.0' pyproject.toml && grep -q 'langgraph>=0.2.76,<1.0.0' pyproject.toml && grep -q 'openai==2.32.0' pyproject.toml && grep -q 'numpy==2.4.4' pyproject.toml && grep -q 'datasets==2.21.0' pyproject.toml && grep -q '"infrastructure"' pyproject.toml && echo PASS`
  - **Files**: pyproject.toml
  - **Done when**: All 6 conditions met (dspy range, langgraph range, openai, numpy, datasets, coverage source)
  - **Commit**: `chore(spec): verify pyproject.toml`
  - _Requirements: FR-1, AC (pyproject.toml dependencies + coverage source)_

- [ ] 1.6 [VERIFY] Verify docs/dependency-compatibility.md has all required sections
  - **Do**: Check that the document contains all required sections per FR-2
  - **Verify**: `grep -q '## 2. CVE and Security' docs/dependency-compatibility.md && grep -q '## 3. Version Pinning Rationale' docs/dependency-compatibility.md && grep -q '## 4. Expected Downgrades' docs/dependency-compatibility.md && grep -q '## 5. Python 3.14 Caveats' docs/dependency-compatibility.md && grep -q '## 7. Installation Baselines' docs/dependency-compatibility.md && grep -q '## 8. Optional: Torch' docs/dependency-compatibility.md && grep -q 'GHSA-r75f-5x8p-qvmc' docs/dependency-compatibility.md && grep -q 'GHSA-53mr-6c8q-9789' docs/dependency-compatibility.md && echo PASS`
  - **Files**: docs/dependency-compatibility.md
  - **Done when**: All 8 sections/CVEs present
  - **Commit**: `chore(spec): verify docs sections`
  - _Requirements: FR-2, AC (full section coverage, all 6 CVE IDs)_

## Phase 2: Fix Headers and Minor Issues

Focus: Resolve the check_headers.py failure on infrastructure/__init__.py and verify remaining compliance.

- [ ] 2.1 [VERIFY] Fix infrastructure/__init__.py header to pass check_headers
  - **Do**: Add AEGF copyright header to infrastructure/__init__.py (empty package marker needs header per project convention)
  - **Files**: infrastructure/__init__.py
  - **Done when**: `python scripts/check_headers.py --check` passes for infrastructure/__init__.py
  - **Verify**: `python scripts/check_headers.py --check 2>&1 | grep -q "OK: Todas las cabeceras críticas están presentes" && echo PASS`
  - **Commit**: `fix(spec): add copyright header to infrastructure/__init__.py`

- [ ] 2.2 [VERIFY] Verify dependency_check.py source code quality
  - **Do**: Verify key code quality attributes: no bare except, single logger, __main__ guard, frozen dataclasses
  - **Verify**: `grep -q '__all__: list\[str\] = \[\]' infrastructure/dependency_check.py && grep -q 'if __name__ == "__main__":' infrastructure/dependency_check.py && grep -q 'logger = logging.getLogger(__name__)' infrastructure/dependency_check.py && ! grep -q 'except:' infrastructure/dependency_check.py && grep -q '@dataclass(frozen=True)' infrastructure/dependency_check.py && echo PASS`
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: All 5 code quality attributes confirmed
  - **Commit**: `chore(spec): verify source code quality attributes`
  - _Requirements: FR-3, AC (no bare except, single logger, __main__ guard, frozen dataclasses)_

- [ ] 2.3 [VERIFY] Verify optional packages skip in dependency_check
  - **Do**: Confirm OPTIONAL_PACKAGES is defined and google-genai is skipped during import check
  - **Verify**: `grep -q 'OPTIONAL_PACKAGES.*frozenset' infrastructure/dependency_check.py && python infrastructure/dependency_check.py 2>&1 | grep -q 'Skipping optional package' && echo PASS`
  - **Files**: infrastructure/dependency_check.py
  - **Done when**: OPTIONAL_PACKAGES defined and skip behavior confirmed at runtime
  - **Commit**: `chore(spec): verify optional packages handling`
  - _Requirements: FR-3, AC (extensible parsing)_

## Phase 3: Quality Checkpoints

Focus: Full lint and integration verification.

- [ ] 3.1 [VERIFY] Quality checkpoint: ruff + dependency_check
  - **Do**: Run ruff on infrastructure/ and dependency_check.py one more time after any header fixes
  - **Verify**: `ruff check infrastructure/ && python infrastructure/dependency_check.py && echo PASS`
  - **Done when**: Both commands exit 0
  - **Commit**: `chore(spec): pass quality checkpoint`

- [ ] 3.2 [VERIFY] Verify numpy imports work in existing code
  - **Do**: Confirm numpy can be imported (fixes pre-existing ModuleNotFoundError in eval_bpb.py and measure_performance.py)
  - **Verify**: `python -c "import numpy; print(numpy.__version__)" && python -c "import dspy" && python -c "import langgraph" && python -c "import datasets" && python -c "import openai" && echo PASS`
  - **Done when**: All 5 imports succeed with zero errors
  - **Commit**: `chore(spec): verify numpy and new dep imports`
  - _Requirements: FR-1, AC (numpy imports succeed in eval_bpb.py:30 and measure_performance.py:34)_

## Phase 4: End-to-End Verification

Focus: Run the full pre-merge checklist from the design.

- [ ] 4.1 [VERIFY] Full verification: install and check
  - **Do**: Run the complete pre-merge checklist from design Section 8.3
  - **Verify**: `pip install -r requirements.txt 2>&1 | grep -q 'Successfully installed\|Requirement already satisfied' && python infrastructure/dependency_check.py && ruff check infrastructure/ && echo PASS`
  - **Done when**: All three commands pass (pip install, dependency_check.py, ruff check)
  - **Commit**: `chore(spec): full pre-merge verification`

- [ ] 4.2 [VERIFY] Verify docs CVE list completeness
  - **Do**: Confirm all 6 CVE IDs are present in the docs document
  - **Verify**: `for cve in GHSA-r75f-5x8p-qvmc GHSA-jjhc-v7c2-5hh6 GHSA-v4p8-mg3p-g94g GHSA-xqmj-j6mv-4862 GHSA-69x8-hrgq-fjj8 GHSA-53mr-6c8q-9789; do grep -q "$cve" docs/dependency-compatibility.md || echo MISSING: $cve; done && echo PASS`
  - **Done when**: All 6 CVE IDs found in docs
  - **Commit**: `chore(spec): verify CVE completeness`
  - _Requirements: FR-2, AC (all 6 CVE IDs with IDs)_

## Phase 5: Final Verification + Sign-off

Focus: Confirm goal is met and document decision gate status.

- [ ] 5.1 [VERIFY] Goal verification: all FRs satisfied
  - **Do**: Run a consolidated check across all deliverables
  - **Verify**:
    ```bash
    # FR-1: requirements files
    ruff check infrastructure/ > /dev/null 2>&1 && \
    grep -q 'dspy==3.2.0' requirements.txt && \
    grep -q 'langgraph==0.2.76' requirements.txt && \
    grep -q 'openai==2.32.0' requirements.txt && \
    grep -q 'numpy==2.4.4' requirements.txt && \
    grep -q 'datasets==2.21.0' requirements.txt && \
    ! grep -q 'openai' requirements-dev.txt && \
    grep -q '"infrastructure"' pyproject.toml && \
    # FR-2: docs
    grep -q 'GHSA-r75f-5x8p-qvmc' docs/dependency-compatibility.md && \
    grep -q '## 5. Python 3.14 Caveats' docs/dependency-compatibility.md && \
    # FR-3: script
    python infrastructure/dependency_check.py > /dev/null 2>&1 && \
    # FR-4: code quality
    ! grep -q 'except:' infrastructure/dependency_check.py || grep -q 'except (FileNotFoundError' infrastructure/dependency_check.py && \
    echo "ALL FRs VERIFIED" && echo PASS
    ```
  - **Done when**: All conditions pass
  - **Commit**: `chore(spec): goal verification complete`

- [ ] 5.2 [VERIFY] Decision gate: confirm litellm CVE status is documented
  - **Do**: Verify the decision gate section exists in requirements.md and docs
  - **Verify**: `grep -q 'Decision Gate' specs/dependency-compatibility/requirements.md && grep -q 'Decision Gate' docs/dependency-compatibility.md && grep -q 'P0' specs/dependency-compatibility/requirements.md && echo PASS`
  - **Done when**: Decision gate documented in both specs/requirements.md and docs/
  - **Commit**: `chore(spec): confirm decision gate documented`
  - _Requirements: Decision Gate section, P0 status_

## Notes

- **All code is already committed** to branch `ralph-factory-frameworks`. These tasks verify what was done.
- **Known issue**: `infrastructure/__init__.py` is empty — needs a copyright header for check_headers.py to pass.
- **pyright not installed** in this venv (only ruff is). pyright --strict verification skipped; the design spec showed 0 errors on initial run.
- **No unit tests** for dependency_check.py exist yet (tests/infrastructure/ is empty). Per POC-first, testing is deferred.
- **Decision gate**: litellm CVE acceptance requires human sign-off before merge. Documented in both requirements.md and docs/dependency-compatibility.md.
- **POC shortcuts**: No unit tests, no pyright check (not installed), no E2E browser/CI testing needed for this XS spec.
