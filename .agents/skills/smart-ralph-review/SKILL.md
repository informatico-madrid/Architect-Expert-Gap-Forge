---
name: smart-ralph-review
user-invocable: true
description: "Use when: you want to review and validate a Smart-Ralph spec using BMAD agents and a top-tier reasoning model. The skill performs multi-layer review (adversarial, editorial, edge-case) respecting Smart-Ralph formalism and produces actionable reports before implementation. Valid for any Smart-Ralph phase (research, requirements, design, plan, execution, review). Uses BMAD party-mode consensus to prevent false positives and applies corrections via native ralph-specum commands to preserve artifact format."
applyTo: "**/*.md"
---

# smart-ralph-review

## Purpose

Review a Smart-Ralph specification using **BMAD's full intelligence stack** with a **top-tier reasoning model**. The skill:

1. **Detects issues** via multi-layer review (adversarial, editorial, edge-case, deep analysis)
2. **Validates findings** via BMAD party-mode consensus to prevent false positives
3. **Applies corrections** via native ralph-specum commands (`/ralph-specum:research`, `/ralph-specum:requirements`, etc.) to preserve artifact format
4. **Verifies corrections** via spec-reviewer rubric validation

This ensures that only **confirmed** changes are applied, and the original Smart-Ralph artifact format is always preserved because corrections go through the native ralph-specum pipeline.

## When to Use

- Pre-implementation review of any Smart-Ralph spec artifact
- Quality gate before passing to Ralph Loop execution
- Post-iteration review when spec was modified by a cheap model
- "Walk me through this spec" checkpoint review
- Any phase: research, requirements, design, plan, tasks, execution

## Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spec_path` | string | (required) | Path to spec directory (e.g., `specs/feature-x/`) or individual artifact (e.g., `specs/feature-x/plan.md`) |
| `phase` | string | auto-detect | Smart-Ralph phase: `research`, `requirements`, `design`, `tasks`, `execution`, `review` |
| `model` | string | `top-tier` | Model for deep analysis (use best reasoning model available) |
| `review_mode` | string | `full` | `full` (all layers), `adversarial` (critical only), `editorial` (prose), `edge-case` (boundaries) |
| `apply_fixes` | boolean | `false` | If `true`, automatically apply confirmed corrections via ralph-specum commands |
| `consensus_threshold` | string | `majority` | `unanimous` (all agents agree), `majority` (>50%), `any` (at least one confirms) |

## Outputs

All outputs written to `_bmad-output/reviews/smart-ralph/{spec-name}/{timestamp}/`:

| File | Description |
|------|-------------|
| `review-report.md` | Executive summary + findings by severity + consensus status |
| `annotated-spec.md` | Copy of spec with inline comments marking each finding |
| `review-checklist.json` | Structured findings with severity, consensus, suggestion |
| `corrections-applied.md` | Log of ralph-specum commands invoked and results |

## Architecture: Three-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: MULTI-LAYER REVIEW (detect issues)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ Contract     │→│ Adversarial  │→│ Editorial    │→│ Edge-Case │ │
│  │ Validation   │ │ Review       │ │ Review       │ │ Hunt      │ │
│  │ (self)       │ │ (BMAD agent) │ │ (BMAD agent) │ │ (BMAD)    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│                          ↓                                          │
│                    Raw Findings Pool                                │
├─────────────────────────────────────────────────────────────────────┤
│  PHASE 2: BMAD CONSENSUS (validate findings)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Party-Mode Roundtable: Winston + John + Amelia + Mary      │   │
│  │  Each agent votes: CONFIRM / REJECT / NEEDS_CONTEXT         │   │
│  │  Only CONFIRMED findings proceed to correction               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│                   Confirmed Findings                                │
├─────────────────────────────────────────────────────────────────────┤
│  PHASE 3: CORRECTION (apply via ralph-specum)                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  For each confirmed finding:                                │   │
│  │  1. Map finding → ralph-specum command                      │   │
│  │  2. Spawn subagent with correction context                  │   │
│  │  3. Subagent invokes /ralph-specum:{phase} with changes     │   │
│  │  4. spec-reviewer validates corrected artifact              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│                   Verified Corrections                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Multi-Layer Review

### Layer 1: Contract Validation (Fast, no agent needed)

- Parse YAML frontmatter from each spec file
- Check required fields per Smart-Ralph phase:
  - `research.md`: `spec`, `phase: research`, `created`
  - `requirements.md`: FR-* with priorities, AC-* mapped to FRs
  - `design.md`: `phase: design`, architecture sections
  - `tasks.md`: Do/Files/Done-when/Verify/Commit per task
- Check `.ralph-state.json` consistency (phase matches files present)
- Check Smart-Ralph ↔ BMAD contract: `sprint_id`, `story_id`, `executor.type`
- Report missing fields as HIGH severity

### Layer 2: Adversarial Review (BMAD Agent)

Invoke `bmad-review-adversarial-general` skill with the spec content:

- Find at least 10 issues assuming worst case
- Check for missing steps, not just wrong ones
- Trace dependencies between phases
- Verify FR/AC coverage matrix
- Check that claims are grounded (file paths, URLs, version numbers)

### Layer 3: Editorial Review (BMAD Agent)

Invoke `bmad-editorial-review-prose` and `bmad-editorial-review-structure`:

- Prose clarity: ambiguous ACs, vague "done when" criteria
- Structural organization: sections flow logically, handoffs between phases clear
- Terminology consistency across all spec files
- Cross-reference integrity (FR citations in AC, tasks cite FR and design)

### Layer 4: Edge-Case Hunt (BMAD Agent)

Invoke `bmad-review-edge-case-hunter`:

- Boundary conditions in acceptance criteria
- Security: secret leaks, credential references, unauthorized external calls
- Concurrency and race conditions in design
- Error state handling completeness
- Missing edge cases in test strategy

### Layer 5: Deep Analysis (Top-Tier Model)

Use the best reasoning model available for:

- Semantic consistency across ALL spec files (research → requirements → design → tasks)
- Logical gaps: requirements not covered by design, design not covered by tasks
- Design decision rationale: are trade-offs documented and justified?
- Feasibility: do verify commands actually work? Are file paths real?
- Hidden assumptions that could block implementation

## Phase 2: BMAD Consensus (Prevent False Positives)

**The Problem**: A single reviewer (even a top-tier model) can flag correct content as wrong. We need multiple independent perspectives to confirm.

**The Solution**: BMAD Party-Mode roundtable where each agent independently evaluates each finding, with the orchestrator acting as final arbiter when consensus is unclear.

### Consensus Protocol

1. **Present all raw findings** from Phase 1 to a party-mode roundtable of 3-4 BMAD agents:
   - **Winston** (architect): Evaluates technical accuracy and architectural implications
   - **John** (PM): Evaluates whether the finding affects project goals and requirements
   - **Amelia** (developer): Evaluates implementability and code-level accuracy
   - **Mary** (analyst): Evaluates business logic and requirement completeness

2. **Each agent votes per finding**:
   - `CONFIRM`: The finding is valid and the suggested change is necessary
   - `REJECT`: The finding is a false positive — the current content is correct
   - `NEEDS_CONTEXT`: Cannot determine — needs more information

3. **Orchestrator adjudication** (three-tier decision matrix):

   | Consensus Level | CONFIRM Count | Action | Rationale |
   |----------------|---------------|--------|-----------|
   | **Strong consensus** | All agents CONFIRM (4/4) | ✅ AUTO-APPLY | No doubt — all experts agree |
   | **Clear majority** | Majority CONFIRM (3/4 or 2/3) | ✅ AUTO-APPLY | Strong signal — dissenting opinion noted but overruled |
   | **Split / Disputed** | 50/50 split (2/4 or 1/2) | ⚖️ ORCHESTRATOR DECIDES | Arguments are weighted — the orchestrator reads each agent's reasoning and makes a judgment call based on: (a) which agent has the most domain expertise for this specific finding type, (b) quality and specificity of the reasoning provided, (c) severity of the finding (HIGH findings need more scrutiny) |
   | **Low consensus** | Minority CONFIRM (1/4) | ⏸️ ESCALATE TO USER | Too uncertain — present both sides to the user for final decision |
   | **No consensus** | 0 CONFIRM (all REJECT) | ❌ AUTO-REJECT | Clear false positive — all agents agree the finding is wrong |

4. **Orchestrator Decision Criteria** (for disputed findings):

   When the orchestrator must break a tie, evaluate:

   a. **Domain expertise weighting**: For a security finding, Amelia's vote (implementation expert) may outweigh John's (PM). For a requirements ambiguity, John's vote carries more weight. Weight by relevance:
      - Technical/architectural findings → Winston (2x) + Amelia (1.5x)
      - Requirements/scope findings → John (2x) + Mary (1.5x)
      - Implementation feasibility → Amelia (2x) + Winston (1.5x)
      - Business logic/completeness → Mary (2x) + John (1.5x)

   b. **Reasoning quality**: An agent that provides specific line references, code examples, or concrete evidence has a stronger argument than one that gives a vague opinion.

   c. **Severity modifier**: For HIGH severity findings, the orchestrator should be more conservative (lean toward applying the fix to avoid shipping a critical bug). For LOW severity, lean toward rejecting to minimize unnecessary changes.

   d. **Orchestrator's own analysis**: The orchestrator (using the top-tier model) may independently verify the finding by reading the cited lines and forming its own judgment.

5. **Output**: Each finding gets a final status:
   - `CONFIRMED` → proceeds to Phase 3 (correction)
   - `REJECTED` → logged with rejection reason, not applied
   - `DISPUTED-CONFIRMED` → orchestrator decided to apply (with reasoning documented)
   - `DISPUTED-REJECTED` → orchestrator decided to reject (with reasoning documented)
   - `ESCALATED` → presented to user for final decision

### Consensus Prompt Template

For each finding, each agent receives:

```
## Finding to Evaluate

**ID**: SR-001
**Severity**: HIGH
**Layer**: adversarial
**File**: requirements.md
**Location**: Line 42, FR-003
**Description**: FR-003 states "circuit breaker threshold ≥ 0.2" but design.md
  line 156 uses "circuit breaker threshold > 0.2" (≥ vs >). This changes
  behavior when exactly 20% fail.
**Suggested Fix**: Align to ≥ in both files (research.md justifies inclusive bound).

## Your Task
As {agent_name} ({role}), evaluate:
1. Is this finding factually correct? (verify the cited lines exist and say what's claimed)
2. Is the suggested fix appropriate? (would it improve the spec without introducing new issues?)
3. Could this be a false positive? (is there a valid reason for the current state?)

Vote: CONFIRM / REJECT / NEEDS_CONTEXT
Reasoning: [1-3 sentences — be specific, cite evidence if possible]
```

### Orchestrator Adjudication Template

When the orchestrator must decide on a disputed finding:

```
## Orchestrator Adjudication: SR-001

### Agent Votes:
- Winston (architect): CONFIRM — "The ≥ vs > difference changes edge case behavior"
- John (PM): REJECT — "Both interpretations are acceptable for MVP"
- Amelia (developer): CONFIRM — "Off-by-one error will cause flaky tests"
- Mary (analyst): NEEDS_CONTEXT

### Domain Weighting:
- This is a technical/implementation finding → Winston (2x) + Amelia (1.5x)
- Weighted CONFIRM: 2.0 + 1.5 = 3.5 | Weighted REJECT: 1.0 | NEEDS_CONTEXT: 0

### Reasoning Quality:
- Winston: Specific (cites edge case behavior) — STRONG
- John: Vague ("acceptable for MVP") — WEAK
- Amelia: Specific (cites flaky tests) — STRONG

### Severity Modifier: HIGH → lean toward applying fix

### Decision: CONFIRMED
The weighted expert opinion and specific reasoning from Winston and Amelia
outweigh John's vague objection. The HIGH severity also favors applying the fix.
Applying correction via /ralph-specum:requirements.
```

## Phase 3: Correction via ralph-specum Commands

**Key Principle**: Never modify spec files directly. Always use the native ralph-specum commands so the artifact format is preserved automatically.

### Command Mapping

| Artifact | ralph-specum Command | Subagent Type |
|----------|---------------------|---------------|
| `research.md` | `/ralph-specum:research {spec} --quick` | `research-analyst` |
| `requirements.md` | `/ralph-specum:requirements {spec} --quick` | `product-manager` |
| `design.md` | `/ralph-specum:design {spec} --quick` | `architect-reviewer` |
| `tasks.md` | `/ralph-specum:tasks {spec} --quick` | `task-planner` |

### Correction Protocol

For each confirmed finding:

1. **Group findings by target artifact** (all research.md findings together, etc.)

2. **Build correction context** for the subagent:
   ```
   You are correcting {artifact} for spec {spec-name}.
   
   The following issues were found and CONFIRMED by BMAD consensus review.
   Apply ONLY these specific corrections. Do NOT change anything else.
   
   ## Confirmed Corrections:
   1. [SR-001] Line 42: Change "threshold > 0.2" to "threshold ≥ 0.2" 
      (align with research.md justification)
   2. [SR-005] Line 89: Add missing AC-3.4 for FR-003 edge case
      ...
   
   ## Important:
   - Preserve ALL existing content that is not explicitly targeted
   - Maintain the exact Smart-Ralph format (frontmatter, sections, FR/AC IDs)
   - Only modify what is specified in the corrections above
   ```

3. **Spawn subagent** that invokes the appropriate ralph-specum command with the correction context. The subagent uses `--quick` mode to skip interviews and go directly to artifact generation with the provided corrections.

4. **Post-correction validation**: After the subagent completes, invoke `spec-reviewer` to validate the corrected artifact against the appropriate rubric (research rubric, requirements rubric, etc.).

5. **If REVIEW_FAIL**: Re-invoke the subagent with the reviewer's feedback (max 2 retries). If still fails after 2 retries, log warning and keep original.

6. **If REVIEW_PASS**: Accept the correction, log to `corrections-applied.md`.

### Correction Safety Guarantees

- **Scope limiting**: The correction context explicitly lists ONLY what to change
- **Format preservation**: ralph-specum commands generate artifacts in the correct format
- **Validation loop**: spec-reviewer rubric catches format violations
- **Rollback**: Original artifact is backed up before any correction
- **No cascade**: Correcting one artifact does NOT automatically trigger re-generation of downstream artifacts (user decides)

## Smart-Ralph Phase Detection

Auto-detect from `.ralph-state.json`:

| Phase | Key Files | Review Focus |
|-------|-----------|-------------|
| `research` | `research.md` | Claims grounded, sources cited, methodology sound |
| `requirements` | `requirements.md` | FR/AC complete, testable, non-ambiguous |
| `design` | `design.md` | Architecture consistent, schema valid, trade-offs documented |
| `tasks` | `tasks.md` | Task decomposition, dependencies, verify commands executable |
| `execution` | `tasks.md`, `chat.md` | Progress tracking, completion evidence |
| `review` | `.progress.md`, `checklists/` | Completeness, quality gates passed |

If no `.ralph-state.json` exists, infer phase from which files are present in the spec directory.

## Smart-Ralph Formalism Reference

Corrections must respect these format conventions:

| Element | Format | Example |
|---------|--------|---------|
| FR IDs | `FR-XXX` or `FR-XX.X` | `FR-001`, `FR-002.3` |
| AC IDs | `AC-X.X` | `AC-1.1`, `AC-8.2` |
| NFR IDs | `NFR-XXX` | `NFR-001`, `NFR-007` |
| Task IDs | `T-XXX` or `US-N` | `T-001`, `US-3` |
| Phase names | lowercase | `research`, `requirements` |
| Done-when | Complete sentence | "Tests pass with 100% coverage" |
| Verify | Executable shell command | `pytest tests/ -x --tb=short` |
| Commit | Conventional Commits | `feat(scope): description` |
| Frontmatter | YAML between `---` markers | `spec: name\nphase: research` |

## Output Schema (review-checklist.json)

```json
{
  "spec_name": "feature-x",
  "spec_path": "specs/feature-x/",
  "phase": "requirements",
  "review_timestamp": "2026-04-26T07:00:00Z",
  "model_used": "top-tier",
  "review_mode": "full",
  "consensus_threshold": "majority",
  "findings": [
    {
      "id": "SR-001",
      "severity": "HIGH",
      "layer": "adversarial",
      "file": "requirements.md",
      "line_ref": "42",
      "category": "consistency",
      "description": "FR-003 threshold uses ≥ but design.md uses >",
      "suggestion": "Align to ≥ in both files",
      "consensus": {
        "winston": "CONFIRM",
        "john": "CONFIRM",
        "amelia": "CONFIRM",
        "mary": "CONFIRM",
        "result": "CONFIRMED",
        "adjudication": null
      },
      "correction_applied": true,
      "correction_command": "/ralph-specum:requirements feature-x --quick",
      "post_correction_review": "REVIEW_PASS"
    },
    {
      "id": "SR-005",
      "severity": "MEDIUM",
      "layer": "edge-case",
      "file": "design.md",
      "line_ref": "156",
      "category": "completeness",
      "description": "Missing error state for API timeout",
      "suggestion": "Add timeout error handling to component diagram",
      "consensus": {
        "winston": "CONFIRM",
        "john": "REJECT",
        "amelia": "CONFIRM",
        "mary": "NEEDS_CONTEXT",
        "result": "DISPUTED-CONFIRMED",
        "adjudication": "Orchestrator decided: Winston(2x technical) + Amelia(1.5x) outweigh John's vague objection. HIGH severity modifier applied."
      },
      "correction_applied": true,
      "correction_command": "/ralph-specum:design feature-x --quick",
      "post_correction_review": "REVIEW_PASS"
    }
  ],
  "summary": {
    "total_raw_findings": 15,
    "confirmed_by_consensus": 6,
    "disputed_confirmed_by_orchestrator": 4,
    "rejected_by_consensus": 3,
    "escalated_to_user": 1,
    "needs_context": 1,
    "corrections_applied": 8,
    "corrections_failed": 2
  },
  "quality_gates": {
    "contract_valid": true,
    "fr_ac_coverage": false,
    "verify_commands_valid": true,
    "smart_ralph_format": true,
    "consensus_reached": true
  }
}
```

## Execution Flow (Step by Step)

### Step 1: Initialization

1. Parse `spec_path` argument (directory or file)
2. If directory: read `.ralph-state.json` to detect phase
3. If file: infer phase from filename
4. Load all related spec files in the directory
5. Read `_bmad-output/project-context.md` for project conventions
6. Read `.specify/memory/constitution.md` for architectural rules

### Step 2: Phase 1 — Multi-Layer Review

Execute review layers sequentially (each layer receives findings from previous to avoid duplicates):

1. Contract validation (self, no agent)
2. Adversarial review → spawn `bmad-review-adversarial-general`
3. Editorial review → spawn `bmad-editorial-review-prose` + `bmad-editorial-review-structure`
4. Edge-case hunt → spawn `bmad-review-edge-case-hunter`
5. Deep analysis → use top-tier reasoning model

Collect all findings into Raw Findings Pool.

### Step 3: Phase 2 — BMAD Consensus

1. Group findings by target artifact
2. Spawn party-mode roundtable with Winston, John, Amelia, Mary
3. Each agent votes CONFIRM/REJECT/NEEDS_CONTEXT per finding
4. Apply consensus threshold
5. Produce Confirmed Findings list

### Step 4: Present Findings to User

Display review report:
```
## Smart-Ralph Review: {spec-name} (Phase: {phase})

### Summary
- Raw findings: {N}
- ✅ Confirmed by consensus: {M} ({P}%)
- ⚖️ Disputed → Orchestrator confirmed: {D}
- ❌ Rejected (false positives): {R}
- ⏸️ Escalated to you: {E}
- Total corrections to apply: {C}

### ✅ Confirmed Findings (Strong Consensus)
| # | Severity | File | Description | Consensus |
|---|----------|------|-------------|-----------|
| SR-001 | HIGH | requirements.md:42 | Threshold mismatch ≥ vs > | 4/4 CONFIRM |
| SR-002 | MEDIUM | design.md:89 | Missing error state | 3/4 CONFIRM |
...

### ⚖️ Disputed → Orchestrator Decisions
| # | Severity | File | Description | Vote Split | Orchestrator Reasoning |
|---|----------|------|-------------|------------|----------------------|
| SR-005 | MEDIUM | design.md:156 | Missing timeout error | 2C/1R/1NC | Winston+Amelia outweigh John (technical domain) |
...

### ⏸️ Escalated to You (Low Consensus — Your Decision Required)
| # | Severity | File | Description | Vote Split | Key Arguments |
|---|----------|------|-------------|------------|--------------|
| SR-012 | LOW | research.md:89 | Claim lacks source | 1C/2R/1NC | Winston: confirm (no citation). John+Mary: reject (common knowledge) |
...

### ❌ Rejected Findings (False Positives)
| # | Description | Why Rejected |
|---|-------------|-------------|
| SR-008 | "Verify command too long" | All agents: command follows project convention |
...
```

For escalated findings, ask the user to decide each one:
"SR-012 needs your decision: Winston says the claim at research.md:89 lacks a source citation. John and Mary say it's common knowledge. Apply fix? [Yes/No/Skip]"

Then ask: "Apply {C} confirmed + {D} disputed + {user-decided} corrections via ralph-specum?"

### Step 5: Phase 3 — Apply Corrections (if user approves)

For each confirmed finding:
1. Backup original artifact
2. Spawn subagent with correction context
3. Subagent invokes appropriate `/ralph-specum:{phase}` command
4. Validate corrected artifact with spec-reviewer rubric
5. Log result to `corrections-applied.md`

### Step 6: Finalize

1. Write `review-report.md`
2. Write `annotated-spec.md` (original with inline comments)
3. Write `review-checklist.json`
4. Write `corrections-applied.md`
5. Update `.progress.md` with review completion note

## Usage Examples

```
# Full review with consensus and auto-apply
/smart-ralph-review specs/anchor-dataset/ --apply-fixes=true

# Review only, no corrections
/smart-ralph-review specs/anchor-dataset/requirements.md

# Adversarial-only review (fast)
/smart-ralph-review specs/feature-x/research.md --review-mode=adversarial

# Strict consensus (all agents must agree)
/smart-ralph-review specs/feature-x/ --consensus-threshold=unanimous

# Review and apply with majority consensus
/smart-ralph-review specs/feature-x/ --apply-fixes=true --consensus-threshold=majority
```

## Configuration

```yaml
# Default configuration
model: top-tier
severity_threshold: medium
apply_fixes: false
consensus_threshold: majority
review_mode: full
output_format: both
max_correction_retries: 2
```

## Safety Mechanisms

| Mechanism | Purpose |
|-----------|---------|
| BMAD Consensus | Prevents false positives from reaching correction phase |
| ralph-specum Commands | Preserves artifact format (never direct file edits) |
| spec-reviewer Validation | Catches format violations after correction |
| Original Backup | Always possible to rollback |
| Scope Limiting | Correction context lists ONLY what to change |
| No Cascade | Correcting one artifact doesn't auto-trigger downstream regeneration |

## Integration with BMAD Agents

| Agent | Role in Review |
|-------|---------------|
| `bmad-review-adversarial-general` | Phase 1 Layer 2: Cynical review |
| `bmad-editorial-review-prose` | Phase 1 Layer 3: Prose quality |
| `bmad-editorial-review-structure` | Phase 1 Layer 3: Structural organization |
| `bmad-review-edge-case-hunter` | Phase 1 Layer 4: Boundary conditions |
| Winston (architect) | Phase 2: Technical accuracy vote |
| John (PM) | Phase 2: Requirements alignment vote |
| Amelia (developer) | Phase 2: Implementability vote |
| Mary (analyst) | Phase 2: Business logic vote |
| spec-reviewer (ralph-specum) | Phase 3: Post-correction validation |
