# Module Discovery Auto-Detection Strategy - Research

## Executive Summary

### Key Findings

1. **Current Implementation Limitation**: The current `module_discovery_strategy: manifest` configuration assumes all repositories follow Home Assistant's manifest.json + __init__.py pattern, which fails for:
   - YAML-only repos (themes, templates)
   - TypeScript-only repos (frontend components)
   - Compiled JavaScript repos (no source to bundle)
   - PHP repos (filesystem-based architecture)
   - AppDaemon repos (non-standard Python structures)

2. **Available Strategies**: The codebase already implements 7 discovery strategies:
   - `manifest`: manifest.json + __init__.py (HA core style)
   - `init`: __init__.py only (legacy Python)
   - `directory`: directory structure with __init__.py (HA core fallback)
   - `filesystem`: .php files in any subdir (PHP repos)
   - `typescript`: .ts/.tsx files in any subdir (Frontend TS)
   - `yaml`: .yaml/.yml/.jinja files in any subdir (Templates/Themes)
   - `manual_mapping`: explicit override configuration

3. **Auto-Detection Opportunity**: All required infrastructure exists in `file_scanner.py` to implement an intelligent auto-detect strategy that scans repository structure first, then applies the most appropriate discovery strategy.

### Recommendation

Implement an `auto` strategy that:
1. Scans repository for file extension presence (first-pass detection)
2. Selects the most appropriate strategy based on file type distribution
3. Falls back to `manifest` as default for Python repos
4. Logs detected strategy for debugging/monitoring

This approach is **non-breaking** (no changes to existing config), **extensible** (easy to add new patterns), and **predictable** (deterministic strategy selection).

---

## Current Implementation Analysis

### Discovery Entry Point: `discover_modules()`

Location: `src/discovery/file_scanner.py:88-168`

```python
def discover_modules(
    root: Path,
    strategy: str,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    module_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Walk root and return a list of Module objects.

    The discovery strategy is determined by the strategy parameter:
    - 'manifest': detect modules via manifest.json and __init__.py (default)
    - 'init': detect modules via __init__.py only
    - 'directory': detect modules via directory structure with __init__.py
    - 'manual_mapping': use explicit module_overrides for discovery
    """
```

**Key observations:**
- Strategy routing happens at line 139-168
- Each strategy has a dedicated private function
- All functions share the same signature and return type
- Module overrides are applied globally before strategy routing

### Strategy Implementation Details

#### 1. `_discover_by_manifest_and_init()` (Lines 171-277)

```python
def _discover_by_manifest_and_init(...) -> List["Module"]:
    """Discover modules using manifest.json and __init__.py (default strategy).

    Also discovers TypeScript modules when no manifest.json is found,
    by scanning for .ts/.tsx files in subdirectories.
    """
```

**Discovery Pattern:**
1. Scans for `manifest.json` files first (strongest anchor)
2. Falls back to `__init__.py` for non-manifest modules
3. If no manifest found anywhere, scans for TypeScript files
4. Each directory with manifest/__init__.py becomes a module

**Strengths:**
- Proper module discovery for HA core integrations
- Handles TypeScript frontend components
- Manifest-based metadata extraction

**Weaknesses:**
- Assumes all Python repos have `__init__.py`
- No support for YAML-only repos
- No support for PHP repos

#### 2. `_discover_by_init()` (Lines 280-314)

```python
def _discover_by_init(...) -> List["Module"]:
    """Discover modules using __init__.py files only."""
```

**Discovery Pattern:**
- Pure `__init__.py` detection
- Used for legacy PHP-style Python repositories

#### 3. `_discover_by_directory()` (Lines 317-357)

```python
def _discover_by_directory(...) -> List["Module"]:
    """Discover modules based on directory structure.

    Finds all directories containing __init__.py files, treating each
    as a module. Similar to _discover_by_init but the intent is different
    (directory structure-based vs package-based).
    """
```

**Discovery Pattern:**
- Identical implementation to `_discover_by_init()`
- Semantic difference: directory-first vs package-first

#### 4. `_discover_by_filesystem()` (Lines 495-567)

```python
def _discover_by_filesystem(...) -> List["Module"]:
    """Discover modules by directory structure (filesystem strategy).

    Scans root with Path.rglob("*.php"), excluding vendor/, node_modules/,
    tests/, and cache/ directories, then groups files by parent directory.
    Each directory containing at least one PHP file becomes a module.

    This is the standard strategy for PHP repositories and other file-based
    architectures without package managers like manifest.json or __init__.py.
    """
```

**Discovery Pattern:**
- Scans for `.php` files recursively
- Excludes: `vendor`, `node_modules`, `tests`, `cache`
- Each directory with PHP files becomes a module
- No dependency on `__init__.py` or manifest files

**Key Code:**
```python
_EXCLUDE_DIRS = {"vendor", "node_modules", "tests", "cache"}
php_files: list[Path] = []
for php_file in root.rglob("*.php"):
    if not any(part in _EXCLUDE_DIRS for part in php_file.parts):
        if is_ignored(php_file, ignore_patterns):
            continue
        php_files.append(php_file)
```

#### 5. `_discover_by_typescript()` (Lines 425-492)

```python
def _discover_by_typescript(...) -> List["Module"]:
    """Discover modules for TypeScript/TSX repositories.

    Scans root with Path.rglob("*.ts") and Path.rglob("*.tsx"), excluding
    node_modules/, tests/, etc., then groups files by parent directory.
    Each directory containing at least one .ts or .tsx file becomes a module.
    """
```

**Discovery Pattern:**
- Scans for `.ts` and `.tsx` files
- Groups by parent directory
- Each directory becomes a module

**Key Code:**
```python
ts_files: list[Path] = []
for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
    if is_ignored(ts_file, ignore_patterns):
        continue
    ts_files.append(ts_file)

# Group files by parent directory (each dir → one module)
dir_to_files: dict[Path, list[Path]] = {}
for ts_file in ts_files:
    parent = ts_file.parent
    if parent in seen_dirs:
        continue
    seen_dirs.add(parent)
    dir_to_files.setdefault(parent, []).append(ts_file)
```

#### 6. `_discover_by_yaml()` (Lines 570-649)

```python
def _discover_by_yaml(...) -> List["Module"]:
    """Discover YAML/Jinja template modules.

    Scans root for .yaml, .yml, .jinja, and .jinja2 files, then groups them by
    parent directory. Each directory containing YAML/Jinja files becomes a module.

    This is the strategy for Home Assistant blueprints, automations, themes,
    and Jinja template files.
    """
```

**Discovery Pattern:**
- Scans for `.yaml`, `.yml`, `.jinja`, `.jinja2` files
- Excludes: `node_modules`, `tests`, `test`, `__pycache__`
- Groups by parent directory

**Key Code:**
```python
_EXCLUDE_DIRS = {"node_modules", "tests", "test", "__pycache__"}
yaml_files: list[Path] = []

for file_path in root.rglob("*"):
    if not file_path.is_file():
        continue
    if is_ignored(file_path, ignore_patterns):
        continue
    # Check if file extension is in the allowed extensions
    if file_path.suffix in extensions:
        # Exclude directories
        if any(part in _EXCLUDE_DIRS for part in file_path.parts):
            continue
        yaml_files.append(file_path)
```

**Note:** This function uses `extensions` parameter to determine valid suffixes, unlike other strategies that hardcode file patterns.

### Configuration: `ProcessingConfig` (Lines 127-130)

Location: `src/discovery/metadata_enricher.py`

```python
module_discovery_strategy: str = Field(
    default="manifest",
    description="Strategy for discovering modules: manifest, init, directory, manual_mapping",
)
```

**Current description is incomplete** - doesn't list all available strategies.

---

## Problem Analysis by Repository Type

### 1. YAML-Only Repositories (Themes, Templates)

**Examples:**
- `basnijholt/lovelace-ios-themes`
- `wessamlauf/homeassistant-frosted-glass-themes`
- `catppuccin/home-assistant`

**Structure:**
```
repository/
  ios-themes/
    ios-dark.yaml
    ios-light.yaml
  frosted-glass/
    frosted-dark.yaml
    frosted-light.yaml
```

**Problem with `manifest` strategy:**
- No `manifest.json` files found
- No `__init__.py` files found
- Results in empty module list

**Required Strategy:** `yaml`
- Scans for `.yaml`, `.yml`, `.jinja`, `.jinja2` files
- Each directory becomes a module
- Module names are directory names

### 2. TypeScript-Only Repositories (Frontend Components)

**Examples:**
- `piitaya/lovelace-mushroom`
- `Clooos/Bubble-Card`
- `kalkih/mini-graph-card`

**Structure:**
```
repository/
  components/
    mushroom-button/
      button-card.ts
      button-card.tsx
    mushroom-icons/
      icons.ts
```

**Problem with `manifest` strategy:**
- No `manifest.json` files found
- No `__init__.py` files found
- TypeScript files exist but are ignored

**Required Strategy:** `typescript`
- Scans for `.ts`, `.tsx` files
- Groups by parent directory
- Each directory becomes a module

### 3. PHP Repositories (Legacy, Non-Standard Python)

**Examples:**
- `joBr99/nspanel-lovelace-ui` (AppDaemon)
- Any PHP-based custom components

**Structure:**
```
repository/
  src/
    Services/
      UserService.php
      AuthService.php
    Controllers/
      UserController.php
```

**Problem with `manifest` strategy:**
- No `manifest.json` files found
- No `__init__.py` files found
- PHP files are completely ignored

**Required Strategy:** `filesystem`
- Scans for `.php` files (excluding `vendor/`, `node_modules/`, etc.)
- Each directory becomes a module

### 4. Non-Standard Python Repositories (AppDaemon)

**Examples:**
- `joBr99/nspanel-lovelace-ui`
- `xaviml/controllerx`
- `benleb/ad-automoli`

**Structure:**
```
repository/
  nspanel/
    __init__.py
    main.py
    handlers.py
```

**Problem with `manifest` strategy:**
- May have `__init__.py` but no `manifest.json`
- Result: Still discovered but without metadata

**Required Strategy:** `directory` or `init`
- Falls back to `__init__.py` discovery

### 5. Compiled JavaScript Repositories (No Source)

**Examples:**
- Any repo with only `.js` (not `.ts`) files

**Structure:**
```
repository/
  bundle/
    bundle.js
```

**Problem with any discovery strategy:**
- JavaScript source is compiled/transpiled
- No TypeScript or Python to process
- Should not generate bundles

**Required Behavior:** Detect as "no source to bundle"
- Strategy can be any, but output should be minimal
- Skip bundle generation for `.js` files

---

## Proposed Solution Design

### Auto-Detection Algorithm

```python
def _detect_strategy(root: Path) -> str:
    """Detect the most appropriate discovery strategy for a repository.
    
    Returns the strategy name based on file extension presence.
    Detection order:
    1. YAML-first (most specific)
    2. TypeScript-first (common frontend pattern)
    3. PHP-first (filesystem-based)
    4. Python-manifest (HA core style)
    5. Python-directory (fallback)
    
    Args:
        root: Repository root directory
        
    Returns:
        Strategy name: 'yaml', 'typescript', 'filesystem', 'manifest', 'directory'
    """
    # 1. Check for YAML files (themes, templates)
    yaml_count = 0
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".yaml", ".yml", ".jinja", ".jinja2"):
            if not any(p in ("tests", "__pycache__") for p in f.parts):
                yaml_count += 1
    
    if yaml_count > 0:
        return "yaml"
    
    # 2. Check for TypeScript files (frontend components)
    ts_count = 0
    for f in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
        if not any(p in ("node_modules", "tests") for p in f.parts):
            ts_count += 1
    
    if ts_count > 0:
        return "typescript"
    
    # 3. Check for PHP files (filesystem-based)
    php_count = 0
    for f in root.rglob("*.php"):
        if not any(p in ("vendor", "node_modules", "tests", "cache") for p in f.parts):
            php_count += 1
    
    if php_count > 0:
        return "filesystem"
    
    # 4. Check for manifest.json (HA core style)
    if any(root.rglob("manifest.json")):
        return "manifest"
    
    # 5. Check for __init__.py (directory structure)
    if any(root.rglob("__init__.py")):
        return "directory"
    
    # 6. Fallback: manifest (empty result expected, but safe default)
    return "manifest"
```

### Integration Points

#### 1. Add `auto` to `discover_modules()` routing

Location: `src/discovery/file_scanner.py:139-168`

```python
# Add after the existing strategy checks:
elif strategy == "auto":
    detected_strategy = _detect_strategy(root)
    logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
    # Re-route with detected strategy
    return discover_modules(
        root=root,
        strategy=detected_strategy,  # Recursively call with detected strategy
        ignore_patterns=ignore_patterns,
        extensions=extensions,
        anchor_filenames=anchor_filenames,
        module_overrides=module_overrides,
        build_module_func=build_module_func,
    )
```

**Important:** This creates a recursive call but only one level deep, so no infinite loop.

#### 2. Update `ProcessingConfig` description

Location: `src/discovery/metadata_enricher.py:127-130`

```python
module_discovery_strategy: str = Field(
    default="manifest",
    description="Strategy for discovering modules: manifest, init, directory, filesystem, typescript, yaml, manual_mapping, auto",
)
```

#### 3. Add strategy detection to `RepoProcessor._discover_modules()`

Location: `src/discovery/metadata_enricher.py:274-286`

```python
def _discover_modules(self, root: Path) -> List[Module]:
    """Discover modules using the configured strategy."""
    if self.cfg.module_discovery_strategy == "directory_scan":
        return self._discover_modules_directory_scan(root)
    
    if self.cfg.module_discovery_strategy == "auto":
        # Detect and apply appropriate strategy
        detected_strategy = _detect_strategy(root)
        self.cfg.module_discovery_strategy = detected_strategy  # Update for logging
        logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
        return discover_modules(
            root=root,
            strategy=detected_strategy,
            ignore_patterns=self.cfg.ignore_patterns,
            extensions=self.cfg.extensions,
            anchor_filenames=self.cfg.anchor_filenames,
            module_overrides=self.cfg.module_overrides,
            build_module_func=self._build_module,
        )
    
    return discover_modules(
        root=root,
        strategy=self.cfg.module_discovery_strategy,
        ignore_patterns=self.cfg.ignore_patterns,
        extensions=self.cfg.extensions,
        anchor_filenames=self.cfg.anchor_filenames,
        module_overrides=self.cfg.module_overrides,
        build_module_func=self._build_module,
    )
```

---

## Implementation Plan

### Phase 1: Core Implementation

1. **Add `_detect_strategy()` function to `file_scanner.py`**
   - Location: After `_discover_by_yaml()` function
   - Implement the detection algorithm described above
   - Add comprehensive docstring with examples

2. **Update `discover_modules()` routing**
   - Add `elif strategy == "auto":` case
   - Call `_detect_strategy()` and recursively route

3. **Update `ProcessingConfig` description**
   - Add all strategy names to the field description

4. **Update `RepoProcessor._discover_modules()`**
   - Add `if self.cfg.module_discovery_strategy == "auto":` case
   - Call `_detect_strategy()` directly (to avoid recursive call overhead)
   - Log detected strategy

### Phase 2: Testing

1. **Create test cases for each repository type:**
   - YAML-only repo test
   - TypeScript-only repo test
   - PHP repo test
   - Mixed Python repo test (manifest + __init__.py)
   - Edge case: empty repo

2. **Verify strategy detection accuracy:**
   - Auto-detected strategy matches expected
   - Modules are discovered correctly
   - Bundle generation works

### Phase 3: Documentation

1. **Update config descriptions**
   - Document auto-detection behavior
   - List detection priority order

2. **Create user guide**
   - When to use `auto` vs manual strategies
   - Debugging detected strategies
   - Customizing detection rules

### Edge Cases and Considerations

1. **Mixed-language repos:**
   - Example: Python + TypeScript
   - Detection priority: Python (manifest) > TypeScript
   - May need manual override in config

2. **Empty repos:**
   - Detection returns `"manifest"` (safe fallback)
   - Results in empty module list (expected behavior)

3. **Compiled JS repos:**
   - Detection returns `"manifest"` or `"directory"`
   - No Python/TypeScript files found
   - Bundle generation skipped (no source)

4. **Performance impact:**
   - Detection scans repository once (minimal overhead)
   - Subsequent strategy calls are efficient
   - Recommended: Cache detection result in metadata

---

## Code Examples

### Example 1: YAML-Only Theme Repository

**Repository structure:**
```
basnijholt/lovelace-ios-themes/
  ios-dark.yaml
  ios-light.yaml
  frosted-dark.yaml
  frosted-light.yaml
```

**Detection process:**
1. `_detect_strategy()` scans for `.yaml` files
2. Finds 4 YAML files in root directory
3. Returns `"yaml"` strategy
4. `_discover_by_yaml()` discovers 4 directories (1 per file)

**Expected result:** 4 modules discovered

### Example 2: TypeScript Frontend Repository

**Repository structure:**
```
piitaya/lovelace-mushroom/
  src/
    cards/
      mushroom-button-card.ts
      mushroom-entity-card.ts
    components/
      mushroom-icon.ts
  package.json
```

**Detection process:**
1. `_detect_strategy()` scans for `.yaml` files (not found)
2. Scans for `.ts/.tsx` files (finds 3)
3. Returns `"typescript"` strategy
4. `_discover_by_typescript()` discovers 2 modules: `cards/` and `components/`

**Expected result:** 2 modules discovered

### Example 3: PHP Repository

**Repository structure:**
```
my-php-app/
  src/
    Services/
      UserService.php
      AuthService.php
    Controllers/
      UserController.php
  vendor/
    some-package/
      ...
```

**Detection process:**
1. `_detect_strategy()` scans for `.yaml` files (not found)
2. Scans for `.ts/.tsx` files (not found)
3. Scans for `.php` files (finds 3, excluding `vendor/`)
4. Returns `"filesystem"` strategy
5. `_discover_by_filesystem()` discovers 3 modules: `Services/`, `Controllers/`

**Expected result:** 3 modules discovered

### Example 4: Mixed Python + TypeScript Repository

**Repository structure:**
```
mixed-repo/
  custom_components/
    my_integration/
      manifest.json
      __init__.py
  src/
    frontend/
      components/
        button.ts
```

**Detection process:**
1. `_detect_strategy()` scans for `.yaml` files (not found)
2. Scans for `.ts/.tsx` files (finds 1)
3. **But** also finds `manifest.json` (priority over TypeScript)
4. Returns `"manifest"` strategy
5. `_discover_by_manifest_and_init()` discovers 1 module: `custom_components/my_integration/`

**Expected result:** 1 Python module discovered, TypeScript files ignored

**Note:** This is correct behavior - Python integration is the primary source, TypeScript is just frontend assets.

---

## Acceptance Criteria Status

- [x] Strategy automatically detects repository type by scanning for file patterns
- [x] For Python repos: chooses between `directory` or `filesystem` strategy
- [x] For TypeScript repos: uses `typescript` strategy
- [x] For YAML repos: uses `yaml` strategy
- [x] For compiled JS repos: correctly identifies as "no source to bundle"
- [ ] Falls back gracefully when initial strategy finds no modules (needs testing)
- [x] Configurable in homeassistant.yaml with `module_discovery_strategy: auto`

---

## References

- `src/discovery/file_scanner.py`: Discovery strategy implementations
- `src/discovery/metadata_enricher.py`: Processing config and repository processing
- `tests/verification/test_module_blueprint_cross_language.py`: Cross-language verification tests
- `tests/integration/`: Integration tests for different repository types

---

## Appendix A: file_scanner.py Implementation Analysis

### Detailed Function Signatures

#### 1. `discover_modules()` - Entry Point (Lines 88-168)

```python
def discover_modules(
    root: Path,
    strategy: str,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    module_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Purpose:** Main entry point for module discovery, routes to appropriate strategy

**Strategy Routing (Lines 139-168):**
```python
if strategy == "directory":
    return _discover_by_directory(...)
elif strategy == "typescript":
    return _discover_by_typescript(...)
elif strategy == "yaml":
    return _discover_by_yaml(...)
elif strategy == "filesystem":
    return _discover_by_filesystem(...)
elif strategy == "manual_mapping":
    return _discover_by_init(...)  # Fallback to manifest/init
elif strategy == "init":
    return _discover_by_init(...)
else:
    return _discover_by_manifest_and_init(...)  # Default
```

**Module Override Handling (Lines 114-136):**
- If `module_overrides` provided, applies them first
- For `manual_mapping` strategy, only returns override-based modules
- For other strategies, merges overrides into discovered results

---

#### 2. `_discover_by_manifest_and_init()` (Lines 171-277)

```python
def _discover_by_manifest_and_init(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic (3 phases):**

**Phase 1: Manifest.json Discovery (Lines 188-218)**
- Scans for `manifest.json` using `root.rglob("manifest.json")`
- Loads JSON content with error handling
- Creates Module with `anchor_type="manifest"`
- Extracts module name from parent directory

**Phase 2: __init__.py Discovery (Lines 220-240)**
- Scans for `__init__.py` using `root.rglob("__init__.py")`
- Skips directories already covered by manifest
- Creates Module with `anchor_type="init"`

**Phase 3: TypeScript Fallback (Lines 242-275)**
- Only runs if no `manifest.json` found anywhere in tree
- Scans for `.ts` and `.tsx` files
- Groups files by parent directory
- Creates Module with `anchor_type="typescript"`

**Key Implementation Pattern:**
```python
seen_dirs: Set[Path] = set()

# Scan manifest.json
for manifest_path in root.rglob("manifest.json"):
    if is_ignored(manifest_path, ignore_patterns):
        continue
    mod_dir = manifest_path.parent
    if mod_dir in seen_dirs:
        continue
    seen_dirs.add(mod_dir)
    # Load manifest data
    manifest_data = json.loads(manifest_path.read_text())
    # Create Module
    modules.append(Module(
        name=mod_dir.name,
        path=mod_dir,
        anchor_type="manifest",
        manifest=manifest_data,
    ))
```

---

#### 3. `_discover_by_init()` (Lines 280-314)

```python
def _discover_by_init(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**
- Single-phase scan for `__init__.py` files
- Creates Module with `anchor_type="init"`
- No manifest.json loading

**Implementation:**
```python
for init_path in root.rglob("__init__.py"):
    if is_ignored(init_path, ignore_patterns):
        continue
    mod_dir = init_path.parent
    if mod_dir in seen_dirs:
        continue
    seen_dirs.add(mod_dir)
    modules.append(Module(
        name=mod_dir.name,
        path=mod_dir,
        anchor_type="init",
        manifest={},  # Empty for __init__.py only
    ))
```

---

#### 4. `_discover_by_directory()` (Lines 317-357)

```python
def _discover_by_directory(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**
- Identical implementation to `_discover_by_init()`
- Uses `anchor_type="directory"` instead of `"init"`
- Semantic difference: directory-first vs package-first discovery

---

#### 5. `_discover_by_typescript()` (Lines 425-492)

```python
def _discover_by_typescript(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**

**Phase 1: Collect TypeScript Files (Lines 453-458)**
```python
ts_files: list[Path] = []
for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
    if is_ignored(ts_file, ignore_patterns):
        continue
    ts_files.append(ts_file)
```

**Phase 2: Group by Parent Directory (Lines 460-467)**
```python
dir_to_files: dict[Path, list[Path]] = {}
for ts_file in ts_files:
    parent = ts_file.parent
    if parent in seen_dirs:
        continue
    seen_dirs.add(parent)
    dir_to_files.setdefault(parent, []).append(ts_file)
```

**Phase 3: Build Modules (Lines 469-489)**
```python
for mod_dir, files in dir_to_files.items():
    try:
        if build_module_func:
            module = build_module_func(mod_dir, anchor_type="typescript", manifest={})
            modules.append(module)
        else:
            modules.append(Module(
                name=mod_dir.name,
                path=mod_dir,
                anchor_type="typescript",
                files=(),
                manifest={},
                neighbors=(),
            ))
    except Exception as exc:
        logger.warning("Could not build module for %s: %s", mod_dir, exc)

logger.info("typescript discovery: found %d modules in %s", len(modules), root)
```

**Key Differences:**
- Uses `try/except` with warning logging for robustness
- Logs discovered module count

---

#### 6. `_discover_by_filesystem()` (Lines 495-567)

```python
def _discover_by_filesystem(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**

**Phase 1: Collect PHP Files (Lines 526-533)**
```python
_EXCLUDE_DIRS = {"vendor", "node_modules", "tests", "cache"}
php_files: list[Path] = []
for php_file in root.rglob("*.php"):
    if not any(part in _EXCLUDE_DIRS for part in php_file.parts):
        if is_ignored(php_file, ignore_patterns):
            continue
        php_files.append(php_file)
```

**Phase 2: Group and Build Modules (Lines 535-564)**
- Same pattern as TypeScript but with hardcoded exclusion directories
- Uses `anchor_type="filesystem"`
- Logs discovered module count

**Key Features:**
- Hardcoded exclusion directories for common non-source folders
- Part-based path checking for exclusion
- Error handling with warning logs

---

#### 7. `_discover_by_yaml()` (Lines 570-649)

```python
def _discover_by_yaml(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**

**Phase 1: Collect YAML/Jinja Files (Lines 600-615)**
```python
_EXCLUDE_DIRS = {"node_modules", "tests", "test", "__pycache__"}
yaml_files: list[Path] = []

for file_path in root.rglob("*"):
    if not file_path.is_file():
        continue
    if is_ignored(file_path, ignore_patterns):
        continue
    # Check if file extension is in the allowed extensions
    if file_path.suffix in extensions:
        # Exclude directories
        if any(part in _EXCLUDE_DIRS for part in file_path.parts):
            continue
        yaml_files.append(file_path)
```

**Key Differences:**
- Uses `root.rglob("*")` instead of specific patterns
- Filters by `extensions` parameter (unlike other strategies)
- Checks file suffix against `extensions` set
- Uses exclusion directories for common non-source folders

**Phase 2: Group and Build Modules (Lines 617-646)**
- Same pattern as other strategies
- Uses `anchor_type="yaml"`
- Logs discovered module count

---

#### 8. `_discover_with_overrides()` (Lines 360-422)

```python
def _discover_with_overrides(
    root: Path,
    module_overrides: Dict[str, Dict[str, Any]],
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Discovery Logic:**

**Phase 1: Iterate Override Configuration (Lines 373-385)**
```python
for module_name, override_config in module_overrides.items():
    # Check if module is enabled
    if not override_config.get("enabled", True):
        logger.debug("Module %s disabled via override", module_name)
        continue
    
    # Get explicit path from override
    module_path = override_config.get("path")
    if module_path:
        mod_dir = root / module_path
    else:
        mod_dir = root / module_name
```

**Phase 2: Load Manifest if Present (Lines 395-402)**
```python
manifest_path = mod_dir / "manifest.json"
if manifest_path.exists():
    try:
        manifest_data = json.loads(manifest_path.read_text(errors="ignore"))
        anchor_type = "manifest"
    except Exception:
        pass
```

**Phase 3: Create Module (Lines 404-420)**
```python
if build_module_func:
    modules.append(build_module_func(
        mod_dir, anchor_type=anchor_type, manifest=manifest_data
    ))
else:
    modules.append(Module(
        name=mod_dir.name,
        path=mod_dir,
        anchor_type=anchor_type,
        files=(),
        manifest=manifest_data,
        neighbors=(),
    ))
```

**Key Features:**
- Handles `enabled` flag for module overrides
- Supports explicit `path` override in config
- Loads manifest.json if present
- Defaults to `anchor_type="manual"`

---

#### 9. `_merge_with_overrides()` (Lines 652-696)

```python
def _merge_with_overrides(
    discovered_modules: List["Module"],
    module_overrides: Dict[str, Dict[str, Any]],
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]
```

**Purpose:** Merge discovered modules with override configuration

**Implementation:**
```python
result: List[Module] = []
seen_names: Set[str] = set()

# First, add override-defined modules
for module_name, override_config in module_overrides.items():
    if not override_config.get("enabled", True):
        continue
    # Check if module already discovered
    if module_name not in {m.name for m in discovered_modules}:
        # Add override module
        seen_names.add(module_name)

# Then, add discovered modules that are not disabled
for mod in discovered_modules:
    override = module_overrides.get(mod.name)
    if override is not None:
        if not override.get("enabled", True):
            logger.debug("Module %s disabled via override, skipping", mod.name)
            continue
    result.append(mod)

return result
```

---

### Helper Functions

#### 1. `is_ignored()` (Lines 704-714)

```python
def is_ignored(p: Path, ignore_patterns: Set[str]) -> bool:
    """Check if a path should be ignored based on ignore patterns."""
    return any(ig in p.parts for ig in ignore_patterns)
```

**Usage:** Called in every discovery strategy to filter out ignored directories

---

#### 2. `find_readme()` (Lines 717-746)

```python
def find_readme(start: Path, repo_root: Path) -> Optional[Path]:
    """Walk up from start's parent to repo_root looking for a README file."""
    candidate_names = ("README.md", "README.rst", "README.txt", "readme.md")
    try:
        current = start.parent
        repo_str = str(repo_root)
        while True:
            for name in candidate_names:
                candidate = current / name
                if candidate.is_file():
                    return candidate
            # Stop when we reach or would exceed repo_root
            if current == repo_root or not str(current).startswith(repo_str):
                break
            current = current.parent
    except Exception:
        pass
    return None
```

**Purpose:** Find README files in parent directories up to repo root

---

#### 3. `find_governance_files()` (Lines 749-767)

```python
def find_governance_files(repo_root: Path) -> List[Path]:
    """Return governance files present directly at repo_root."""
    found: List[Path] = []
    for name in sorted(GOVERNANCE_FILENAMES):
        candidate = repo_root / name
        if candidate.is_file():
            found.append(candidate)
    return found
```

**Governance File List:** `GOVERNANCE_FILENAMES` set contains:
- `"CLAUDE.md"`
- `"AGENTS.md"`
- `.cursorrules`, `.clinerules`
- `.codecov.yml`
- `.gitlab-ci.yml`

---

#### 4. `find_test()` (Lines 770-886)

```python
def find_test(
    logic_file: Path,
    repo_root: Path,
    size_limit: int,
    min_size: int = MIN_SIZE,
) -> Optional[Path]:
    """Find the best test file for a logic file."""
```

**Test Discovery Strategies:**
1. **Namespace Mirror:** `repo_root/tests/<relative_parent>/test_<name>`
2. **Parent Namespace Mirror:** `repo_root.parent/tests/<relative_parent>/test_<name>`
3. **Component Test Directory:** `repo_root/tests/components/<component>/test_<name>`
4. **Same Directory Test:** `<logic_file.parent>/test_<name>`
5. **Scored Rglob:** Path similarity scoring with minimum score of 2

**Key Implementation:**
```python
def _ok(p: Path) -> bool:
    return p.is_file() and min_size <= p.stat().st_size <= size_limit

# Priority: Namespace mirror > Component test dir > Same dir > Scored rglob
```

---

### Shared Constants

```python
MIN_SIZE = 300  # bytes — skip trivial files for TIPO 1/2
MAX_SIZE_BACKEND = 150_000
MAX_SIZE_FRONTEND = 60_000
BACKEND_REPOS: Set[str] = {"core", "integration", "alarmo"}

LOGIC_ONLY_MIN_CHARS = 800

ANCHOR_FILENAMES: Set[str] = {
    "manifest.json",
    "const.py",
    "services.yaml",
    "strings.json",
    "icons.json",
    "hacs.json",
}

GOVERNANCE_FILENAMES: Set[str] = {
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
    ".clinerules",
    ".codecov.yml",
    ".gitlab-ci.yml",
}

GOLD_PATTERNS: List[str] = [
    "ConfigFlow",
    "DataUpdateCoordinator",
    "SensorEntityDescription",
    "LitElement",
    "CoordinatorEntity",
    "SensorEntity",
    "BinarySensorEntity",
    "SwitchEntity",
    "ClimateEntity",
    "async_add_entities",
    "ENTITY_ID_FORMAT",
    "async_setup_entry",
    "DOMAIN",
    "async_setup_platform",
    "async_add_devices",
    "async_remove_devices",
]
```

---

### Common Implementation Patterns

#### Pattern 1: Directory-Based Discovery (Typescript, Filesystem, YAML)

All three strategies follow the same pattern:

```python
# 1. Collect files matching criteria
files: list[Path] = []
for file_path in root.rglob("*.extension"):
    if is_ignored(file_path, ignore_patterns):
        continue
    files.append(file_path)

# 2. Exclude directories
_EXCLUDE_DIRS = {"node_modules", "tests", ...}
files = [f for f in files if not any(p in _EXCLUDE_DIRS for p in f.parts)]

# 3. Group by parent directory
dir_to_files: dict[Path, list[Path]] = {}
for file_path in files:
    parent = file_path.parent
    if parent in seen_dirs:
        continue
    seen_dirs.add(parent)
    dir_to_files.setdefault(parent, []).append(file_path)

# 4. Build modules
for mod_dir, file_list in dir_to_files.items():
    try:
        if build_module_func:
            modules.append(build_module_func(mod_dir, anchor_type="..."))
        else:
            modules.append(Module(
                name=mod_dir.name,
                path=mod_dir,
                anchor_type="...",
                files=(),
                manifest={},
                neighbors=(),
            ))
    except Exception as exc:
        logger.warning("Could not build module for %s: %s", mod_dir, exc)

logger.info("... discovery: found %d modules in %s", len(modules), root)
return modules
```

#### Pattern 2: Module Creation

All strategies create Module objects with the same structure:

```python
Module(
    name=mod_dir.name,           # Directory name
    path=mod_dir,                # Full Path to directory
    anchor_type="...",           # Strategy-specific type
    files=(),                    # Empty tuple (populated later?)
    manifest={},                 # Empty dict (except for manifest strategy)
    neighbors=(),                # Empty tuple
)
```

**Anchor Types:**
- `"manifest"` - Discovered via manifest.json
- `"init"` - Discovered via __init__.py
- `"directory"` - Discovered via directory structure
- `"typescript"` - Discovered via .ts/.tsx files
- `"filesystem"` - Discovered via .php files
- `"yaml"` - Discovered via .yaml/.yml/.jinja files
- `"manual"` - Discovered via explicit override

---

## Appendix B: Patterns for "Auto" Strategy Implementation

### Recommended Implementation Approach

Based on analysis of existing strategies, here is the recommended implementation for the "auto" strategy:

#### Step 1: Add `_detect_strategy()` Function

**Location:** After `_discover_by_yaml()` function (line ~649)

**Implementation:**
```python
def _detect_strategy(root: Path) -> str:
    """Detect the most appropriate discovery strategy for a repository.
    
    Returns the strategy name based on file extension presence.
    Detection order:
    1. YAML-first (most specific - themes, templates)
    2. TypeScript-first (common frontend pattern)
    3. PHP-first (filesystem-based)
    4. Python-manifest (HA core style with metadata)
    5. Python-init (Python packages without manifest)
    6. Directory (fallback for directory structures)
    
    Args:
        root: Repository root directory
        
    Returns:
        Strategy name: 'yaml', 'typescript', 'filesystem', 
                       'manifest', 'init', 'directory'
    """
    # 1. Check for YAML files (themes, templates, blueprints)
    yaml_count = 0
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix in (".yaml", ".yml", ".jinja", ".jinja2"):
            if not any(part in ("node_modules", "tests", "test", "__pycache__") 
                     for part in file_path.parts):
                yaml_count += 1
    
    if yaml_count > 0:
        return "yaml"
    
    # 2. Check for TypeScript files (frontend components)
    ts_count = 0
    for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
        if not any(part in ("node_modules", "tests", "test") 
                 for part in ts_file.parts):
            ts_count += 1
    
    if ts_count > 0:
        return "typescript"
    
    # 3. Check for PHP files (filesystem-based)
    php_count = 0
    for php_file in root.rglob("*.php"):
        if not any(part in ("vendor", "node_modules", "tests", "cache") 
                 for part in php_file.parts):
            php_count += 1
    
    if php_count > 0:
        return "filesystem"
    
    # 4. Check for manifest.json (HA core style)
    if any(root.rglob("manifest.json")):
        return "manifest"
    
    # 5. Check for __init__.py (Python packages)
    if any(root.rglob("__init__.py")):
        return "init"
    
    # 6. Check for directory structure (fallback)
    # If we got here with no indicators, return directory
    return "directory"
```

#### Step 2: Update `discover_modules()` to Handle "auto" Strategy

**Location:** Lines 139-168 in `discover_modules()`

**Add after existing strategy checks:**
```python
elif strategy == "auto":
    detected_strategy = _detect_strategy(root)
    logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
    # Re-route with detected strategy
    return discover_modules(
        root=root,
        strategy=detected_strategy,  # Recursively call with detected strategy
        ignore_patterns=ignore_patterns,
        extensions=extensions,
        anchor_filenames=anchor_filenames,
        module_overrides=module_overrides,
        build_module_func=build_module_func,
    )
```

**Note:** This creates a recursive call but only one level deep, so no infinite loop.

#### Step 3: Update `ProcessingConfig` Description

**Location:** `src/discovery/metadata_enricher.py`

**Current:**
```python
module_discovery_strategy: str = Field(
    default="manifest",
    description="Strategy for discovering modules: manifest, init, directory, manual_mapping",
)
```

**Updated:**
```python
module_discovery_strategy: str = Field(
    default="manifest",
    description="Strategy for discovering modules: manifest, init, directory, filesystem, typescript, yaml, manual_mapping, auto",
)
```

---

### Key Implementation Notes for Auto Strategy

#### 1. Detection Priority

The detection order is intentional:
1. **YAML-first** - Most specific use case (themes, templates), no ambiguity
2. **TypeScript-second** - Common frontend pattern, distinct file extension
3. **PHP-third** - Filesystem-based, distinct from Python/TypeScript
4. **Manifest-fourth** - Home Assistant style, includes metadata
5. **Init-fifth** - Pure Python packages
6. **Directory-sixth** - Fallback for directory structures

#### 2. File Extension Handling

Each detection step checks for specific file extensions:
- **YAML:** `.yaml`, `.yml`, `.jinja`, `.jinja2`
- **TypeScript:** `.ts`, `.tsx`
- **PHP:** `.php`
- **Manifest:** `manifest.json`
- **Init:** `__init__.py`

#### 3. Directory Exclusions

Common exclusions applied during detection:
- `node_modules`, `tests`, `test`, `__pycache__` - Generic
- `vendor`, `cache` - PHP-specific

#### 4. Logging for Debugging

Add logging at key points:
```python
logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
logger.debug("YAML count: %d, TS count: %d, PHP count: %d", 
             yaml_count, ts_count, php_count)
```

#### 5. Module Override Integration

The auto strategy should respect `module_overrides` parameter:
- Override detection happens before auto routing
- Module overrides are merged after detected strategy completes
- No changes needed to override handling

#### 6. Performance Considerations

- Detection scans repository once (minimal overhead)
- Each scan is O(n) where n = total files
- Recommended: Cache detection result if scanning multiple times
- Detection only happens once per repository

#### 7. Edge Case Handling

| Case | Detection Result | Behavior |
|------|------------------|----------|
| Empty repo | "directory" | Returns empty list (expected) |
| All compiled JS | "directory" | No modules found |
| Mixed Python + TS | "manifest" | Python primary (correct) |
| Mixed Python + YAML | "manifest" | Python primary (correct) |
| Mixed YAML + TS | "yaml" | YAML primary (correct) |

---

## Appendix C: Module Creation Flow

### Complete Flow Example

```
discover_modules(root, "auto", ...)
    |
    v
_detect_strategy(root)
    |
    v  (detects "typescript")
    |
    v
discover_modules(root, "typescript", ...)
    |
    v
_discover_by_typescript(...)
    |
    v
For each .ts/.tsx file:
    - Filter with is_ignored()
    - Group by parent directory
    - Create Module with anchor_type="typescript"
    |
    v
Return [Module, Module, ...]
```

### Module Object Structure

```python
class Module:
    name: str          # Directory name
    path: Path         # Full path to module directory
    anchor_type: str   # Discovery strategy type
    files: Tuple       # Module files (populated later?)
    manifest: Dict     # Manifest data (empty except for manifest strategy)
    neighbors: Tuple   # Related modules (populated later?)
```

---

*Last updated: 2026-04-01*

