# Language Policy
All generated documentation, specifications (specs), technical plans, and tasks MUST be written entirely in English. Code comments, variable names, and commit messages must also follow this English-only rule.

---

# Rich Terminal Output Requirement

## CLI Scripts Must Use rich-terminal-output Skill

**ALL new CLI scripts or modifications to existing CLI scripts MUST use the `rich-terminal-output` skill** to provide enhanced terminal output.

### What this means:

When implementing or modifying a CLI script that produces output to the terminal, you MUST:

1. **Import Rich components**: Use `Console`, `Panel`, `Table`, `Progress`, etc. from the `rich` library
2. **Follow the skill pattern**: Reference `.roo/skills/rich-terminal-output/SKILL.md` for implementation patterns
3. **Use appropriate components**:
   - `Console` for all output
   - `Panel` for startup headers and summary output
   - `Progress` for long-running operations
   - `Table` for structured data display
   - Syntax highlighting for code/output samples

### Example pattern:

```python
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

console = Console()

# Startup header
console.print(Panel("[bold]Script Name[/bold]", title="AEGF"))

# Progress for long operations
with Progress() as progress:
    task = progress.add_task("Processing...", total=100)
    # ... work ...
    progress.update(task, completed=100)

# Summary panel
console.print(Panel(f"Completed: {n} items", title="[green]Success[/green]"))
```

### Verification:

After implementing a CLI script with Rich, verify the output is visually enhanced with Rich components before marking the task as complete.