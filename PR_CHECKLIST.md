# PR Checklist: Stage 1 — Discovery (Refactor Language Abstraction)

## Overview
- **Branch:** `001-stage1-discovery`
- **Target:** `main`
- **Status:** Draft PR

## Summary of Changes

This PR implements the Stage 1 discovery refactor, introducing a language abstraction layer for extractors and improving Git resilience.

### Key Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Extractor adapters (`base.py`, `python_ast_adapter.py`, `factory.py`) | ✅ Complete | `src/utils/extractors/` |
| Processor refactor to use adapters | ✅ Complete | `src/discovery/processor.py` |
| Profile-based ingestion with filters | ✅ Complete | `src/discovery/ingestor.py` |
| Module discovery strategies (manifest, directory, manual_mapping) | ✅ Complete | `src/discovery/processor.py` |
| Master documents loading | ✅ Complete | `src/factory/production_v11.py` |
| Git resilience with retry policy | ✅ Complete | `src/discovery/ingestor.py` |
| Rate limit backoff | ✅ Complete | `src/discovery/ingestor.py` |
| Reference corpus fixtures | ✅ Complete | `tests/fixtures/reference_corpus/` |
| Recall measurement harness | ✅ Complete | `scripts/measure_recall.py`, `tests/integration/test_recall_harness.py` |
| Observability metrics | ⚠️ Code Complete (Not Integrated) | `src/utils/metrics.py` — exists but not emitted in main flow |
| Benchmarking scripts | ⚠️ Scripts Exist (Baseline Pending) | `scripts/benchmark/measure_performance.py` — requires execution post-merge |
| Test suite | ✅ Complete | `tests/unit/`, `tests/integration/` |

## Test Migration Results (T031)

The following tests have been audited for AST fallback dependency per `specs/001-stage1-discovery/migrations/test_migration_plan.md`:

| Test File | Priority | Strategy | Status |
|-----------|----------|----------|--------|
| `tests/test_production_v11.py` | High | A (ParseError-first) | Pending migration |
| `tests/test_production_v11_helpers.py` | High | A (ParseError-first) | Pending migration |
| `tests/test_model_evaluator_integration_paths.py` | High | A/B (review needed) | Pending migration |
| `tests/test_sampling.py` | High | Review/Classify | Not AST-related |
| `tests/test_model_evaluator_extended_paths.py` | High | Review/Classify | Pending migration |

See: `specs/001-stage1-discovery/migrations/test_migration_plan.md`

## Benchmark Baseline (T032)

- **Script:** `scripts/benchmark/measure_performance.py` — exists but baseline not yet captured
- **Integration test:** `tests/integration/test_benchmark_compare.py` — exists but blocked on corpus
- **Reference corpus:** `tests/fixtures/reference_corpus/homeassistant/` — 5 repos with gold dependencies
- Run after merge: `python scripts/benchmark/measure_performance.py` to capture baseline

## Verification Steps for Reviewers

### Pre-flight Checks
```bash
# 1. Run test suite
pytest tests/unit tests/integration -v

# 2. Check formatting
ruff format .

# 3. Check headers
python scripts/check_headers.py --check

# 4. Verify no lint errors
ruff check .
```

### Core Functionality Verification
```bash
# 5. Test extractor adapters
pytest tests/unit/test_extractor_adapter_contract.py -v
pytest tests/unit/test_python_ast_adapter.py -v
pytest tests/unit/test_extractors_factory.py -v

# 6. Test processor integration
pytest tests/integration/test_processor_adapter_integration.py -v

# 7. Test Git resilience
pytest tests/unit/test_ingestor_git_fallback.py -v
pytest tests/integration/test_ingestor_git_recovery.py -v

# 8. Test rate limiting
pytest tests/unit/test_rate_limit_backoff.py -v

# 9. Test metrics emission
pytest tests/unit/test_metrics.py -v
```

### Acceptance Criteria (from spec.md)

- [x] All unit tests pass locally (744 passed, 1 skipped)
- [x] `ruff format .` passes with no changes needed
- [x] Header check passes: `python scripts/check_headers.py --check`
- [x] Extractor adapters correctly parse Python files
- [x] Git resilience handles network errors with exponential backoff
- [x] Rate limit backoff respects `X-RateLimit-Reset` headers
- [x] Parse error policy defaults to `abort` (marks `needs_manual_review`)

## Files Changed

### Source Code
- `src/utils/extractors/` — New adapter package
- `src/discovery/processor.py` — Refactored to use adapters
- `src/discovery/ingestor.py` — Added profile filters, Git resilience, rate limiting
- `src/factory/production_v11.py` — Added `load_master_docs()`
- `src/utils/metrics.py` — New observability metrics

### Tests
- `tests/unit/test_extractor_*.py` — Adapter contract tests
- `tests/unit/test_ingestor_git_fallback.py` — Git resilience unit tests
- `tests/unit/test_rate_limit_backoff.py` — Rate limit tests
- `tests/unit/test_metrics.py` — Metrics tests
- `tests/integration/test_processor_*.py` — Integration tests
- `tests/integration/test_ingestor_git_recovery.py` — Git recovery integration tests

### Specs & Configs
- `specs/001-stage1-discovery/` — Full spec documents
- `configs/stage_1_discovery/` — Example configs

## Notes

- Migration of AST fallback tests (T031) is pending — tracked in `specs/001-stage1-discovery/migrations/test_migration_plan.md`
- Benchmark results should be generated after merging to compare baseline vs post-refactor performance

---

**Generated by:** Ralph Wiggum autonomous loop
**Date:** 2026-03-11
