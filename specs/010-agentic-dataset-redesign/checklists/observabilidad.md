# Checklist: Observabilidad — Métricas y Alertas

**Purpose**: Asegurar que los requisitos cubren métricas, trazas y alertas operativas.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Se enumeran las métricas clave a recoger en Stage 2/3 (latencia, errores, coste por token)? [Measurability]
- [ ] CHK002 - ¿Se especifican las trazas y logs necesarios para depurar fallos de generación y mezcla? [Traceability]
- [ ] CHK003 - ¿Están definidas las alertas (umbral, destinatarios) para errores repetidos o picos de latencia? [Non-Functional]
- [ ] CHK004 - ¿Se documenta cómo se correlacionan logs de API con artefactos (seed, batch_id, timestamp)? [Consistency]
- [ ] CHK005 - ¿Se especifica retención y acceso a métricas para auditoría y debugging? [Coverage]
