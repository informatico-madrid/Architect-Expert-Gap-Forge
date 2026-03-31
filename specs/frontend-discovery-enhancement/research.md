# Research: Fragment Types and Language-Agnostic Architecture

## Executive Summary

The data factory uses a **language-agnostic adapter protocol** where adapters parse files and extract dependencies, while the **discovery strategy** determines which files get processed. Fragment types (1-5) are generated based on file analysis and test pairing, NOT by adapter. **Type 2 (FUNCTIONAL_UNIT_WITH_CONTEXT) is not currently generated** - it was removed or never implemented. The **discovery strategy priority is for architecture detection only**, not file filtering - if adapters exist for file types, those files should be processed regardless of repository architecture.

---

## Fragment Types Analysis

### Type 1: FUNCTIONAL_UNIT (CODE + TEST)

**Location:** [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py#L382-L392)

**Generation:**
```python
def _emit_module(self, module: Module) -> Iterator[Bundle]:
    # First emit MODULE_BLUEPRINT (Type 4)
    yield self._build_blueprint(module)
    
    # Then process logic files
    for logic_file in module.files:
        if logic_file.is_implementation:
            # Find matching test
            test_file = self._find_matching_test(module, logic_file)
            
            if test_file:
                # Type 1: Code + Test
                yield self._build_functional_unit(module, logic_file, test_file)
```

**Content:** Logic file + matching test file paired together. Used for Python, TypeScript, YAML - any language with test files.

---

### Type 2: FUNCTIONAL_UNIT_WITH_CONTEXT (MISSING)

**Status:** **NOT IMPLEMENTED** - This type does not exist in the current codebase.

**Expected Content (based on naming):** Would be Type 1 + README/context files.

**Current State:** The code only generates:
- Type 1: Code + Test (no context)
- Type 3: Code only (no test)
- Type 4: Blueprint (architecture context)
- Type 5: Governance rules

**Research Question:** Where was Type 2 defined or was it never implemented?

---

### Type 3: LOGIC_ONLY (CODE WITHOUT TEST)

**Location:** [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py#L400-L415)

**Generation:**
```python
if not test_file and len(content) >= MIN_SIZE:
    # Type 3: Standalone logic without test
    yield self._build_logic_only(module, logic_file)
```

**Content:** Files without matching tests that pass size gate (≥800 chars). AST-chunked for Python, whole-file for PHP.

**Example:** HomeAssistant frontend `.ts`/`.tsx` files without corresponding `.test.ts` files.

---

### Type 4: MODULE_BLUEPRINT (ARCHITECTURE CONTEXT)

**Location:** [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py#L382-L392)

**Generation:**
```python
yield self._build_blueprint(module)  # Called for every module
```

**Content:** Architecture index aggregating anchor files:
- `manifest.json` (domain, name, version, dependencies)
- `const.py` (constants, domains)
- `services.yaml` (service definitions)
- `README.md` (documentation)
- Other configuration files

**Purpose:** Provides architecture context for training in later stages. Each module gets exactly one blueprint.

---

### Type 5: GOVERNANCE_RULES (CODING STANDARDS)

**Location:** [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py#L382-L392)

**Generation:**
```python
governance_files = self._discover_governance(repo_path)
for file in governance_files:
    yield self._build_governance(file)
```

**Content:** Development rules from:
- `CLAUDE.md`
- `AGENTS.md`
- `.cursorrules`
- Other coding standard files

**Purpose:** Captures repository-level coding conventions and development guidelines.

---

## Discovery Strategy Priority System

### What It Is

The discovery strategy determines **which files get discovered and processed**. Each strategy has an associated `extensions` set that filters which files are included.

**Location:** [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py#L284-L340)

### Auto-Detection Priority

```python
def _detect_discovery_strategy(self, repo_path: Path) -> str:
    has_manifest = any(repo_path.rglob("manifest.json"))
    has_init_py = any(repo_path.rglob("__init__.py"))
    has_ts_files = list(repo_path.rglob("*.ts")) + list(repo_path.rglob("*.tsx"))
    has_yaml_files = list(repo_path.rglob("*.yaml")) + list(repo_path.rglob("*.yml")) + \
                     list(repo_path.rglob("*.jinja")) + list(repo_path.rglob("*.jinja2"))
    has_php_files = any(repo_path.rglob("*.php"))
    has_composer_json = any(repo_path.rglob("composer.json"))
    
    if has_manifest:
        return "manifest"
    elif has_init_py:
        return "init"
    elif len(has_ts_files) > 50:
        return "typescript"
    elif len(has_yaml_files) > 5:
        return "yaml"
    elif has_php_files or has_composer_json:
        return "filesystem"
    else:
        return "directory"
```

### Strategies and Their Extensions

| Strategy | Extensions | Purpose |
|----------|-----------|---------|
| `manifest` | `{".py", ".md", ".json", ".yaml", ".yml"}` | HA integrations with manifest.json |
| `init` | `{".py", ".md", ".json", ".yaml", ".yml"}` | Python packages with __init__.py |
| `directory` | `{".py", ".md", ".json", ".yaml", ".yml"}` | Generic Python directory scanning |
| `typescript` | `{".ts", ".tsx", ".json"}` | TypeScript/React components |
| `yaml` | `{".yaml", ".yml", ".jinja", ".jinja2"}` | HomeAssistant blueprints/templates |
| `filesystem` | `{".php", ".inc"}` | PHP legacy repositories |

---

## Adapter Selection and File Processing

### The Adapter Protocol

**Location:** [`src/utils/extractors/base.py`](src/utils/extractors/base.py#L29-L64)

All adapters implement the `ExtractorAdapter` protocol:

```python
@runtime_checkable
class ExtractorAdapter(Protocol):
    def parse_file(self, file_path: Path) -> ParseResult
    def extract_dependencies(self, file_path: Path) -> List[Dependency]
```

### Adapter Registry

**Location:** [`src/utils/extractors/factory.py`](src/utils/extractors/factory.py#L45-L112)

| Adapter | File Types | Purpose |
|---------|-----------|---------|
| `PythonAstAdapter` | `.py` | Python AST dependency extraction |
| `TypeScriptAdapter` | `.ts`, `.tsx`, `.json` | TypeScript/React component extraction |
| `YamlAdapter` | `.yaml`, `.yml`, `.jinja` | YAML/Blueprint pattern extraction |
| `JinjaAdapter` | `.jinja` | Jinja template variable extraction |
| `PhpLegacyAdapter` | `.php`, `.inc` | PHP legacy extraction pipeline |

### Processing Pipeline

```
1. Discovery Strategy → Selects extensions set
2. File Scanner → Finds files matching extensions
3. Adapter → Parses each file and extracts dependencies
4. Fragment Builder → Creates fragments based on file analysis
```

**Key Insight:** The discovery strategy determines **which files are discovered**, but the adapter determines **how each file is parsed**.

---

## Critical Finding: Discovery Strategy vs Adapter Selection

### The Problem

The discovery strategy determines which files get processed. If a repository is detected as "manifest" (Python HA integration), only Python files are discovered. TypeScript and YAML files in the same repository are **never discovered** because they're not in the `extensions` set for the manifest strategy.

### The User's Insight (CORRECT)

> "If a repository is primarily Python but has some JS for a reason, if we have an adapter for it we should also add its fragment."

**This is correct.** The discovery strategy should be for **architecture detection only** (to find the right blueprint), not for filtering which files get processed.

### Current Behavior

```
Repository: homeassistant/frontend (Python + TypeScript + YAML)
Discovery: manifest → extensions = {".py", ".md", ".json", ".yaml", ".yml"}
Result: TypeScript files (.ts, .tsx) are NEVER discovered
```

### Desired Behavior

```
Repository: homeassistant/frontend (Python + TypeScript + YAML)
Discovery: manifest → architecture context
Processing: ALL file types → adapters process each type
Result: Python files → PythonAstAdapter, TypeScript files → TypeScriptAdapter
```

---

## Answers to User Questions

### Q1: Where is Type 2?

**A:** Type 2 (FUNCTIONAL_UNIT_WITH_CONTEXT) is **not implemented**. The code only generates:
- Type 1: Code + Test
- Type 3: Code only (no test)
- Type 4: Blueprint
- Type 5: Governance

Type 2 may have been planned but never implemented, or removed during refactoring.

### Q2: What is the priority system for?

**A:** The priority system is for **discovery strategy selection**, not for filtering files. It determines:
1. Which files get discovered (based on extensions)
2. Which architecture/blueprint to use

**It should NOT be used to exclude files that have adapters.**

### Q3: How do adapters work with language-agnostic processing?

**A:** Adapters are selected by **file extension**, not by repository type:

```python
ext_mapping = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".yaml": "yaml",
    ".jinja": "jinja",
}
```

**Problem:** The discovery strategy's `extensions` set filters files BEFORE adapter selection. So TypeScript files in a Python repository are never discovered.

### Q4: Is priority only for architecture detection?

**A:** **YES.** The priority should be for:
1. Detecting the right architecture/blueprint
2. Finding anchor files (manifest.json, const.py, etc.)

It should NOT be used to exclude files that have adapters.

### Q5: Should we process files with adapters regardless of repository type?

**A:** **YES.** If adapters exist for file types, those files should be processed regardless of repository architecture.

**Example:** A Python repository with some TypeScript files should:
1. Use "manifest" strategy for architecture context
2. Process Python files with PythonAstAdapter
3. Process TypeScript files with TypeScriptAdapter

---

## Recommendations

### 1. Change Discovery Strategy to Process All Files

Instead of having separate strategies that filter by extensions, use a **single "all" strategy** that discovers all file types:

```python
class AllDiscoveryStrategy:
    extensions = {".py", ".ts", ".tsx", ".json", ".yaml", ".yml", ".jinja", ".jinja2", ".php", ".inc"}
```

### 2. Keep Discovery Strategy for Architecture Detection Only

The discovery strategy should only determine:
1. Which architecture/blueprint to use
2. Which anchor files to collect

Not which files get processed.

### 3. Adapter Selection by File Extension

Maintain the current adapter registry where each file extension maps to the appropriate adapter.

### 4. Implement Type 2 (Optional)

If Type 2 is needed, it would generate:
```
Type 2: Code + Test + README
```

This would provide full context for each functional unit including documentation.

---

## Open Questions

1. Was Type 2 ever implemented and removed, or was it never implemented?
2. Should the discovery strategy be replaced with separate "architecture detection" and "file processing" concerns?
3. Should TypeScript files in Python repositories be processed automatically, or requires explicit configuration?

---

## Files

| File | Purpose |
|------|---------|
| [`src/discovery/metadata_enricher.py`](src/discovery/metadata_enricher.py) | ProcessingConfig, discovery strategy, fragment generation |
| [`src/discovery/file_scanner.py`](src/discovery/file_scanner.py) | Strategy implementations |
| [`src/utils/extractors/factory.py`](src/utils/extractors/factory.py) | Adapter registry |
| [`src/utils/extractors/base.py`](src/utils/extractors/base.py) | ExtractorAdapter protocol |
| [`src/factory/fragment_extractor.py`](src/factory/fragment_extractor.py) | Bundle parsing, fragment types |
