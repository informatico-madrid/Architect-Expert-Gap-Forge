# Quickstart: PHPLegacyDriver

**Feature**: 004-php-legacy-driver | **Date**: 2026-03-12

## Prerequisites

- Python 3.11+
- Repositorio PHP legacy en `data/raw/multi_legacy/<platform>/`
- Pipeline AEGF configurado (configs existentes)

## Usage

### 1. Register the PHP Legacy Adapter

El adapter se registra automáticamente en `src/utils/extractors/factory.py`:

```python
from src.utils.extractors.factory import get_adapter

adapter = get_adapter("php_legacy")
```

### 2. Run Stage 1 (Discovery) on a PHP Repository

```python
from src.discovery.processor import RepoProcessor, ProcessingConfig

config = ProcessingConfig(
    repo_path="data/raw/multi_legacy/oscommerce",
    profile="php_legacy",
    extensions={".php", ".inc"},
    module_discovery_strategy="directory_scan",
    output_dir="data/outputs/oscommerce_bundles",
)

processor = RepoProcessor(config)
bundles = processor.process()
# → Generates .txt bundles in output_dir
```

### 3. Verify Bundle Output

```bash
# Check generated bundles
ls data/outputs/oscommerce_bundles/*.txt | head -5

# Inspect a bundle
head -40 data/outputs/oscommerce_bundles/admin_categories.txt
# Should show [ARCH_HEADER] with LANGUAGE: php, PLATFORM: oscommerce
# Followed by [MODULE_MAP], [LEGACY_SIGNATURES], fragments
```

### 4. Run Stage 2 (Factory) with PHP Bundles

Stage 2 processes PHP bundles automatically when the Extension Mapper detects `.php` fragments:

```python
from src.factory.production_v11 import ProductionPipeline

pipeline = ProductionPipeline(
    blueprint_dir="data/outputs/oscommerce_bundles",
    taxonomy_path="configs/stage_2_factory/taxonomy/php_legacy/taxonomy.yaml",
    doctrine_path="configs/stage_2_factory/taxonomy/php_legacy/master_symfony_hex.md",
)

results = pipeline.run()
# → Generates training pairs with DEBT_DIAGNOSTIC / MODERN_PROPOSAL / MAPPING_LOGIC
```

### 5. Run Tests

```bash
# Unit tests only
pytest tests/unit/test_php_legacy_adapter.py tests/unit/test_php_fragmenter.py -v

# Integration tests (requires fixtures)
pytest tests/integration/test_php_processor_bundles.py -v

# All PHP-related tests
pytest -k "php" -v

# With coverage
pytest -k "php" --cov=src --cov-report=term-missing
```

## Key Files

| File | Purpose |
|------|---------|
| `src/utils/extractors/php_legacy_adapter.py` | ExtractorAdapter implementation |
| `src/discovery/php_fragmenter.py` | Heuristic block fragmenter |
| `src/discovery/php_signatures.py` | LEGACY_ACTION pattern engine |
| `src/discovery/php_include_graph.py` | Include/require dependency graph |
| `src/discovery/php_platform_profiles.py` | Platform detection |
| `src/factory/production_v11.py` | Stage 2 (modified: Extension Mapper + generic sections) |
| `src/discovery/processor.py` | Stage 1 (modified: directory_scan strategy) |
| `configs/stage_2_factory/taxonomy/php_legacy/` | Prompt templates + doctrine |

## Configuration

ProcessingConfig fields for PHP:

```python
ProcessingConfig(
    profile="php_legacy",                    # Triggers PHP adapter
    extensions={".php", ".inc"},             # PHP file extensions
    module_discovery_strategy="directory_scan",  # No manifest/init needed
    exclude_patterns={"vendor/*", "node_modules/*", "tests/*", "cache/*"},
)
```

## Expected Output

Un bundle PHP contiene:
1. `[ARCH_HEADER]` — con LANGUAGE: php, PLATFORM: <detected>
2. `[MODULE_MAP]` — archivos del módulo
3. `[LEGACY_SIGNATURES]` — anti-patterns detectados
4. `[INCLUDE_GRAPH]` — dependencias include/require
5. Fragmentos delimitados por `--- FRAGMENT: <name> (<type>) ---`
