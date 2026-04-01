# Auto-Detection Feature Guide

## Overview

The **auto-detection** strategy automatically determines the appropriate module discovery approach based on repository structure and file patterns. This eliminates the need for manual strategy configuration when processing repositories with unknown or mixed content.

## Detection Priority Order

The auto-detection algorithm evaluates repository patterns in strict priority order:

1. **YAML Strategy** (Priority 1)
   - Matches: `.yaml`, `.yml`, `.jinja`, `.jinja2` files
   - Use case: Home Assistant themes, templates, automations, blueprints
   - Excludes: `node_modules/`, `tests/`, `test/`, `__pycache__/`

2. **TypeScript Strategy** (Priority 2)
   - Matches: `.ts`, `.tsx` files
   - Use case: Frontend React/Web components
   - Excludes: `node_modules/`, `tests/`, `test/`

3. **Filesystem Strategy** (Priority 3)
   - Matches: `.php` files
   - Use case: PHP-based applications without package managers
   - Excludes: `vendor/`, `node_modules/`, `tests/`, `cache/`

4. **Manifest Strategy** (Priority 4)
   - Matches: `manifest.json` files
   - Use case: Home Assistant integrations, npm/Composer projects
   - Higher priority than TypeScript for mixed repos

5. **Init Strategy** (Priority 5)
   - Matches: `__init__.py` files
   - Use case: Python packages without manifest

6. **Directory Strategy** (Priority 6 - Fallback)
   - Use case: Generic directory structure analysis
   - Applied when no specific patterns detected

## When to Use Auto vs Manual

### Use Auto-Discovery When

| Scenario | Benefits |
|----------|----------|
| Processing diverse repository collections | No manual configuration required |
| Unknown repository types | Automatically adapts to detected patterns |
| Mixed-language repositories | Correctly prioritizes Python over TypeScript |
| Rapid prototyping | Minimizes configuration overhead |
| Home Assistant integrations | Handles themes, templates, blueprints automatically |
| Frontend components | Detects TypeScript/React structures |

### Use Manual Strategy When

| Scenario | Recommendation |
|----------|----------------|
| Consistent repository type | Use explicit strategy for clarity |
| Performance-critical processing | Manual strategy skips detection overhead |
| Repository with unusual structure | Manual override may be needed |
| Debugging discovery issues | Explicit strategy simplifies troubleshooting |
| Production pipelines with known repos | Documented strategy improves reproducibility |

## Examples

### YAML-Only Repository

```
my-repo/
  themes/
    dark.yaml
    light.yaml
  templates/
    automation.jinja
  blueprints/
    automation.yaml
```

**Detection Result:** `yaml` strategy

```python
config = ProcessingConfig(
    module_discovery_strategy="auto"
)
# Auto-detected as "yaml"
```

### TypeScript Frontend

```
my-repo/
  src/
    components/
      Button.tsx
      Card.tsx
    hooks/
      useToggle.ts
  tests/
    components/
      Button.test.tsx
```

**Detection Result:** `typescript` strategy

```python
config = ProcessingConfig(
    module_discovery_strategy="auto"
)
# Auto-detected as "typescript"
```

### PHP Application

```
my-repo/
  src/
    Controllers/
      HomeController.php
    Services/
      UserService.php
  vendor/
    package/
      package.php  # Excluded from discovery
```

**Detection Result:** `filesystem` strategy

```python
config = ProcessingConfig(
    module_discovery_strategy="auto"
)
# Auto-detected as "filesystem"
```

### Mixed Python/TypeScript

```
my-repo/
  custom_components/
    my_integration/
      manifest.json  # Python takes priority
      __init__.py
  src/
    frontend/
      button.ts  # Ignored when Python detected
```

**Detection Result:** `manifest` strategy (Python prioritized)

```python
config = ProcessingConfig(
    module_discovery_strategy="auto"
)
# Auto-detected as "manifest" - TypeScript files ignored
```

## Performance Characteristics

### Complexity Analysis

| Metric | Value |
|--------|-------|
| Time Complexity | O(n) single-pass scan |
| Expected Time | < 1 second for 10,000 files |
| Memory Usage | O(d) where d = directory depth |
| File Access | Read-only, existence checks only |

### Performance Optimization Techniques

1. **Early Exit Detection**
   - Returns immediately upon finding highest-priority pattern
   - Avoids scanning entire repository when YAML detected first

2. **Pattern-Specific Traversal**
   - Uses `Path.rglob()` with specific patterns where possible
   - Minimizes unnecessary file operations

3. **Exclusion at Path Level**
   - Checks directory parts before processing
   - Avoids scanning excluded directories

4. **Count-Based Detection**
   - Counts matches for YAML/TS/PHP patterns
   - Only processes files that match exclusion criteria

### Benchmark Results

```
Repository: 10,000 files across 500 directories
Detection Time: ~450ms
Memory Peak: ~12 MB
```

## Error Handling

The auto-detection implementation provides robust error handling:

| Error Type | Handling |
|------------|----------|
| Permission Denied | Logged as WARNING, continues scanning |
| Broken Symlinks | Silently skipped via `is_file()` check |
| Empty Repositories | Returns `directory` fallback |
| Detection Exceptions | Returns `directory` fallback with WARNING |

### Never Raises Exceptions

The `_detect_strategy()` function is guaranteed to return a valid strategy name:
```python
try:
    # Detection logic
    if condition:
        return "yaml"
    if condition:
        return "typescript"
    ...
except Exception:
    logger.warning("Detection failed, using directory fallback")
    return "directory"  # Always returns valid strategy
```

## Configuration Examples

See [Configuration Examples](./config-examples.md) for complete YAML configuration with auto-strategy examples.

## Logging

Auto-detection produces the following log messages:

| Level | Message | Example |
|-------|---------|---------|
| INFO | Auto-detected strategy | `Auto-detected strategy: yaml for /repo` |
| DEBUG | Detection counts | `Detection counts: YAML=5, TS=0, PHP=0, manifest=0, init=0 -> yaml` |
| WARNING | Permission errors | `Permission denied accessing directory: ...` |
| WARNING | Detection failures | `Detection failed, using directory fallback` |

Enable DEBUG logging for detailed detection diagnostics:

```yaml
logging:
  level: DEBUG
```
