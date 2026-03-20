# Research: Rich Terminal Output para CLI

**Feature**: Rich Terminal Output para CLI  
**Branch**: 014-rich-cli-output  
**Date**: 2026-03-20

## Objetivo

Investigar cómo integrar la biblioteca Rich en los scripts CLI existentes del proyecto AEGF para mejorar la experiencia de usuario (CLI UX).

## Technology Selection

### Decision: Usar biblioteca Rich de Python

**Rationale**:
- Skill existente definida en `.roo/skills/rich-terminal-output/SKILL.md`
- Biblioteca madurada y bien mantenida
- Cumple con todos los requerimientos del usuario:
  - Tablas para datos estructurados
  - Barras de progreso para operaciones largas
  - Paneles para resultados
  - Syntax highlighting para código
  - Rich tracebacks para errores
- Compatible con el sistema de logging existente via RichHandler

**Alternatives evaluated**:

| Alternative | Why Rejected |
|------------|--------------|
| colorama | Solo colores básicos, no soporta tablas/progreso |
| click | Framework de CLI, no es para mejorar output existente |
| textual | Framework completo de TUI, overkill para necesidad |
| blessed | Menos documentación y comunidad más pequeña |

## Implementation Strategy

### Enfoque de Migración

1. **Instalación**: Agregar `rich` a dependencias del proyecto
2. **Import**: Usar import lazy para no afectar startup time
3. **Console instance**: Crear una instancia compartida por módulo
4. **Progressive migration**: Modificar scripts uno por uno, verificando tests

### Patrones de Uso

Basado en la skill `.roo/skills/rich-terminal-output/SKILL.md`:

```python
# Console básico
from rich.console import Console
console = Console()

# Para operaciones largas - Progress
from rich.progress import Progress, track

# Tablas
from rich.table import Table

# Paneles
from rich.panel import Panel

# Errores - Rich tracebacks
from rich.traceback import install
```

### Manejo de No-TTY

Importante considerar cuando la salida es pipeada:

```python
console = Console(force_terminal=sys.stdout.isatty())
```

## Scripts Objetivo

Lista de 23 scripts a modificar, categorizados por módulo:

### audit/ (2 scripts)
- `src/audit/cli.py`
- `src/audit/calibration.py`

### curation/ (2 scripts)
- `src/curation/curator_cli.py`
- `src/curation/rewrite_cli.py`

### discovery/ (2 scripts)
- `src/discovery/ingestor.py`
- `src/discovery/processor_cli.py`

### factory/ (2 scripts)
- `src/factory/cli.py`
- `src/factory/agentic_cli.py`

### merger/ (14 scripts)
- `src/merger/analisis_avanzado.py`
- `src/merger/check_alignment.py`
- `src/merger/clean_dna.py`
- `src/merger/diagnostico.py`
- `src/merger/dna_fix_v2.py`
- `src/merger/dna_strict.py`
- `src/merger/final_ignition.py`
- `src/merger/fusionar_final.py`
- `src/merger/guardar_tokenizador.py`
- `src/merger/merge_shards.py`
- `src/merger/repara_stage2.py`
- `src/merger/repair_dna.py`
- `src/merger/repair_triple_dna.py`
- `src/merger/shotgun_dna.py`

### research/ (1 script)
- `src/research/generate_batch_distilabel.py`

## Considerations

### Testing Compatibility

- Los tests deben seguir pasando 100%
- Rich puede coexistir con print() estándar
- Usar RichHandler para integrar con logging existente

### Performance

- Import lazy de rich para evitar overhead en startup
- Lazy formatting en logging
- Detectar TTY para evitar overhead innecesario en pipes

### Mantenibilidad

- Considerar crear módulo helper en `src/utils/rich_helpers.py` si hay patrones repetidos
- Documentar uso en cada script modificado
