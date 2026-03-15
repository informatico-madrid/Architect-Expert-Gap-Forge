# Data Model: Inference Calibration Suite (Stage 6)

## Overview

This document defines the data structures for the calibration system. All dataclasses follow AEGF conventions: frozen=True, slots=True, and fully typed.

## Core Entities

### SamplingProfile

Represents a sampling parameter configuration to test.

```python
@dataclass(slots=True, frozen=True)
class SamplingProfile:
    """Configuration for LLM sampling parameters."""
    
    temperature: float        # Range: 0.0 to 2.0
    top_k: int              # Range: 0 (disabled) or positive integer
    min_p: float            # Range: 0.0 to 1.0
    repetition_penalty: float # Range: 1.0 to 2.0
    presence_penalty: float | None = None  # Optional: -2.0 to 2.0
```

**Validation Rules**:
- temperature: 0.0 <= value <= 2.0
- top_k: value >= 0
- min_p: 0.0 <= value <= 1.0
- repetition_penalty: 1.0 <= value <= 2.0
- presence_penalty (if set): -2.0 <= value <= 2.0

---

### CalibrationResult

Represents the outcome of a single calibration iteration.

```python
@dataclass(slots=True, frozen=True)
class CalibrationResult:
    """Result of evaluating one parameter profile against one prompt."""
    
    profile: SamplingProfile
    exam_id: str                    # ID of the prompt/exam being tested
    judge_scores: dict[str, float]  # {'ha_modernity': 0.x, 'reasoning_depth': 0.x, ...}
    composite_score: float           # Weighted sum using SCORING_WEIGHTS
    adjusted_score: float           # composite_score with length penalty applied
    response_length: int            # Word count of the generated response
    timestamp: str                  # ISO 8601 timestamp
```

**Calculations**:

1. **Composite Score**:
```python
composite_score = (
    judge_scores['ha_modernity'] * 0.30 +
    judge_scores['reasoning_depth'] * 0.25 +
    judge_scores['functionality'] * 0.25 +
    judge_scores['completeness'] * 0.12 +
    judge_scores['style'] * 0.08
)
```

2. **Length Penalty** (for investigation tasks only):
```python
if response_length < 200:
    penalty_factor = response_length / 200  # 0.0 to 1.0
    adjusted_score = composite_score * penalty_factor
else:
    adjusted_score = composite_score
```

---

### CalibrationReport

Aggregated results of the entire calibration run.

```python
@dataclass(slots=True, frozen=True)
class CalibrationReport:
    """Complete calibration run results."""
    
    timestamp: str                      # ISO 8601 start time
    total_iterations: int              # Number of profile × prompt combinations
    best_profile: SamplingProfile      # Profile with highest aggregate score
    all_results: list[CalibrationResult] # All individual results
    statistics: dict[str, Any]         # Aggregated statistics
```

**Statistics Structure**:
```python
{
    "mean_composite_score": float,
    "std_composite_score": float,
    "mean_response_length": float,
    "prompts_tested": int,
    "profiles_tested": int,
    "duration_seconds": float,
}
```

---

### CalibrationCheckpoint

State for resume functionality.

```python
@dataclass(slots=True, frozen=True)
class CalibrationCheckpoint:
    """Progress checkpoint for resume capability."""
    
    timestamp: str
    current_prompt_idx: int
    current_profile_idx: int
    completed_results: list[CalibrationResult]
    total_prompts: int
    total_profiles: int
```

---

## Parameter Grids

### Default Search Space

As specified in FR-003:

| Parameter | Values |
|----------|--------|
| temperature | [0.5, 0.6, 0.7] |
| top_k | [20, 40, 50] |
| min_p | [0.02, 0.05] |
| repetition_penalty | [1.1, 1.15, 1.2] |

**Total Combinations**: 3 × 3 × 2 × 3 = 54 profiles

Note: This differs from the 27 mentioned in SC-001 (which assumed a subset). The full grid has 54 combinations.

---

## Output Formats

### calibration_report.json

```json
{
  "timestamp": "2026-03-15T12:00:00Z",
  "total_iterations": 270,
  "best_profile": {
    "temperature": 0.6,
    "top_k": 40,
    "min_p": 0.05,
    "repetition_penalty": 1.15,
    "presence_penalty": null
  },
  "statistics": {
    "mean_composite_score": 0.75,
    "std_composite_score": 0.08,
    "mean_response_length": 350.2,
    "prompts_tested": 5,
    "profiles_tested": 54,
    "duration_seconds": 1800.5
  },
  "results": [
    {
      "profile": {"temperature": 0.5, "top_k": 20, "min_p": 0.02, "repetition_penalty": 1.1},
      "exam_id": "prompt_001",
      "judge_scores": {"ha_modernity": 0.8, "reasoning_depth": 0.7, ...},
      "composite_score": 0.72,
      "adjusted_score": 0.72,
      "response_length": 320,
      "timestamp": "2026-03-15T12:00:05Z"
    }
  ]
}
```

### vllm_config.yaml

```yaml
# Best sampling parameters for SFT model
temperature: 0.6
top_k: 40
top_p: 0.95
min_p: 0.05
repetition_penalty: 1.15
presence_penalty: 0.0
max_tokens: 65536
```

---

## Relationships

```
CalibrationReport
├── best_profile: SamplingProfile
├── all_results: List[CalibrationResult]
│   └── CalibrationResult.profile: SamplingProfile
│   └── CalibrationResult.judge_scores: Dict
└── statistics: Dict

CalibrationCheckpoint
├── completed_results: List[CalibrationResult]
└── (references same nested types)
```
