# Plan: Soporte para Múltiples Ralph Loops Concurrentes

## Objetivo

Permitir ejecutar múltiples instancias de Ralph Loop simultáneamente en diferentes specs sin conflictos de estado.

## Problema Actual

1. **Lock global único** (`/tmp/ralph-test.lock`) - bloquea todos los loops
2. **Estado JSON compartido** (`state.json`) - riesgo de corrupción

## Solución Propuesta

### 1. Lock Específico por Spec

**Ubicación actual:** Línea 1278-1285 en `.ralph/ralph-loop.sh`

```bash
# CAMBIO: De lock global a lock por spec
# ANTES:
exec 9>/tmp/ralph-test.lock
# DESPUÉS:
LOCK_FILE="/tmp/ralph-lock-${SLUG}.lock"
exec 9>"$LOCK_FILE"
```

**Slugs de ejemplo:**
- `specs/001-stage1-discovery` → `001-stage1-discovery`
- `specs/010-agentic-dataset-redesign` → `010-agentic-dataset-redesign`

### 2. Estado JSON por Spec

**Ubicación actual:** Línea 238 en `.ralph/ralph-loop.sh`

```bash
# CAMBIO: De estado único a estado por spec
# ANTES:
STATE_FILE="$PROJECT_DIR/.ralph/state.json"
# DESPUÉS:
STATE_FILE="$PROJECT_DIR/.ralph/state-${SLUG}.json"
```

**Archivos de estado:**
- `.ralph/state-001-stage1-discovery.json`
- `.ralph/state-010-agentic-dataset-redesign.json`

## Cambios Requeridos

### Archivo: `.ralph/ralph-loop.sh`

| Línea(s) | Cambio |
|----------|--------|
| 238 | `STATE_FILE` usar slug |
| ~190 | Definir `SLUG` desde `SPEC_DIR` |
| 1278-1285 | `LOCK_FILE` usar slug |
| 1068-1070 | Verificar estado existente por spec |
| 1028 | Limpiar `state.json.tmp` genérico |

### Archivo: `.ralph/scripts/merge_state.py`

| Cambio | Descripción |
|--------|-------------|
| Soporte múltiples archivos | Aceptar `--state-file` como argumento |
| Mantener backward compatibility | Si no se especifica, usar `state.json` |

##Diagrama de Flujo

```mermaid
graph TD
    A[Inicio ralph-loop.sh] --> B[Extraer SLUG de SPEC_DIR]
    B --> C{STATE_FILE existe?}
    C -->|No| D[init_state con state-{SLUG}.json]
    C -->|Sí| E[resume_mode con state-{SLUG}.json]
    D --> F[Crear LOCK_FILE=/tmp/ralph-lock-{SLUG}.lock]
    E --> F
    F --> G[Adquirir flock específico]
    G --> H[Loop principal]
    H --> I[update_state en state-{SLUG}.json]
    I --> J[¿Otra iteración?]
    J -->|Sí| H
    J -->|No| K[Fin]
```

## Backward Compatibility

- Si se ejecuta con `--resume` y existe `state.json` (viejo formato), migrar automáticamente
- warning en logs si se detecta formato antiguo

## Testing

1. Ejecutar dos loops en specs diferentes simultáneamente
2. Verificar que cada uno usa su propio lock
3. Verificar que cada uno usa su propio state file
4. Verificar que los worktrees son independientes

## Risk Assessment

| Riesgo | Mitigación |
|--------|------------|
| Lock file leftover | Cleanup en trap EXIT |
| Migration desde state.json | Script de migración automático |
| Archivos huérfanos | Cleanup периодический |
