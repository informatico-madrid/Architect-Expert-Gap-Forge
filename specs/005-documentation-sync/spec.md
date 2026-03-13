## SPEC 005: DOCUMENTATION SYNCHRONIZATION PROTOCOL

### Objective
Ensure all project documentation (AGENTS_ARCHITECTURE.md, METHODOLOGY.md, PHP_MODERNIZATION_FORGE.md) accurately reflects the current codebase state post-Specs 003 and 004. Eliminate terminology mismatches and implementation gaps between documented architecture and actual code.

### Scope
- Update AGENTS_ARCHITECTURE.md to reflect actual Ralph Loop implementation (factory pipeline without Git worktrees)
- Promote PHPLegacyDriver from test-only to production implementation
- Standardize TIPO 5 terminology across all documents
- Correct legacy pattern detection logic in pipeline_runner.py
- Validate all case studies against current implementation

### Requirements
1. **AGENTS_ARCHITECTURE.md**
   - Replace "Ralph Loop uses Git Worktrees for parallel execution" with "Factory pipeline implements parallel execution via async task scheduling"
   - Remove references to Git worktrees in Ralph Loop section

2. **METHODOLOGY.md**
   - Replace all "TIPO 5 GOVERNANCE_RULES" with "governance_cache" in code references
   - Update Hybrid Gold-Injection Protocol section to match actual implementation logic

3. **PHP_MODERNIZATION_FORGE.md**
   - Change "PHPLegacyDriver (NEW) — Pluggable driver for PHP parsing" to "PHPLegacyDriver (PRODUCTION) — Fully implemented PHP parsing driver"
   - Remove "✅ DELIVERED" status from driver description (now in production)

4. **pipeline_runner.py**
   - Fix legacy pattern detection: `if not has_legacy:` should only skip Gold Injection for clean fragments, not all fragments with legacy patterns

### Verification Checklist
- [ ] All TIPO 5 references updated to governance_cache in documentation
- [ ] PHPLegacyDriver promoted to production in src/factory/
- [ ] Legacy pattern detection logic matches METHODOLOGY.md description
- [ ] Case study examples validated against current implementation
- [ ] No Git worktree references remain in Ralph Loop documentation

### Acceptance Criteria
Documentation must pass `docs/audit/verify_documentation_sync.py` with 100% pass rate before Spec 005 merge.