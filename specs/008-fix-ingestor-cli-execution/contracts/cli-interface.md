# Contract: CLI Interface

**Date**: 2026-03-19  
**Spec**: [`specs/008-fix-ingestor-cli-execution/spec.md`](specs/008-fix-ingestor-cli-execution/spec.md)  
**Type**: Command Line Interface

## Overview

This document defines the contract for the AEGF Ingestor CLI. The interface is stable and backward compatible.

## Invocation

### Module Execution (Recommended)

```bash
python3 -m src.discovery.ingestor [OPTIONS]
```

**Requirements**:
- Must be run from **project root directory** (not from external directories like `/tmp`)
- No PYTHONPATH configuration required
- Works with Python 3.11+

### Direct Execution (Legacy)

```bash
python3 src/discovery/ingestor.py [OPTIONS]
```

**Requirements**:
- Must be run from project root
- Config path relative to project root

## Arguments

### `--config, -c`

**Type**: String (file path)  
**Required**: Yes  
**Description**: Path to YAML configuration file

**Examples**:
```bash
--config configs/stage_1_discovery/php_legacy.yaml
-c configs/stage_1_discovery/php_legacy.yaml
```

**Validation**:
- File must exist
- File must be valid YAML
- File must contain valid DiscoveryConfig schema

### `--dry-run`

**Type**: Boolean flag  
**Required**: No  
**Default**: False  
**Description**: Preview actions without executing

**Behavior**:
- Prints discovery results
- Prints clone/update commands
- Does not clone repositories

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (config parsing, execution failure) |

## Exit Code Details

### Success (0)

**Conditions**:
- Config parsed successfully
- Discovery completed
- All repositories cloned/updated successfully

**Output**:
```
2026-03-19 10:30:45,123 - INFO - Initiating discovery for category: php_legacy
2026-03-19 10:30:46,456 - INFO - Cloning: owner/repo1
2026-03-19 10:30:47,789 - INFO - Successfully updated owner/repo2
```

### Error (1)

**Conditions**:
- Config file not found
- Invalid YAML syntax
- Invalid config schema
- GitHub API error
- Git clone failure

**Output**:
```
2026-03-19 10:30:45,123 - ERROR - Config file not found: configs/invalid.yaml
```

## Configuration Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Target subdirectory name |
| `mode` | string | Discovery mode: "dynamic" or "static" |

### Conditional Fields

**Static Mode**:
- `static_repos`: List of repository identifiers (e.g., "owner/repo")

**Dynamic Mode**:
- `search_query`: GitHub search query string

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `profile` | string | null | Profile name for filtering |
| `profile_extensions` | list | null | File extensions to filter |
| `profile_ignored_paths` | list | null | Paths to ignore |
| `min_stars` | int | 0 | Minimum stars filter |
| `limit` | int | 50 | Max repos to fetch |
| `per_page` | int | 100 | GitHub API page size |

## Logging

### Log Format

```
{timestamp} - {level} - {message}
```

**Example**:
```
2026-03-19 10:30:45,123 - INFO - Initiating discovery for category: php_legacy
```

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| INFO | General operation information |
| WARNING | Non-critical issues |
| ERROR | Errors that prevent completion |

## Rate Limiting

### GitHub API Limits

- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5000 requests/hour

### Retry Policy

- Maximum 2 retries per endpoint
- Exponential backoff on rate limit hit
- Automatic sleep until rate limit reset

### Error Handling

```
2026-03-19 10:30:45,123 - WARNING - Rate limit hit. Sleeping 120s.
```

## Security

### GitHub Token

**Storage**: Environment variable only

**Variable**: `GITHUB_TOKEN`

**Never stored in**:
- Source code
- Configuration files
- Logs

**Usage**:
```bash
export GITHUB_TOKEN=your_token_here
python3 -m src.discovery.ingestor --config configs/...
```

## Performance

### Expected Metrics

| Metric | Value |
|--------|-------|
| Config parsing | <10ms |
| Discovery (static) | <100ms |
| Discovery (dynamic) | <5s per page |
| Clone (single repo) | <10s |
| Update (single repo) | <5s |

### Memory Usage

- Base: ~50MB
- Per repository: ~5MB
- GitHub API session: ~10MB

## Backward Compatibility

### Breaking Changes

**None**. All existing functionality is preserved.

### Deprecated Features

**None**. No features are being deprecated.

### Migration Guide

**From**: `export PYTHONPATH=/path/to/repo`  
**To**: No configuration needed

**Before**:
```bash
export PYTHONPATH=/path/to/repo
cd /some/dir
python3 -m src.discovery.ingestor --config configs/...
```

**After**:
```bash
cd /some/dir
python3 -m src.discovery.ingestor --config configs/...
# Works automatically!
```

## Testing

### Unit Tests

```bash
pytest tests/unit/test_ingestor*.py -v
```

**Expected**: All 21 tests pass

### Integration Tests

```bash
# Test from project root
cd /mnt/bunker_data/ai/data_factory
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml --dry-run

# Test from different directory
cd /tmp
python3 -m src.discovery.ingestor --config /mnt/bunker_data/ai/data_factory/configs/stage_1_discovery/php_legacy.yaml --dry-run
```

## Support

For issues or questions:

1. Check [troubleshooting section](../specs/008-fix-ingestor-cli-execution/quickstart.md#-troubleshooting)
2. Review [specification](../specs/008-fix-ingestor-cli-execution/spec.md)
3. Contact: joao@informatico-madrid.com

---

**Version**: 1.0.0  
**Last Updated**: 2026-03-19  
**Status**: ✅ Production Ready
