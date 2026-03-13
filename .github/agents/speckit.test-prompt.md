---
description: Test creation standards for Ralph Loop - MANDATORY
---

## Test Creation Standards - MANDATORY

This file provides the STANDARDIZED test patterns that MUST be used for ALL test creation in Ralph Loop. The agent MUST follow these patterns exactly.

---

## 1. Test Structure - AAA Pattern (MANDATORY)

Every test MUST follow this EXACT structure:

```python
class Test[ModuleName]:
    """Tests for src/module.py"""

    @pytest.fixture
    def setup_(self) -> SomeType:
        """Arrange: Create test fixtures and mocks."""
        return SomeType()

    def test_[function]_[scenario]_[expected](self, setup_):
        """Test that [description of what is tested]."""
        # SECTION 1: ARRANGE (setup)
        # - Create test data
        # - Set up mocks  
        # - Prepare inputs
        # NO function execution here
        input_data = ...

        # SECTION 2: ACT (execute) - ONLY ONE LINE
        result = function_under_test(input_data)

        # SECTION 3: ASSERT (verify)
        assert result == expected, f"Expected {expected}, got {result}"
```

**VIOLATIONS WILL BE REJECTED** if tests don't follow this structure.

---

## 2. Test Categories - MUST SPECIFY

Add this comment at the TOP of EVERY test file:

```python
# =============================================================================
# UNIT TESTS: Pure functions, no I/O, no network
# Location: tests/unit/
# Example: tests/unit/test_math_helpers.py
# =============================================================================

# =============================================================================
# INTEGRATION TESTS: Cross-module, real I/O allowed  
# Location: tests/integration/
# Example: tests/integration/test_pipeline.py
# =============================================================================

# =============================================================================
# CONTRACT TESTS: API/interface validation
# Location: tests/contract/
# Example: tests/contract/test_api_client.py
# =============================================================================
```

---

## 3. Test Naming Convention - MANDATORY

Pattern: `test_[module]_[function]_[scenario]_[expected]`

**GOOD Examples:**
```python
def test_parser_parse_valid_json_returns_dict(self):
def test_parser_parse_invalid_json_raises_ValueError(self):
def test_calculator_add_negative_numbers_returns_negative(self):
def test_api_client_timeout_raises_TimeoutError(self):
def test_validator_empty_string_returns_false(self):
```

**BAD Examples (REJECTED):**
```python
def test_parser(self):  # Too vague
def test_function1(self):  # No context
def test_case2(self):  # Meaningless
def test_valid_input(self):  # Missing module/function
```

---

## 4. Mocking Guidelines - USE IN ORDER

### Priority 1: Use Existing Fixtures from conftest.py

```python
# Available fixtures (USE THESE):
@pytest.fixture def mock_inference_client() -> MagicMock
@pytest.fixture def sample_record() -> SampleRecord
@pytest.fixture def exam_record() -> ExamRecord
@pytest.fixture def scorecard() -> ScoreCard
@pytest.fixture def audit_report() -> AuditReport

# Usage:
def test_something(mock_inference_client):
    mock_inference_client.generate.return_value = '{"result": "ok"}'
    # ...
```

### Priority 2: unittest.mock.patch Decorator

```python
from unittest.mock import patch, MagicMock

@patch('module.function_to_mock')
def test_with_mock(mock_func):
    mock_func.return_value = 'expected'
    result = function_under_test()
    assert result == 'expected'
```

### Priority 3: MagicMock Inline

```python
def test_api_call():
    mock_client = MagicMock()
    mock_client.get.return_value.json.return_value = {'key': 'value'}
    # ...
```

**PROHIBITED:**
- Mock internal implementation details
- Create mock chains > 3 levels
- Mock data structures (use real objects)

---

## 5. Edge Cases Checklist - REQUIRED

For EVERY function, test these edge cases:

### Input Boundaries
- [ ] Empty inputs: `[]`, `{}`, `""`, `None`
- [ ] Single element: `[x]`, `{x: y}`
- [ ] Maximum values: `sys.maxsize`, `float('inf')`
- [ ] Minimum values: `0`, negative numbers
- [ ] Whitespace: `" "`, `"\t\n"`

### Type Errors
- [ ] Wrong input types (int instead of str)
- [ ] None when expecting value
- [ ] Extra/missing arguments

### Error Paths
- [ ] Every `raise` statement needs a test
- [ ] Every exception handler needs a test
- [ ] Network/file errors

### Example:
```python
def test_divide_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_parse_empty_string_returns_none():
    assert parse("") is None

def test_validate_none_returns_false():
    assert validate(None) is False
```

---

## 6. Coverage Strategy - TO REACH 90%+

### Golden Path + Error Path (MINIMUM 2 per function)
```python
# Happy path
def test_add_two_positive_numbers():
    assert add(2, 3) == 5

# Error path  
def test_add_negative_result():
    assert add(-1, -2) == -3
```

### Branch Coverage
```python
# Test BOTH branches
if condition:
    do_something()  # Test True path
    
# and
if not condition:
    do_other()  # Test False path
```

### Exception Coverage
```python
# Every raise needs a test
def test_function_raises_on_invalid_input():
    with pytest.raises(ValueError, match="expected message"):
        function(invalid_input)
```

### Tuple/List Index Coverage
```python
a, b = result  # Test a AND test b
```

---

## 7. Fixture Creation Pattern

When creating NEW fixtures, follow this pattern:

```python
@pytest.fixture
def sample_[name]([params]) -> ReturnType:
    """Create a [description] for testing.
    
    Args:
        [param_name]: [description], default: [default]
    
    Returns:
        [ReturnType]: [description]
    """
    return ReturnType(
        field1=value1,
        field2=value2,
    )
```

---

## 8. Test File Organization

```
tests/
├── unit/                    # Pure unit tests
│   ├── test_module_a.py
│   └── test_module_b.py
├── integration/             # Cross-module tests
│   ├── test_pipeline.py
│   └── test_workflow.py
├── contract/               # API/interface tests
│   └── test_api_client.py
├── fixtures/               # Shared fixtures (NOT tests!)
│   ├── __init__.py
│   └── mock_providers.py
└── conftest.py              # Global fixtures
```

---

## 9. Example: GOOD Test

```python
"""
Tests for src/factory/production_v11.py - Fragment extraction

UNIT TESTS for pure functions in production_v11 module.
"""

import pytest
from src.factory.production_v11 import parse_bundle


class TestParseBundle:
    """Tests for parse_bundle function."""

    @pytest.fixture
    def valid_bundle(self) -> dict:
        """A valid bundle dictionary for testing."""
        return {
            "type": "FUNCTIONAL_UNIT",
            "content": "def hello(): pass",
            "metadata": {"name": "test.py"},
        }

    def test_valid_bundle_returns_dict(self, valid_bundle):
        """Test that parse_bundle returns dict for valid input."""
        # Arrange
        # (already done in fixture)
        
        # Act
        result = parse_bundle(valid_bundle)
        
        # Assert
        assert isinstance(result, dict)
        assert result["type"] == "FUNCTIONAL_UNIT"

    def test_invalid_type_raises_value_error(self):
        """Test that parse_bundle raises ValueError for invalid type."""
        # Arrange
        invalid_bundle = {"type": "INVALID", "content": "test"}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid bundle type"):
            parse_bundle(invalid_bundle)

    def test_empty_content_returns_empty_dict(self):
        """Test that parse_bundle handles empty content."""
        # Arrange
        bundle = {"type": "FUNCTIONAL_UNIT", "content": ""}
        
        # Act
        result = parse_bundle(bundle)
        
        # Assert
        assert result == {"type": "FUNCTIONAL_UNIT", "content": ""}
```

---

## 10. Example: BAD Test (WILL BE REJECTED)

```python
# BAD: No category comment
import pytest

# BAD: Vague class name
class TestStuff:
    # BAD: No docstring
    def test_one(self):
        # BAD: No arrange/act/assert sections
        assert True  # What does this test???
    
    # BAD: Too vague, no context
    def test_valid(self):
        data = {"a": 1}
        result = parse(data)  # What function???
        assert result  # What should result be???
```

---

## Summary Checklist

Before marking a test task as DONE, verify:

- [ ] Test file has category comment (UNIT/INTEGRATION/CONTRACT)
- [ ] Test follows AAA pattern (Arrange/Act/Assert sections)
- [ ] Test name follows pattern: `test_[module]_[function]_[scenario]_[expected]`
- [ ] Test has docstring explaining what is tested
- [ ] Edge cases covered (empty, None, error paths)
- [ ] Existing fixtures from conftest.py are used when applicable
- [ ] No `# pragma: no cover` unless absolutely necessary
- [ ] Coverage target: >= 90% for new modules
