# Corrections Applied — aegf-infrastructure Review

**Review Date:** 2026-04-26T23:16:00Z
**Reviewer:** External Reviewer (autonomous loop)

---

## SR-001 (HIGH): output-dir default mismatch

**File:** `infrastructure/anchor_dataset_builder.py:48`
**Change:** `default="outputs"` → `default="datasets/anchors/v1/"`
**Help text:** `"Output directory (default: outputs)"` → `"Output directory (default: datasets/anchors/v1/)"`
**Verification:** `python3 infrastructure/anchor_dataset_builder.py --help` shows updated default
**Ruff:** PASS
**Status:** ✅ APPLIED

---

## SR-002 (MEDIUM): dependency_check.py crash on missing module

**File:** `infrastructure/dependency_check.py:166-172`
**Change:** Added `try/except ModuleNotFoundError` around `find_spec()` call
**Before:**
```python
for module_name in modules:
    spec = find_spec(module_name)
    if spec is None:
        failures.append(...)
```
**After:**
```python
for module_name in modules:
    try:
        spec = find_spec(module_name)
    except ModuleNotFoundError:
        failures.append(
            f"module not installed: '{module_name}' "
            f"(package: '{package}')"
        )
        continue
    if spec is None:
        failures.append(...)
```
**Verification:** `python3 infrastructure/dependency_check.py` no longer crashes — reports "module not installed" for missing deps
**Ruff:** PASS
**Status:** ✅ APPLIED

---

## Rejected Corrections (Not Applied)

| Finding | Reason |
|---------|--------|
| SR-003 (7 .example.yaml vs 4) | AUTO-REJECT by consensus (0/4 CONFIRM). Extras are bonus. |
| SR-004 (no physical dataset) | DISPUTED-REJECT by orchestrator. Operational step, not spec defect. |
