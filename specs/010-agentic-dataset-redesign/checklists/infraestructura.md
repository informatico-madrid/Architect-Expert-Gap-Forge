# Checklist: Infraestructura — Artefactos y Resiliencia

**Purpose**: Validar requisitos infraestructurales: checkpoints, paths, backup y reanudo.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Está documentado el path de checkpoint por defecto y su formato en disco (`teacher_model.checkpoint_path`)? [Traceability, Spec §FR-008c]
- [ ] CHK002 - ¿Se define el comportamiento de reanudo (resume) tras fallo y qué se guarda en cada checkpoint? [Clarity]
- [ ] CHK003 - ¿Se indican requisitos de almacenamiento (espacio esperado, TTL, política de backups)? [Performance]
- [ ] CHK004 - ¿Están especificadas las rutas y nombres de artefactos (JSONL final, reportes, logs) y su convención? [Consistency]
- [ ] CHK005 - ¿Se documenta la política de retención y quién puede borrar artefactos antiguos? [Coverage]
- [ ] CHK006 - ¿Se define la semilla de shuffle y cómo se registra para reproducción en infra? [Traceability, Spec §FR-013]
