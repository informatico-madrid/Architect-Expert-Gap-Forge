# Checklist: API — Calidad de Requisitos

**Purpose**: Verificar la calidad y cobertura de los requisitos relacionados con APIs y el `TeacherModelClient`.
**Created**: 2026-03-19
**Feature**: [spec.md](../spec.md)

---

- [ ] CHK001 - ¿Están especificados los formatos de respuesta y códigos de error para todos los escenarios de fallo de la API del Teacher? [Completeness, Spec §FR-008c]
- [ ] CHK002 - ¿Está documentada la política de reintentos y backoff (códigos objetivo, max_retries, backoff_factor)? [Clarity, Spec §FR-008c]
- [ ] CHK003 - ¿Se define claramente el mecanismo de autenticación y la gestión de credenciales (env vars, nombres de variables)? [Security, Assumptions]
- [ ] CHK004 - ¿Se especifican límites de tasa (rate limits) esperados y parámetros configurables (`request_delay_ms`)? [Coverage, Spec §FR-008c]
- [ ] CHK005 - ¿Se ha definido el comportamiento idempotente e identificación de seeds para evitar duplicados en llamadas reentrantes? [Consistency, Spec §FR-008c]
- [ ] CHK006 - ¿Están definidos los requisitos de logging y monitorización para llamadas a la API (métricas, trazas, coste estimado)? [Non-Functional, Spec §FR-008c]
- [ ] CHK007 - ¿Se documenta el esquema de errores transitorios vs permanentes y la acción esperada ante cada uno? [Clarity, Spec §FR-008c]
- [ ] CHK008 - ¿La configuración `teacher_model.*` está tipada y tiene validación (provider, model_name, api_key_env)? [Traceability, Spec §FR-008b]
- [ ] CHK009 - ¿Se especifica un mecanismo para estimar y reportar costes de generación por lote/seed? [Measurability, Spec §FR-008c]
