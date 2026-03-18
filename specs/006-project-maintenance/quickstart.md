# Quickstart: Rapid Experimentation Pipeline

**Feature**: 006-project-maintenance  
**Date**: 2026-03-18  
**Status**: Draft

## Overview

This guide shows how to run a complete experiment loop in under 30 minutes using the rapid experimentation pipeline.

## Prerequisites

- Python 3.11+ installed
- Virtualenv activated: `source .venv/bin/activate`
- Dependencies installed: `pip install -r requirements-dev.txt`
- Axolotl installed: `pip install axolotl`
- vLLM installed: `pip install vllm`

## Quick Start (5 minutes)

### Step 1: Define Your Experiment

Create a simple experiment variant with parameters:

```python
from src.research.experiment_orchestrator import ExperimentOrchestrator, ExperimentVariant

# Define your variant
variant = ExperimentVariant(
    name="test_variant",
    dedup_threshold=0.95,
    gold_injection_rate=0.1,
    min_length=512,
    sample_weighting="uniform",
    created_by="your.email@example.com",
)

# Initialize orchestrator
orchestrator = ExperimentOrchestrator(
    variant=variant,
    axolotl_config="configs/stage_4_training/axolotl/fast_mode.yaml",
    tokenizer_path="data/tokenizers/canonical",
    output_dir="output/experiments/test_variant",
)
```

### Step 2: Run the Experiment

Execute the full pipeline:

```python
# Generate dataset, tokenize, train, evaluate
report = orchestrator.run_experiment(
    fast_mode=True,  # Use small model, short TIME_BUDGET
    validation_shards=10,  # Fixed validation shards for speed
)

# Print summary
print(report.summary)
```

### Step 3: Review Results

Check the generated report:

```python
# Best run
print(f"Best BPB: {report.best_run_id}")
print(f"Best variant: {report.best_variant}")

# Recommendations
for rec in report.recommendations:
    print(f"✓ {rec}")
```

## Full Workflow (10 minutes)

### 1. Create Dataset Variants

Generate multiple dataset variants for comparison:

```python
variants = [
    ExperimentVariant(name="v1", dedup_threshold=0.90, gold_injection_rate=0.05, min_length=256),
    ExperimentVariant(name="v2", dedup_threshold=0.95, gold_injection_rate=0.10, min_length=512),
    ExperimentVariant(name="v3", dedup_threshold=0.98, gold_injection_rate=0.15, min_length=1024),
]

# Generate datasets
for variant in variants:
    orchestrator.generate_dataset(variant)
```

### 2. Train Models

Train models for each variant:

```python
for variant in variants:
    print(f"Training {variant.name}...")
    run = orchestrator.train_model(variant, fast_mode=True)
    print(f"  Val BPB: {run.val_bpb:.4f}")
    print(f"  MFU: {run.mfu_percent:.2f}%")
    print(f"  Peak VRAM: {run.peak_vram_mb:.0f} MB")
```

### 3. Evaluate & Compare

Evaluate all runs and generate comparison report:

```python
# Evaluate all runs
for variant in variants:
    eval_run = orchestrator.evaluate_model(variant)
    print(f"{variant.name}: BPB={eval_run.val_bpb:.4f}")

# Generate comparison report
report = orchestrator.generate_comparison_report(variants)
report.save("output/reports/experiment_comparison.tsv")
```

### 4. Identify Best Configuration

Find the best variant based on efficiency score:

```python
# Find best run
best_run = max(report.runs, key=lambda r: r.efficiency_score)
print(f"Best variant: {best_run.variant_name}")
print(f"Efficiency score: {best_run.efficiency_score:.4f}")

# Get recommendations
for rec in report.recommendations:
    print(f"Recommendation: {rec}")
```

## Configuration

### Fast Mode Settings

Fast mode uses these settings to reduce training time:

- **Model size**: 7B parameters (vs 70B for full training)
- **TIME_BUDGET**: 30 minutes (vs 24 hours for full training)
- **Validation shards**: 10 (vs 100 for full training)
- **Training steps**: 1000 (vs 10000 for full training)

### Axolotl Config

Fast mode uses `configs/stage_4_training/axolotl/fast_mode.yaml`:

```yaml
base_model: mistralai/Mistral-7B-v0.1
gradient_accumulation_steps: 4
micro_batch_size: 1
per_device_train_batch_size: 1
num_epochs: 1
warmup_steps: 10
learning_rate: 2e-5
weight_decay: 0.01
optimizer: adamw_torch
lr_scheduler: linear
warmup_ratio: 0.03
```

## Common Patterns

### Pattern 1: Grid Search

Run a grid search over multiple parameters:

```python
from itertools import product

# Define parameter grid
params = {
    "dedup_threshold": [0.90, 0.95, 0.98],
    "gold_injection_rate": [0.05, 0.10, 0.15],
}

# Generate all combinations
variants = []
for dedup, gold in product(params["dedup_threshold"], params["gold_injection_rate"]):
    variants.append(
        ExperimentVariant(
            name=f"dedup_{dedup}_gold_{gold}",
            dedup_threshold=dedup,
            gold_injection_rate=gold,
            min_length=512,
        )
    )

# Run experiments
for variant in variants:
    orchestrator.run_experiment(variant)
```

### Pattern 2: Iterative Refinement

Iteratively refine based on previous results:

```python
# Run initial experiment
initial_variant = ExperimentVariant(name="initial", dedup_threshold=0.90, gold_injection_rate=0.05)
initial_report = orchestrator.run_experiment(initial_variant)

# Refine based on results
refined_variant = ExperimentVariant(
    name="refined",
    dedup_threshold=0.95,  # Increased from 0.90
    gold_injection_rate=0.10,  # Increased from 0.05
    min_length=512,
    parent_variant="initial",
)

# Run refined experiment
refined_report = orchestrator.run_experiment(refined_variant)

# Compare results
print(f"Improvement: {initial_report.best_run.val_bpb - refined_report.best_run.val_bpb:.4f} BPB")
```

### Pattern 3: Ablation Study

Run ablation studies to understand component contributions:

```python
# Baseline
baseline = ExperimentVariant(name="baseline", dedup_threshold=0.95, gold_injection_rate=0.0)

# Ablation 1: No deduplication
no_dedup = ExperimentVariant(name="no_dedup", dedup_threshold=1.0, gold_injection_rate=0.0)

# Ablation 2: No gold injection
no_gold = ExperimentVariant(name="no_gold", dedup_threshold=0.95, gold_injection_rate=0.0)

# Run ablations
for variant in [baseline, no_dedup, no_gold]:
    report = orchestrator.run_experiment(variant)
    print(f"{variant.name}: BPB={report.best_run.val_bpb:.4f}")
```

## Troubleshooting

### Issue: Training takes too long

**Solution**: Reduce TIME_BUDGET in Axolotl config:

```yaml
# In configs/stage_4_training/axolotl/fast_mode.yaml
time_budget_minutes: 15  # Reduce from 30
```

### Issue: Out of memory

**Solution**: Reduce micro_batch_size:

```yaml
# In configs/stage_4_training/axolotl/fast_mode.yaml
micro_batch_size: 1  # Reduce from 2 or 4
```

### Issue: BPV is very high (>10)

**Solution**: Check dataset quality:

```python
# Verify dataset
from src.audit.dataset_health_check import check_dataset_quality
quality = check_dataset_quality(variant.dataset_path)
print(f"Dataset quality: {quality.score:.2f}")
```

## Next Steps

- Read [docs/experiments.md](docs/experiments.md) for detailed documentation
- Review [data-model.md](data-model.md) for entity definitions
- Check [configs/stage_4_training/axolotl/README.md](configs/stage_4_training/axolotl/README.md) for tokenizer guidance

## Success Criteria

✅ **Completed when**:
- Experiment loop runs in <30 minutes
- All 10 variant comparisons complete in <5 minutes
- Documentation allows new researcher to run first experiment in <10 minutes
- Zero CI failures due to style violations (after formatting)
