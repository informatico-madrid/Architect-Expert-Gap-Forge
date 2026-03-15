# Quickstart: Inference Calibration Suite (Stage 6)

## Overview

The Calibration Suite automates the search for optimal sampling parameters for your SFT model. It uses the existing Professor Judge as a reward function to evaluate different parameter configurations.

## Prerequisites

1. **vLLM server running** with your SFT model deployed
2. **Professor Judge configured** (same as Stage 5)
3. **5-10 investigation prompts** in YAML format (see example prompts below)

## Installation

No additional installation required. The calibration module is part of the existing `src/audit` package.

## Usage

### 1. Prepare Your Prompts

Create a YAML file with your investigation prompts. Use the example file as template:

```bash
# Copy the example prompts
cp configs/stage_6_calibration/calibration_prompts.example.yaml \
   configs/stage_6_calibration/calibration_prompts.yaml

# Edit with your custom prompts
vim configs/stage_6_calibration/calibration_prompts.yaml
```

Example prompts are "psychological test" type questions designed to evaluate reasoning depth:

```yaml
- id: calibration_prompt_001
  question: |
    A detective arrives at a crime scene... Analyze each suspect's potential motive.
  type: investigation
  expected_reasoning_depth: high
```

The prompts should require deep reasoning, not simple factual recall.

### 2. Run Calibration

```bash
# Using the CLI (basic)
python -m src.audit.cli calibrate \
  --prompts configs/stage_6_calibration/calibration_prompts.yaml \
  --output-dir ./calibration_results

# Recommended: Use noxious filter to reduce iterations
python -m src.audit.cli calibrate \
  --prompts configs/stage_6_calibration/calibration_prompts.yaml \
  --use-noxious-filter \
  --output-dir ./calibration_results

# With intelligent calibration (uses prompt metadata)
python -m src.audit.cli calibrate \
  --prompts configs/stage_6_calibration/calibration_prompts.yaml \
  --use-prompt-metadata \
  --output-dir ./calibration_results

# Or import programmatically
from src.audit.calibration import run_calibration

results = run_calibration(
    prompts=prompts_list,
    output_dir="./calibration_results",
    use_noxious_filter=True,  # Reduce iterations
)
```

### Output Format

Each iteration shows progress and scores:

```
▶ [1/135000] P001 @ temperature=0.3 top_p=0.8 top_k=40 min_p=0.05 repetition_penalty=1.2
    📊 composite=0.085 adjusted=0.085 ↑ +0.017 | parameter_effectiveness=0.85 task_completion=0.95... | words=892
    🎯 Target params: top_k, presence_penalty
    🏆 NEW BEST! Profile: temperature=0.3 top_p=0.8...
```

- `↑ +0.017` = better than previous iteration
- `↓ -0.023` = worse than previous iteration
- `words` = response word count

### 3. Review Results

After completion, you'll find:

```
calibration_results/
├── calibration_report.json   # Full results with all profiles
├── vllm_config.yaml         # Optimal parameters ready to use
└── checkpoints/            # Intermediate progress (for resume)
```

### 4. Apply Optimal Parameters

Edit your vLLM deployment config:

```yaml
# vllm_config.yaml
temperature: 0.6
top_k: 40
min_p: 0.05
repetition_penalty: 1.15
```

## Configuration

### Parameter Grid

The default expanded search space is:

| Parameter | Values | Default Pivot |
|-----------|--------|---------------|
| temperature | 0.3, 0.5, 0.6, 0.7, 0.9, 1.1 | 0.6 |
| top_p | 0.7, 0.8, 0.9, 0.95, 1.0 | 0.9 |
| top_k | 5, 10, 20, 40, 60, 80 | 20 |
| min_p | 0.0, 0.02, 0.05, 0.1, 0.15 | 0.0 |
| repetition_penalty | 1.0, 1.05, 1.1, 1.15, 1.2 | 1.0 |
| presence_penalty | 0.0, 0.5, 1.0, 1.5, 2.0 | 1.0 |

**Total combinations:** 6 × 5 × 6 × 5 × 5 × 5 = **18,750 profiles**

**Use `--use-noxious-filter`** to automatically discard "noxious" values that consistently perform worse than the pivot (reduces to ~500-2000 iterations).

### Custom Grids

You can override the default parameter grid:

```python
from src.audit.calibration_schema import SamplingProfile, PARAM_GRIDS

# Custom grid
custom_grid = {
    "temperature": [0.4, 0.5, 0.6, 0.7, 0.8],
    "top_k": [10, 20, 40],
    "min_p": [0.0, 0.05, 0.1],
    "repetition_penalty": [1.0, 1.1, 1.2]
}
```

## Resume Interrupted Runs

If the calibration is interrupted, it can resume from the last checkpoint:

```bash
python -m src.audit.cli calibrate \
  --prompts configs/stage_6_calibration/calibration_prompts.yaml \
  --output-dir ./calibration_results \
  --resume
```

The system will automatically detect existing checkpoints and continue from where it left off.

## Understanding Results

### Composite Score

The composite score is a weighted average:

| Dimension | Weight |
|-----------|--------|
| ha_modernity | 0.30 |
| reasoning_depth | 0.25 |
| functionality | 0.25 |
| completeness | 0.12 |
| style | 0.08 |

### Length Penalty

Responses shorter than 200 words receive a proportional penalty:

```
adjusted_score = composite_score × (response_length / 200)
```

This ensures the model provides substantial responses for investigation tasks.

## Troubleshooting

### Judge Fails to Score

If the Judge fails on a particular response, the system logs the error and continues with the next profile. Check `calibration_report.json` for details.

### Slow Performance

- Reduce the parameter grid size
- Use fewer prompts
- Ensure vLLM server has sufficient GPU memory

### Memory Issues

The system processes one prompt at a time to minimize memory usage. If you encounter OOM errors, reduce batch size in the config.
