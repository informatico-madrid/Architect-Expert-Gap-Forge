# Checklist: Entrenamiento — Configuración y Validación

**Purpose**: Verificar que la configuración de entrenamiento (Axolotl) cumple la spec para NEFTune, LoRA y dataset único.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Está `neftune_noise_alpha` presente y validado en el YAML con rango [5,15]? [Clarity, Spec §FR-017]
- [ ] CHK002 - ¿`num_epochs` está fijado a 2 para el caso Home Assistant o es configurable con validación? [Acceptance, Spec §FR-018]
- [ ] CHK003 - ¿Los parámetros LoRA (`lora_r`, `lora_alpha`, `peft_use_rslora`) coinciden con la spec? [Consistency, Spec §FR-019]
- [ ] CHK004 - ¿El `axolotl.yaml` referencia exclusivamente el único archivo JSONL pre-procesado de Stage 3? [Traceability, Spec §FR-020]
- [ ] CHK005 - ¿Están definidos `val_set_size`, `eval_steps` y `early_stopping_patience` acordes a SC-006 y SC-008? [Measurability, Spec §SC-006]
- [ ] CHK006 - ¿Se documenta cómo se registra NEFTune en WandB y qué métricas se deben monitorizar? [Traceability, Spec §FR-017]
- [ ] CHK007 - ¿Se verificó compatibilidad con Deepspeed/FP configs actuales y límites de memoria? [Non-Functional, Spec §FR-018]
- [ ] CHK008 - ¿Hay un paso de validación previo al entrenamiento que verifique el esquema del JSONL y la proporción 30/70? [Coverage, Spec §FR-012]
