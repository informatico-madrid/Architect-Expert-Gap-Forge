# Configuration Examples

This document provides complete configuration examples for the AEGF processor, including both explicit and auto-strategy configurations.

## Available Discovery Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| `auto` | Automatically detects repository type | Unknown repos, diverse collections |
| `yaml` | YAML/Jinja template discovery | Themes, templates, blueprints |
| `typescript` | TypeScript/TSX discovery | Frontend React/Web components |
| `filesystem` | PHP filesystem discovery | PHP apps without package manager |
| `manifest` | Home Assistant manifest discovery | Python integrations with manifest.json |
| `init` | Python `__init__.py` discovery | Python packages without manifest |
| `directory` | Generic directory structure | Fallback for unknown structures |
| `manual_mapping` | Explicit override mapping | Special cases requiring custom paths |

## Complete Example Configurations

### Auto-Strategy: Home Assistant YAML Repository

```yaml
# Detects YAML-only repositories automatically
category: yaml_repos
mode: static
static_repos:
  - "basnijholt/lovelace-ios-themes"
  - "catppuccin/home-assistant"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "yaml"
extensions:
  - ".yaml"
  - ".yml"
  - ".jinja"
  - ".j2"
ignore_patterns:
  - ".git"
  - "node_modules"
  - "__pycache__"
  - "tests"
min_stars: 0
limit: 100
```

**Detection Result:** YAML strategy

**Expected Output:**
- Discover themes directory as module
- Discover templates directory as module
- Discover blueprints directory as module

### Auto-Strategy: TypeScript Frontend

```yaml
# Detects TypeScript-only repositories automatically
category: typescript_repos
mode: static
static_repos:
  - "kalkih/mini-graph-card"
  - "custom-cards/button-card"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "typescript"
extensions:
  - ".ts"
  - ".tsx"
  - ".js"
  - ".jsx"
ignore_patterns:
  - ".git"
  - "node_modules"
  - "__pycache__"
  - "tests"
limit: 50
```

**Detection Result:** TypeScript strategy

**Expected Output:**
- Discover src/components directory as module
- Discover src/hooks directory as module
- Discover src/utils directory as module

### Auto-Strategy: PHP Application

```yaml
# Detects PHP filesystem repositories automatically
category: php_repos
mode: static
static_repos:
  - "joBr99/nspanel-lovelace-ui"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "filesystem"
extensions:
  - ".php"
  - ".js"
  - ".css"
ignore_patterns:
  - ".git"
  - "vendor"
  - "node_modules"
  - "tests"
limit: 30
```

**Detection Result:** Filesystem strategy

**Expected Output:**
- Discover Controllers directory as modules
- Discover Services directory as modules
- Discover Models directory as modules

### Auto-Strategy: Python Home Assistant Integration

```yaml
# Detects Python manifest repositories automatically
category: ha_integrations
mode: static
static_repos:
  - "basnijholt/adaptive-lighting"
  - "AlexxIT/SonoffLAN"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "manifest"
extensions:
  - ".py"
  - ".json"
  - ".yaml"
  - ".md"
ignore_patterns:
  - ".git"
  - "__pycache__"
  - "tests"
limit: 200
```

**Detection Result:** Manifest strategy

**Expected Output:**
- Discover custom_components/integration_name as modules
- Extract manifest.json metadata
- Process __init__.py files

### Explicit Strategy: Fixed YAML Discovery

```yaml
# Skip auto-detection, use explicit YAML strategy
category: yaml_explicit
mode: static
static_repos:
  - "basnijholt/lovelace-ios-themes"
profile: explicit
module_discovery_strategy: yaml  # Explicit, no detection overhead
extensions:
  - ".yaml"
  - ".yml"
  - ".jinja"
ignore_patterns:
  - ".git"
  - "node_modules"
  - "tests"
limit: 100
```

**Advantages:**
- Faster processing (no detection phase)
- Predictable results
- Easier debugging

**When to Use:**
- Known repository structure
- Production pipelines
- Performance-critical scenarios

## Mixed Language Repositories

### Python + TypeScript (Python Priority)

```yaml
# When both Python and TypeScript present, Python takes priority
category: mixed_python_ts
mode: static
static_repos:
  - "home-assistant/core"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "manifest"
extensions:
  - ".py"
  - ".ts"
  - ".tsx"
  - ".json"
ignore_patterns:
  - ".git"
  - "__pycache__"
  - "tests"
```

**Behavior:**
- Python modules discovered via manifest/__init__.py
- TypeScript files ignored (lower priority)
- Detection priority: manifest > typescript

### YAML + TypeScript (YAML Priority)

```yaml
# When YAML and TypeScript present, YAML takes priority
category: mixed_yaml_ts
mode: static
static_repos:
  - "some_repo_with_templates_and_components"
profile: auto
module_discovery_strategy: auto  # Auto-detected as "yaml"
extensions:
  - ".yaml"
  - ".yml"
  - ".jinja"
  - ".ts"
  - ".tsx"
```

**Behavior:**
- YAML templates discovered via YAML strategy
- TypeScript files ignored (lower priority)
- Detection priority: yaml > typescript

## Error Handling Configuration

All auto-strategy configurations include built-in error handling:

```yaml
# Graceful handling of:
# - Permission errors (logged, continues scanning)
# - Broken symlinks (silently skipped)
# - Empty repositories (returns directory fallback)
# - Detection exceptions (returns directory fallback)

profile: auto
module_discovery_strategy: auto
```

## Performance Considerations

### Auto Strategy Overhead
- Detection time: 50-200ms per repository
- For 100 repositories: ~10-20 seconds total overhead
- Memory usage: O(directory depth)
- I/O: Read-only file existence checks

### When to Use Explicit Strategy
- Processing 1000+ known repositories
- CI/CD pipelines with fixed configurations
- Debugging and testing scenarios

## Configuration Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | string | Yes | Output subdirectory name |
| `mode` | string | Yes | `static` or `dynamic` |
| `static_repos` | list | Yes (static mode) | List of `owner/repo` strings |
| `module_discovery_strategy` | string | No | Default: `auto` |
| `extensions` | list | No | File extensions to include |
| `ignore_patterns` | list | No | Directory patterns to exclude |
| `limit` | int | No | Maximum repositories to process |
| `min_stars` | int | No | Minimum stars filter |
| `raw_subdir` | path | No | Input directory under base_dir |
| `output_subdir` | path | No | Output directory for bundles |

## Best Practices

1. **Use auto for initial discovery**: Let auto-detection identify repository types
2. **Switch to explicit for production**: Document and pin strategies for reproducibility
3. **Monitor detection performance**: Use DEBUG logging to verify detection time
4. **Handle edge cases explicitly**: Use explicit strategy for unusual repository structures
5. **Document strategy decisions**: Include comments explaining why auto vs explicit was chosen

See [Auto-Detection Feature Guide](./auto-detection.md) for more details on the auto-detection algorithm and performance characteristics.
