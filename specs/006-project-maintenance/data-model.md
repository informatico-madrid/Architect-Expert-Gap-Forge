# Data Model: Project Maintenance

**Feature**: 006-project-maintenance  
**Date**: 2026-03-18  
**Status**: Draft

## Overview

This document defines the core data entities for the rapid experimentation pipeline and project maintenance tasks.

## Entities

### ExperimentVariant

Represents a unique combination of dataset parameters for experimentation.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass(frozen=True, slots=True)
class ExperimentVariant:
    """Unique combination of dataset parameters."""
    
    # Identifier
    name: str  # e.g., "dedup_0.95_gold_0.1"
    
    # Parameters
    dedup_threshold: float  # Fuzzy deduplication threshold (0.0-1.0)
    gold_injection_rate: float  # Percentage of gold records to inject (0.0-1.0)
    min_length: int  # Minimum sequence length
    sample_weighting: str  # "uniform", "length-weighted", "quality-weighted"
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # e.g., "researcher@company.com"
    parent_variant: Optional[str] = None  # Parent variant name for iterative experiments
    
    # Computed fields
    @property
    def description(self) -> str:
        return f"dedup={self.dedup_threshold:.2f},gold={self.gold_injection_rate:.2f},min_len={self.min_length}"
```

**Validation Rules**:
- `dedup_threshold`: Must be in range [0.0, 1.0]
- `gold_injection_rate`: Must be in range [0.0, 1.0]
- `min_length`: Must be > 0
- `name`: Must be unique across all variants

### TrainingRun

Represents a single training execution with metrics and artifacts.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass(frozen=True, slots=True)
class TrainingRun:
    """Single training execution with metrics and artifacts."""
    
    # Identifier
    run_id: str  # UUID or deterministic hash
    variant_name: str  # Parent ExperimentVariant
    
    # Metrics
    val_bpb: float  # Validation bits per byte (lower is better)
    peak_vram_mb: float  # Peak VRAM usage in MB
    mfu_percent: float  # Model FLOPs Utilization percentage
    total_tokens_M: float  # Total tokens processed in millions
    
    # Configuration
    axolotl_config_path: str  # Path to Axolotl YAML config
    tokenizer_path: str  # Path to tokenizer files
    checkpoint_path: str  # Path to model checkpoint
    
    # Metadata
    started_at: datetime
    completed_at: datetime
    duration_seconds: float  # Computed field
    
    # Artifacts
    model_checkpoint: str  # Path to model.safetensors
    tokenizer_files: list[str]  # List of tokenizer files (vocab.json, merges.txt, etc.)
    
    # Computed fields
    @property
    def efficiency_score(self) -> float:
        """Higher is better: low BPB, high MFU, low VRAM.
        
        Formula: (1.0 / val_bpb) * mfu_percent / (peak_vram_mb / 1000)
        """
        return (1.0 / self.val_bpb) * self.mfu_percent / (self.peak_vram_mb / 1000)
```

**Validation Rules**:
- `val_bpb`: Must be > 0 (valid BPB range typically 1.0-10.0)
- `peak_vram_mb`: Must be > 0
- `mfu_percent`: Must be in range [0.0, 100.0]
- `total_tokens_M`: Must be > 0
- `duration_seconds`: Must be > 0

**Implementation**: Task 2.5 - Create TrainingRun dataclass

### TokenizerConfig

Defines the canonical BPE tokenizer configuration.

```python
from dataclasses import dataclass, field
from typing import Set

@dataclass(frozen=True, slots=True)
class TokenizerConfig:
    """BPE tokenizer configuration."""
    
    # Core settings
    vocab_size: int  # Vocabulary size (e.g., 32000, 64000)
    vocab_file: str  # Path to vocab.json
    merges_file: str  # Path to merges.txt
    
    # Settings
    byte_fallback: bool  # Whether to use byte-fallback for unknown tokens
    trim_offsets: bool  # Whether to trim offsets in merges
    
    # Added tokens (for model compatibility)
    added_tokens: Set[str] = field(default_factory=set)  # Tokens added to base vocab
    
    # Axolotl compatibility
    axolotl_compatible: bool = True  # Whether tokenizer is compatible with Axolotl
    
    # Computed fields
    @property
    def embedding_expansion_needed(self) -> bool:
        """Whether model embeddings need to be expanded."""
        return len(self.added_tokens) > 0
    
    @property
    def embedding_expansion_size(self) -> int:
        """Number of new embeddings needed."""
        return len(self.added_tokens)
```

**Validation Rules**:
- `vocab_size`: Must be > 0
- `byte_fallback`: Boolean only
- `trim_offsets`: Boolean only

### ExperimentReport

Aggregated results from an experiment run with comparison and recommendations.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True, slots=True)
class ExperimentReport:
    """Aggregated experiment results with recommendations."""
    
    # Identification
    report_id: str  # UUID
    experiment_name: str  # e.g., "v1_dedup_threshold_scan"
    
    # Results
    runs: List[TrainingRun]  # List of training runs
    
    # Comparison
    baseline_variant: Optional[str] = None  # Variant to compare against
    baseline_metrics: Optional[dict] = None  # Baseline metrics dict
    
    # Best run
    best_run_id: Optional[str] = None  # Run with best efficiency_score
    best_variant: Optional[str] = None  # Variant of best run
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)  # Actionable recommendations
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    researcher: Optional[str] = None
    
    # Computed fields
    @property
    def summary(self) -> dict:
        """Summary statistics for the experiment."""
        if not self.runs:
            return {}
        
        return {
            "total_runs": len(self.runs),
            "avg_val_bpb": sum(r.val_bpb for r in self.runs) / len(self.runs),
            "best_val_bpb": min(r.val_bpb for r in self.runs),
            "avg_mfu_percent": sum(r.mfu_percent for r in self.runs) / len(self.runs),
            "total_tokens_M": sum(r.total_tokens_M for r in self.runs),
        }
```

**Validation Rules**:
- `runs`: Must be non-empty list
- `recommendations`: Must be non-empty if best_run_id is set

## Relationships

### ExperimentVariant → TrainingRun
- One-to-Many: One variant can have multiple training runs (e.g., different seeds, hyperparameters)
- Foreign key: `TrainingRun.variant_name` references `ExperimentVariant.name`

### ExperimentVariant → ExperimentReport
- One-to-Many: One experiment can have multiple reports (e.g., incremental runs)
- Foreign key: `ExperimentReport.experiment_name` references `ExperimentVariant.name`

### TrainingRun → TokenizerConfig
- Many-to-One: Multiple training runs can use the same tokenizer
- Foreign key: `TrainingRun.tokenizer_path` references `TokenizerConfig`

### ExperimentReport → TrainingRun
- Many-to-One: One report contains multiple training runs
- Foreign key: `ExperimentReport.runs` is a list of `TrainingRun` objects

## Data Flow

1. **Create Variant**: Researcher defines `ExperimentVariant` with parameters
2. **Generate Dataset**: Variant parameters generate dataset files
3. **Train Model**: `train_tokenizer.py` and training pipeline create `TrainingRun`
4. **Evaluate**: `eval_bpb.py` computes metrics for `TrainingRun`
5. **Orchestrate**: `experiment_orchestrator.py` coordinates the full loop
6. **Report**: Results aggregated into `ExperimentReport` with recommendations

## Storage

All data is stored as:
- **JSON**: Variant metadata, experiment reports
- **TSV**: Tabular results for quick comparison
- **SQLite**: Optional database for experiment tracking (future enhancement)

## Extensibility

New entities can be added by:
1. Defining new dataclass with `@dataclass(frozen=True, slots=True)`
2. Adding validation rules in docstring
3. Updating data flow diagram
4. Adding migration script if modifying existing entities
