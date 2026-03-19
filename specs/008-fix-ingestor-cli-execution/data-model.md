# Data Model: Ingestor CLI Execution Fix

**Date**: 2026-03-19  
**Spec**: [`specs/008-fix-ingestor-cli-execution/spec.md`](specs/008-fix-ingestor-cli-execution/spec.md)  
**Status**: ✅ Complete - No new data models required

## Executive Summary

This feature does **not introduce new data models**. The changes are purely implementation-focused:
- Auto-detection of project root path
- Working directory management
- Module entry point creation

All existing data structures remain unchanged.

---

## Existing Data Models (No Changes)

### DiscoveryConfig

**Location**: `src/discovery/ingestor.py`

**Purpose**: Configuration schema for repository discovery and ingestion.

**Fields**:
```python
class DiscoveryConfig(BaseModel):
    category: str                    # Target subdirectory name
    mode: Literal["dynamic", "static"]  # Discovery mode
    profile: Optional[str]           # Profile name for filtering
    profile_extensions: Optional[Set[str]]  # File extensions to filter
    profile_ignored_paths: Optional[Set[str]]  # Paths to ignore
    search_query: Optional[str]      # GitHub search query
    min_stars: int                   # Minimum stars filter
    limit: int                       # Max repos to fetch
    per_page: int                    # GitHub API page size
    static_repos: List[str]          # List of repos to fetch
    base_dir: Path                   # Base directory (auto-detected)
    raw_subdir: str                  # Raw data subdirectory
    github_token: Optional[str]      # GitHub API token (env var)
```

**Validation**:
- `mode == "static"` requires non-empty `static_repos`
- `mode == "dynamic"` requires non-empty `search_query`
- `limit >= 1`
- `per_page` in range [1, 100]

**Status**: ✅ No changes required

---

### RepoIngestor

**Location**: `src/discovery/ingestor.py`

**Purpose**: Engine for discovering and cloning repositories.

**State**:
```python
class RepoIngestor:
    cfg: DiscoveryConfig               # Configuration
    raw_path: Path                     # Output directory for repos
    session: requests.Session          # HTTP client
    _rate_limit_retries: dict[str, int]  # Retry tracking
    _metrics: MetricsCollector         # Metrics tracking
```

**Methods**:
- `discover() -> List[str]` - Discover repositories
- `fetch(repos: List[str], dry_run: bool) -> None` - Clone/update repos
- `_github_search() -> List[str]` - GitHub API search
- `_should_include_repo(repo_id: str) -> bool` - Profile filtering
- `_has_matching_extensions(repo_path: Path) -> bool` - Extension check
- `_filter_repos(repos: List[str]) -> List[str]` - Apply filters
- `_clone_repo(repo_id: str, target: Path) -> None` - Git clone
- `_update_repo(repo_id: str, target: Path) -> None` - Git update
- `_handle_backoff(resp: Response) -> None` - Rate limit handling

**Status**: ✅ No changes required (only `os.chdir()` added at module level)

---

## New Constants (Not Data Models)

### PROJECT_ROOT

**Location**: `src/discovery/ingestor.py` (module level)

**Type**: `Path`

**Value**: `Path(__file__).resolve().parent.parent.parent`

**Purpose**: Auto-detected project root path

**Usage**:
- Sets working directory via `os.chdir(PROJECT_ROOT)`
- Can be referenced for absolute paths if needed

**Status**: ✅ New constant (not a data model)

---

## Interface Contracts

### CLI Interface (Unchanged)

**Invocation**:
```bash
python3 -m src.discovery.ingestor --config <path> [--dry-run]
```

**Arguments**:
- `--config, -c` (required): Path to YAML config file
- `--dry-run` (optional): Print actions without executing

**Exit Codes**:
- `0`: Success
- `1`: Error (config parsing, execution failure)

**Status**: ✅ No changes to CLI interface

---

### Module Interface (New)

**Invocation**:
```bash
python3 -m src.discovery.ingestor
```

**Entry Point**: `src/discovery/__main__.py`

**Behavior**:
- Imports `main()` from `src.discovery.ingestor`
- Executes `main()` with CLI argument parsing
- Same behavior as direct execution

**Status**: ✅ New entry point (no API changes)

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Execution Context                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Module Import (src/discovery.ingestor)                  │
│     - PROJECT_ROOT detected                                 │
│     - os.chdir(PROJECT_ROOT)                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. CLI Argument Parsing                                    │
│     - Parse --config, --dry-run                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Config Loading                                          │
│     - Read YAML config                                      │
│     - Validate with Pydantic                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Discovery & Fetch                                       │
│     - Discover repos (GitHub API or static list)            │
│     - Clone/update repositories                             │
└─────────────────────────────────────────────────────────────┘
```

**Status**: ✅ No changes to data flow

---

## Backward Compatibility

### Existing Tests

**Status**: ✅ All existing tests continue to work

**Reason**:
- `os.chdir()` is called at module import time
- Tests import the module, so `chdir()` is executed
- Tests can still access files via relative paths from repo root

**Verification**:
```bash
pytest tests/unit/test_ingestor*.py -v
# All tests should pass
```

### Existing Documentation

**Status**: ⚠️ Requires update

**Changes Needed**:
- Remove PYTHONPATH references from README
- Update execution examples to show `python3 -m` syntax
- Add note about "works from any directory"

---

## Migration Guide

### For Developers

**Before**:
```bash
# Required PYTHONPATH
export PYTHONPATH=/path/to/repo
cd /some/other/dir
python3 -m src.discovery.ingestor --config configs/...
```

**After**:
```bash
# No PYTHONPATH needed
cd /some/other/dir
python3 -m src.discovery.ingestor --config configs/...
# Works!
```

### For CI/CD

**Before**:
```yaml
- name: Run Ingestor
  run: |
    export PYTHONPATH=$(pwd)
    python3 -m src.discovery.ingestor --config configs/...
```

**After**:
```yaml
- name: Run Ingestor
  run: |
    python3 -m src.discovery.ingestor --config configs/...
```

---

## Summary

| Item | Status | Notes |
|------|--------|-------|
| New Data Models | ❌ None | No new data structures |
| Modified Data Models | ❌ None | Existing models unchanged |
| New Constants | ✅ PROJECT_ROOT | Path resolution constant |
| New Entry Points | ✅ `__main__.py` | Module execution |
| API Changes | ❌ None | CLI interface unchanged |
| Breaking Changes | ❌ None | Fully backward compatible |

**Conclusion**: This is a **non-breaking, implementation-only** change that improves developer experience without modifying data models or public APIs.
