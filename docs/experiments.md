# Rapid Experimentation Pipeline

> Guide for running quick experiments with different model configurations and evaluation strategies.

---

## Overview

The rapid experimentation pipeline enables fast iteration on model configurations, prompts, and evaluation strategies. This document covers how to set up and run experiments using the Stage 6 evaluation infrastructure.

## Quick Start

### Running a Simple Experiment

```bash
# Run evaluation with default configuration
python -m src.research.experiment_orchestrator --config configs/stage_5_evaluation/eval_config.yaml

# Run with custom parameters
python -m src.research.experiment_orchestrator \
  --config configs/stage_5_evaluation/eval_config.yaml \
  --professor-backend vllm \
  --judge-model custom-judge
```

### Configuration Files

Key configuration locations:

| Stage | Config Path | Purpose |
|-------|-------------|---------|
| Stage 4 (Training) | `configs/stage_4_training/` | Axolotl training configs |
| Stage 5 (Evaluation) | `configs/stage_5_evaluation/` | Evaluation and judgment |
| Stage 6 (Calibration) | `configs/stage_6_calibration/` | Parameter optimization |

## Experiment Workflow

### 1. Define Parameters

Create or modify a configuration file:

```yaml
# configs/stage_5_evaluation/my_experiment.yaml
professor_backend: "vllm"
judge_model: "custom-judge"
api_url: "http://localhost:8000/v1"
audit_dir: "data/my_experiment"
gap_dir: "data/Gap"
```

### 2. Run Evaluation

```bash
python -m src.audit.cli evaluate --config configs/stage_5_evaluation/my_experiment.yaml
```

### 3. Analyze Results

Results are stored in the audit directory with the following structure:

```
data/my_experiment/
├── exams/           # Generated exam questions
├── inferences/      # Model responses
├── scorecards/      # Evaluation scores
└── reports/        # Final analysis reports
```

## BPB Evaluation

Bits-Per-Byte (BPB) evaluation provides compression-based quality metrics:

```python
from src.audit.eval_bpb import calculate_bpb, aggregate_bpb_metrics

# Calculate BPB for a single prediction
score = calculate_bpb(predicted="model output", target="reference text")

# Aggregate metrics across multiple samples
from src.audit.eval_bpb import evaluate_bpb_scores
scores = evaluate_bpb_scores(predictions, targets)
metrics = aggregate_bpb_metrics(scores)
print(f"Mean BPB: {metrics['mean']:.4f}")
```

## Integration with Training

### Fine-tuning Workflow

1. **Generate Training Data** → Use Stage 2 curation pipeline
2. **Train Model** → Use Stage 4 Axolotl configs
3. **Evaluate** → Run Stage 5/6 evaluation
4. **Iterate** → Adjust parameters and repeat

### Axolotl Configuration

See `configs/stage_4_training/axolotl/README.md` for detailed Axolotl setup instructions.

## Results Registration

Experiment results are automatically registered in TSV format for tracking and comparison.

### TSV Results File

Results are stored in `experiments/experiment_results.tsv` with the following columns:

| Column | Description |
|--------|-------------|
| experiment_name | Unique experiment identifier |
| variant | Model variant tested |
| fast_mode | Whether fast mode was used |
| status | Experiment status (completed, failed, running) |
| start_time | Experiment start timestamp |
| end_time | Experiment end timestamp |
| duration_seconds | Total duration |
| val_bpb | Validation bits-per-byte score |
| peak_vram_mb | Peak VRAM usage in MB |
| mfu_percent | Model FLOPs utilization percentage |
| total_tokens_M | Total tokens processed (millions) |
| num_epochs | Number of training epochs |
| batch_size | Training batch size |
| learning_rate | Learning rate used |
| max_steps | Maximum training steps |
| train_samples | Number of training samples |
| eval_samples | Number of evaluation samples |
| checkpoint_path | Path to model checkpoint |
| error | Error message if failed |

### Using the Results Registry

```python
from src.research.experiment_orchestrator import ResultsRegistry, ExperimentOrchestrator

# Create registry manually
registry = ResultsRegistry(results_dir="experiments")

# Query results
results = registry.query_results(variant="phi-2", status="completed")

# Get best result by val_bpb
best = registry.get_best_result(metric="val_bpb")

# Export to CSV
registry.export_to_csv("results.csv")

# Using orchestrator (auto-registers results)
orch = ExperimentOrchestrator(experiment_dir="experiments")
report = orch.run_experiment("my_exp", "phi-2", fast_mode=True)
# Results are automatically registered
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| AEGF_RESULTS_DIR | Results directory | "experiments" |
| AEGF_EXPERIMENT_DIR | Experiment directory | "experiments" |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| API connection failed | Check `api_url` in config and ensure vLLM is running |
| Missing HA metadata | Ensure GAP files are properly formatted |
| Out of memory | Reduce batch size in config |
| Results not saving | Check write permissions on results directory |

### Debug Mode

```bash
python -m src.research.experiment_orchestrator \
  --config configs/stage_5_evaluation/eval_config.yaml \
  --debug
```
