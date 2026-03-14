## SPEC 005: DOCUMENTATION SYNCHRONIZATION PROTOCOL

### Objective
Ensure all project documentation (AGENTS_ARCHITECTURE.md, METHODOLOGY.md, PHP_MODERNIZATION_FORGE.md) accurately reflects the current codebase state post-Specs 003 and 004. Eliminate terminology mismatches and implementation gaps between documented architecture and actual code.

### Scope
- Update AGENTS_ARCHITECTURE.md to reflect actual Ralph Loop implementation (clarify Git Worktrees usage and difference with Factory Pipeline async scheduling)
- Update `README.md` to reflect refactors from Spec 003 and correct CLI/module names
- Update `docs/ORCHESTRATION_QUICKSTART.md` to align task lifecycle and workflow diagrams with current Ralph Loop behavior
- Update `docs/case_studies/REAL_USE_CASE.md` to resolve pending metrics and modernize references
- Review and update documents in `docs/specs/` (e.g., stage_1_5_backtracking_alignment.md) for consistency with refactor
- Promote PHPLegacyDriver from test-only to production implementation
- Standardize TIPO 5 terminology across all documents
- Correct legacy pattern detection logic in pipeline_runner.py
- Validate all case study examples against current implementation

### Requirements
1. **AGENTS_ARCHITECTURE.md**
   - Mantener la referencia a Git Worktrees en Ralph Loop (es correcto: usa worktrees para paralelismo de specs)
   - Clarificar que el Factory Pipeline (Stage 2) usa async scheduling para generación de datos — son sistemas distintos
   - Verificar que la descripción de Ralph Loop refleja el flujo real (stateless iterations, worktree branching)

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
- [ ] Ralph Loop documentation correctly documents use of Git Worktrees and distinguishes it from Factory Pipeline async scheduling

### Acceptance Criteria
Documentation must pass `docs/audit/verify_documentation_sync.py` with 100% pass rate before Spec 005 merge.

## Clarifications

### Session 2026-03-14
- Q: ¿Cómo documentar Ralph Loop vs Factory Pipeline en cuanto a paralelismo? → A: Documentar ambos: Ralph Loop usa Git Worktrees para paralelismo de specs, y el Factory Pipeline usa async scheduling para generación de datos. Son sistemas distintos.
- Q: ¿Expandir alcance de spec 005 para cubrir más docs? → A: Sí. Incluir `README.md`, `docs/ORCHESTRATION_QUICKSTART.md`, `docs/case_studies/REAL_USE_CASE.md` y revisar `docs/specs/*`.