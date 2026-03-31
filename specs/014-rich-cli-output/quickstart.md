# Quickstart: Rich Terminal Output para CLI

**Feature**: Rich Terminal Output para CLI  
**Branch**: 014-rich-cli-output

## Objetivo

Mejorar la experiencia de usuario (CLI UX) en los scripts Python del proyecto AEGF mediante el uso de la biblioteca Rich para formatear la salida de terminal.

## Prerequisites

- Python 3.11+
- Dependencias del proyecto instaladas: `pip install -r requirements.txt`
- Biblioteca Rich: `pip install rich`

## Instalación de Rich

```bash
# Agregar a requirements.txt
echo "rich" >> requirements.txt

# O instalar directamente
pip install rich

# Verificar instalación
python -c "from rich import print; print('[bold green]Rich working![/]')"
```

## Uso Básico

### Console

```python
from rich.console import Console

console = Console()
console.print("Hello, World!")
console.print("[bold red]Error:[/] Something went wrong")
console.print("[green]Success![/] Operation completed")
```

### Barras de Progreso

```python
from rich.progress import track
import time

for item in track(range(100), description="Processing..."):
    time.sleep(0.01)
```

### Tablas

```python
from rich.table import Table

table = Table(title="Results")
table.add_column("File", style="cyan")
table.add_column("Status", justify="center")

table.add_row("file1.py", "✓ Success")
table.add_row("file2.py", "✗ Error")

console.print(table)
```

### Paneles

```python
from rich.panel import Panel

console.print(Panel(
    "[green]Operation completed![/]\n\n"
    "Processed 42 files in 3.2s",
    title="Success",
    border_style="green"
))
```

## Scripts a Modificar

Consultar la lista completa en [research.md](research.md).

### Ejemplo de Modificación

**Antes (src/audit/cli.py)**:
```python
print(f"Processing {len(files)} files...")
print("Done!")
```

**Después**:
```python
from rich.console import Console
from rich.progress import Progress

console = Console()

with Progress() as progress:
    task = progress.add_task("[cyan]Processing files...", total=len(files))
    for f in files:
        # process file
        progress.update(task, advance=1)

console.print(Panel(
    f"[green]Processed {len(files)} files successfully![/]",
    title="Complete"
))
```

## Verificación

Después de modificar un script:

1. Ejecutar el script y verificar el output visual
2. Ejecutar los tests: `pytest`
3. Verificar que todos los tests pasen

## Integración con Logging

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
```

## Recursos

- Documentación de Rich: https://rich.readthedocs.io/
- Skill: `.roo/skills/rich-terminal-output/SKILL.md`
