# Checklist: QA y Validación — Pruebas y CI

**Purpose**: Comprobar que los requisitos incluyen pruebas automáticas, validadores y entrampas de QA.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Se requieren tests unitarios e integrados para `TeacherModelClient`, generador y mixer? [Completeness]
- [ ] CHK002 - ¿Se define un esquema JSON Schema/Pydantic y fixtures de ejemplo para validación? [Clarity]
- [ ] CHK003 - ¿Qué cobertura mínima de tests se exige (p.ej. cobertura de módulos críticos)? [Measurability]
- [ ] CHK004 - ¿Se describen jobs de CI para header checks, lint, tests y check-prerequisites? [Traceability]
- [ ] CHK005 - ¿Están las instrucciones para ejecutar pruebas locales y reproducir fallos en CI? [Clarity]
- [ ] CHK006 - ¿Se documenta la verificación del JSONL final en CI antes de permitir el entrenamiento? [Acceptance, Spec §FR-020]
