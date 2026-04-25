# Design: Prompt Externalization

## Overview

Extract prompts from 7 source locations across `src/` and `configs/` into `.example.yaml` template files with English translations. No production code changes. Format conversion handles 3 source formats: dict-with-templates, list-of-objects, and plain-text.

## Architecture

```
Source Files                          Output Files
─────────────────                     ──────────────
trajectory_generator.py ──────────►   prompts_trajectory.example.yaml
hard_query_builder.py ────────────►   prompts_hard_query.example.yaml
eval_prompts.yaml (stage_5) ─────►    prompts_judge.example.yaml
calibration_prompts.yaml (stage_6) ─► prompts_calibration.example.yaml
prompts_taxonomy.yaml ────────────►   prompts_taxonomy.example.yaml
frontend_taxonomy_prompts.py ─────►   prompts_frontend.example.yaml
backtracking_system.txt ──────────►   prompts_backtracking.example.yaml
reconstruction_system.txt ────────►   (same file, 2nd prompt)
```

## Components

### 1. Trajectory Prompts Extractor
**Source**: `src/factory/trajectory_generator.py` — `_default_templates()` method
**Output**: `src/factory/prompts_trajectory.example.yaml`
**Prompts**: 6 turn templates (observation, reasoning, action, error, correct, verify)

**Conversion strategy**: Turn templates don't have system/user semantics. Map each template to `prompts.<turn_type>.system` with an empty user field. The template string (e.g., `"Observacion: {context}\nPregunta: {question}"`) becomes the system content.

**Keys** (6):
- `prompts.observation.system` = `"Observation: {context}\nQuestion: {question}"`
- `prompts.reasoning.system` = `"Reasoning: {reasoning}"`
- `prompts.action.system` = `"Action: Executing {tool_name}"`
- `prompts.error.system` = `"Error: {error_description}"`
- `prompts.correct.system` = `"Correction: {corrective_action}"`
- `prompts.verify.system` = `"Verification: {verification_result}"`

### 2. Hard Query Prompts Extractor
**Source**: `src/factory/hard_query_builder.py` — `_default_templates()` method
**Output**: `src/factory/prompts_hard_query.example.yaml`
**Prompts**: 1 template (problem_focused) + forbidden_terms list

**Conversion strategy**: `forbidden_terms` is a data list, not a prompt template. Store it at `prompts.forbidden_terms` as a YAML list. The `problem_focused` template maps to `prompts.problem_focused.system` with empty user.

**Keys** (2):
- `prompts.forbidden_terms` = list of 5 terms (Spanish terms remain as-is since they are domain-specific forbidden strings, not prompts)
- `prompts.problem_focused.system` = `"Objective: {objective}\n\nContext: {context}"`

### 3. Judge Prompts Extractor
**Source**: `configs/stage_5_evaluation/eval_prompts.yaml`
**Output**: `src/audit/prompts_judge.example.yaml`
**Prompts**: 4 groups (professor_exam, professor_judge, gap_analysis, professor_judge_calibration)

**Conversion strategy**: Source already uses `key: system: | / user: |` format. Direct copy with translation. Two groups (professor_exam, professor_judge, professor_judge_calibration) are already English — verify fidelity. One group (gap_analysis) is Spanish — translate.

**Keys** (4): Direct copy of source keys.

### 4. Calibration Prompts Extractor
**Source**: `configs/stage_6_calibration/calibration_prompts.yaml` — list-of-objects format
**Output**: `src/audit/prompts_calibration.example.yaml`
**Prompts**: 6 active prompts (ids 001-006)

**Conversion strategy**: Source format is `[{id, question, type, parameter_target, evaluation_focus}]`. Convert to dict: each prompt gets `prompts.<id>.system` = parameter_target as a system directive, `prompts.<id>.user` = translated question. The `type`, `parameter_target`, and `evaluation_focus` fields are metadata — store as `prompts.<id>.metadata` in the YAML to preserve information losslessly (per FR-4).

**Keys** (6):
- `prompts.calibration_prompt_001.system` = parameter_target context
- `prompts.calibration_prompt_001.user` = translated question
- ... same pattern for 002-006

### 5. Taxonomy Prompts Extractor
**Source**: `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml`
**Output**: `src/factory/prompts_taxonomy.example.yaml`
**Prompts**: ~21 prompt groups (actual templates with system/user or plain content)

**Conversion strategy**: Source has deeply nested keys (`prompts.system.python.base`, `prompts.system.jinja.nominal_suffix`, etc.). Flatten to use the dotted key path as the YAML key.

**Excluded from output** (per spec scope — these are data/definitions, not prompts):
- `version`, `ha_error_templates`, `legacy_2023_patterns`, `jinja_ha_error_templates`, `jinja_legacy_2023_patterns` (data objects)
- `tools_definition` (tool definitions, not prompts)

**Included prompt groups** (21 total):
- system.python: base, nominal_suffix, contrast_suffix, error_recovery_suffix, blueprint_context, governance_context (6)
- system.jinja: base, nominal_suffix, contrast_suffix, error_recovery_suffix (4)
- system.theory (1)
- user.python: nominal_easy, nominal_medium, nominal_hard_anchor, contrast, error_recovery, functional_unit (6)
- user.jinja: nominal_easy, nominal_medium, nominal_hard_anchor, contrast, error_recovery (5)

**Key mapping**: Dotted paths become flattened keys:
- `prompts.system_python_base.system` = <content>
- `prompts.user_python_nominal_easy.user` = <content>

Note: Each key maps to either `.system` or `.user` based on its parent: `system.*` -> `.system`, `user.*` -> `.user`. For `system.theory` (flat key), use `.system`.

**Consolidation note**: `agentic_taxonomy.yaml` is 99% identical. Only note differences in a comment header. `hacs_expert/prompts_taxonomy.yaml` is byte-identical (verified).

### 6. Frontend Prompts Extractor
**Source**: `src/export/frontend_taxonomy_prompts.py` — 4 system + 1 user prompt strings
**Output**: `src/export/prompts_frontend.example.yaml`
**Prompts**: 4 system + 1 user (5 total)
**Dead code annotation**: File header YAML comment noting source is never imported

**Conversion strategy**: Each constant maps directly:
- `prompts.component_system.system` = FRONTEND_COMPONENT_SYSTEM_PROMPT
- `prompts.lit_component_system.system` = LIT_COMPONENT_SYSTEM_PROMPT
- `prompts.i18n_key_system.system` = I18N_KEY_SYSTEM_PROMPT
- `prompts.service_call_system.system` = SERVICE_CALL_SYSTEM_PROMPT
- `prompts.extract_component.user` = EXTRACT_COMPONENT_USER_PROMPT

All source content is English.

### 7. Backtracking Prompts Extractor
**Sources**: `configs/prompts/backtracking_system.txt` + `configs/prompts/reconstruction_system.txt`
**Output**: `src/curation/prompts_backtracking.example.yaml`
**Prompts**: 2 system prompts

**Conversion strategy**: Plain text -> structured YAML. Each file maps to a single `prompts.<name>.system` entry. No user component exists — use empty string.

**Keys** (2):
- `prompts.backtracking_system.system` = full file content translated
- `prompts.reconstruction_system.system` = full file content translated

## Format Conversion Strategy

| Source Format | Example Source | Conversion |
|---|---|---|
| dict-with-templates (Python _default_templates()) | trajectory_generator.py, hard_query_builder.py | Extract template strings, assign to system/user |
| dict-with-system-user (YAML) | eval_prompts.yaml | Direct copy, translate in-place |
| list-of-objects (YAML) | calibration_prompts.yaml | Flatten to dict, metadata preserved in `metadata` field |
| plain text (.txt) | backtracking_system.txt | Wrap in `prompts.<name>.system` |

## Translation Guidelines

| Source Language | Approach | Examples |
|---|---|---|
| Spanish | Translate to English, preserve placeholders ({var}, $var) | `Razonamiento: {reasoning}` -> `Reasoning: {reasoning}` |
| English | Verify fidelity, minor rephrasing only | Keep as-is unless wording is ambiguous |
| Mixed EN/ES (eval_prompts.yaml) | Translate ES portions, keep EN portions | gap_analysis: fully ES -> fully EN; professor_exam: keep EN |
| Domain terms | Keep untranslated (technical terms) | `async_setup_entry`, `DataUpdateCoordinator`, `ConfigEntryNotReady` |

## Technical Decisions

| Decision | Options | Choice | Rationale |
|---|---|---|---|
| Schema mapping for non-system/user sources | Force into system/user | Adapt to preserve semantics | Trajectory turns are not system/user pairs — use `.system` with empty `.user` |
| Metadata preservation (calibration) | Discard non-prompt fields | Store in `prompts.<id>.metadata` | FR-4: preserve all original content; `type`/`parameter_target` are useful metadata |
| Taxonomy nesting | Flatten fully vs preserve hierarchy | Flatten dotted paths to single keys | Simpler for DSPy to reference; nested dicts add no value for this use case |
| Dead code annotation | YAML comment vs metadata section | YAML comment in file header | FR-7: file-level annotation; YAML comments are the standard way |
| Excluded taxonomy sections | Include all keys vs filter | Filter out data/definition keys | Only prompts (system/user templates, theory questions) are actual prompts |

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `src/factory/prompts_trajectory.example.yaml` | Create | 6 turn templates from trajectory_generator.py |
| `src/factory/prompts_hard_query.example.yaml` | Create | 1 template + forbidden_terms from hard_query_builder.py |
| `src/factory/prompts_taxonomy.example.yaml` | Create | ~21 prompt groups from prompts_taxonomy.yaml |
| `src/audit/prompts_judge.example.yaml` | Create | 4 judge groups from eval_prompts.yaml |
| `src/audit/prompts_calibration.example.yaml` | Create | 6 calibration prompts from calibration_prompts.yaml |
| `src/export/prompts_frontend.example.yaml` | Create | 5 prompts from frontend_taxonomy_prompts.py (dead code) |
| `src/curation/prompts_backtracking.example.yaml` | Create | 2 prompts from plain text files |

No production code modifications. No existing files changed.

## Error Handling

| Error Scenario | Handling Strategy | Impact |
|---|---|---|
| Source file missing | Error — spec depends on seed data | ESCALATE (per requirements verification contract) |
| Translation ambiguity | Preserve original + add translator note as YAML comment | Minimal — XS scope, human review handles edge cases |
| Non-prompt content in taxonomy | Exclude data sections, note in file header | By design — only prompt templates exported |

## Edge Cases

- **Calibration prompts with no explicit system prompt**: The source list has only `question` text. Use `parameter_target` as system directive context. The question becomes the user prompt.
- **Taxonomy theory templates**: `theory_question_templates` is a list-of-objects (not system/user). Flatten to `prompts.theory.question.templates` array — store as-is since it's query templates, not conversation prompts.
- **Backtracking prompts reference "HA 2026 GOVERNANCE CONTEXT"**: These prompts expect external context injection at runtime. Preserve the placeholder/reference in the translated output.
- **Hard query forbidden_terms contain Spanish phrases**: These are literal strings checked against output — keep as-is (not prompts, not translatable).

## Test Strategy

### Test Double Policy
This spec creates static YAML files. No code is written, no functions tested. Verification is file-level:

| Aspect | Verification | Method |
|---|---|---|
| YAML validity | All 7 files parse | `yaml.safe_load()` |
| English content | No Spanish text in output | `grep -P '[a-z]{3,}' ` pattern check |
| Schema compliance | All files have `prompts` top-level key | Structural check |
| Prompt count | Source count = output count | Count comparison |

### Mock Boundary
Not applicable — no code, no functions, no I/O boundaries to test.

### Fixtures & Test Data
Not applicable — source files are the "fixtures." Output is derived, not computed.

### Test Coverage Table
Not applicable — this spec produces static data files. No logic to test.

### Test File Conventions
- Test runner: pytest 9.0.2 (project root `tests/` directory)
- Test command: `python -m pytest tests/ -v`
- This spec creates no testable code — only YAML files
- Verification is done manually: `python -c "import yaml; [yaml.safe_load(open(f)) for f in files]"`

## Performance Considerations
N/A — no runtime code. Files are static templates.

## Security Considerations
- `.example.yaml` files are templates — no secrets or credentials in prompts
- Translated prompts should not re-introduce any sensitive strings from originals
- No code changes means no new attack surface

## Existing Patterns to Follow
- YAML style: `---` document separator at top, `# ──` section dividers (matching existing YAML files)
- Template placeholders: preserve `{var}` syntax (Python str.format style used in production code)
- File header: include AEGF copyright comment block (matching existing YAML convention)
- `.example.yaml` naming: signals "template, copy and customize" — never directly loaded

## Implementation Plan

1. **Create `prompts_trajectory.example.yaml`** — extract 6 turn templates from `trajectory_generator.py._default_templates()`, translate Spanish to English, flatten to `prompts.<type>.system`
2. **Create `prompts_hard_query.example.yaml`** — extract `forbidden_terms` list (keep as-is) and `problem_focused` template (translate), two keys under `prompts:`
3. **Create `prompts_judge.example.yaml`** — direct port of `eval_prompts.yaml` 4 groups, translate `gap_analysis` from Spanish, verify fidelity on English groups
4. **Create `prompts_calibration.example.yaml`** — convert 6-item list-of-objects to dict format, store `parameter_target`/`type`/`evaluation_focus` as metadata, translate questions from Spanish
5. **Create `prompts_taxonomy.example.yaml`** — flatten nested `prompts.*` keys (21 groups), exclude data/definition sections, translate all Spanish content, note `agentic_taxonomy.yaml` 99% identity in header
6. **Create `prompts_frontend.example.yaml`** — extract 5 prompt constants, add dead code header comment, content already English
7. **Create `prompts_backtracking.example.yaml`** — convert 2 plain text files to structured YAML, translate from Spanish
8. **Verify** — `yaml.safe_load()` on all 7 files, count prompt keys match source, grep for remaining Spanish (except domain terms/forbidden_terms)
