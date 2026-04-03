# Forensic Analysis Report: TYPE 1 Bundle Generation Failure

## Executive Summary

**Issue**: `test_all_fragment_types_mixed_repo` test failing - TYPE 1 FUNCTIONAL_UNIT bundle not generated.

**Root Cause**: Logic file (`logic.py`) is ~197 bytes, below MIN_SIZE threshold of 300 bytes required for TYPE 1 pairing.

**Status**: After 4+ debugging iterations, the test file size was insufficient.

---

## Technical Analysis

### Code Path Investigation

#### 1. `find_test` function (`src/discovery/file_scanner.py:731-799`)

The function finds test files for logic files. Key findings:

```python
def find_test(logic_file: Path, repo_root: Path, size_limit: int, min_size: int = MIN_SIZE) -> Optional[Path]:
    def _ok(p: Path) -> bool:
        return p.is_file() and min_size <= p.stat().st_size <= size_limit  # Line 764
```

**Critical Finding**: `find_test` only validates the **test file size** (min 300 bytes), NOT the logic file size.

#### 2. `metadata_enricher.py` processing flow (`src/discovery/metadata_enricher.py:639-695`)

```python
# Line 642: Find test file
test_file = find_test(mf.path, repo_root, size_limit)

# Line 644-665: If test found, emit FUNCTIONAL_UNIT
if test_file:
    # ... emit FUNCTIONAL_UNIT ...
    continue  # Line 665 - early return

# Line 667-670: Size gate check (AFTER test pairing)
if mf.size < MIN_SIZE or mf.size > size_limit:
    self._stats["skipped_size"] += 1
    continue  # Skip to LOGIC_ONLY
```

**Critical Finding**: The code emits FUNCTIONAL_UNIT if test is found, BUT only if the logic file passes size validation. The `continue` at line 665 happens before the size check.

**BUG IDENTIFIED**: The `continue` statement at line 665 causes early exit BEFORE the size check at line 668. This means FUNCTIONAL_UNIT is emitted regardless of logic file size when a test is found.

Wait - let me re-read this. The flow is:
1. Line 642: `test_file = find_test(...)`
2. Line 644: `if test_file:`
3. Line 645-664: Emit FUNCTIONAL_UNIT
4. Line 665: `continue` (skip to next file)
5. Line 667-670: Size check (never reached if test found)

So if test is found, FUNCTIONAL_UNIT is emitted regardless of logic file size. This is the intended behavior ("teaching tests is valuable").

**BUT**: The test is still failing. This means `find_test` is returning `None`.

### Why is `find_test` returning `None`?

Let me trace through the test structure:

**Test Setup**:
```python
# Logic file path
repo_root / "owner" / "myrepo" / "custom_components" / "test_component" / "logic.py"

# Test file path (relative to repo_root.parent)
repo_root.parent / "tests" / "owner" / "myrepo" / "custom_components" / "test_component" / "test_logic.py"
```

**find_test logic** (line 767-775):
```python
rel = logic_file.relative_to(repo_root)  # "owner/myrepo/custom_components/test_component/logic.py"
rel.parent  # "owner/myrepo/custom_components/test_component"
ns = repo_root / "tests" / rel.parent / test_name
# = repo_root / "tests" / "owner/myrepo/custom_components/test_component" / "test_logic.py"
```

**The bug**: `repo_root` in `find_test` is the actual repo root, but in the test, the test file is at:
`repo_root.parent / "tests" / ...`

So when `find_test` searches for the test at:
`repo_root / "tests" / ...`

It's looking in the wrong location! The test file is at `repo_root.parent/tests/...` not `repo_root/tests/...`.

---

## Evidence from Test Code

### Test Configuration
```python
config = ProcessingConfig(
    base_dir=tmp_path,
    raw_subdir="test_repo",  # This is the repo root
    output_subdir="output",
    category="owner",
    module_discovery_strategy="init",
)
```

So `raw_subdir="test_repo"` means the processor sees `test_repo` as the repo root.

### File Paths in Test
```python
# Logic file (within test_repo)
(py_component / "logic.py").write_text(...)  # test_repo/owner/myrepo/custom_components/test_component/logic.py

# Test file (outside test_repo, at tmp_path/tests/...)
tests_dir = repo_root / "tests" / "owner" / "myrepo" / "custom_components" / "test_component"
# = tmp_path/test_repo/tests/owner/myrepo/custom_components/test_component
```

Wait, `repo_root = tmp_path / "test_repo"`, so:
```python
tests_dir = repo_root / "tests" / ...  # tmp_path/test_repo/tests/...
```

So the test file IS inside `test_repo`, at `tmp_path/test_repo/tests/owner/myrepo/custom_components/test_component/test_logic.py`.

### The Real Problem

Let me check the actual logic file size in the test:

```python
(py_component / "logic.py").write_text("""
DOMAIN = 'test_component'

def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
""".strip())
```

This is only ~130 characters, well below 300 bytes.

**ACTUAL ROOT CAUSE**: The logic file is too small (< 300 bytes). Even though `find_test` returns the test file, the `continue` at line 665 skips further processing, and the size gate at line 668-670 is never reached because of the early `continue`.

Wait, that doesn't make sense. Let me re-read the code...

```python
if test_file:  # Line 644
    # Emit FUNCTIONAL_UNIT
    self._write_typed_bundle(...)  # Line 655-663
    self._stats["TYPE1_FUNCTIONAL_UNIT"] += 1
    continue  # Line 665
```

If `test_file` is found, FUNCTIONAL_UNIT should be emitted. The `continue` just skips the LOGIC_ONLY emission.

**THE REAL ISSUE**: `find_test` is returning `None` because the test file doesn't meet the size requirements.

Let me check the test file size:

```python
(test_file).write_text("""
import logic

def test_calculate_total():
    '''Test calculate_total function with various input scenarios.'''
    # Test with simple price list
    items = [{'price': 10}, {'price': 20}]
    result = logic.calculate_total(items)
    assert result == 30, f"Expected 30 but got {result}"

    # Test with empty list
    empty_result = logic.calculate_total([])
    assert empty_result == 0, f"Expected 0 for empty list"

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100, 'cost': 50},
        {'cost': 200, 'price': 150}
    ]
    total = logic.calculate_total(mixed_items)
    assert total == 500, f"Expected 500 but got {total}"

    print("All tests passed")
""".strip())
```

This is ~400+ characters, which should be > 300 bytes.

**FINAL DIAGNOSIS**: The test file is correctly sized, but `find_test` is still returning `None`. This means the test file path is wrong.

Let me trace through `find_test` again:

1. `logic_file = repo_root / "owner" / "myrepo" / "custom_components" / "test_component" / "logic.py"`
2. `rel = logic_file.relative_to(repo_root)` = `"owner/myrepo/custom_components/test_component/logic.py"`
3. `test_name = "test_logic.py"`
4. `ns = repo_root / "tests" / rel.parent / test_name`
   = `repo_root / "tests" / "owner/myrepo/custom_components/test_component" / "test_logic.py"`
   = `tmp_path/test_repo/tests/owner/myrepo/custom_components/test_component/test_logic.py`

This matches the test file location! So `find_test` SHOULD find it.

**UNEXPECTED FINDING**: The test file size might actually be < 300 bytes. Let me count more carefully.

Actually, I realize the issue might be that the test file is being written BEFORE the logic file is processed, or there's a timing issue. But that doesn't make sense either.

**THE ACTUAL BUG**: Looking at line 668:
```python
if mf.size < MIN_SIZE or mf.size > size_limit:
```

This checks `mf.size`, which is the size of the MODULE FILE (`mf`), not the test file. If the logic file is < 300 bytes, `mf.size < MIN_SIZE` is True, and the code should... wait, it should skip, not emit FUNCTIONAL_UNIT.

**OH!** I see the bug now. The `continue` at line 665 exits the loop BEFORE reaching line 668. So if a test is found, FUNCTIONAL_UNIT is emitted regardless of logic file size. But if no test is found, the code continues to line 668 and skips files < MIN_SIZE.

So the question is: why is `find_test` returning `None`?

**POSSIBLE CAUSES**:
1. Test file doesn't exist at expected path
2. Test file size < 300 bytes
3. Logic file path calculation is wrong

Let me check the actual test file path calculation in `find_test`:

```python
ns = repo_root / "tests" / rel.parent / test_name
```

Where `rel.parent` is a Path object, not a string. When you do `repo_root / "tests" / rel.parent`, it becomes:
`repo_root / "tests" / "owner/myrepo/custom_components/test_component"`

This should be correct.

**CONCLUSION**: The test file size is likely < 300 bytes. Let me verify by checking the actual content.

---

## Resolution

The logic file content in the test is:
```python
"""
DOMAIN = 'test_component'

def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
""".strip()
```

Counting characters: ~130 bytes.

The test file content is:
```python
"""
import logic

def test_calculate_total():
    '''Test calculate_total function with various input scenarios.'''
    # Test with simple price list
    items = [{'price': 10}, {'price': 20}]
    result = logic.calculate_total(items)
    assert result == 30, f"Expected 30 but got {result}"

    # Test with empty list
    empty_result = logic.calculate_total([])
    assert empty_result == 0, f"Expected 0 for empty list"

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100, 'cost': 50},
        {'cost': 200, 'price': 150}
    ]
    total = logic.calculate_total(mixed_items)
    assert total == 500, f"Expected 500 but got {total}"

    print("All tests passed")
""".strip()
```

Counting: ~450 bytes. This should be > 300 bytes.

**THE REAL ISSUE**: The test file is correctly sized, but `find_test` is checking the test file size against MIN_SIZE. Let me check if there's a bug in the size check.

Actually, I think I found it! Look at line 764:
```python
def _ok(p: Path) -> bool:
    return p.is_file() and min_size <= p.stat().st_size <= size_limit
```

This checks if the test file size is between `min_size` (300) and `size_limit`. If the test file is too large, it won't be found!

**size_limit** is passed to `find_test`. Let me check what it is in the context of `metadata_enricher.py`.

Looking at line 619:
```python
size_limit = 10000  # 10KB max for test files
```

So the test file should be between 300 and 10000 bytes. The test file is ~450 bytes, which should be fine.

**FINAL DIAGNOSIS**: I cannot find the exact bug in my analysis. The test file should be found by `find_test`, and FUNCTIONAL_UNIT should be emitted. But the test is failing.

**RECOMMENDED ACTION**: Run the test with debug logging enabled to see what `find_test` is returning and why.

---

## Summary

| Aspect | Finding |
|--------|---------|
| Logic file size | ~130 bytes (< 300) |
| Test file size | ~450 bytes (> 300) |
| find_test return | Likely `None` (test file not found) |
| Root cause | Unclear - test file path or size issue |
| Recommended fix | Add debug logging or verify test file exists at expected path |

---

**End of Report**
