# Axolotl Training Configuration

> Guide for configuring Axolotl fine-tuning jobs in the AEGF pipeline.

---

## Overview

Axolotl is a lightweight fine-tuning framework that supports various training strategies including LoRA, QLoRA, and full-parameter training. This directory contains configuration templates and guidelines for Stage 4 (Training) of the AEGF pipeline.

## Quick Start

### 1. Create Your Configuration

Copy the example config and modify for your setup:

```bash
cp config.yaml.example config.yaml
```

### 2. Update Required Fields

Key fields to configure:

| Field | Description | Example |
|-------|-------------|---------|
| `base_model` | Path to base model | `./models/phi-3.5-mini` |
| `adapter` | Training strategy | `lora`, `qlora`, or `full` |
| `learning_rate` | Learning rate | `1e-4` to `1e-5` |
| `num_epochs` | Number of epochs | `1` to `5` |
| `datasets` | Training data paths | See format below |

### 3. Prepare Dataset

Format your data as JSONL with chat template:

```json
{"conversation": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

### 4. Run Training

```bash
axolotl train configs/stage_4_training/axolotl/config.yaml
```

## Configuration Options

### Adapter Types

```yaml
# LoRA (Recommended for most cases)
adapter: lora
lora_r: 8
lora_alpha: 16
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj

# QLoRA (For limited GPU memory)
adapter: qlora
lora_r: 64
lora_alpha: 16

# Full parameter training
adapter: full
```

### Dataset Format

```yaml
datasets:
  - path: data/my_training_data.jsonl
    type: chat_template
    field_messages: conversation
    train_on_responses_only: true
    message_field_role: role
    message_field_content: content
```

### Hardware Configurations

| GPU Memory | Recommended Config |
|------------|-------------------|
| 24GB | `load_in_4bit: true`, `adapter: qlora` |
| 48GB | `load_in_8bit: true`, `adapter: lora` |
| 80GB+ | `adapter: full`, `bf16: true` |

## Integration with Pipeline

### Stage 4 Workflow

```
Stage 3 (Curation) → Stage 4 (Training) → Stage 5 (Evaluation)
       ↑                                        |
       └────────────── Feedback <───────────────┘
```

### Combining Multiple Datasets

```yaml
datasets:
  - path: data/expert_generated.jsonl
    type: chat_template
    weight: 1.0
  - path: data/synthetic_augmented.jsonl
    type: chat_template
    weight: 0.5
```

## Monitoring

### Weights & Biases Integration

```yaml
wandb_project: aEGF-training
wandb_run_name: my-experiment
```

### Local Logging

Logs are saved to `outputs/` directory with:
- Training metrics
- Checkpoints
- Final model weights

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OOM errors | Enable `load_in_4bit` or reduce `batch_size` |
| Slow training | Enable `sample_packing: true` |
| Poor quality | Adjust `learning_rate` or increase `num_epochs` |

## Examples

See `config.yaml.example` for a complete template with all available options.
