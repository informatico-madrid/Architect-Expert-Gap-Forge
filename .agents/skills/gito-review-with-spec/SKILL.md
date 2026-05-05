---
name: gito-review-with-spec
description: Run Gito code review WITH SPEC CONTEXT. The agent decides what context is relevant based on the comparison being made. Sends relevant spec context to Gito to reduce false positives. Uses bmad-consensus-party + bmad-review-adversarial-general to classify each Gito issue as REAL or FALSE_POSITIVE. Invokable via: gito review, review code, /gito, /gito-review, quality gate.
---

# Gito Review With Spec Context

**The agent decides what context to provide** based on what it knows about the comparison.

## When to Use

- Running Gito review where you want accurate findings
- Quality gates for feature development
- Any code review where spec context helps distinguish real bugs from intentional patterns

**Trigger phrases**: gito review, review code, /gito, /gito-review, quality gate

## When NOT to Use

- Quick syntax checks (use ruff/pyright directly)
- Just reading code (not reviewing)
- Already have perfect context

## How the Agent Decides Context

When you invoke this skill, **you already know**:

1. **What comparison**: `HEAD..main`, `commit_a..commit_b`, staged files, etc.
2. **What branch**: `feature-m403-*`, `hotfix/*`, `main`, etc.
3. **What changed**: The agent can see which files are different
4. **What spec applies**: You know what feature you're working on

### Decision Framework

Use this logic to decide context:

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

## Workflow (For the Agent)

### Step 1: Analyze the Comparison

Based on what you know:

```bash
# What are we comparing?
COMPARISON="${1:-HEAD..main}"

# Get changed files
git diff --name-only $COMPARISON

# What's the base branch?
git merge-base HEAD main  # or the specified base

# What's our current branch?
git branch --show-current
```

### Step 2: Determine Context Level

| Situation | Context Level | What to Load |
|-----------|---------------|--------------|
| Feature branch review | FULL | Load full tasks.md + spec.md |
| Hotfix (main changes) | MINIMAL | Only general patterns |
| Cross-spec files | PARTIAL | Load only relevant sections |
| Unknown/no spec | NONE | No spec context |

### Step 3: Build Context Block

Based on what you found:

```markdown
## SPEC CONTEXT

Feature: {spec_name}
Phase: {phase from .ralph-state.json or "unknown"}
Status: {task count and completion}

### Intentional Patterns (NOT bugs):
- {patterns from tasks.md that explain intentional code}

### Relevant Implementation Details:
- {sections from tasks.md that relate to changed files}
```

### Step 4: Run Gito with Context

```bash
# Run gito with the comparison
.venv/bin/gito review $COMPARISON --output gito-report

# Read the report
cat gito-report/code-review-report.json | jq '.issues'
```

### Step 5: Classify Issues

For each Gito issue, use your knowledge:

```bash
# For each issue, ask yourself:
# - Does the spec/task mention this pattern as intentional?
# - Is this a genuine bug or a spec-required pattern?

# Use bmad-consensus-party for ambiguous cases:
bmad-consensus-party "Is this a REAL bug or FALSE_POSITIVE?"
    --context "Issue: $issue
              File: $file:$line
              What I know: $spec_context"
```

## Context Decision Examples

### Example 1: Feature Branch Review
```
User: /gito-review HEAD..main
Agent knows: We're in feature-m403-dynamic-soc-capping branch
Decision: LOAD FULL SPEC CONTEXT
→ Load specs/m403-dynamic-soc-capping/tasks.md
→ Context says: "BatteryCapacity has mutable _soh_value for SOH caching - this is intentional"
→ Gito won't report this as a bug
```

### Example 2: Hotfix Review
```
User: /gito-review HEAD..main (on main branch)
Agent knows: We're reviewing a hotfix on main
Decision: MINIMAL CONTEXT
→ Don't load any spec
→ Only apply general Python/HA best practices
→ Focus on: runtime errors, security, breaking changes
```

### Example 3: Cross-Spec Review
```
User: /gito-review commit_a..commit_b
Agent knows: Files changed are calculations.py AND sensor.py
            These are from different specs
Decision: PARTIAL CONTEXT
→ Load specs/m403-dynamic-soc-capping/tasks.md (for calculations.py)
→ Load specs/m4-sensor-refactor/tasks.md (for sensor.py)
→ Only the sections mentioning these files
```

### Example 4: Unknown Files
```
User: /gito-review some_old_commit..another_old_commit
Agent knows: Files changed don't relate to any known spec
Decision: NO SPEC CONTEXT
→ Let Gito use general Python/HA knowledge
→ No spec context would help anyway
```

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

## BMAD Party Mode for Classification

For ambiguous issues, invoke bmad-consensus-party:

**Question**: "Is this a REAL bug or FALSE_POSITIVE given the spec context?"

**Context to provide**:
- The Gito issue description
- The file and line number
- Your spec context (what you loaded in Step 2)
- What you know about the implementation

**Agents to use**:
- Winston (Architect) - technical analysis
- Amelia (Developer) - implementation context  
- Mary (Business Analyst) - if requirements related

## Integration with Gito

For automatic context, configure `.gito/config.toml`:

```toml
# The agent provides context, not gito
# But gito can be configured to not analyze specs

exclude_files = [
    "specs/**",  # Don't analyze specs as code
]
```

Or use gito's built-in context feature:

```bash
# Agent creates context file
echo "## SPEC CONTEXT\n$CONTEXT" > /tmp/gito-context.md

# Run gito with context
gito review $COMPARISON --aux-context /tmp/gito-context.md