---
name: gito-review-with-spec
description: Run Gito code review WITH SPEC CONTEXT. Adds context files to .gito/config.toml to reduce false positives. Uses bmad-review-adversarial-general to classify each Gito issue as REAL or FALSE_POSITIVE. Invokable via: gito review, review code, /gito, /gito-review, quality gate.
---

# Gito Review With Spec Context

**IMPORTANT: The context mechanism differs between `gito review` and `gito ask`**

## When to Use

- Running Gito review where you want accurate findings
- Quality gates for feature development
- Any code review where spec context helps distinguish real bugs from intentional patterns

**Trigger phrases**: gito review, review code, /gito, /gito-review, quality gate

## When NOT to Use

- Quick syntax checks (use ruff/pyright directly)
- Just reading code (not reviewing)
- Already have perfect context (context.md is already set up in .gito/)

---

## How Gito Accepts Context

### For `gito review` (code review):
**Context is added via `.gito/config.toml`**:

```toml
# In .gito/config.toml
aux_files = [".gito/context.md"]
```

### For `gito ask` (question answering):
**Context can be added via CLI flag OR config.toml**:

```bash
# Via CLI (ask command only)
gito ask "Why is this function async?" --aux-files .gito/context.md

# Or via config.toml (same as review)
```

### Key Discovery:
- **`gito review` does NOT have `--aux-context` or `--aux-files`** - These options do NOT exist for the review command
- **`gito ask` DOES have `--aux-files`** - This is for question-answering
- **The only way to add context to `gito review` is via `config.toml`**

---

## Workflow (For the Agent)

### Step 1: Ensure Context File Exists

Create or update `.gito/context.md` with relevant spec information:

```markdown
## SPEC CONTEXT — {feature_name}

**Branch**: {branch}
**Base**: {base_branch}
**Spec**: specs/{spec_dir}/spec.md

### Intentional Patterns (NOT bugs):
- {explanation of intentional code patterns}

### Relevant Implementation Details:
- {implementation notes relevant to the review}
```

### Step 2: Configure aux_files in config.toml

Make sure `.gito/config.toml` includes:

```toml
aux_files = [".gito/context.md"]
```

### Step 3: Run Gito Review

```bash
# Run gito review (context comes from config.toml)
.venv/bin/gito review HEAD..main --output gito-report

# Read the report
cat gito-report/code-review-report.json | jq '.issues'
```

### Step 4: Classify Issues

For each Gito issue, use your knowledge:

```bash
# For each issue, ask yourself:
# - Does the spec/task mention this pattern as intentional?
# - Is this a genuine bug or a spec-required pattern?

# Use bmad-review-adversarial-general for ambiguous cases:
# (This skill exists and can be invoked via the skill tool)
```

---

## Context Decision Framework

When deciding what context to include, use this logic:

```
IF comparing feature branch to main:
    → Full spec context from that feature's spec
    → Load tasks.md + .ralph-state.json
    
ELIF comparing hotfix (main branch changes):
    → Minimal context only
    → General Python/HA patterns
    → Focus on: runtime errors, security, breaking changes
    
ELIF comparing cross-spec files:
    → Partial context from each relevant spec
    → Only load sections that mention changed files
    
ELIF no spec applies:
    → No spec context
    → Gito uses general Python/HA knowledge
```

### Decision Examples

#### Example 1: Feature Branch Review
```
User: /gito-review HEAD..main
Agent knows: We're in feature-m403-dynamic-soc-capping branch
Decision: LOAD FULL SPEC CONTEXT
→ Load specs/m403-dynamic-soc-capping/tasks.md
→ Context says: "BatteryCapacity has mutable _soh_value for SOH caching - this is intentional"
→ Gito won't report this as a bug
```

#### Example 2: Hotfix Review
```
User: /gito-review HEAD..main (on main branch)
Agent knows: We're reviewing a hotfix on main
Decision: MINIMAL CONTEXT
→ Don't load any spec
→ Only apply general Python/HA best practices
→ Focus on: runtime errors, security, breaking changes
```

#### Example 3: Cross-Spec Review
```
User: /gito-review commit_a..commit_b
Agent knows: Files changed are calculations.py AND sensor.py
            These are from different specs
Decision: PARTIAL CONTEXT
→ Load specs/m403-dynamic-soc-capping/tasks.md (for calculations.py)
→ Load specs/m4-sensor-refactor/tasks.md (for sensor.py)
→ Only the sections mentioning these files
```

---

## What to Include in Context

Based on what you know about the comparison:

1. **Spec name and phase** - so Gito knows what feature
2. **Intentional patterns** - what looks like a bug but isn't
3. **Relevant implementation notes** - why code is structured a certain way
4. **Current task focus** - what the current sprint/phase is about

## What NOT to Include

1. **Unrelated spec sections** - don't dump the entire tasks.md
2. **Outdated context** - if the spec has moved on, only use current phase
3. **Generic documentation** - specs/ directory has too much noise

---

## Output

checkpoint.json with your classification:

```json
{
  "gito_review": {
    "comparison": "HEAD..main",
    "context_used": "full|partial|minimal|none",
    "spec": "m403-dynamic-soc-capping or none",
    "issues": [
      {
        "id": 9,
        "title": "Set.get() called on set",
        "classification": "REAL",
        "reasoning": "This is a genuine AttributeError - sets don't have .get()"
      },
      {
        "id": 15,
        "title": "MagicMock instead of AsyncMock",
        "classification": "FALSE_POSITIVE", 
        "reasoning": "async_set in HA is fire-and-forget, MagicMock is correct"
      }
    ],
    "total_real": 19,
    "total_false_positive": 4
  }
}
```

---

## Integration with .gito/config.toml

The correct way to add context to `gito review`:

```toml
# .gito/config.toml
aux_files = [".gito/context.md"]

# Keep exclude_files as needed
exclude_files = [
    "*.lock",
    "node_modules/**",
    "specs/**",
    # etc.
]
```

### Important: `bmad-consensus-party` does NOT exist

Use `bmad-review-adversarial-general` instead for classifying issues as REAL or FALSE_POSITIVE.