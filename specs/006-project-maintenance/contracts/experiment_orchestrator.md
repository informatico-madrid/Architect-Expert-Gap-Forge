# Contract: Experiment Orchestrator API

**Feature**: 006-project-maintenance  
**Date**: 2026-03-18  
**Status**: Draft

## Overview

This document defines the public API contract for the Experiment Orchestrator module.

## Public API

### `ExperimentOrchestrator` Class

#### Constructor

```python
class ExperimentOrchestrator:
    def __init__(
        self,
        variant: ExperimentVariant,
        axolotl_config: str,
        tokenizer_path: str,
        output_dir: str,
        validation_shards: int = 10,
        fast_mode: bool = True,
    )
```

**Parameters**:
- `variant` (ExperimentVariant): The experiment variant configuration
- `axolotl_config` (str): Path to Axolotl YAML configuration
- `tokenizer_path` (str): Path to tokenizer files
- `output_dir` (str): Output directory for results
- `validation_shards` (int, optional): Number of validation shards (default: 10)
- `fast_mode` (bool, optional): Use fast mode settings (default: True)

**Raises**:
- `ValueError`: If variant parameters are invalid
- `FileNotFoundError`: If axolotl_config or tokenizer_path don't exist

#### `generate_dataset()` Method

```python
def generate_dataset(self) -> str:
    """Generate dataset files for this variant.
    
    Returns:
        str: Path to generated dataset directory
    
    Raises:
        RuntimeError: If dataset generation fails
    """
```

#### `train_model()` Method

```python
def train_model(self, fast_mode: bool = True) -> TrainingRun:
    """Train model for this variant.
    
    Args:
        fast_mode (bool, optional): Use fast mode settings (default: True)
    
    Returns:
        TrainingRun: Training run with metrics and artifacts
    
    Raises:
        RuntimeError: If training fails
    """
```

#### `evaluate_model()` Method

```python
def evaluate_model(self) -> TrainingRun:
    """Evaluate trained model using BPB metric.
    
    Returns:
        TrainingRun: Evaluation run with BPB metrics
    
    Raises:
        RuntimeError: If evaluation fails
    """
```

#### `run_experiment()` Method

```python
def run_experiment(self, fast_mode: bool = True) -> ExperimentReport:
    """Run complete experiment loop (generate → train → evaluate → report).
    
    Args:
        fast_mode (bool, optional): Use fast mode settings (default: True)
    
    Returns:
        ExperimentReport: Aggregated results with recommendations
    
    Raises:
        RuntimeError: If any step fails
    """
```

#### `generate_comparison_report()` Method

```python
def generate_comparison_report(self, variants: List[ExperimentVariant]) -> ExperimentReport:
    """Generate comparison report across multiple variants.
    
    Args:
        variants (List[ExperimentVariant]): List of variants to compare
    
    Returns:
        ExperimentReport: Comparison report with best run and recommendations
    
    Raises:
        ValueError: If variants list is empty
    """
```

## Input/Output Contracts

### Input: ExperimentVariant

```json
{
  "name": "string (required, unique)",
  "dedup_threshold": "float (0.0-1.0, required)",
  "gold_injection_rate": "float (0.0-1.0, required)",
  "min_length": "int (>0, required)",
  "sample_weighting": "string (uniform|length-weighted|quality-weighted, optional)",
  "created_by": "string (optional)",
  "parent_variant": "string (optional)"
}
```

### Output: TrainingRun

```json
{
  "run_id": "string (UUID)",
  "variant_name": "string",
  "val_bpb": "float (>0)",
  "peak_vram_mb": "float (>0)",
  "mfu_percent": "float (0-100)",
  "total_tokens_M": "float (>0)",
  "axolotl_config_path": "string",
  "tokenizer_path": "string",
  "checkpoint_path": "string",
  "started_at": "ISO 8601 timestamp",
  "completed_at": "ISO 8601 timestamp",
  "duration_seconds": "float (>0)",
  "model_checkpoint": "string",
  "tokenizer_files": ["string"]
}
```

### Output: ExperimentReport

```json
{
  "report_id": "string (UUID)",
  "experiment_name": "string",
  "runs": ["TrainingRun"],
  "baseline_variant": "string (optional)",
  "baseline_metrics": "object (optional)",
  "best_run_id": "string (optional)",
  "best_variant": "string (optional)",
  "recommendations": ["string"],
  "created_at": "ISO 8601 timestamp",
  "researcher": "string (optional)"
}
```

## Error Handling

### Standard Error Responses

All errors return HTTP-like status codes:

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | ValueError | Invalid input parameters |
| 404 | FileNotFoundError | Missing required files |
| 500 | RuntimeError | Internal processing error |

### Error Format

```json
{
  "error_type": "ValueError",
  "message": "Invalid dedup_threshold: must be in range [0.0, 1.0]",
  "field": "dedup_threshold",
  "value": 1.5
}
```

## Versioning

This API is versioned as part of the feature specification:

- **v1**: Initial API (current)
- **v2**: Future enhancements (not yet defined)

Backward compatibility is maintained for all public methods.

## Testing

Unit tests must cover:
- Input validation (all invalid parameter combinations)
- Error handling (missing files, training failures)
- Output format (all fields present and correctly typed)

Integration tests must cover:
- Complete experiment loop (generate → train → evaluate → report)
- Comparison across multiple variants
- Fast mode vs normal mode performance

## Dependencies

This module depends on:
- `src/research/train_tokenizer.py`
- `src/audit/eval_bpb.py`
- `configs/stage_4_training/axolotl/fast_mode.yaml`

## Security

- No external network calls (all operations local)
- No credential handling (uses environment variables)
- Input validation prevents injection attacks
