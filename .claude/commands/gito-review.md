---
description: Run Gito code review on the current branch against main, with spec context, classification, fixes, and quality gate.
---

## User Input

```text
$ARGUMENTS
```

## Gito Code Review Workflow

Execute this workflow end-to-end. Follow the steps in order.

### Step 1: Quality Gate Baseline

Invoke `/quality-gate` to establish the baseline. Record the result. This is the quality baseline for comparison after fixes.

### Step 2: Identify the Spec

Determine what feature/spec applies to the current branch vs main:
- `git branch --show-current` to get branch name
- `git diff --name-only HEAD main` to see changed files
- Match the branch/changed files to the appropriate spec under `specs/`
- If comparing feature branch to main: FULL spec context from that spec
- If comparing hotfix or no spec matches: MINIMAL context only

### Step 3: Prepare Gito Context

Create or update `.gito/context.md` with the spec information:
- Spec name, branch, base, feature description
- Intentional patterns (NOT bugs) from the spec
- Implementation details relevant to the review

Then ensure `.gito/config.toml` includes:
```toml
aux_files = [".gito/context.md"]
```

### Step 4: Run Gito Review

```bash
.venv/bin/gito review HEAD..main --output gito-report
```

The review runs in the background. Note the PID.

### Step 5: Wait for Gito to Complete

Poll the process every 4.5 minutes:

```bash
sleep 270 && ls /proc/<PID>/status 2>/dev/null && echo "RUNNING" || echo "DONE"
```

Repeat the sleep until Gito finishes. Gito can take hours — do not give up or kill the process.

### Step 6: Review the Report

When Gito finishes, read `gito-report/code-review-report.md`:
- `head -50` and `tail -50` for overview
- Review the issue count and categories

### Step 7: Classify Issues with bmad-review-adversarial-general

For ambiguous issues, Use `bmad-consensus-party` with  the `bmad-review-adversarial-general` skill to classify each issue as REAL or FALSE_POSITIVE:
- REAL: genuine bugs that need fixing
- FALSE_POSITIVE: intentional patterns per spec, documentation-only, out-of-scope

Repeat `bmad-consensus-party` for issues where agents disagree — run until consensus is reached.

### Step 8: Fix Real Issues

For each REAL issue, use `/bmad-quick-dev` to fix them. Before fixing each issue, read the spec to understand the full context.

### Step 9: Final Quality Gate

Invoke `/quality-gate` again after all fixes. Compare against the baseline from Step 1: expect 1845 tests passing, 1 skipped, zero regressions.

### Step 10: Report Summary

Report the final result:
- How many issues Gito found
- How many were REAL vs FALSE_POSITIVE
- How many were fixed
- Quality gate comparison (before vs after)
- Any remaining issues that are out of scope or deferred
