# Checklist: Rendimiento — Non-Functional Requirements

**Purpose**: Asegurar que los requisitos de rendimiento y recursos estén definidos y medibles.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Se define el tiempo máximo para generar el reporte de composición (SC-008) y está medido con dataset de referencia? [Measurability, Spec §SC-008]
- [ ] CHK002 - ¿Se documenta la tolerancia de tiempo adicional por NEFTune (<10%) y la métrica para comprobarlo? [Performance, Spec §SC-006]
- [ ] CHK003 - ¿Están justificadas `sequence_len`, `sample_packing`, y `pad_to_sequence_len` en el config de entrenamiento? [Clarity]
- [ ] CHK004 - ¿Se han definido requisitos mínimos de hardware (CPU, RAM, disco) para Stage 2 y Stage 3? [Coverage]
- [ ] CHK005 - ¿Se valida la configuración de `micro_batch_size` y `gradient_accumulation_steps` para evitar OOM en GPUs objetivo? [Coverage]
- [ ] CHK006 - ¿Existen métricas y alertas (p95 latency, GPU memory) para monitorizar cargas y fallos en producción? [Non-Functional]
- [ ] CHK007 - ¿Se describen estrategias de mitigación ante OOM o tiempos excesivos (split, submuestreo, reduce packing)? [Edge Case]
