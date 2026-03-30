# Architect-Expert-Gap-Forge (AEGF) 🛠️🧠

**Bridging the LLM Knowledge Gap via Synthetic Data Synthesis & Specialized SFT.**

## 📌 Project Overview

AEGF is a high-performance pipeline designed to solve the **Knowledge Cutoff problem** in Large Language Models. While frontier models are excellent generalists, they often hallucinate or fail when dealing with rapidly evolving APIs, legacy-to-modern migrations, or domain-specific architectures (e.g., Home Assistant 2026 standards).

This project provides the infrastructure to:
1. **Extract "Gold Code"** from high-star production repositories.
2. **Inject "API Deltas"**: Real-time context from Changelogs and Breaking Changes.
3. **Synthesize "Platinum-Tier" Trajectories**: Generating `<think>` and `<tool_call>` datasets via a hybrid gold‑injection scheme (GI vs GS) that balances fidelity with corrective learning.
4. **MoE-Aware Fine-Tuning**: Specialized SFT protocols for Mixture-of-Experts architectures on NVIDIA Blackwell (sm_120).

---

## 🏗️ The Sovereign Data Factory: Architecture

AEGF is structured as a modular, **6-stage industrial pipeline**. The core engine is agnostic and driven by external configuration, although the current repository ships with Home Assistant–centric examples and master documents.  
> TODO: when repurposing the factory for other domains, replace or remove HA-specific references.

### Stage 1 — Discovery (`src/discovery/`)
**Engine:** `ingestor.py`

Purpose: Curated repository ingestion that builds the "Raw Gold" source corpus used by later synthesis stages. The engine is fully **domain-agnostic** — behaviour is driven exclusively by external YAML configuration files (`configs/*.yaml`).

#### Profile System (Language-Agnostic)

The Stage 1 engine uses a **Profile-based architecture** to support multiple languages and use cases:

| Profile | Language | Use Case | Extractor Adapter |
|---------|----------|----------|-------------------|
| `homeassistant` | Python | Home Assistant integrations | `PythonASTAdapter` |
| `php_hexagonal` | PHP | Legacy PHP → Hexagonal architecture | `PHPExtractorAdapter` |

**Profile Configuration** (FR-001):
```yaml
profile: homeassistant           # Profile identifier
profile_extensions: ['.py', '.ts', '.tsx']  # Python + TypeScript/TSX for frontend
profile_ignored_paths:          # Paths to ignore
  - vendor
  - node_modules
  - __pycache__
```

#### Modes (set via `mode:` in the YAML config)

- **`static` (Primary / Recommended):** Clones a hand-picked list of vetted repositories defined under `static_repos` in the config. No GitHub token required.
- **`dynamic` (Experimental):** Queries the GitHub API to discover repositories. Automatically selects the `search/repositories` or `search/code` endpoint depending on the query syntax:
  - Queries containing `filename:` or `in:file` → **Code Search** (`search/code`)
  - All other queries → **Repository Search** (`search/repositories`), sorted by stars descending

#### YAML Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `category` | str | *(required)* | Output subdirectory name under `raw_subdir` |
| `mode` | `static` \| `dynamic` | `static` | Ingestion mode |
| `static_repos` | list[str] | `[]` | `owner/repo` entries to clone (required in static mode) |
| `search_query` | str | `null` | GitHub search query (required in dynamic mode) |
| `min_stars` | int | `0` | Minimum stars filter appended to repo queries (`stars:>=N`) |
| `limit` | int | `50` | Maximum number of repositories to process |
| `per_page` | int | `100` | Results per GitHub API page (1–100) |
| `base_dir` | path | `cwd()` | Root directory of the project |
| `raw_subdir` | str | `data/raw` | Subdirectory under `base_dir` for cloned repos |
| `profile_extensions` | list[str] | `null` | File extensions to include (e.g., `['.py']`) |
| `profile_ignored_paths` | list[str] | `null` | Paths to ignore during processing |

#### Output Structure

Repositories are cloned to:
```
{base_dir}/{raw_subdir}/{category}/{owner}/{name}/
```
Example: `data/raw/homeassistant/hacs/integration/`  
> TODO: swap this sample path for your own domain; the HA example is included for historical reasons.

#### GitHub Token (optional but recommended for dynamic mode)

The engine reads the token from the environment — **never put it in the YAML**:
```bash
export GITHUB_TOKEN=ghp_yourtoken
```
Without a token, the GitHub API is limited to 60 requests/hour. The engine handles rate-limit backoff automatically (`X-RateLimit-Reset` header).

#### Dynamic Search Query Examples

```
# Repository search (high-authority integrations):
topic:home-assistant stars:>1000

# Repository search (bleeding edge):
pushed:>2026-01-01 language:python topic:home-assistant

# Code search (detects filename:, switches to search/code endpoint):
"domain" filename:manifest.json path:custom_components
```

#### CLI Reference

```
python3 -m src.discovery.ingestor --config <path> [--dry-run]
```

| Argument | Description |
|----------|-------------|
| `--config`, `-c` | *(required)* Path to the YAML config file |
| `--dry-run` | Discover repos and log what would be cloned — no git operations performed |

> **Note:** `limit` and all other parameters are controlled via the YAML config, not the CLI.

#### Execution (quick)

1. Create or edit a config: `configs/stage_1_discovery/<your_domain>.yaml`
2. Run (static mode, no token needed):
```bash
python3 -m src.discovery.ingestor --config configs/homeassistant.yaml
```
3. Preview without cloning (dry-run):
```bash
python3 -m src.discovery.ingestor --config configs/homeassistant.yaml --dry-run
```
4. With GitHub token for dynamic mode:
```bash
GITHUB_TOKEN=ghp_xxx python3 -m src.discovery.ingestor --config configs/homeassistant.yaml
```

**Note:** Static/manual ingestion is preferred to avoid low-signal bulk crawling and reduce architectural hallucinations at the source.

### Stage 1.5 — Processing & Repackaging (`src/discovery/`)
**Engine:** `processor_cli.py` (Module-aware V2)

> **Nota:** Tras la refactorización de spec 003, `processor.py` fue dividido en submódulos de responsabilidad única. El CLI principal es `processor_cli.py`.

Purpose: Transform raw repository clones into per-module, typed `.txt` bundles (Logical Entities) that preserve architectural context for SFT.

💎 Key Features (V2):
- **Module-aware output:** Modules are discovered via `manifest.json` (strong anchor) or `__init__.py` (package anchor). Bundles are written into per-module directories under the configured `output_subdir/output_category` (e.g. `.../homeassistant-main_txt/camera/`).
- **Module Blueprint (TIPO 4):** Each module always receives a `MODULE_BLUEPRINT` bundle that aggregates anchor files and includes a dedicated `[README]` section. There is no separate TIPO 2 anymore; README content is folded into the blueprint.
- **README Inheritance (walk-up):** If a module has no README inside its folder, the processor walks up the tree toward the repository root and inherits the first `README.md|README.rst|README.txt` it finds; that README is associated to the module and included in the blueprint.
- **Anchors:** Files treated as anchors include `manifest.json`, `const.py`, `services.yaml`, `strings.json`, `icons.json`, `hacs.json` (and `.json/.yaml/.yml` by suffix). Anchor files are rendered into the blueprint (with `const.py` rendered to a `[VOCABULARY]` block and `services.yaml` to `[SCHEMA]`).
- **Tests-first RULE:** If an exact matching test is found for a logic file (namespace mirror, component test dir, or scored rglob), the file is emitted as `TIPO 1 — FUNCTIONAL_UNIT` (logic + test) and this emission bypasses the `MIN_SIZE` size gate so small utility functions with tests are preserved.
- **Size & Gold filters (legacy behavior):** For files without tests, `MIN_SIZE` and `GOLD_PATTERNS` are still applied; long logic files become `TIPO 3 — LOGIC_ONLY`.
- **Local-imports normalization:** `_extract_local_imports` now returns concrete filenames (e.g., `const.py`, `helpers.py`) instead of dotted module fragments; duplicates are suppressed. These filenames populate the bundle's `[ARCH_HEADER]` `LOCAL_IMPORTS` field.
- **INFRASTRUCTURE purged:** Loose root-level files are no longer emitted as a virtual `INFRASTRUCTURE` module — the processor only emits discovered modules (manifest/__init__).

#### ExtractorAdapter Architecture (FR-005)

The processor uses a **pluggable extractor system** that adapts to different programming languages:

```python
from src.utils.extractors import get_adapter

# Initialize adapter based on profile
adapter = get_adapter(profile="homeassistant")
```

| Adapter | Language | Key Methods |
|---------|----------|-------------|
| `PythonASTAdapter` | Python | `extract_dependencies()`, `parse_file()` |
| `PHPExtractorAdapter` | PHP | `extract_dependencies()`, `parse_file()` |
| `TypeScriptAdapter` | TypeScript/TSX | `parse_file()` (uses LitComponentExtractor, I18nKeyExtractor, ServiceCallExtractor) |

#### TypeScript/Frontend Extraction (spec: frontend-discovery-enhancement)

The `TypeScriptAdapter` supports **Lit web component** parsing for frontend files:

```python
from src.utils.extractors.factory import get_adapter

# Get TypeScript adapter for .ts/.tsx files
adapter = get_adapter('typescript')
```

**Built-in Extractors:**

| Extractor | Purpose | Detects |
|-----------|---------|---------|
| `LitComponentExtractor` | Lit custom elements | `@customElement`, `@property`, `@state` decorators |
| `I18nKeyExtractor` | i18n keys | `localize()`, `hass.localize()`, template literals |
| `ServiceCallExtractor` | Service calls | `hass.callService(domain, service, data)` |
| `TranslationJsonParser` | Translation JSON | Nested JSON → dot-path keys |

**Supported Frontend Patterns:**
- **Lit components**: `@customElement('ha-dialog')` tag registration
- **Properties**: `@property({ type: String })` reactive properties
- **States**: `@state() private _opened = false`
- **i18n**: `localize('ui.card.door.unlocked')`, `hass.localize("ui.common.back")`
- **Service calls**: `this.hass.callService("cover", "open_cover", { entity_id: ... })`

**Translation JSON:**
```python
from src.utils.extractors.parsers.translation_json import parse_translation_json

entries = parse_translation_json(Path("strings.json"))
# Returns: [{"key": "ui.card.door.unlocked", "value": "Door unlocked", "is_leaf": true}, ...]
```

**Export Format:**
```python
from src.export.chatml_exporter import ChatMLExporter

exporter = ChatMLExporter()
for record in exporter.export(tokens, system_prompt):
    print(record.json())
```

**Frontend Taxonomy Prompts:**
```python
from src.export.frontend_taxonomy_prompts import FRONTEND_COMPONENT_SYSTEM_PROMPT

# Component metadata extraction prompt
system_msg = FRONTEND_COMPONENT_SYSTEM_PROMPT
# Returns JSON: {tag, class, file_path, props, events, service_calls, i18n_keys}
```

#### ParseError Policy (FR-006)

When the extractor fails to parse a file, the system follows a configurable policy:

| Policy | Behavior |
|--------|----------|
| `abort` (default) | Mark file as `needs_manual_review` and abort repo processing |
| `skip` | Skip the file and continue processing |
| `mark_and_continue` | Mark file, log error, and continue |

The `ParseError` exception includes:
- `file_path`, `line`, `error`, `diagnosis`, `fix_hint`, `adapter`

#### Module Detection Strategies (FR-008)

Three strategies for grouping files into modules/bounded contexts:

| Strategy | Description |
|----------|-------------|
| `manifest` | Detect modules via manifest files (`manifest.json`, `composer.json`, `package.json`) |
| `directory` | Group by directory rules (e.g., `app/`, `src/`, `controllers/`) |
| `manual_mapping` | Use explicit `manual_module_mapping` table in YAML config |

Operational Flow (examples):

Run Ingestion (Stage 1):
```
python3 -m src.discovery.ingestor --config configs/homeassistant.yaml
```

Run Processing (Stage 1.5):
```
python -m src.discovery.processor_cli --config configs/homeassistant.yaml
```

Notes:
- The processor writes bundles into a module-named directory and includes an `[ARCH_HEADER]` block in every bundle with `MODULE`, `FILE_ROLE`, `FRAGMENT_TYPE`, `LOCAL_IMPORTS`, and `NEIGHBORS`.
- If you relied on an `INFRASTRUCTURE` output previously, that behavior was intentionally removed — adjust downstream tooling to consume only module subfolders.
- No action is required for `production_v11.py` invocations; the `--raw-dir` default still targets the `*_main_txt` output category but downstream consumers should expect per-module subdirectories.
---

### Stage 1.75 — Master Documents (`data/Gap/`)

> ⚠️ **This is a manual curation step.** There is no script that generates these files automatically. They must be written, maintained, and updated by the human architect as the Home Assistant API evolves.

These three Markdown documents are the **API Delta knowledge base** of the entire factory. Both `production_v11.py` and `agentic_gen.py` load them at startup via `load_master_docs()` and inject them verbatim into every system prompt as `$master`, `$changelog`, and `$jinja_guide` using `string.Template.safe_substitute()`.  
> TODO: the sample documents reference here are Home Assistant–specific; substitute equivalent docs when adapting the pipeline to another ecosystem.

**If any file is missing, both scripts fail immediately** with a precise `FileNotFoundError` pointing to `--gap-dir`.

#### Required Files

| File | Variable | Purpose |
|------|----------|---------|
| `HA_MASTER_GUIDE_2026.md` | `$master` | Core HA integration standards for 2026: entry setup, CoordinatorEntity, ConfigFlow, state machine best practices |
| `technical_changelog_2026.md` | `$changelog` | Exhaustive API delta: every breaking change from HA 2023 → 2026.x with before/after migration examples |
| `HA_JINJA_YAML_GUIDE_2026.md` | `$jinja_guide` | Jinja2 & YAML template breaking changes from HA 2024.10 → 2026.2 (automations, templates, entities) |

All three files live in `data/Gap/` by default (override with `--gap-dir`).

#### Dynamic Profile-Based Loading (FR-009)

Master Documents are loaded dynamically based on the active **profile**:

```python
from src.factory import prompt_builder
from pathlib import Path

# Load master docs for a specific profile
master_docs = prompt_builder.load_master_docs(
    gap_dir=Path('data/Gap'),
    profile='homeassistant'  # or 'php_hexagonal'
)
```

**Profile Master Documents Mapping:**

| Profile | Required Files |
|---------|---------------|
| `homeassistant` | `HA_MASTER_GUIDE_2026.md`, `technical_changelog_2026.md`, `HA_JINJA_YAML_GUIDE_2026.md` |
| `php_hexagonal` | `PHP_MASTER_GUIDE.md`, `hexagonal_architecture.md`, `SOLID_PRINCIPLES.md` |

The mapping is defined in `configs/stage_1_discovery/master_docs_map.yaml`. If a required document is missing, the system raises `FileNotFoundError` with a clear message.

#### How to Create / Maintain Them

These documents are the most important inputs that govern sample quality. The recommended approach per file:

**`HA_MASTER_GUIDE_2026.md`** — Domain standards reference:
- Synthesize from the official [Home Assistant Developer Docs](https://developers.home-assistant.io/) *(or your own platform's reference; this link is HA‑specific)*
- Focus on: entity lifecycle, async patterns, `CoordinatorEntity`, `ConfigFlow`, `EntityDescription`, unit enums
- Keep concise (5–15 KB). It is injected into every prompt — size directly affects token consumption.

**`technical_changelog_2026.md`** — Running API delta journal:
- Start with the official [Home Assistant Release Notes](https://www.home-assistant.io/blog/categories/release-notes/) from 2023.1 onward *(replace with your domain's changelog feed as needed)*
- For each breaking change, document: what changed, the old pattern, the new pattern, and the deprecation timeline
- Update after every HA major release. This is the primary anti-hallucination mechanism.
- The `homeassistant-main_txt/` bundles produced by Stage 1.5 are good source material — scan them for deprecated patterns.

**`HA_JINJA_YAML_GUIDE_2026.md`** — Jinja2/YAML migration guide:
- Source: HA release notes for `template`, `automation`, and `script` breaking changes
- Cover: `trigger:` → `triggers:`, `action:` → `actions:`, `platform:` removal, `value_template:` deprecation, `this` variable semantics, snake_case state normalization
- The `homeassistant-jinja_txt/` bundles from Stage 1.5 are ideal reference material.

#### CLI

```bash
# Default: auto-resolves to <project_root>/data/Gap
python -m src.factory.cli --workers 16

# Custom location
python -m src.factory.cli --gap-dir /path/to/master/docs --workers 16

# Verify all three files exist before a long run
python -c "
from pathlib import Path
from src.factory import prompt_builder
m, c, j = prompt_builder.load_master_docs(Path('data/Gap'))
print(f'Master Guide:      {len(m):,} chars')
print(f'Changelog:         {len(c):,} chars')
print(f'Jinja/YAML Guide:  {len(j):,} chars')
"
```

---

### Stage 2 — Factory (`src/factory/`)
**Engines:** `pipeline_runner.py` (Stable) & `agentic_runner.py` (Experimental)

> **Nota:** Tras la refactorización de spec 003, los archivos monolíticos fueron divididos en submódulos. El motor de producción principal ahora es `pipeline_runner.py` (orquestador) que usa los submódulos `prompt_builder.py`, `fragment_extractor.py`, `ldi_validator.py`, `checkpoint.py` y `config.py`. Para ejecución CLI, usa `cli.py`.

Synthetic trajectory generation codebase with decoupled semantics (Prompts in external YAML Taxonomies) and Fail-Fast architectures.

#### 🔹 Gold Injection — `production_v11.py` (Stable)

The core production engine. Forces the model to reason (`<think>`) toward a pre-validated, existing code solution, eliminating syntactical hallucinations.

**Features:**
- Evol-Instruct diversification (50% nominal / 30% contrast 2023→2026 / 20% error recovery)
- Strict Anti-Schizophrenia legacy filter
- Async semaphore scaling (16-64 workers)
- Checkpoint/resume support for interrupted runs
- Dynamic CLI paths for Master Documents (`--gap-dir`)
- Jinja2/YAML template processing (`--extensions`)
- Theory mode for pure doctrine datasets
- Uses `prompts_taxonomy.yaml` (external YAML taxonomy)
- Real-time filtering of repetitive reasoning patterns before disk write, reducing dataset volume by ~15-20% while maintaining semantic integrity.

**Common Usage Examples:**

```bash
# Test mode: quick validation with 10 fragments
python -m src.factory.cli --test 10 --workers 4

# Full production run: 24 workers, 50 raw files
python -m src.factory.cli --limit 50 --workers 24

# Process Jinja2/YAML templates with custom extension filter
python -m src.factory.cli --raw-dir data/raw/ha-jinja \
  --extensions .jinja .jinja2 .yaml .yml \
  --workers 16

# Theory mode: Generate 100 doctrine samples (teacher-student format)
python -m src.factory.cli --theory --theory-reps 100 --workers 8 \
  --output data/synthetic/theory_dataset.jsonl

# Resume interrupted run (auto-skips processed fragments)
python -m src.factory.cli --resume data/synthetic/v10_run_20260224.jsonl \
  --workers 16 --limit 50

# Custom gap directory + custom taxonomy path
python -m src.factory.cli --gap-dir /path/to/master/docs \
  --taxonomy /path/to/custom_taxonomy.yaml --workers 16
```

**Key Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--test` | int | None | Test mode: process only N fragments for validation |
| `--limit` | int | None | Limit processing to N raw input files |
| `--workers` | int | 8 | Number of parallel async workers (2-64 recommended) |
| `--model` | str | `qwen3-30b-a3b-thinking-fp8` | Inference model endpoint |
| `--base-url` | str | `http://localhost:8000/v1` | vLLM server URL |
| `--api-key` | str | `xxxx-xxxxx-xxxxx-xxxxx` | Server API key |
| `--output` | str | Generated | Custom JSONL output path |
| `--seed` | int | 42 | Reproducibility seed |
| `--resume` | str | None | Path to previous JSONL to resume from checkpoint |
| `--raw-dir` | str | `data/raw/homeassistant-main_txt` | Input directory with `.txt` packs |
| `--extensions` | list | None | Filter by extensions (e.g., `.jinja .jinja2 .yaml .yml`) |
| `--theory` | flag | False | Enable theory/doctrine mode |
| `--theory-reps` | int | 3 | Repetitions per section in theory mode |
| `--gap-dir` | str | `data/Gap` (auto-resolved) | Directory with master documents |
| `--taxonomy` | str | Auto-resolved | Path to `prompts_taxonomy.yaml` |

**Output Structure (JSONL):**
Each line is a JSON sample with structure:
```json
{
  "id": "v10_nominal_a1b2c3d4e5f6",
  "conversation": [
    {"role": "user", "content": "...implement..."},
    {"role": "assistant", "content": "<think>...</think><write_action>..."}
  ],
  "metadata": {
    "example_type": "nominal|contrast|error_recovery",
    "evol_difficulty": "easy|medium|hard",
    "ldi": 1.234,
    "gold_injected": true,
    "legacy_detected": false,
    "checkpoint_key": "a1b2c3d4e5f6g7h8"
  }
}
```

---

#### 🔹 Agentic Multi-Turn — `agentic_cli.py` (Experimental)

Generates complex 4-turn tool-calling trajectories optimized for tool-use fine-tuning:
- Turn 1: User request with context
- Turn 2: Assistant writes code (with Gold Injection)
- Turn 3: Tool response (simulated success)
- Turn 4: Assistant closes with `attempt_completion`

**Features:**
- Pydantic-validated tool-call JSON
- 4-turn multi-turn conversation format
- Identical robustness to V10
- Driven by own taxonomy (`agentic_taxonomy.yaml`)
- Fail-fast master document loading

**Common Usage Examples:**

```bash
# Quick test: 5 fragments, 4 workers
python -m src.factory.agentic_cli --test 5 --workers 4

# Full production: 16 workers, all raw files
python -m src.factory.agentic_cli --workers 16

# Limit to 30 raw files with custom output path
python -m src.factory.agentic_cli --limit 30 \
  --output data/synthetic/agentic_run_20260224.jsonl \
  --workers 12

# Resume from checkpoint
python -m src.factory.agentic_cli --resume data/synthetic/agentic_v10mt_20260223.jsonl \
  --workers 16

# Custom model, API endpoint, and gap directory
python -m src.factory.agentic_cli --model qwen3-32b \
  --base-url http://vllm-server:8000/v1 \
  --api-key my-custom-key \
  --gap-dir /custom/master/docs \
  --workers 8

# Low-resource test (small worker pool, custom seed)
python -m src.factory.agentic_cli --test 3 --workers 2 --seed 123
```

**Key Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--test` | int | None | Test mode: process only N fragments |
| `--limit` | int | None | Limit to N raw input files |
| `--workers` | int | 8 | Parallel async workers (2-64 recommended) |
| `--model` | str | `qwen3-30b-a3b-thinking-fp8` | Inference model |
| `--base-url` | str | `http://localhost:8000/v1` | vLLM server URL |
| `--api-key` | str | `xxxxx-xxxxxx-xxxxx-xxxxx` | Server API key |
| `--output` | str | Generated | Custom JSONL output path |
| `--seed` | int | 42 | Reproducibility seed |
| `--resume` | str | None | Path to previous JSONL for checkpoint resume |
| `--gap-dir` | str | `data/Gap` (auto-resolved) | Directory with master documents |
| `--taxonomy` | str | Auto-resolved | Path to `agentic_taxonomy.yaml` |

**Output Structure (JSONL):**
Each line contains a 4-turn conversation:
```json
{
  "id": "v10mt_nominal_xyz789",
  "conversation": [
    {"role": "user", "content": "Context: ... Task: ..."},
    {"role": "assistant", "content": "<think>Reasoning...</think><tool_call>{\"name\": \"write_to_file\", ...}"},
    {"role": "tool", "content": "{\"status\": \"success\", ...}"},
    {"role": "assistant", "content": "<think>Closing...</think><tool_call>{\"name\": \"attempt_completion\", ...}"}
  ],
  "metadata": {
    "example_type": "nominal|contrast|error_recovery",
    "evol_difficulty": "easy|medium|hard|null",
    "ldi": 1.567,
    "gold_injected": true,
    "checkpoint_key": "xyz789..."
  }
}
```

---

#### 📋 Master Documents & Taxonomies

> **Prerequisite:** Master documents must exist before running either factory script. See **[Stage 1.75](#stage-175--master-documents-datagap)** for how to create and maintain them. This is a **manual curation process** — no script generates these files.

Both scripts require the following inputs:

**Master Documents** (loaded via `load_master_docs()`, injected into every system prompt):

| # | File | Prompt Variable | Purpose |
|---|------|-----------------|---------|
| 1 | `data/Gap/HA_MASTER_GUIDE_2026.md` | `$master` | Core HA integration standards |
| 2 | `data/Gap/technical_changelog_2026.md` | `$changelog` | Full API delta 2023 → 2026 |
| 3 | `data/Gap/HA_JINJA_YAML_GUIDE_2026.md` | `$jinja_guide` | Jinja2/YAML breaking changes |

**Taxonomy YAMLs** (prompt templates, decoupled from code):
- `configs/taxonomy/home_assistant/hacs_expert/prompts_taxonomy.yaml` → `production_v11.py`
- `configs/taxonomy/home_assistant/hacs_expert/agentic_taxonomy.yaml` → `agentic_gen.py`

If any master document is missing, both scripts **fail-fast** with a clear `FileNotFoundError` that includes the missing path and directs you to use `--gap-dir`.

**Auto-Resolution Behavior:**
- Default gap directory: `<project_root>/data/Gap`
- Default taxonomy paths: `<project_root>/configs/taxonomy/home_assistant/hacs_expert/{prompts_taxonomy.yaml|agentic_taxonomy.yaml}`

Override with CLI params:
```bash
python -m src.factory.cli --gap-dir /custom/master/docs --taxonomy /custom/taxonomy.yaml
```

### Stage 3 — Curation (`src/curation/`)
**Engine:** `curator_cli.py` — Unified AEGF Curation Suite

> **Nota:** Tras la refactorización de spec 003, `nemo_curator_suite.py` fue dividido en submódulos: `dedup_filter.py`, `quality_filter.py`, `curator_pipeline.py` y `curator_cli.py`.

A single, composable command-line engine that chains **four independent curation phases** into a professional pipeline. Phases can run individually or in any combination.

> ⚠️ **Phase 1 (`--filter`) requires the `aegf_curator` Docker container** (image: `nvcr.io/nvidia/nemo-curator:25.09`). Phases 0, 2 and 3 are pure-Python and run anywhere without special dependencies.

#### 🔹 Launching the Container (required for Phase 1)

The container is defined in `deploy/docker/docker-compose.yaml` (service `curator`) and configured via `deploy/.env`:

```bash
# 1. Set variables in deploy/.env (already configured for "The Bunker"):
#    NEMO_IMAGE=nvcr.io/nvidia/nemo-curator:25.09
#    AEGF_PROJECT_ROOT=../../   # mounts as /workspace inside the container

# 2. Start the curator container:
cd deploy/docker
docker compose up -d curator

# 3. Open a shell inside the container:
docker exec -it aegf_curator bash

# 4. Run the suite from inside the container
#    (project root is mounted at /workspace):
python -m src.curation.curator_cli \
    --input  /workspace/data/synthetic/CLEAN.jsonl \
    --output /workspace/data/synthetic/CURATED.jsonl \
    --exact-dedup --filter --structural --dedup --apply
```

#### 🔹 Four-Phase Architecture

| Phase | Flag | Container required | Description |
|-------|------|--------------------|-------------|
| **0 — Exact dedup** | `--exact-dedup` | No | SHA-256 hash on full conversation; removes byte-identical records. |
| **1 — NeMo filter** | `--filter` | **Yes** | Distributed Ray + NeMo Curator battery (word count, boilerplate, n-gram repetition, symbol ratio, etc.). |
| **2 — Structural gate** | `--structural` | No | Syntax integrity (`</think><tool_call>`), think depth ≥ 500 chars, meta-speech detection, LDI on `<tool_call>` ≥ 0.15. |
| **3 — Semantic dedup** | `--dedup` | No | MinHash-LSH near-duplicate clustering (`datasketch`); falls back to O(n²) Jaccard if unavailable. |

Phases chain automatically in order. Intermediate results are written to temp files and cleaned up automatically.

#### 🔹 CLI Reference

**Required I/O:**
```
--input   FILE    Source JSONL dataset
--output  FILE    Output JSONL dataset
```

**Phase Selection (at least one required):**
```
--exact-dedup    Phase 0: SHA-256 exact deduplication
--filter         Phase 1: NeMo Curator quality filters  ⚠️  needs container
--structural     Phase 2: Syntax, LDI, think-depth, meta-speech
--dedup          Phase 3: MinHash-LSH semantic deduplication
```

**Execution flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--apply` | off | Persist output. Without this, runs in **dry-run** mode (statistics only). |
| `--sample N` | 0 (all) | Process only the first N records for quick validation. |
| `--reports-dir DIR` | `data/reports` | Directory for the JSON statistics report. |

**Phase 1 — NeMo filter thresholds:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--min-words` | 80 | Minimum word count in assistant text |
| `--max-symbol-ratio` | 0.10 | Max symbol-to-word ratio |
| `--max-non-alpha-ratio` | 0.25 | Max non-alphanumeric ratio |
| `--max-url-ratio` | 0.20 | Max URL-to-text ratio |
| `--max-no-endmark-ratio` | 0.85 | Max sentences without terminal punctuation |
| `--max-boilerplate-ratio` | 0.40 | Max boilerplate-string ratio |
| `--max-repeated-lines` | 0.70 | Max fraction of repeated lines |
| `--max-ngram-ratio` | 0.08 | Max repeating top-N-gram ratio |
| `--ngram-size` | 3 | N-gram order for repetition filter |

**Phase 2 — Structural gate thresholds:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--min-think-chars` | 500 | Minimum characters required in `<think>` block |
| `--ldi-min-ratio` | 0.15 | Minimum Logic Density Index on `<tool_call>` block (Calibrated formula, range 0–1) |
| `--no-attempt-check` | off | Disable `attempt_completion` check (use for single-turn `production_v11` data) |

**Phase 3 — Dedup thresholds:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dedup-threshold` | 0.85 | MinHash similarity threshold (0–1) |
| `--quality-cutoff` | 0.30 | Minimum heuristic quality score to retain |
| `--minhash-perms` | 128 | MinHash permutations (higher = more accurate, slower) |
| `--shingle-k` | 5 | Character shingle size for MinHash signatures |

> **Note:** Intermediate temporary files created during multi-phase runs live in `/tmp` and are automatically cleaned up. The engine retries with new names if a stale path already exists, so you should no longer encounter "File exists" errors when running multiple times.

#### 🔹 Usage Examples

**Full pipeline — all four phases (inside container):**
```bash
python -m src.curation.curator_cli \
    --input  /workspace/data/synthetic/v11_clean.jsonl \
    --output /workspace/data/synthetic/CURATED.jsonl \
    --exact-dedup --filter --structural --dedup \
    --min-words 80 --dedup-threshold 0.85 --quality-cutoff 0.30 \
    --reports-dir /workspace/data/reports \
    --apply
```

**Structural + semantic dedup only (no container needed):**
```bash
python -m src.curation.curator_cli \
    --input  data/synthetic/v11_clean.jsonl \
    --output data/synthetic/CURATED.jsonl \
    --exact-dedup --structural --dedup \
    --no-attempt-check \
    --apply
```

**Dry-run — statistics without writing files:**
```bash
python -m src.curation.curator_cli \
    --input  data/synthetic/v11_clean.jsonl \
    --output data/synthetic/CURATED.jsonl \
    --exact-dedup --structural --dedup
# → Prints full curation report; no file written.
```

**Quick validation on 1 000 records:**
```bash
python -m src.curation.curator_cli \
    --input  data/synthetic/v11_clean.jsonl \
    --output /tmp/test.jsonl \
    --structural --dedup --sample 1000 --apply
```

#### 🔹 Output

After `--apply`, the suite writes:

1. **Curated JSONL** (`--output`): records annotated with `metadata.curation = {kept: true, quality_score: <float>}`.
2. **Statistics report** (`data/reports/nemo_curator_suite_report.json`):
   ```json
   {
     "timestamp": "2026-03-01T10:00:00Z",
     "total_input": 17155,
     "removed": {
       "exact_duplicates": 42,
       "nemo_filtered": 310,
       "invalid_syntax": 88,
       "shallow_thinking": 120,
       "meta_speech": 35,
       "low_ldi": 97,
       "low_quality_score": 201,
       "semantic_duplicates": 465,
       "total": 1358
     },
     "total_output": 15797,
     "retention_pct": 92.09
   }
   ```

### Stage 3.5 — Backtracking Alignment (`src/curation/`)
**Engine:** `rewrite_cli.py`

> **Nota:** Tras la refactorización de spec 003, `backtracking_rewriter.py` fue dividido en submódulos: `backtracking_config.py`, `backtracking_helpers.py`, `backtrack_strategy.py`, `rewrite_engine.py` y `rewrite_cli.py`.

A post-curation rewriting stage that transforms `<think>` blocks to embed **self-correction and backtracking** patterns. Inspired by OpenCodeReasoning and AgentMathPlus research, this stage teaches the model to detect mistakes in its own reasoning, backtrack, and converge on the correct architectural solution — rather than always presenting a "perfect first attempt" that does not match real inference behaviour.

#### Why Backtracking?

Standard SFT datasets present reasoning as a clean, linear chain. In practice, reasoning models naturally explore, make mistakes, and self-correct. Training exclusively on linear trajectories creates a **distribution mismatch** between training and inference. Backtracking Alignment reduces this gap by injecting realistic error-correction patterns into the `<think>` block while preserving the sacred code after `</think>` byte-for-byte.

#### Rewrite Strategies

The rewrite strategy for each record is determined by `classify_rewrite_strategy` in the code. Priority (highest → lowest) is: `theory` (skip) → `legacy_detected` → `gold_injected` → `error_recovery` → `contrast` → default `pass_through`.

| Strategy | Eligibility | Description |
|----------|-------------|-------------|
| `full_backtracking` | `metadata.legacy_detected == True` | Full backtracking for records flagged as containing legacy API usage: guide the model to name the legacy impulse, self-evaluate, backtrack and produce a modern solution. |
| `trace_reconstruction` | `metadata.gold_injected == True` | Reconstruct the expert reasoning trace that justifies the provided perfect solution code. |
| `error_first` | `example_type == "error_recovery"` | Start from an error-focused scenario, propose a wrong fix, then identify and correct it. |
| `contrast_backtracking` | `example_type == "contrast"` | Present both old and new approaches and explicitly reject the legacy one with technical justification. |
| `pass_through` | default (clean nominal examples) | Preserve the original think block; no rewrite applied. |
| `skip` | `example_type in config.excluded_types` (e.g. `theory`) | These records are not processed by the rewriter. |

#### Sacred Constraint

> **The code after `</think>` is NEVER modified.** Only the reasoning block inside `<think>…</think>` is rewritten. The rewriter enforces byte-identical preservation of the action block.

#### CLI

```bash
# Minimal run — default config values
python -m src.curation.rewrite_cli \
  --input  data/synthetic/v11_DISTILLED.jsonl \
  --output data/synthetic/v11_backtracking_aligned.jsonl

# Using the project YAML config
python -m src.curation.rewrite_cli \
  --input  data/synthetic/v11_DISTILLED.jsonl \
  --output data/synthetic/v11_backtracking_aligned.jsonl \
  --config configs/stage_3_curation/backtracking_alignment.yaml

# Override specific parameters without editing the YAML
python -m src.curation.rewrite_cli \
  --input  data/synthetic/v11_DISTILLED.jsonl \
  --output data/synthetic/v11_backtracking_aligned.jsonl \
  --config configs/stage_3_curation/backtracking_alignment.yaml \
  --model  qwen3-30b-a3b-thinking-fp8 \
  --temperature 0.5 \
  --batch-size 20 \
  --log-level DEBUG

# Audit run: save full rewritten think blocks for offline inspection
python -m src.curation.rewrite_cli \
  --input  data/synthetic/v11_DISTILLED.jsonl \
  --output data/synthetic/v11_backtracking_aligned.jsonl \
  --config configs/stage_3_curation/backtracking_alignment.yaml \
  --audit-dir data/reports/backtracking_audit \
  --log-level INFO

# Quick validation on 50 records (Python API — corrected async usage)
python -c "import asyncio; from pathlib import Path; from src.curation.rewrite_engine import rewrite_pipeline, BacktrackingConfig; cfg = BacktrackingConfig(batch_size=50); report = asyncio.run(rewrite_pipeline(Path('data/synthetic/v11_DISTILLED.jsonl'), Path('/tmp/bt_test.jsonl'), cfg)); print(report)"
```

**CLI reference:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input`, `-i` | Yes | — | Source JSONL dataset |
| `--output`, `-o` | Yes | — | Destination JSONL dataset |
| `--config`, `-c` | No | built-in defaults | YAML config file |
| `--model` | No | `qwen3-30b-a3b-thinking-fp8` | vLLM model name |
| `--base-url` | No | `http://localhost:8000/v1` | vLLM API base URL (YAML key: `vllm_api_url`) |
| `--temperature` | No | `0.6` | Sampling temperature |
| `--max-tokens` | No | `4000` | Max context-token filter (records estimated above this are discarded) |
| `--max-generation-tokens` | No | `3000` | Max tokens per single rewrite request to the model |
| `--batch-size` | No | `10` | Progress log interval (eligible records between log lines) |
| `--log-level` | No | `INFO` | Verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |
| `--audit-dir` | No | None | Directory to save full rewritten `<think>` blocks (timestamped run subdir) |

#### Configuration (`configs/stage_3_curation/backtracking_alignment.yaml`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_tokens` | 4000 | Max context-token filter: estimated tokens (chars//4) above this value are excluded from processing. |
| `temperature` | 0.6 | Sampling temperature for the vLLM requests |
| `max_generation_tokens` | 3000 | Max tokens requested from the model for a single think-block rewrite |
| `excluded_types` | `[theory]` | Example types to skip from rewriting |
| `batch_size` | 10 | Progress log interval (how many eligible records between progress log lines) |
| `seed` | 42 | Reproducibility seed used by the pipeline |
| `workers` | 8 | Concurrency level (asyncio Semaphore for parallel vLLM calls) |
| `vllm_api_url` | `http://localhost:8000/v1` | vLLM endpoint (YAML key `vllm_api_url`, CLI override `--base-url`) |
| `vllm_model` | `qwen3-30b-a3b-thinking-fp8` | vLLM model name |

#### Output

The pipeline writes a new JSONL with the same schema as the input. Rewritten records gain `metadata.backtracking_strategy` indicating which strategy was applied. Implementation notes:

- The pipeline accumulates rewritten records in memory in an `output` list and writes the final JSONL atomically at the end of the run (`save_jsonl` writes to a `.tmp` file and renames it). If the process is interrupted, the final JSONL will not be created.
- When `--audit-dir` is provided the rewriter writes one pretty-printed JSON per processed record into a timestamped run subdirectory as the job proceeds (`_emit_audit_file`). These audit files are useful to recover progress if the main run is interrupted.

The `PipelineReport` dataclass summarizes counts per strategy and overall throughput.

---

### Stage 3.x — Dataset Mixing (`src/curation/dataset_mixer.py`)

**Purpose:** Mix specialized and anchor datasets with configurable token proportions (default **65/35 Anti-Pereza**).

```python
from src.curation.dataset_mixer import DatasetMixer, DatasetMixerConfig

config = DatasetMixerConfig(
    specialized_pct=65.0,  # Anti-Pereza: specialized (gold)
    anchor_pct=35.0,       # Anchor (theory/doctrine)
    shuffle_seed=42
)

mixer = DatasetMixer(config)
mixed = mixer.mix(specialized_records, anchor_records)
mixer.export(mixed, Path("output.jsonl"))
report = mixer.generate_report(mixed)
```

**Configuration:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `specialized_pct` | 65.0 | Target % for specialized (gold) dataset |
| `anchor_pct` | 35.0 | Target % for anchor (theory/doctrine) |
| `shuffle_seed` | 42 | Deterministic shuffle seed |
| `target_records` | None | Optional target total records |

**Token-based Proportions:**
- Uses `tiktoken` (cl100k_base) for token counting (~3% drift vs Qwen3)
- Subsamples to achieve exact token % targets, not record counts
- Deterministic shuffle ensures reproducibility

**Output Format:**
- ChatML JSONL format
- Includes composition report with token counts and proportions

---

### Stage 4 — Training
**Engine:** Axolotl

 ##### ⚡ Quick Start
 ```bash
make preprocess 
make train
```

**Protocol:** Rank-64 RSLoRA (Rank-Stabilized LoRA) over Qwen3-30B-A3B-MoE. Optimized for `sm_120` kernels and `bf16` precision. Docker stack defined in `deploy/docker/`.

### Stage 5 — Quality Gate (`src/audit/`)
**Engine:** `cli.py`

> **Nota:** Tras la refactorización de spec 003, `model_evaluator.py` fue dividido en submódulos de responsabilidad única: `config.py`, `gap_generator.py`, `exam_builder.py`, `judge.py`, `scorecard.py`, `report_writer.py` y `cli.py` (punto de entrada).

Automated dual-inference evaluation pipeline that acts as a **mandatory gate** between training and weight consolidation. The evaluator compares the base model (control) against the LoRA adapter (trained) on a stratified sample from the training dataset.

#### Workflow

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐
│ Sample  │───▶│ Baseline │───▶│ Adapter │───▶│  Score  │
│ Extract │    │ Infer    │    │ Infer   │    │ Report  │
└─────────┘    └──────────┘    └─────────┘    └─────────┘
    ▼               ▼              ▼              ▼
 eval_sample   inference_     inference_     audit_report
   .json       baseline.json  adapter.json    _v11.md
```

#### Quick Start

```bash
# Full pipeline (sample → baseline → adapter → score)
python -m src.audit.cli full \
    --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \
    --base-model qwen3-30b-a3b-thinking-fp8 \
    --adapter-model platinum_adapter

# Or step-by-step
python -m src.audit.cli sample  --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl
python -m src.audit.cli baseline --model qwen3-30b-a3b-thinking-fp8
python -m src.audit.cli adapter  --model platinum_adapter
python -m src.audit.cli score
```

#### Validate mode (token-efficient smoke test)

Use `--validate` for a deterministic, low-cost check (sample size = 1). This is useful to verify wiring and prompts without incurring heavy inference costs.
example

```bash
python -m src.audit.cli full \
  --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \
  --base-model qwen3-30b-a3b-thinking-fp8 \
  --adapter-model platinum_adapter \
  --validate
```

Note on Gemini: Google Gemini is intended only as a test-time fallback when the local vLLM instance is busy or unavailable. If you use Gemini, set a valid `GOOGLE_API_KEY` in your environment. Be aware that calling Gemini may incur API costs; CI intentionally leaves `GOOGLE_API_KEY` unset and tests use local mocks or vLLM to avoid external calls.

#### Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Structural Fidelity | 30% | Code similarity to gold reference |
| API Modernity | 25% | Modern HA 2026 patterns vs legacy |
| Reasoning Depth | 20% | Quality of `<think>` block analysis |
| Completeness | 15% | Coverage of functions/classes from reference |
| Style Consistency | 10% | Adherence to AEGF conventions |

The evaluator emits a **Final Grade (0–100)** with a verdict: `PASS` (≥80), `CONDITIONAL` (60–79), `WARN` (40–59), or `FAIL` (<40).

#### Output

| File | Description |
|------|-------------|
| `data/audit/eval_sample.json` | Persisted stratified sample (deterministic seed) |
| `data/audit/inference_baseline.json` | Base model responses |
| `data/audit/inference_adapter.json` | LoRA adapter responses |
| `data/audit/audit_report_v11.md` | Full comparative Markdown report |
| `data/audit/audit_report_v11.json` | Structured JSON report |

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AEGF_VLLM_API_URL` | `http://localhost:8000/v1` | vLLM API endpoint |
| `AEGF_AUDIT_DIR` | `data/audit` | Output directory |
| `AEGF_SAMPLE_SIZE` | `20` | Records per evaluation sample |
| `AEGF_BASE_MODEL` | `qwen3-30b-a3b-thinking-fp8` | Base model name |
| `AEGF_ADAPTER_MODEL` | `platinum_adapter` | LoRA adapter name |
| `AEGF_MAX_TOKENS` | `4096` | Max generation tokens |
| `AEGF_TEMPERATURE` | `0.3` | Sampling temperature |

### Stage 6 — Inference Calibration Suite (`src/audit/calibration.py`)
**Engine:** `calibration.py`

Stage 6 implements an **Inference Calibration Suite** for automated sampling parameter optimization using LLM-as-Judge. This stage systematically explores the parameter space to discover optimal inference settings that maximize response quality without requiring manual tuning.

#### Overview

The calibration engine performs a **grid search** (Cartesian product) across multiple sampling parameters, evaluating each configuration using the Professor Judge and selecting the optimal combination based on composite quality scores.

#### Parameter Grid (Expanded)

| Parameter | Values | Description |
|-----------|--------|-------------|
| `temperature` | [0.3, 0.5, 0.6, 0.7, 0.9, 1.1] | Controls randomness in sampling |
| `top_p` | [0.7, 0.8, 0.9, 0.95, 1.0] | Nucleus sampling threshold |
| `top_k` | [5, 10, 20, 40, 60, 80] | Limits vocabulary to top-k tokens |
| `min_p` | [0.0, 0.02, 0.05, 0.1, 0.15] | Minimum probability threshold |
| `repetition_penalty` | [1.0, 1.05, 1.1, 1.15, 1.2] | Penalizes repeated tokens |
| `presence_penalty` | [0.0, 0.5, 1.0, 1.5, 2.0] | Penalizes repeated tokens (presence) |

**Default pivot values:** temperature=0.6, top_p=0.9, top_k=20, min_p=0.0, repetition_penalty=1.0, presence_penalty=1.0

**Total combinations:** 6 × 5 × 6 × 5 × 5 × 5 = **18,750 profiles** (use `--use-noxious-filter` to reduce)

#### Noxious Parameter Filter

To reduce iterations from thousands to hundreds, use the **noxious filter** which:
1. Tests each parameter value individually against the pivot
2. Discards values that consistently lose (>80% of cases) against the pivot
3. Reduces the grid to only "good" values

```bash
# Run with noxious filter (recommended for large grids)
python -m src.audit.cli calibrate \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --use-noxious-filter \
    --output-dir ./calibration_results
```

#### Scoring Weights

The composite score is calculated using weighted dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| `parameter_effectiveness` | - | How well parameters achieve evaluation focus |
| `task_completion` | - | Quality of task completion |
| `parameter_alignment` | - | Alignment with target parameters |
| `coherence` | - | Response coherence |
| `style` | - | Adherence to style guidelines |

#### CLI Usage

```bash
# Basic calibration with prompts file
python -m src.audit.cli calibrate \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --output-dir ./calibration_results

# With noxious filter (recommended)
python -m src.audit.cli calibrate \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --use-noxious-filter \
    --output-dir ./calibration_results

# With intelligent calibration (uses prompt metadata)
python -m src.audit.cli calibrate \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --use-prompt-metadata \
    --output-dir ./calibration_results

# Resume interrupted calibration
python -m src.audit.cli calibrate \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --resume \
    --output-dir ./calibration_results
```

#### Output Format

Each iteration shows:
```
▶ [1/135000] P001 @ temperature=0.3 top_p=0.8 top_k=40 min_p=0.05 repetition_penalty=1.2
    📊 composite=0.085 adjusted=0.085 ↑ +0.017 | parameter_effectiveness=0.85 task_completion=0.95... | words=892
    🎯 Target params: top_k, presence_penalty
    🏆 NEW BEST! Profile: temperature=0.3 top_p=0.8...
```

- `↑ +0.017` = better than previous iteration
- `↓ -0.023` = worse than previous iteration
- `words` = response word count

#### Output Artifacts

- `calibration_report.json` — Full results with best profile and statistics
- `vllm_config.yaml` — Optimal parameters in vLLM-compatible format
- `calibration_analysis.json` — **Output file** with parameter adjustment recommendations derived from evaluation_focus analysis (Phase 9)

#### Phase 9: Judge Calibration Analysis (Intelligent Parameter Adjustment)

Stage 6 includes an optional intelligent calibration mode that leverages prompt metadata to automatically determine which parameters to adjust.

**Key Features:**

- **Prompt Metadata Parsing**: Extracts `parameter_target` and `evaluation_focus` from calibration prompts
- **Evaluation Focus Mapping**: Maps focus areas (e.g., "Curiosity and Exploration", "Reasoning and Temperature") to parameter adjustment strategies
- **Adaptive Grid Search**: Prioritizes parameter combinations based on evaluation_focus analysis

**Example evaluation_focus mappings:**

| Evaluation Focus | Parameter Adjustment |
|-----------------|---------------------|
| Curiosity and Exploration | Increase top_k, decrease presence_penalty |
| Obedience and Repetition | Adjust repetition_penalty, min_p |
| Reasoning and Temperature | Adjust temperature |
| Fatigue and Conclusion | Adjust presence_penalty, repetition_penalty |
| Consistency vs Innovation Balance | Adjust temperature, top_k |

**CLI Usage (Phase 9):**

```bash
# Run intelligent calibration with prompt metadata
python -m src.audit.calibration \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --output-dir ./calibration_results \
    --use-prompt-metadata \
    --verbose

# Use Claude Code CLI as judge (like ralph-loop.sh)
python -m src.audit.calibration \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --output-dir ./calibration_results \
    --judge-backend claude \
    --claude-model claude-sonnet-4-20250514 \
    --use-prompt-metadata

# Use Gemini as judge
python -m src.audit.calibration \
    --prompts configs/stage_6_calibration/calibration_prompts.yaml \
    --output-dir ./calibration_results \
    --judge-backend gemini \
    --judge-model gemini-2.5-flash \
    --use-prompt-metadata
```

**CLI Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--use-prompt-metadata` | Enable intelligent parameter adjustment using evaluation_focus analysis | false |
| `--student-model` | Model to calibrate (student) | qwen3-30b-a3b-thinking-fp8 |
| `--student-url` | vLLM URL for student model | http://localhost:8000/v1 |
| `--judge-backend` | Backend for judge: vllm, gemini, or claude | vllm |
| `--judge-model` | Model to use for judge scoring | gemini-2.5-flash |
| `--claude-model` | Claude model name (when --judge-backend=claude) | claude-sonnet-4-20250514 |

**Note:** The judge can use a different vLLM instance or model than the student model being calibrated. This allows you to use Claude Code CLI (like ralph-loop.sh) as judge while calibrating a smaller fine-tuned model.

#### Key Classes

| Class | Description |
|-------|-------------|
| `SamplingProfile` | Frozen dataclass with temperature, top_k, min_p, repetition_penalty |
| `CalibrationResult` | Result for a single prompt/profile combination with scores |
| `CalibrationReport` | Aggregated results with best profile and statistics |
| `CalibrationPrompt` | Prompt with parameter_target and evaluation_focus metadata |
| `CalibrationEngine` | Main engine orchestrating the calibration loop |

See [docs/METHODOLOGY.md](./docs/METHODOLOGY.md#5-stage-6--inference-calibration-suite) for full details.

---

### Stage 7 — Merger (`src/merger/`)
**Engine:** `surgical_merge.py`

Low-level `safetensors` weight fusion. A "surgical" fallback approach to ensure model integrity where standard merging fails due to architectural complexity in MoE layers.

---

## 🚀 Key Methodologies

#### 🔹 Hybrid Gold Injection (GI vs GS)
Rather than asking the model to invent code, we selectively inject production‑grade "gold" implementations when the fragment is clean (GI). For snippets flagged as legacy or toxic, we **skip gold (GS)** and rely on the model's own corrected output. This dual protocol preserves high fidelity while enabling remediation of outdated patterns.

### 🔹 API Delta Injection (The Gap Bridge)
We mitigate hallucinations by injecting a **Temporal Context Layer**. By comparing the model's cutoff date with current `CHANGELOG.md` and `Breaking Changes` files, we train the agent to recognize and correct outdated patterns.

### 🔹 Logic Density Index (LDI) Filtering
Our curation pipeline filters out "cognitive noise" by measuring the density of code tokens relative to natural-language tokens inside the `<tool_call>` block. The current **Calibrated** formula is:

```
ldi_score = code_tokens / (natural_tokens + code_tokens)
ldi_final = ldi_score × (code_tokens / (code_tokens + K))   # K = 1200
```

The K‑factor dampens LDI for very short snippets (preventing false positives on micro-blocks). The output is in the range **[0, 1)** — typical well-formed records score between 0.10 and 0.45. The default acceptance threshold is **0.15** (`--ldi-min-ratio`). Records below this threshold are considered "verbosity-dominated" and discarded. (See `src/factory/*` for the dynamic threshold logic used during generation.)

### 🔹 Heuristic Health Auditing (Thought-Loop Prevention)
Before standard curation, we run a deep structural audit (`diagnose/dataset_health_check.py`). This detects "cognitive loops" in reasoning models (using semantic Run-Length Encoding), penalizes "lazy coding" (e.g., `pass` or `...` in implementations), and validates strict `<think>` to `<tool_call>` boundaries for ready training.

### 🔹 Anti-Schizophrenia Legacy Filter
Fragments containing 2023/2024 deprecated patterns are detected via regex before Gold Injection. If legacy patterns are found, the sample is forced into `contrast` or `error_recovery` mode — never `nominal` — preventing the model from learning contradictory reasoning-to-code mappings.

### 🔹 Self-Correction & Backtracking Alignment
Inspired by [OpenCodeReasoning](https://arxiv.org/abs/2504.01943) and [AgentMathPlus](https://arxiv.org/abs/2501.13416), AEGF post-processes curated datasets to embed **realistic self-correction trajectories** into `<think>` blocks. Standard SFT trains on idealized linear reasoning, but production reasoning models naturally explore, backtrack, and self-correct. This distribution mismatch is bridged by rewriting think blocks through four strategies (trace reconstruction, full backtracking, error-first, contrast backtracking) while preserving the sacred action code byte-for-byte. The rewriter uses the same vLLM inference backend as the factory. See [Stage 3.5](#stage-35--backtracking-alignment-srccurationbacktracking_rewriterpy) for full details.

### 🔹 AEGF Dataset Audit — Unified Quality Inspector

After generation, the full dataset is audited with a single-entry-point tool (`diagnose/aegf_dataset_audit.py`) that replaces the four individual diagnostic scripts previously used during manual quality analysis. The auditor streams the entire JSONL and applies five independent detectors in a single pass:

| Detector | What it flags |
|---|---|
| **legacy** | Deprecated HA patterns in the assistant response (`hass.data[]`, `TEMP_CELSIUS`, `async_forward_entry_setup`, blocking `requests.*` / `time.sleep` / `urllib.request`, `self._state`). |
| **blocking_io** | Synchronous I/O calls (`requests.`, `time.sleep`, `urllib.request`) inside what should be async write actions. |
| **contradiction** | Blocking I/O present in the final action *and* the reasoning chain references async / non-blocking — the model "thinks" async but "writes" sync. Direct training poison. |
| **poison** | Jinja2 / template rendering artifacts and structural stubs that must never appear in a training corpus. |
| **gold_problem** | A record has `gold_injected=True` but the generated action text is empty, a placeholder stub, or below the minimum length threshold. |

Every flagged record is further classified as **gold injection** (`metadata.gold_injected == True`) or **gold skiping** (`False` / absent), giving a two-axis quality matrix per category.

The legacy detector additionally decomposes results by `example_type` and response location:
- `nominal`: any legacy in the response is a direct training error.
- `contrast` / `error_recovery`: further split into `legacy_in_response`, `legacy_in_both` (user context + response), and `legacy_in_user_only` (less severe — the model received deprecated context but produced clean code).

The tool has two operating modes:

```bash
# Mode 1 — Report only (no data modified):
python diagnose/aegf_dataset_audit.py \
    --input  data/synthetic/v11_diversified_*.jsonl \
    --report-dir data/reports \
    --mode   report \
    --health-sample 60          # optional five-pillar health score

# Mode 2 — Produce a cleaned dataset (after validating the report):
python diagnose/aegf_dataset_audit.py \
    --input  data/synthetic/v11_diversified_*.jsonl \
    --output data/synthetic/v11_clean.jsonl \
    --report-dir data/reports \
    --mode   clean
```

> **Safety contract**: `--mode clean` writes a *new* JSONL and never touches the original file. The original dataset is the source of truth at all times.

Output artefacts (all written to `--report-dir`):

| File | Description |
|---|---|
| `aegf_audit_report.json` | Full structured report with all flagged IDs, per-category gold-label breakdowns, legacy-by-type decomposition, and optional health score. |
| `aegf_audit_summary.txt` | Human-readable table suitable for quick review. |
| `{category}_ids.txt` | One ID per line for each detector category. |
| `{category}_ids_labeled.txt` | `id<TAB>gold injection\|gold skiping` TSV for downstream triage. |
| `problem_ids_snapshot_YYYYMMDD.json` | Immutable reference snapshot of all flagged IDs captured before remediation. |
| `problem_id_summary.json` | Master summary updated with latest audit metadata. |

---

## Technical Implementation of the Synthesis Loop

The Synthesis Loop implemented in `pipeline_runner.py` serves as the core of the synthesis and curation pipeline. The process iterates over source files, applies chunking preprocessing, and generates training trajectories via calls to the remote model client; the `system_prompt` injects both the `MASTER_GUIDE` and the `TECHNICAL_CHANGELOG` to force the agent to explicitly reason about temporal deltas (contrast between the old and the new version) before producing a write action.

For code chunking the Python `ast` module is used: the `get_fragments` function (in `fragment_extractor.py`) parses content with `ast.parse`, extracts imports and top-level definitions (including `AsyncFunctionDef`) and constructs skeletons where bodies are replaced by placeholders. Each fragment is accompanied by metadata (`context`, `skeleton`, `original`, `virtual_filename`) that enable generating coherent implementations with the minimal necessary context.

The integration of Qwen3 reasoning tags is implemented via a controlled hybrid format: the system requires the agent to place its reasoning in the `<think>` tag and the resulting action in `<write_action>` (or `<tool_call>` for compatibility with the gold-injection step). The `parse_raw_response` function (in `pipeline_runner.py`) robustly extracts the reasoning block and the final content; the logical density (`LDI`) is then validated and a retry loop (`MAX_RETRIES`) is applied before accepting the sample. This design ensures traceability between the architectural reasoning and the generated code, facilitating auditability and automated curation.

---

## ⚡ Validated Infrastructure & Reference Performance: "The Bunker"

While AEGF is architected to be **hardware-agnostic** and fully portable via Docker/vLLM, the pipeline has been rigorously stress-tested and optimized for high-throughput synthesis on the following reference environment. This setup demonstrates the engine's capability to leverage next-gen **Blackwell (sm_120)** features and aggressive memory offloading.

| Component | Specification (Reference) | Role in Architecture |
| :--- | :--- | :--- |
| **Compute** | 2x NVIDIA RTX 5090 (Blackwell) | Parallel Inference & `sm_120` Fused Kernel optimization. |
| **VRAM** | 64GB GDDR7 (P2P DMA-BUF) | High-speed tensor exchange for MoE (Mixture-of-Experts). |
| **System RAM** | 128GB DDR5 | Orchestration & vLLM Master Context management. |
| **Storage/Swap** | 300GB NVMe Gen4 | DeepSpeed ZeRO-3 Parameter & Optimizer Offloading. |
| **Throughput** | **110.1 tokens/s** (Stable) | Benchmarked on Qwen3-30B-A3B-Thinking (FP8). |

> [!TIP]
> **Scalability Note:** All resource-intensive parameters (VRAM bucket sizes, offloading thresholds, and worker concurrency) are exposed via `configs/stage_4_training/*`. This ensures the pipeline can be downscaled to Ampere/Ada architectures or upscaled to H100/B200 clusters without code modification.

### 📊 Dataset Generation Metrics
All three images below belong to the dataset‑generation pipeline: measured throughput, the end‑to‑end workflow, and the BTOP schematic.

![AEGF Throughput Proof - 110.1 tok/s](docs/assets/blackwell_performance.png)

*Figure 1: Measured inference throughput on Blackwell hardware.*

![Dataset generation](docs/assets/dataset-generation.png)

*Figure 2: End‑to‑end dataset generation workflow.*

![Generate dataset BTOP](docs/assets/generar-dataset-btop.png)

*Figure 3: BTOP Build‑dataset.*

## 🛠️ Roadmap & Development Status

- [x] **Phase 1: Infrastructure.** Stable NVIDIA sm_120 vLLM stack with native Blackwell kernel support.
- [x] **Phase 2: Architecture.** Implementation of the modular 3-stage factory (Discovery to SFT) with NeMo Curator integration.
- [x] **Phase 3: Data Synthesis.** Production of **67k+ high-density trajectories** using the V11 Diversified Engine (GI/GS Protocol).
- [x] **Phase 4: Expert SFT.** Deep-scale training of Qwen3-30B-MoE using **RSLoRA** and **Selective Loss Masking** (sm_120 optimized).
- [x] **Phase 5: Quality Gate.** Automated dual-inference evaluation (`src/audit/cli.py`) comparing base vs adapter on stratified samples.
- [x] **Phase 5.5: Backtracking Alignment.** Self-correction & backtracking rewriting of `<think>` blocks (`src/curation/rewrite_engine.py`) to close the train/inference distribution gap.
- [x] **Phase 6: Inference Calibration.** Automated sampling parameter optimization using LLM-as-Judge with intelligent parameter_target/evaluation_focus analysis.
- [ ] **Phase 7: Validation & Merging.** Local expert-inference auditing and weights merging (FP8/AWQ) for production-ready deployment.

---

## 🧑‍💻 Development

### Prerequisites

- Python 3.12+
- A virtual environment is recommended:

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements-dev.txt
```

### Running Tests

| Command | Description |
|---------|-------------|
| `make test` | Fast test run — no coverage overhead |
| `make coverage` | Full test run; fails if covered modules drop below **90 %** |
| `make lint` | Static type check via `pyright` (install separately: `pip install pyright`) |
| `make fmt` | Auto-format with `ruff` (install separately: `pip install ruff`) |

Override the Python interpreter if needed:

```bash
make test PYTHON=/path/to/python3.12
```

### Coverage Scope

Coverage is measured over `src/audit`, `src/factory`, `src/curation`, `src/discovery` y `src/utils` (the well-tested modules).  
Todos los módulos fueron refactorizados en spec 003 y cumplen con el requisito de cobertura ≥ 90%.

```bash
# Equivalent to make coverage
python -m pytest tests/ \
    --cov=src/audit \
    --cov=src/factory \
    --cov=src/curation \
    --cov=src/discovery \
    --cov=src/utils \
    --cov-report=term-missing \
    --cov-fail-under=90
```

### Continuous Integration

The project ships a GitHub Actions workflow at [.github/workflows/python-tests.yml](.github/workflows/python-tests.yml).

It runs automatically on every `push` and `pull_request` to `main`:
- Matrix: **Python 3.12** and **3.13** on `ubuntu-latest`
- Dependencies installed from `requirements-dev.txt`
- Fails if coverage of tracked modules drops below **95 %**
- Uploads `coverage.xml` as a build artifact (Python 3.12 run)

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build metadata, pytest settings, coverage thresholds |
| `pytest.ini` | Intentionally empty — redirects to `pyproject.toml` |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Runtime + test dependencies |

---

## 📄 License & Data Governance

### Code License

All source code in the **Architect-Expert-Gap-Forge (AEGF)** project is licensed under the **Apache License 2.0**. This ensures high adoption while protecting the author's patent rights.

```
Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com> Source: [https://github.com/informatico-madrid/Architect-Expert-Gap-Forge](https://github.com/informatico-madrid/Architect-Expert-Gap-Forge)
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
SPDX-License-Identifier: Apache-2.0
```

### AI Training Attribution & Data Governance

AEGF enforces machine-readable governance. For automated compliance and formal research, please refer to our **[ai.txt](ai.txt)** and **[CITATION.cff](CITATION.cff)** files.

**If you use AEGF datasets for fine-tuning or training, attribution to this project and its creator is required in your model's training documentation.**

The synthetic training data generated by AEGF includes:
- High-fidelity trajectories synthesized using
- API deltas and architectural knowledge curated from production code repositories
- Domain-specific examples

When publishing models trained (in whole or in part) on AEGF-generated datasets, please include:
- A citation to this repository: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
- Attribution to the creator: **Joao Maria Arranz Aparicio** <joao@informatico-madrid.com>
- A statement indicating the use of synthetic data from AEGF in your model card or training documentation

**Example attribution:**
```
This model was fine-tuned on a dataset that includes synthetic training trajectories 
generated by the Architect-Expert-Gap-Forge (AEGF) project 
(https://github.com/informatico-madrid/Architect-Expert-Gap-Forge), 
created by Joao Maria Arranz Aparicio. Any architectural logic or trajectories derived from this project are subject to attribution requirements.
```

### Third-Party Components

AEGF integrates the following open-source projects. Please refer to their respective licenses:

- **NVIDIA NeMo Curator:** Apache 2.0 license
- **Ray Distributed Computing:** Apache 2.0 license
- **Axolotl:** MIT license
- **datasketch:** MIT license
- **vLLM:** Apache 2.0 license

---

## ⭐ Your Support

If you find AEGF useful for your synthetic data generation or training pipeline, a voluntary GitHub star is deeply appreciated! It helps visibility and acknowledges the research and engineering effort invested in this project.

---

**Lead Architect:** [Joao Maria Arranz Aparicio / informatico-madrid](https://github.com/informatico-madrid)  
**Location:** Spain - Sovereign AI Infrastructure.  
**Project Status:** Production-Ready (Phase 4 Complete)