# Checklist: Datos — Calidad y Mezcla de Datasets

**Purpose**: Validar requisitos de datos: normalización, mezcla 30/70, deduplicado y esquema ChatML.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Están listados los datasets ancla con versiones concretas y enlaces (HF IDs)? [Completeness, Spec §FR-009]
- [ ] CHK002 - ¿Se especifica el esquema ChatML objetivo (campo `messages`, roles, content)? [Clarity, Spec §FR-010]
- [ ] CHK003 - ¿Está documentado el algoritmo de mezcla de tokens y la tolerancia objetivo (30%/70%)? [Measurability, Spec §FR-012]
- [ ] CHK004 - ¿Se define el método de deduplicado (hash exacto, normalización previa) y su alcance (intra/inter-dataset)? [Coverage, Spec §FR-014]
- [ ] CHK005 - ¿Se especifica la validación y rechazo de registros no-convertibles a ChatML sin pérdida semántica? [Ambiguity, Spec §FR-011]
- [ ] CHK006 - ¿Está definido el formato y los campos obligatorios del JSONL final (metadata: origin, type, use_case, token_count, format)? [Clarity, Spec §Registro de Dataset]
- [ ] CHK007 - ¿Se documenta la validación de `no-call` (qué constituye no-call y reglas para descartes)? [Edge Case, Spec §FR-015]
- [ ] CHK008 - ¿Se detalla la semilla de shuffle, reproducibilidad bit-a-bit y cómo regenerar el JSONL único? [Traceability, Spec §FR-013]
- [ ] CHK009 - ¿Se describe el reporte de composición de Stage 3 (campos, muestreo, motivos de descarte)? [Acceptance, Spec §FR-016]
- [ ] CHK010 - ¿Hay límites y controles para submuestrear datasets ancla grandes para cumplir proporciones token? [Coverage, Spec §FR-012]
