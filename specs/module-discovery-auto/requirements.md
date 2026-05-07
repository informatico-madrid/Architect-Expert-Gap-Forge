# Module Discovery Auto-Detection Requirements

## Overview

This document specifies requirements for implementing an intelligent auto-detection module discovery strategy that automatically identifies repository types based on file patterns and applies the appropriate discovery strategy.

**Spec Name:** `module-discovery-auto`
**Goal:** Implement an intelligent `auto` module discovery strategy that automatically detects repository type based on file patterns and selects the appropriate discovery strategy

**Author:** Joao Maria Arranz Aparicio
**Date:** 2026-04-01

---

## 1. Functional Requirements

### FR1: Auto-Detection Algorithm Implementation

**FR1.1:** Implement a `_detect_strategy()` function in `src/discovery/file_scanner.py` that scans repository file patterns and returns the most appropriate discovery strategy.

**FR1.2:** Detection must follow this priority order:

| Priority | Detection Method | Strategy |
|----------|------------------|----------|
| 1 | Presence of `.yaml`, `.yml`, `.jinja`, `.jinja2` files (excluding `node_modules`, `tests`, `test`, `__pycache__`) | `yaml` |
| 2 | Presence of `.ts`, `.tsx` files (excluding `node_modules`, `tests`, `test`) | `typescript` |
| 3 | Presence of `.php` files (excluding `vendor`, `node_modules`, `tests`, `cache`) | `filesystem` |
| 4 | Presence of `manifest.json` files | `manifest` |
| 5 | Presence of `__init__.py` files | `init` |
| 6 | No specific patterns found | `directory` |

**FR1.3:** The `_detect_strategy()` function signature:

```python
def _detect_strategy(root: Path) -> str:
    """Detect the most appropriate discovery strategy for a repository.

    Returns the strategy name based on file extension presence and directory structure.
    Detection order:
    1. YAML-first (themes, templates, blueprints)
    2. TypeScript-second (frontend components)
    3. PHP-third (filesystem-based)
    4. Python-manifest (HA core style with metadata)
    5. Python-init (packages without manifest)
    6. Directory (fallback for directory structures)

    Args:
        root: Repository root directory to scan

    Returns:
        Strategy name: 'yaml', 'typescript', 'filesystem', 'manifest', 'init', or 'directory'
    """
```

**FR1.4:** Detection must complete a full file system scan within 1 second for typical repositories containing up to 10,000 files.

### FR2: Strategy Routing Integration

**FR2.1:** Update `discover_modules()` in `src/discovery/file_scanner.py` to handle the `auto` strategy by:

1. Detecting the appropriate strategy using `_detect_strategy()`
2. Logging the detected strategy
3. Recursively calling `discover_modules()` with the detected strategy

**FR2.2:** Route implementation:

```python
elif strategy == "auto":
    detected_strategy = _detect_strategy(root)
    logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
    return discover_modules(
        root=root,
        strategy=detected_strategy,
        ignore_patterns=ignore_patterns,
        extensions=extensions,
        anchor_filenames=anchor_filenames,
        module_overrides=module_overrides,
        build_module_func=build_module_func,
    )
```

**FR2.3:** The recursive call must complete in a single pass without infinite recursion.

### FR3: Configuration Updates

**FR3.1:** Update the `module_discovery_strategy` field in `ProcessingConfig` class in `src/discovery/metadata_enricher.py` to include all available strategies in the description:

```python
module_discovery_strategy: str = Field(
    default="manifest",
    description="Strategy for discovering modules: manifest, init, directory, filesystem, typescript, yaml, manual_mapping, auto",
)
```

**FR3.2:** Document that `auto` automatically detects repository type and selects appropriate strategy.

### FR4: Logging for Detected Strategies

**FR4.1:** Log detected strategy at INFO level:

```python
logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
```

**FR4.2:** Log at DEBUG level when debugging detection:

```python
logger.debug(
    "Strategy detection: YAML=%d, TS=%d, PHP=%d, manifest=%d, init=%d -> %s",
    yaml_count, ts_count, php_count, has_manifest, has_init, detected_strategy
)
```

**FR4.3:** All logs must include the repository root path for debugging context.

---

## 2. Non-Functional Requirements

### NFR1: Performance

**NFR1.1:** Auto-detection must complete in **< 1 second** for typical repositories containing up to 10,000 files.

**NFR1.2:** Detection scans must be efficient:
- Single-pass file enumeration where possible
- Early exit once a pattern match is found at higher priority
- Minimal file content reading (only file existence and extension)

**NFR1.3:** Total processing overhead compared to manual strategy selection must be < 100ms for typical repos.

### NFR2: Reliability

**NFR2.1:** Auto-detection must always return a valid strategy, never raising an exception.

**NFR2.2:** Fallback to `directory` strategy if detection fails or repository is empty.

**NFR2.3:** Must handle permission errors gracefully (log warning, continue scanning).

**NFR2.4:** Must handle symbolic links without infinite loops.

### NFR3: Maintainability

**NFR3.1:** Detection algorithm must be easy to extend:
- New detection patterns should be added as separate checks
- Priority order should be explicit and documented
- Directory exclusions should be configurable constants

**NFR3.2:** Code must follow existing patterns in `file_scanner.py` for consistency.

**NFR3.3:** All new functions must include comprehensive docstrings.

### NFR4: Correctness

**NFR4.1:** Auto-detection must produce identical results to manual strategy selection.

**NFR4.2:** Module discovery results must be deterministic (same repo always returns same strategy).

**NFR4.3:** Module overrides configuration must be respected regardless of detected strategy.

---

## 3. Acceptance Criteria

### AC1: YAML-Only Repos Detection

**AC1.1:** Repository containing only `.yaml`, `.yml`, `.jinja`, or `.jinja2` files must be detected as `yaml` strategy.

**AC1.2:** Example repository:
```
repository/
  themes/
    ios-dark.yaml
    ios-light.yaml
  templates/
    automation.jinja
```

**AC1.3:** Expected result: `_detect_strategy()` returns `"yaml"`, and `_discover_by_yaml()` discovers modules correctly.

### AC2: TypeScript-Only Repos Detection

**AC2.1:** Repository containing `.ts` or `.tsx` files (no other patterns) must be detected as `typescript` strategy.

**AC2.2:** Example repository:
```
repository/
  src/
    components/
      button.ts
      card.tsx
    cards/
      mushroom-card.ts
```

**AC2.3:** Expected result: `_detect_strategy()` returns `"typescript"`, and `_discover_by_typescript()` discovers modules correctly.

### AC3: PHP Repos Detection

**AC3.1:** Repository containing `.php` files (in non-vendor directories) must be detected as `filesystem` strategy.

**AC3.2:** Example repository:
```
repository/
  src/
    Services/
      UserService.php
    Controllers/
      UserController.php
  vendor/
    package/
      package.php  (excluded)
```

**AC3.3:** Expected result: `_detect_strategy()` returns `"filesystem"`, and `_discover_by_filesystem()` discovers modules correctly.

### AC4: Python Repos with manifest Detection

**AC4.1:** Repository containing `manifest.json` must be detected as `manifest` strategy (higher priority than TypeScript).

**AC4.2:** Example repository:
```
repository/
  custom_components/
    my_integration/
      manifest.json
      __init__.py
  src/
    frontend/
      button.ts  (should be ignored)
```

**AC4.3:** Expected result: `_detect_strategy()` returns `"manifest"`, and `_discover_by_manifest_and_init()` discovers the Python integration.

### AC5: Python Repos without manifest Detection

**AC5.1:** Repository containing only `__init__.py` files (no manifest.json) must be detected as `init` strategy.

**AC5.2:** Example repository:
```
repository/
  appdaemon/
    __init__.py
    main.py
  nspanel/
    __init__.py
    handlers.py
```

**AC5.3:** Expected result: `_detect_strategy()` returns `"init"`, and `_discover_by_init()` discovers modules correctly.

### AC6: Config Option `module_discovery_strategy: auto`

**AC6.1:** Setting `module_discovery_strategy: auto` in configuration must work correctly.

**AC6.2:** RepositoryProcessor must route auto strategy to detection logic.

**AC6.3:** All existing tests for other strategies must continue to pass.

---

## 4. Technical Specifications

### 4.1 Function Signatures

#### `_detect_strategy()`

```python
def _detect_strategy(root: Path) -> str:
    """Detect the most appropriate discovery strategy for a repository.

    Args:
        root: Repository root directory to scan

    Returns:
        Strategy name: 'yaml', 'typescript', 'filesystem', 'manifest', 'init', 'directory'
    """
```

#### `discover_modules()` Update

Add case in strategy routing:

```python
elif strategy == "auto":
    detected_strategy = _detect_strategy(root)
    logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
    return discover_modules(
        root=root,
        strategy=detected_strategy,
        ignore_patterns=ignore_patterns,
        extensions=extensions,
        anchor_filenames=anchor_filenames,
        module_overrides=module_overrides,
        build_module_func=build_module_func,
    )
```

### 4.2 Integration Points

| Component | Location | Change Required |
|-----------|----------|-----------------|
| Detection Algorithm | `src/discovery/file_scanner.py` | Add `_detect_strategy()` function |
| Strategy Routing | `src/discovery/file_scanner.py` | Add `auto` case to `discover_modules()` |
| Configuration | `src/discovery/metadata_enricher.py` | Update `module_discovery_strategy` description |
| RepoProcessor | `src/discovery/metadata_enricher.py` | Add auto handling in `_discover_modules()` |

### 4.3 Error Handling

**4.3.1 Permission Errors**

```python
try:
    for file_path in root.rglob("*"):
        if file_path.is_file() and check_condition(file_path):
            ...
except PermissionError as e:
    logger.warning("Permission denied accessing %s: %s", root, e)
    continue
```

**4.3.2 Broken Symbolic Links**

```python
try:
    if file_path.is_file():
        ...
except OSError:
    # Broken symlink, skip
    continue
```

**4.3.3 Detection Failure**

Always return a valid strategy string, never raise an exception:

```python
try:
    # Detection logic
    return detected_strategy
except Exception:
    # Fallback to directory strategy
    return "directory"
```

### 4.4 Logging Requirements

| Level | Message | When |
|-------|---------|------|
| INFO | `Auto-detected strategy: %s for %s` | Every detection |
| DEBUG | `Detection: YAML=%d, TS=%d, PHP=%d, manifest=%d, init=%d -> %s` | Debug mode |
| WARNING | `Permission denied: %s` | Permission errors |
| WARNING | `Could not detect strategy, using fallback` | Detection exception |

---

## 5. Edge Cases

### 5.1 Empty Repositories

**Case:** Repository with no source files (only `.git` directory)

**Expected Behavior:**
- Detection finds no patterns
- Returns `"directory"` as fallback
- Results in empty module list (expected)

**Test Case:**
```bash
repository/
  .git/
    ...
```
Expected: `"directory"` strategy

### 5.2 Mixed-Language Repositories

**Case:** Repository containing both Python and TypeScript files

**Expected Behavior:**
- Python (manifest) takes priority over TypeScript
- Python (init) takes priority over TypeScript
- Only Python modules discovered, TypeScript ignored

**Test Case:**
```
repository/
  custom_components/
    my_integration/
      manifest.json
      __init__.py
  src/
    frontend/
      button.ts
```
Expected: `"manifest"` strategy, Python module only

### 5.3 Compiled-Only JavaScript Repositories

**Case:** Repository containing only `.js` files (no TypeScript source)

**Expected Behavior:**
- No patterns match
- Returns `"directory"` or `"manifest"` fallback
- No modules discovered (no source to bundle)

**Test Case:**
```
repository/
  bundle/
    bundle.js
```
Expected: No modules (or minimal if `manifest.json` present)

### 5.4 Repositories with Both YAML and TypeScript

**Case:** Repository with template files and frontend components

**Expected Behavior:**
- YAML takes priority (templates are processed first)
- TypeScript files ignored

**Test Case:**
```
repository/
  themes/
    dark.yaml
  src/
    components/
      button.ts
```
Expected: `"yaml"` strategy, template modules only

### 5.5 Repositories with Deep Directory Structures

**Case:** Repository with many nested directories

**Expected Behavior:**
- Detection scans all directories
- No performance degradation beyond single O(n) scan
- Early exit on first pattern match at higher priority

**Test Case:**
```
repository/
  level1/
    level2/
      level3/
        .../
          module.py
```
Expected: Fast detection regardless of depth

### 5.6 Large Repositories

**Case:** Repository with 10,000+ files

**Expected Behavior:**
- Detection completes in < 1 second
- Memory usage remains bounded
- No stack overflow from deep recursion

**Test Case:**
```
repository/
  many_files/
    file1.txt
    file2.txt
    ...
    file10000.txt
```
Expected: Detection < 1 second

---

## 6. Testing Requirements

### 6.1 Unit Tests

**T1: `_detect_strategy()` YAML Detection**
- Input: Repository with only `.yaml` files
- Expected: Returns `"yaml"`

**T2: `_detect_strategy()` TypeScript Detection**
- Input: Repository with only `.ts`/`.tsx` files
- Expected: Returns `"typescript"`

**T3: `_detect_strategy()` PHP Detection**
- Input: Repository with only `.php` files
- Expected: Returns `"filesystem"`

**T4: `_detect_strategy()` Manifest Detection**
- Input: Repository with `manifest.json`
- Expected: Returns `"manifest"`

**T5: `_detect_strategy()` Init Detection**
- Input: Repository with only `__init__.py`
- Expected: Returns `"init"`

**T6: `_detect_strategy()` Fallback Detection**
- Input: Empty repository
- Expected: Returns `"directory"`

**T7: `_detect_strategy()` Priority Test**
- Input: Repository with both YAML and TypeScript
- Expected: Returns `"yaml"` (YAML priority over TypeScript)

### 6.2 Integration Tests

**IT1: Full Discovery with Auto Strategy**
- Configure `module_discovery_strategy: auto`
- Process YAML-only repository
- Verify modules discovered correctly

**IT2: Auto Strategy with TypeScript**
- Configure `module_discovery_strategy: auto`
- Process TypeScript repository
- Verify TypeScript modules discovered

**IT3: Auto Strategy with PHP**
- Configure `module_discovery_strategy: auto`
- Process PHP repository
- Verify PHP modules discovered

**IT4: Auto Strategy with Mixed Python/TypeScript**
- Configure `module_discovery_strategy: auto`
- Process mixed repository
- Verify Python modules only (TypeScript ignored)

### 6.3 Performance Tests

**PT1: Detection Time**
- Measure time for repositories of varying sizes
- Verify < 1 second for typical repos
- Document performance for edge cases

---

## 7. Implementation Plan

### Phase 1: Core Implementation

1. **Add `_detect_strategy()` function to `file_scanner.py`**
   - Location: After `_discover_by_yaml()` (line ~649)
   - Implement detection algorithm
   - Add docstring with examples

2. **Update `discover_modules()` routing**
   - Add `elif strategy == "auto":` case
   - Call `_detect_strategy()` and recursively route

3. **Update `ProcessingConfig` description**
   - Add all strategy names to field description

4. **Update `RepoProcessor._discover_modules()`**
   - Add `if self.cfg.module_discovery_strategy == "auto":` case
   - Call `_detect_strategy()` directly
   - Log detected strategy

### Phase 2: Testing

1. Create unit tests for each detection pattern
2. Create integration tests for full discovery flow
3. Create performance tests for large repositories

### Phase 3: Documentation

1. Update config descriptions with all strategies
2. Document detection priority order
3. Create user guide for when to use auto vs manual

---

## 8. Appendix: Detection Algorithm Reference Implementation

```python
def _detect_strategy(root: Path) -> str:
    """Detect the most appropriate discovery strategy for a repository.

    Detection priority:
    1. YAML (themes, templates, blueprints)
    2. TypeScript (frontend components)
    3. PHP (filesystem-based)
    4. Manifest (HA core style)
    5. Init (Python packages)
    6. Directory (fallback)

    Args:
        root: Repository root directory

    Returns:
        Strategy name
    """
    # 1. Check for YAML files
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix in (".yaml", ".yml", ".jinja", ".jinja2"):
            if not any(part in ("node_modules", "tests", "test", "__pycache__")
                     for part in file_path.parts):
                return "yaml"

    # 2. Check for TypeScript files
    for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
        if not any(part in ("node_modules", "tests", "test")
                 for part in ts_file.parts):
            return "typescript"

    # 3. Check for PHP files
    for php_file in root.rglob("*.php"):
        if not any(part in ("vendor", "node_modules", "tests", "cache")
                 for part in php_file.parts):
            return "filesystem"

    # 4. Check for manifest.json
    if any(root.rglob("manifest.json")):
        return "manifest"

    # 5. Check for __init__.py
    if any(root.rglob("__init__.py")):
        return "init"

    # 6. Fallback to directory
    return "directory"
```

---

*Last updated: 2026-04-01*
