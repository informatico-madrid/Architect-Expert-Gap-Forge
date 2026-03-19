# Quickstart: Ingestor CLI Execution

**Date**: 2026-03-19  
**Spec**: [`specs/008-fix-ingestor-cli-execution/spec.md`](specs/008-fix-ingestor-cli-execution/spec.md)  
**Status**: ✅ Production Ready

## 🚀 Quick Start

The AEGF Ingestor can now be executed from **any directory** without requiring `PYTHONPATH` configuration.

### Prerequisites

- Python 3.11+
- Git installed
- (Optional) GitHub token via `GITHUB_TOKEN` environment variable

### Installation

No installation required. The ingestor is part of the AEGF repository:

```bash
cd /mnt/bunker_data/ai/data_factory
```

### Basic Usage

#### Execute from Project Root

```bash
# From the repository root
cd /mnt/bunker_data/ai/data_factory
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
```

#### Execute from Any Directory

```bash
# From any directory (e.g., /tmp, /home, etc.)
cd /tmp
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml

# The script auto-detects the config path relative to project root
```

**Note**: The working directory is automatically changed to the project root when the module is imported, so relative config paths work correctly.

### Configuration

Create a YAML config file in `configs/stage_1_discovery/`:

```yaml
# configs/stage_1_discovery/php_legacy.yaml
category: php_legacy
mode: static
static_repos:
  - owner/repo1
  - owner/repo2
limit: 50
min_stars: 10
```

### Advanced Options

#### Dry Run

Preview actions without cloning:

```bash
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml --dry-run
```

#### Dynamic Discovery

Search GitHub for repositories:

```yaml
# configs/stage_1_discovery/search.yaml
category: python_libs
mode: dynamic
search_query: "language:python stars:>100"
limit: 100
min_stars: 100
```

```bash
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/search.yaml
```

### Profile Filtering

Filter repositories by file extensions:

```yaml
category: python_projects
mode: static
static_repos:
  - owner/project1
  - owner/project2
profile: python
profile_extensions:
  - .py
  - .ipynb
profile_ignored_paths:
  - .git
  - node_modules
```

### GitHub API Integration

Use a GitHub token for higher rate limits:

```bash
export GITHUB_TOKEN=your_token_here
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
```

**Security**: The token is read from the environment variable, never stored in source code.

## 📋 Command Reference

### CLI Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--config` | `-c` | Yes | Path to YAML config file |
| `--dry-run` | | No | Preview actions without executing |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (config parsing, execution failure) |

### Logging

Logs are output in the format:

```
2026-03-19 10:30:45,123 - INFO - Initiating discovery for category: php_legacy
2026-03-19 10:30:46,456 - INFO - Cloning: owner/repo1
```

### Output Directory

Cloned repositories are stored in:

```
data/raw/<category>/<owner>/<repo>/
```

For the example config above:

```
data/raw/php_legacy/owner/repo1/
data/raw/php_legacy/owner/repo2/
```

## ✅ Verification

### Test 1: Execute from Project Root

```bash
cd /mnt/bunker_data/ai/data_factory
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
# Expected: Success, no errors
```

### Test 2: Execute from Different Directory

```bash
cd /tmp
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml
# Expected: Success, no PYTHONPATH required
```

### Test 3: Run Unit Tests

```bash
pytest tests/unit/test_ingestor*.py -v
# Expected: All 21 tests pass
```

## 🎯 Key Features

- ✅ **No PYTHONPATH required** - Works out of the box
- ✅ **Works from any directory** - Auto-detects project root
- ✅ **Backward compatible** - Existing tests continue to work
- ✅ **Developer-friendly** - No setup required
- ✅ **Production-ready** - CI/CD compatible

## 🔧 Troubleshooting

### Issue: `FileNotFoundError: [Errno 2] No such file or directory: 'configs/...'`

**Cause**: The config path is relative to the project root, not the current directory.

**Solution**: The ingestor automatically changes to the project root when imported. If you still see this error, ensure you're using the correct module invocation:

```bash
# ✅ Correct
python3 -m src.discovery.ingestor --config configs/stage_1_discovery/php_legacy.yaml

# ❌ Incorrect (if run from a different directory without module invocation)
python3 src/discovery/ingestor.py --config configs/...
```

### Issue: `ModuleNotFoundError: No module named 'src'`

**Cause**: Python can't find the `src` package.

**Solution**: Use the `-m` flag to invoke as a module:

```bash
python3 -m src.discovery.ingestor --config configs/...
```

### Issue: `PermissionError` when cloning

**Cause**: Insufficient permissions in the output directory.

**Solution**: Ensure the `data/raw` directory is writable:

```bash
chmod -R u+w data/raw/
```

## 📚 Additional Resources

- [Spec: Fix Ingestor CLI Execution](../specs/008-fix-ingestor-cli-execution/spec.md)
- [Implementation Plan](../specs/008-fix-ingestor-cli-execution/plan.md)
- [Research & Technical Decisions](../specs/008-fix-ingestor-cli-execution/research.md)
- [Data Model Documentation](../specs/008-fix-ingestor-cli-execution/data-model.md)

## 🤝 Contributing

To contribute to the AEGF project:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Commit: `git commit -m 'Add your feature'`
6. Push: `git push origin feature/your-feature`
7. Create a Pull Request

---

**Version**: 1.0.0  
**Last Updated**: 2026-03-19  
**Maintainer**: Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
