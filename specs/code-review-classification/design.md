# Design: code-review-classification — Code Review Fixes

## Architecture

The fixes span multiple independent areas. No major architectural changes needed — each fix targets a specific line or small set of lines.

### Fix Categories & Execution Order

```
Phase 1: Blockers (no dependencies)
  ├── #23 SyntaxError — fix indentation (blocks imports)
  └── #43 Malformed JSON — fix JSON (blocks parsers)

Phase 2: Security (no dependencies, high priority)
  ├── #17 Remove hardcoded API key
  └── #30 Fix symlink security check

Phase 3: Missing Dependencies (no dependencies)
  └── #59 Add numpy to requirements.txt

Phase 4: Runtime Crashes (depends on Phase 3 for numpy)
  ├── #31 Uninitialized variable
  ├── #34 Unreachable exception
  ├── #134 Logic inversion TypeError
  ├── #145 Missing self in __setattr__
  ├── #165 NameError typo
  ├── #201 Invalid import syntax
  └── #202 Wrong lambda signatures

Phase 5: API/Integration (depends on Phase 4)
  ├── #19 Gemini API roles
  ├── #66 Exception class names
  ├── #121 Spanish detection regex
  └── #139 is_cascade boolean

Phase 6: Logic/Calculation (depends on Phase 4)
  ├── #82 Operator precedence
  ├── #133 Filter rate precedence
  ├── #152 Unused variable delta
  └── #177 Logical operator

Phase 7: File System/IO (independent)
  ├── #16 exists() → is_file()
  ├── #38 os.chdir() side-effect
  └── #75 os.fsync() fd

Phase 8: Dependency/Config (independent)
  ├── #11 Profile config contradiction
  ├── #12 Auto-detection priority docs
  ├── #15 dspy version notation
  ├── #57/89/91 langgraph version consistency
  └── #86 Invalid constraint syntax

Phase 9: Code Quality (depends on Phase 8)
  ├── #26 Raw reference context
  ├── #27 Docstring inconsistency
  ├── #29 Resume logic
  ├── #60 KeyError from missing key
  └── #143 Overlapping regex

Phase 10: Test Infrastructure (independent, fix in parallel with Phase 1-9)
  ├── #103/#104 Fixture key typos
  ├── #106/#196 Hardcoded paths
  ├── #149 Duplicate fixture function
  ├── #152 Unused delta variable
  ├── #154/#158 Missing assertions
  ├── #160/#162/#164/#168/#185 Wrong test data
  ├── #179/#180 Tautological assertions
  ├── #184 Wrong default value
  └── #151/#189/#190/#191/#193/#194/#195/#198 Weak/wrong assertions

Phase 11: Spec Documentation (independent, fix in parallel)
  ├── #46/#67 Logical contradictions
  ├── #48/#63 Node count consistency
  ├── #69 Missing method
  ├── #70 Invalid JSON Schema
  ├── #73/#74 ID regex + logging level
  ├── #77 Directory paths
  ├── #82 Operator precedence
  ├── #92/#93 Verify commands
  ├── #94/#95/#102/#108/#109 Spec contradictions
  ├── #96/#97 Value mismatches
  ├── #114/#115/#116/#117 Template fixes
  ├── #121 Regex fix
  ├── #122/#123/#125/#127 Spec syntax fixes

## Quality Gate Structure

Every 2-3 tasks: party mode quality gate with full consensus.

```
Tasks 1-2 → QG-1
Tasks 3-5 → QG-2
Tasks 6-8 → QG-3
Tasks 9-11 → QG-4
Tasks 12-14 → QG-5
Tasks 15-17 → QG-6
Tasks 18-20 → QG-7
Tasks 21-23 → QG-8
Tasks 24-26 → QG-9
Tasks 27-29 → QG-10
Tasks 30-32 → QG-11
Tasks 33-35 → QG-12
Tasks 36-38 → QG-13
Tasks 39-41 → QG-14
Tasks 42-44 → QG-15
Tasks 45-47 → QG-16
Tasks 48-50 → QG-17
```

Each Quality Gate checks:
1. **Syntax**: `python -m py_compile` all changed .py files
2. **Linter**: `ruff check` passes with zero errors
3. **Tests**: All tests pass (`pytest tests/ -x`)
4. **Coverage**: No pragma cover, no flaky tests
5. **Spec compliance**: Implementation matches requirements
6. **Import check**: `python -c "import src"` succeeds

## Implementation Strategy

### Independent Fixes (can be parallelized)
Many fixes are isolated to specific files. Group them by file to minimize merge conflicts:
- `infrastructure/` fixes: #16, #17, #18, #19, #26, #27, #29, #30
- `src/` fixes: #133, #134, #139, #140, #143, #145
- `tests/` fixes: ~30 issues across many test files
- `specs/` fixes: ~25 issues across many spec files
- `requirements.txt` fixes: #59, #86
- `configs/` fixes: #11

### File-Grouped Execution Plan

```
Group A: infrastructure/ — 10 fixes
Group B: src/curation/ — 3 fixes
Group C: src/factory/ — 2 fixes
Group D: src/utils/ — 2 fixes
Group E: tests/ — 30+ fixes
Group F: specs/ — 25 fixes
Group G: requirements.txt + configs/ — 5 fixes
Group H: docs/ — 3 fixes
```

Each group is fixed as a batch, then a quality gate runs.
