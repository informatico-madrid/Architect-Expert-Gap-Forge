# Module Discovery Auto-Detection - Implementation Tasks

**Spec Name:** module-discovery-auto  
**Goal:** Implement intelligent auto-detection of repository types based on file patterns  
**Status:** Ready for Implementation  
**Author:** Joao Maria Arranz Aparicio  
**Date:** 2026-04-01  

---

## Phase 1: Proof of Concept (Tasks 1-10)

### Task 1: Add _detect_strategy() Function Stub

**Do:** Create the `_detect_strategy()` function in `src/discovery/file_scanner.py` after `_discover_by_yaml()`.

**Files:**
- `src/discovery/file_scanner.py` - Line 668 (insert after `_discover_by_yaml()` return)

**Done:**
- Function signature matches specification
- Basic docstring with detection priority order
- Function returns "directory" as fallback
- Compiles without errors

**Verify:**
1. Run: `python -c "from src.discovery.file_scanner import _detect_strategy; print('Import successful')"`
2. Function exists and is importable
3. Basic return value works

**Commit:**
```
feat: add _detect_strategy() function stub for auto-detection

Add initial _detect_strategy() function that serves as foundation for
intelligent repository type detection. Returns "directory" as fallback
strategy.
```

---

### Task 2: Implement YAML Detection

**Do:** Add YAML file detection to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 730-740 (YAML detection block)

**Done:**
- Scans for .yaml, .yml, .jinja, .jinja2 files
- Excludes node_modules, tests, test, __pycache__ directories
- Counts YAML files found
- Returns "yaml" if any found

**Verify:**
1. Create test repository with YAML files
2. Call `_detect_strategy()` and verify returns "yaml"
3. Test exclusion directories work correctly

**Commit:**
```
feat: implement YAML detection in _detect_strategy()

Add detection for YAML-based repositories (themes, templates, blueprints).
Scans for .yaml, .yml, .jinja, .jinja2 files while excluding common
non-source directories.
```

---

### Task 3: Implement TypeScript Detection

**Do:** Add TypeScript file detection to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 742-748 (TypeScript detection block)

**Done:**
- Scans for .ts and .tsx files
- Excludes node_modules, tests, test directories
- Counts TypeScript files found
- Returns "typescript" if any found

**Verify:**
1. Create test repository with TypeScript files
2. Call `_detect_strategy()` and verify returns "typescript"
3. Verify TypeScript detection runs after YAML detection

**Commit:**
```
feat: implement TypeScript detection in _detect_strategy()

Add detection for TypeScript-based repositories (frontend components).
Scans for .ts and .tsx files while excluding node_modules and test
directories.
```

---

### Task 4: Implement PHP Detection

**Do:** Add PHP file detection to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 750-762 (PHP detection block)

**Done:**
- Scans for .php files
- Excludes vendor, node_modules, tests, cache directories
- Counts PHP files found
- Returns "filesystem" if any found

**Verify:**
1. Create test repository with PHP files
2. Call `_detect_strategy()` and verify returns "filesystem"
3. Test exclusion directories work correctly

**Commit:**
```
feat: implement PHP detection in _detect_strategy()

Add detection for PHP-based repositories (filesystem).
Scans for .php files while excluding vendor, cache, and test directories.
```

---

### Task 5: Implement manifest.json Detection

**Do:** Add manifest.json detection to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 764-771 (manifest.json detection block)

**Done:**
- Scans for manifest.json files using rglob
- Returns "manifest" if any found

**Verify:**
1. Create test repository with manifest.json
2. Call `_detect_strategy()` and verify returns "manifest"

**Commit:**
```
feat: implement manifest.json detection in _detect_strategy()

Add detection for Home Assistant-style manifest.json files.
Uses rglob for efficient recursive search.
```

---

### Task 6: Implement __init__.py Detection

**Do:** Add __init__.py detection to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 773-782 (__init__.py detection block)

**Done:**
- Scans for __init__.py files using rglob
- Returns "init" if any found

**Verify:**
1. Create test repository with __init__.py files
2. Call `_detect_strategy()` and verify returns "init"

**Commit:**
```
feat: implement __init__.py detection in _detect_strategy()

Add detection for Python package __init__.py files.
Uses rglob for efficient recursive search.
```

---

### Task 7: Implement Directory Fallback

**Do:** Add directory fallback to `_detect_strategy()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 784-785 (directory fallback)

**Done:**
- Returns "directory" if no patterns match
- Serves as final fallback for unrecognized repositories

**Verify:**
1. Create empty repository
2. Call `_detect_strategy()` and verify returns "directory"

**Commit:**
```
feat: implement directory fallback in _detect_strategy()

Add final fallback to "directory" strategy when no patterns match.
```

---

### Task 8: Add "auto" Case to discover_modules() Routing

**Do:** Add auto strategy routing to `discover_modules()` function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 159-172 (auto routing)

**Done:**
- Detects strategy using _detect_strategy()
- Logs detected strategy
- Recursively calls discover_modules() with detected strategy

**Verify:**
1. Call discover_modules with strategy="auto"
2. Verify it detects and uses appropriate strategy
3. Check logs show detected strategy

**Commit:**
```
feat: add auto strategy routing to discover_modules()

Add routing for "auto" strategy that detects repository type
and delegates to appropriate discovery method.
```

---

### Task 9: Basic Unit Test for YAML Detection

**Do:** Create unit test for YAML detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 8-18 (YAML test)

**Done:**
- Test detects YAML files correctly
- Test excludes node_modules, tests, __pycache__

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestDetectStrategy::test_detect_strategy_yaml -v`
2. Test passes

**Commit:**
```
test: add YAML detection unit test

Add unit test for YAML detection in _detect_strategy().
```

---

### Task 10: Verify Basic POC Works End-to-End

**Do:** Verify POC works end-to-end.

**Files:**
- All above tasks combined

**Done:**
- _detect_strategy() returns correct strategy
- discover_modules() routes to correct method
- Modules are discovered correctly

**Verify:**
1. Create test repository
2. Run full discovery with auto strategy
3. Verify modules discovered

**Commit:**
```
feat: verify POC end-to-end

Verify auto-detection works end-to-end for all repository types.
```

---

## Phase 2: Error Handling and Robustness (Tasks 11-25)

### Task 11: Add Permission Error Handling to YAML Detection

**Do:** Add try-except for permission errors in YAML detection.

**Files:**
- `src/discovery/file_scanner.py` - Lines 730-740 (YAML with exception handling)

**Done:**
- Wraps YAML scan in try-except PermissionError
- Logs warning on permission denied
- Continues scanning

**Verify:**
1. Create directory without read permissions
2. Verify detection doesn't crash

**Commit:**
```
feat: add permission error handling to YAML detection

Handle PermissionError gracefully when scanning YAML files.
```

---

### Task 12: Add Permission Error Handling to TypeScript Detection

**Do:** Add try-except for permission errors in TypeScript detection.

**Files:**
- `src/discovery/file_scanner.py` - Lines 742-748 (TypeScript with exception handling)

**Done:**
- Wraps TS scan in try-except
- Logs warning on permission denied
- Continues scanning

**Verify:**
1. Create directory without read permissions
2. Verify detection doesn't crash

**Commit:**
```
feat: add permission error handling to TypeScript detection

Handle PermissionError gracefully when scanning TypeScript files.
```

---

### Task 13: Add Permission Error Handling to PHP Detection

**Do:** Add try-except for permission errors in PHP detection.

**Files:**
- `src/discovery/file_scanner.py` - Lines 750-762 (PHP with exception handling)

**Done:**
- Wraps PHP scan in try-except PermissionError
- Logs warning on permission denied
- Continues scanning

**Verify:**
1. Create directory without read permissions
2. Verify detection doesn't crash

**Commit:**
```
feat: add permission error handling to PHP detection

Handle PermissionError gracefully when scanning PHP files.
```

---

### Task 14: Add Exception Handling for manifest.json Scan

**Do:** Add try-except for OSError (broken symlinks) in manifest.json scan.

**Files:**
- `src/discovery/file_scanner.py` - Lines 764-771 (manifest with exception handling)

**Done:**
- Wraps manifest scan in try-except OSError
- Logs warning on broken symlink
- Continues scanning

**Verify:**
1. Create broken symlink to manifest.json
2. Verify detection doesn't crash

**Commit:**
```
feat: add broken symlink handling to manifest.json scan

Handle OSError gracefully when scanning for manifest.json files.
```

---

### Task 15: Add Exception Handling for __init__.py Scan

**Do:** Add try-except for OSError (broken symlinks) in __init__.py scan.

**Files:**
- `src/discovery/file_scanner.py` - Lines 773-782 (__init__.py with exception handling)

**Done:**
- Wraps __init__.py scan in try-except OSError
- Logs warning on broken symlink
- Continues scanning

**Verify:**
1. Create broken symlink to __init__.py
2. Verify detection doesn't crash

**Commit:**
```
feat: add broken symlink handling to __init__.py scan

Handle OSError gracefully when scanning for __init__.py files.
```

---

### Task 16: Add Outer Exception Wrapper to _detect_strategy()

**Do:** Add outer exception wrapper to _detect_strategy() function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 782-794 (outer exception wrapper)

**Done:**
- Wraps entire function in try-except
- Logs warning on unexpected errors
- Always returns "directory" on error
- Ensures function never crashes

**Verify:**
1. Test with various error conditions
2. Verify function always returns valid strategy

**Commit:**
```
feat: add outer exception wrapper to _detect_strategy()

Ensure _detect_strategy() never raises exceptions and always
returns a valid strategy.
```

---

### Task 17: Add Debug-Level Logging for Detection Counts

**Do:** Add debug logging for detection counts.

**Files:**
- `src/discovery/file_scanner.py` - Lines 788-794 (debug logging)

**Done:**
- Logs YAML, TS, PHP, manifest, init counts at DEBUG level
- Only enabled when DEBUG logging is on

**Verify:**
1. Run with DEBUG logging enabled
2. Check logs show detection counts

**Commit:**
```
feat: add debug logging for detection counts

Add debug-level logging showing counts for each detection type.
```

---

### Task 18: Optimize YAML Detection for Performance

**Do:** Optimize YAML detection for performance.

**Files:**
- `src/discovery/file_scanner.py` - Lines 730-740 (optimized YAML scan)

**Done:**
- Single-pass scan with early exit
- No file content reading
- Only checks file existence

**Verify:**
1. Measure detection time with 10,000 files
2. Verify < 1 second

**Commit:**
```
perf: optimize YAML detection for performance

Optimize YAML detection with single-pass scan and early exit.
```

---

### Task 19: Optimize TypeScript Detection for Performance

**Do:** Optimize TypeScript detection for performance.

**Files:**
- `src/discovery/file_scanner.py` - Lines 742-748 (optimized TS scan)

**Done:**
- Single-pass scan with early exit
- No file content reading
- Only checks file existence

**Verify:**
1. Measure detection time with 10,000 files
2. Verify < 1 second

**Commit:**
```
perf: optimize TypeScript detection for performance

Optimize TypeScript detection with single-pass scan and early exit.
```

---

### Task 20: Optimize PHP Detection for Performance

**Do:** Optimize PHP detection for performance.

**Files:**
- `src/discovery/file_scanner.py` - Lines 750-762 (optimized PHP scan)

**Done:**
- Single-pass scan with early exit
- No file content reading
- Only checks file existence

**Verify:**
1. Measure detection time with 10,000 files
2. Verify < 1 second

**Commit:**
```
perf: optimize PHP detection for performance

Optimize PHP detection with single-pass scan and early exit.
```

---

### Task 21: Add Type Hints to _detect_strategy()

**Do:** Add type hints to _detect_strategy() function.

**Files:**
- `src/discovery/file_scanner.py` - Lines 668-669 (type hints)

**Done:**
- Type hint: `root: Path`
- Type hint: `-> str`
- Type hint: `root: Path` in docstring

**Verify:**
1. Run mypy on file_scanner.py
2. No type errors

**Commit:**
```
style: add type hints to _detect_strategy()

Add proper type hints for function signature and docstring.
```

---

### Task 22: Update discover_modules() Docstring

**Do:** Update discover_modules() docstring to mention auto strategy.

**Files:**
- `src/discovery/file_scanner.py` - Docstring

**Done:**
- Documents auto strategy in docstring
- Explains auto-detection behavior

**Verify:**
1. Check docstring mentions auto strategy

**Commit:**
```
docs: update discover_modules() docstring

Add documentation for auto strategy in discover_modules().
```

---

### Task 23: Update ProcessingConfig module_discovery_strategy Description

**Do:** Update ProcessingConfig field description.

**Files:**
- `src/discovery/metadata_enricher.py` - Lines 127-130 (field description)

**Done:**
- Lists all strategies including "auto"
- Documents auto-detection behavior

**Verify:**
1. Check description includes auto strategy
2. Check description explains auto-detection

**Commit:**
```
docs: update ProcessingConfig field description

Update module_discovery_strategy field to document all strategies
including auto.
```

---

### Task 24: Add Auto Handling to RepoProcessor._discover_modules()

**Do:** Add auto handling to RepoProcessor._discover_modules().

**Files:**
- `src/discovery/metadata_enricher.py` - Lines 276-280 (auto handling)

**Done:**
- Detects strategy using _detect_strategy()
- Logs detected strategy
- Updates cfg.module_discovery_strategy
- Calls discover_modules with detected strategy

**Verify:**
1. Call RepoProcessor.run() with auto strategy
2. Verify detection works correctly

**Commit:**
```
feat: add auto handling to RepoProcessor._discover_modules()

Add auto strategy handling in RepoProcessor for repository processing.
```

---

### Task 25: Add Comprehensive Docstring to _detect_strategy()

**Do:** Add comprehensive docstring with examples.

**Files:**
- `src/discovery/file_scanner.py` - Lines 669-718 (docstring)

**Done:**
- Documents detection priority order
- Includes docstring examples
- Documents return values

**Verify:**
1. Check docstring with: `python -c "from src.discovery.file_scanner import _detect_strategy; help(_detect_strategy)"`

**Commit:**
```
docs: add comprehensive docstring to _detect_strategy()

Add detailed docstring with examples for _detect_strategy().
```

---

## Phase 3: Comprehensive Testing (Tasks 26-38)

### Task 26: Add TypeScript Detection Unit Tests

**Do:** Create unit tests for TypeScript detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 58-127 (TS tests)

**Done:**
- Tests .ts extension
- Tests .tsx extension
- Tests combined .ts and .tsx
- Tests exclusions (node_modules, tests, test)

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestTypeScriptDetection -v`
2. All tests pass

**Commit:**
```
test: add TypeScript detection unit tests

Add comprehensive unit tests for TypeScript detection.
```

---

### Task 27: Add PHP Detection Unit Tests

**Do:** Create unit tests for PHP detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 134-206 (PHP tests)

**Done:**
- Tests .php file detection
- Tests PHP in subdirectories
- Tests exclusions (vendor, cache, node_modules, tests)

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestPHPDetection -v`
2. All tests pass

**Commit:**
```
test: add PHP detection unit tests

Add comprehensive unit tests for PHP detection.
```

---

### Task 28: Add Manifest Detection Unit Tests

**Do:** Create unit tests for manifest.json detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 213-252 (manifest tests)

**Done:**
- Tests manifest.json detection
- Tests manifest priority over TypeScript
- Tests manifest priority over __init__.py

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestManifestDetection -v`
2. All tests pass

**Commit:**
```
test: add manifest.json detection unit tests

Add comprehensive unit tests for manifest.json detection.
```

---

### Task 29: Add Init Detection Unit Tests

**Do:** Create unit tests for __init__.py detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 259-317 (init tests)

**Done:**
- Tests __init__.py detection
- Tests __init__.py priority over YAML
- Tests exclusions (__pycache__)
- Tests multiple __init__.py files

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestInitDetection -v`
2. All tests pass

**Commit:**
```
test: add __init__.py detection unit tests

Add comprehensive unit tests for __init__.py detection.
```

---

### Task 30: Add Priority Order Verification Tests

**Do:** Create tests for priority order verification.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 324-398 (priority tests)

**Done:**
- Tests YAML > TypeScript priority
- Tests TypeScript > PHP priority
- Tests PHP > manifest priority
- Tests manifest > init priority
- Tests init > directory priority

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestPriorityOrderVerification -v`
2. All tests pass

**Commit:**
```
test: add priority order verification tests

Add tests to verify detection priority order is correct.
```

---

### Task 31: Add Fallback Detection Unit Tests

**Do:** Create unit tests for fallback detection.

**Files:**
- `tests/discovery/test_auto_detection.py` - Lines 405-458 (fallback tests)

**Done:**
- Tests empty directory returns "directory"
- Tests .git-only directory returns "directory"
- Tests only non-source files returns "directory"
- Tests only .md files returns "directory"
- Tests only .json files returns "directory"

**Verify:**
1. Run: `pytest tests/discovery/test_auto_detection.py::TestFallbackDetection -v`
2. All tests pass

**Commit:**
```
test: add fallback detection unit tests

Add tests for fallback to "directory" strategy.
```

---

### Task 32: Add Integration Test for YAML Discovery with Auto

**Do:** Create integration test for YAML discovery.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 33-94 (YAML integration test)

**Done:**
- Tests auto strategy detects YAML
- Tests YAML modules discovered
- Tests anchor_type is "yaml"

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestYAMLDiscoveryIntegration::test_auto_yaml_discovery -v`
2. Test passes

**Commit:**
```
test: add YAML discovery integration test

Add integration test for YAML discovery with auto strategy.
```

---

### Task 33: Add Integration Test for TypeScript Discovery with Auto

**Do:** Create integration test for TypeScript discovery.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 100-179 (TS integration test)

**Done:**
- Tests auto strategy detects TypeScript
- Tests TypeScript modules discovered
- Tests anchor_type is "typescript"
- Tests node_modules exclusion

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestTypeScriptDiscoveryIntegration -v`
2. All tests pass

**Commit:**
```
test: add TypeScript discovery integration test

Add integration test for TypeScript discovery with auto strategy.
```

---

### Task 34: Add Integration Test for Mixed Repository

**Do:** Create integration test for mixed repositories.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 186-261 (mixed repo test)

**Done:**
- Tests manifest > TypeScript priority
- Tests init > TypeScript priority
- Tests YAML > TypeScript priority

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestMixedRepositoryIntegration -v`
2. All tests pass

**Commit:**
```
test: add mixed repository integration test

Add integration tests for mixed Python/TypeScript repositories.
```

---

### Task 35: Add Performance Test for Detection Time

**Do:** Create performance test for detection time.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 268-346 (performance tests)

**Done:**
- Tests detection < 1 second for 10,000 files
- Tests module discovery performance

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestDetectionPerformance -v`
2. All tests pass

**Commit:**
```
test: add performance test for detection time

Add performance test to verify detection completes in < 1 second.
```

---

### Task 36: Add Performance Test for Large Repository Processing

**Do:** Create performance test for large repository processing.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 353-404 (large repo test)

**Done:**
- Tests large TypeScript repo processing < 2 seconds
- Tests detection + discovery performance

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestLargeRepositoryPerformance -v`
2. All tests pass

**Commit:**
```
test: add performance test for large repository processing

Add performance test for large repository processing.
```

---

### Task 37: Add Permission Error Test

**Do:** Create test for permission error handling.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 411-475 (permission tests)

**Done:**
- Tests permission errors don't crash detection
- Tests detection continues after permission errors

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestPermissionErrors -v`
2. All tests pass

**Commit:**
```
test: add permission error handling test

Add test for graceful permission error handling.
```

---

### Task 38: Add Broken Symlink Test

**Do:** Create test for broken symlink handling.

**Files:**
- `tests/discovery/test_auto_integration.py` - Lines 482-587 (symlink tests)

**Done:**
- Tests broken symlinks don't crash detection
- Tests symlink handling in discovery

**Verify:**
1. Run: `pytest tests/discovery/test_auto_integration.py::TestBrokenSymlinks -v`
2. All tests pass

**Commit:**
```
test: add broken symlink handling test

Add test for graceful broken symlink handling.
```

---

## Phase 4: Documentation (Tasks 39-43)

### Task 39: Create README for Auto-Detection Feature

**Do:** Create README documentation.

**Files:**
- `docs/auto-detection.md` - Documentation

**Done:**
- Documents auto-detection feature
- Documents detection priority order
- Documents configuration options

**Verify:**
1. Check README exists and is complete

**Commit:**
```
docs: add README for auto-detection feature

Add comprehensive documentation for auto-detection feature.
```

---

### Task 40: Update Configuration Examples

**Do:** Update configuration examples.

**Files:**
- `docs/config-examples.md` - Configuration examples

**Done:**
- Adds auto strategy example
- Documents all strategies

**Verify:**
1. Check config examples include auto strategy

**Commit:**
```
docs: update configuration examples

Add auto strategy to configuration examples.
```

---

### Task 41: Update API Documentation

**Do:** Update API documentation.

**Files:**
- API docs (if exists)

**Done:**
- Documents _detect_strategy() API
- Documents discover_modules() auto routing

**Verify:**
1. Check API documentation is complete

**Commit:**
```
docs: update API documentation

Update API documentation for auto-detection feature.
```

---

### Task 42: Add Usage Guide

**Do:** Add usage guide.

**Files:**
- `docs/usage-guide.md` (if needed)

**Done:**
- Documents when to use auto vs manual
- Documents best practices

**Verify:**
1. Check usage guide exists

**Commit:**
```
docs: add usage guide

Add usage guide for auto-detection feature.
```

---

### Task 43: Update CHANGELOG

**Do:** Update CHANGELOG.

**Files:**
- `CHANGELOG.md`

**Done:**
- Documents auto-detection feature
- Documents breaking changes

**Verify:**
1. Check CHANGELOG includes auto-detection

**Commit:**
```
chore: update CHANGELOG

Update CHANGELOG with auto-detection feature.
```

---

## Phase 5: Quality and Verification (Tasks 44-50)

### Task 44: Run All Existing Tests

**Do:** Run all existing tests.

**Files:**
- All test files

**Done:**
- All tests pass
- No regressions

**Verify:**
1. Run: `pytest tests/ -v`
2. All tests pass

**Commit:**
```
test: run all existing tests

Run all existing tests to verify no regressions.
```

---

### Task 45: Run Code Quality Checks

**Do:** Run code quality checks.

**Files:**
- All source files

**Done:**
- mypy passes
- flake8 passes
- no linting errors

**Verify:**
1. Run: `mypy src/`
2. Run: `flake8 src/`
3. No errors

**Commit:**
```
chore: run code quality checks

Run code quality checks to ensure code quality.
```

---

### Task 46: Add Inline Comments for Complex Logic

**Do:** Add inline comments for complex logic.

**Files:**
- `src/discovery/file_scanner.py`

**Done:**
- Comments added for complex detection logic
- Comments explain priority order

**Verify:**
1. Check code has appropriate comments

**Commit:**
```
style: add inline comments for complex logic

Add inline comments to explain complex detection logic.
```

---

### Task 47: Verify All Line Numbers Match Design Document

**Do:** Verify line numbers match design document.

**Files:**
- `specs/module-discovery-auto/design.md`
- `src/discovery/file_scanner.py`

**Done:**
- All line numbers match design document
- Implementation matches design

**Verify:**
1. Compare implementation with design document

**Commit:**
```
chore: verify line numbers match design document

Verify implementation line numbers match design document.
```

---

### Task 48: Create PR Verification Checklist

**Do:** Create PR verification checklist.

**Files:**
- `.github/PULL_REQUEST_TEMPLATE.md` (if exists)

**Done:**
- Checklist for PR review

**Verify:**
1. Check PR template exists

**Commit:**
```
docs: create PR verification checklist

Add PR verification checklist for auto-detection feature.
```

---

### Task 49: Final Code Review

**Do:** Perform final code review.

**Files:**
- All source files

**Done:**
- Code reviewed
- No issues found
- Ready for merge

**Verify:**
1. Perform code review
2. Verify all requirements met

**Commit:**
```
chore: final code review

Perform final code review before merge.
```

---

### Task 50: Final Verification and Sign-off

**Do:** Final verification and sign-off.

**Files:**
- All artifacts

**Done:**
- All requirements met
- All tests pass
- All documentation complete
- Ready for production

**Verify:**
1. Verify all acceptance criteria met
2. Sign off on implementation

**Commit:**
```
chore: final verification and sign-off

Final verification and sign-off for auto-detection feature.
```
