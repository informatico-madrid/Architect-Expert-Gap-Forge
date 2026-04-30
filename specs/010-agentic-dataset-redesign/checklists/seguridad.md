# Checklist: Seguridad — Gestión de Secrets y Cumplimiento

**Purpose**: Verificar que la especificación cubre la seguridad operativa y de datos.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Se exige que todas las API keys y credenciales se obtengan vía variables de entorno y no se guarden en el repo? [Security, Assumptions]
- [ ] CHK002 - ¿Existen archivos `*.example` y documentación para configurar credenciales de forma segura? [Completeness]
- [ ] CHK003 - ¿Los logs y reportes están sanitizados para evitar exponer secretos? [Security]
- [ ] CHK004 - ¿Se documenta el control de acceso para ejecutar Stage 2 (quién puede lanzar generación masiva)? [Coverage]
- [ ] CHK005 - ¿Se verifica la licencia y compatibilidad legal de los datasets ancla antes de uso? [Compliance, Spec §FR-009]
- [ ] CHK006 - ¿Se ha considerado un threat model para llamadas a herramientas maliciosas o inyecciones vía argumentos? [Ambiguity]
- [ ] CHK007 - ¿Se describen medidas de soft-quarantine para registros sospechosos y su revisión manual? [Edge Case]
