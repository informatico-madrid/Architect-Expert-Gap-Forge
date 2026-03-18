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

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| API connection failed | Check `api_url` in config and ensure vLLM is running |
| Missing HA metadata | Ensure GAP files are properly formatted |
| Out of memory | Reduce batch size in config |

### Debug Mode

```bash
python -m src.research.experiment_orchestrator \
  --config configs/stage_5_evaluation/eval_config.yaml \
  --debug
```
