# Requirements: code-review-classification — Code Review Fixes

## Overview

Apply fixes for all **102 confirmed real problems** identified in the code review classification of the AEGF codebase. Zero false positives remain.

## Acceptance Criteria

### AC-1: All 102 Group 1 Issues Fixed
Every issue in the code-review-classification.md Group 1 list must have:
- A corresponding code/documentation change committed
- The fix must be correct (no new bugs introduced)
- The fix must pass all existing tests

### AC-2: Security Fixes
- **Issue #17**: Remove hardcoded API key fallback (`sk-master-bunker-2026`) — provider must require valid key
- **Issue #30**: Fix symlink security check — must check before `resolve()`
- No new security vulnerabilities introduced

### AC-3: No Runtime Crashes
- All SyntaxError issues fixed (#23, #201)
- All NameError/AttributeError issues fixed (#31, #145, #165, #202)
- All TypeError issues fixed (#134)
- `exists()` → `is_file()` fix (#16)
- `os.fsync()` with proper fd (#75)
- `os.chdir()` replaced with context manager (#38)

### AC-4: API Fixes
- Gemini API roles corrected (#19): `role: 'system'` and `role: 'user'`
- Exception class names consistent (#66): `ConfigValidationError`
- DSPy predictor payload correct is_cascade (#139)
- Spanish text detection regex fixed (#121)

### AC-5: Dependency/Config Fixes
- `profile: typescript` commented out or aligned with docs (#11)
- Auto-detection priority docs match code (#12)
- dspy version notation consistent: `==3.2.0` everywhere (#15)
- Malformed JSON fixed in index-state.json (#43)
- Missing numpy dependency added (#59)
- Invalid dependency constraint syntax fixed (#86)
- langgraph version constraints consistent (no <= vs == conflicts) (#57, #89, #91)

### AC-6: Logic/Calculation Fixes
- Operator precedence fixed in validation (#82)
- Operator precedence fixed in filter rate (#133)
- Unused variable delta assigned/used (#152)
- Logical operator fixed in assertions (#177)

### AC-7: Test Infrastructure Fixes
- All test fixture key typos fixed (#103, #104)
- Hardcoded paths replaced with relative/environment-aware paths (#106, #196)
- Duplicate fixture functions consolidated (#149)
- Tests that claim coverage they don't have: either add real assertions or remove (#154, #158)
- Wrong assertions: fix to match actual implementation (#160, #162, #164, #168, #185)
- Tautological/trivially true assertions removed (#179, #180)
- Wrong default values in getattr fixed (#184)

### AC-8: Test Quality — All Tests Pass and Are Solid
- All tests pass with no flakes
- All tests assert on actual transformation results, not raw input
- All test names match their assertions
- No dead code in tests (no no-op expressions, unreachable code)
- No unused variables breaking test logic
- Test fixtures are valid and consistent with their stated purpose
- Context managers used for file I/O
- Proper exception types caught

### AC-9: Spec Documentation Fixes
- Logical contradictions resolved in acceptance criteria (#46)
- Node count consistency (#48, #63)
- Exception handling design consistent (#67)
- Missing method definitions added to spec (#69)
- Invalid JSON Schema syntax fixed (#70)
- ID regex patterns consistent: `r"^anchor_\d+_\d+$"` everywhere (#73)
- Logging level specification corrected: `warning` not "INFO level" (#74)
- Directory paths consistent (#77)
- Verify commands complete and robust (#92, #93)
- API signatures valid (#94)
- No duplicate task IDs (#95)
- Value mismatches in .progress.md resolved (#96, #97)
- Type 3 LOGIC_ONLY scope clarified (#102)
- No overlapping task line ranges (#108)
- Detection priority consistent across specs (#109)
- Prompt storage format clarified (#122)
- Module reference syntax valid (#123)
- Placeholder replacement preserves dollar signs (#125)
- YAML !input tag placement fixed (#127)

### AC-10: Template/Prompt Fixes
- Key access pattern: use `.get()` instead of `.system` for safety (#114)
- Placeholder syntax consistent: all `{var}` Python str.format style (#115)
- $tools_json template variable defined or removed (#116)
- Spanish text removed from forbidden_terms (#117)
- Flawed regex for language detection fixed (#121)

### AC-11: Quality Gates
- Code passes `ruff check` with zero errors
- All imports succeed (`python -c "import src"` etc.)
- All unit tests pass
- All integration tests pass
- All E2E tests pass (if applicable)
- Syntax: `python -m py_compile` on all .py files
- No unused imports, no dead code
- All test files pass `pytest` without warnings

## Non-Functional Requirements

| NFR | Description | Target |
|-----|-------------|--------|
| NFR-1 | No new issues introduced | Zero regression |
| NFR-2 | All fixes backward compatible | No API breaks |
| NFR-3 | Quality gate consensus | Party mode approval |
| NFR-4 | Test coverage maintained | No pragma cover, no flaky tests |
| NFR-5 | Code style compliance | ruff, black, isort standards |

## Scope Boundary

**In Scope**: All 102 Group 1 issues in code-review-classification.md
**Out of Scope**:
- Any changes to issue classification methodology
- Issues classified as Group 2 (false positives) — by definition not fixing them
- New features beyond the identified fixes
- Architectural changes not directly caused by these fixes
