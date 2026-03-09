# Plan de migración: tests dependientes del fallback AST (T031)

Fecha: 2026-03-08
Estado: Draft

Este documento recoge la estrategia recomendada para migrar los tests que dependen del comportamiento de "fallback" (whole-file / fallback silencioso) detectados por la auditoría T031 (`specs/001-stage1-discovery/ast_fallback_audit.json`).

IMPORTANTE: Este archivo es **especificación** únicamente. No se harán cambios en código, tests ni configuración en este PR/acción. La implementación la realizará otro agente/ingeniero siguiendo las instrucciones aquí descritas.

Resumen
- Objetivo: eliminar la dependencia de fallback silencioso y adaptar los tests al modelo normativo `FR-006` (default: abort y `ParseError`).
- Estrategia preferida (normativa): actualizar tests para esperar el `ParseError` estructurado o para validar la política `on_parse_error` (TDD: tests primero). Solo si la migración exige un coste desproporcionado, usar una estrategia temporal de compatibilidad (perfil `legacy_compat`) como medida transitoria.

Proceso recomendado
1. Generar lista priorizada de tests desde `specs/001-stage1-discovery/ast_fallback_audit.json` (ya generada por T031). Priorizar:
   - Tests unitarios en `tests/` que fallarán inmediatamente tras aplicar FR-006.
   - Tests de integración que cubren `production_v11` y `_ast_fragment_list`.
2. Para cada test, aplicar uno de los tres patrones de migración (preferir A → C):
   - A) Migrar a `ParseError`-first (Recomendado)
       - Cambiar aserciones que esperan un fragmento completo por `with pytest.raises(ParseError):` y validar campos del error (`file_path`, `adapter`, `diagnosis`).
       - Añadir fixture para simular `ProcessingConfig(on_parse_error='abort')` y asserts sobre el reporte del repositorio marcado `needs_manual_review`.
   - B) Validar política `on_parse_error` (`skip` / `mark_and_continue`)
       - Para tests que verifican comportamiento de skip o marca, parametrizar el test con `on_parse_error` y comprobar ambos caminos.
   - C) Compatibilidad temporal mediante `profile: legacy_compat` (Solo si A/B no es viable)
       - Crear una especificación de profile `legacy_compat` que documente oximorónicamente que permite fallback. Esta opción es transitoria y debe acompañarse de un plan y fecha de retirada (max 90 días).

Plantilla de migración (ejemplo)

Antes (test que esperaba fallback whole-file):

```py
def test_invalid_python_fallback_to_whole_file():
    frags = v11._ast_fragment_list("bad.py", "def broken(::", "ctx", {"virtual_filename": "bad.py"})
    assert len(frags) == 1
    assert frags[0]["arch"]["LOCAL_IMPORTS"] == "[]"
```

Después (ParseError-first):

```py
import pytest
from src.utils.extractors.base import ParseError

def test_invalid_python_raises_parse_error():
    with pytest.raises(ParseError) as exc:
        v11._ast_fragment_list("bad.py", "def broken(::", "ctx", {"virtual_filename": "bad.py"})
    err = exc.value
    assert err.file_path.endswith("bad.py")
    assert "SyntaxError" in err.error or err.diagnosis is not None
```

Notas y criterios de aceptación
- Todos los tests migrados deben pasar en el entorno de CI antes de que se fusione la implementación que elimina el fallback.
- Si se crea `legacy_compat`, documentar su uso y añadir una fecha de expiración en la especificación.
- Registrar en el PR los cambios por test (archivo, línea, patrón de migración) para la trazabilidad.

Tareas derivadas (Especificación)
- T031.1: Listado priorizado de tests y propuesta de migración — documento aquí incluido (this file).
- T031.2: Checklist de migración por test (to be filled by implementer).
- T031.3: Revisión y aprobación por propietarios de `production_v11` y `processor`.

Referencias
- Auditoría T031: `specs/001-stage1-discovery/ast_fallback_audit.json`
- Requisito normativo: `specs/001-stage1-discovery/spec.md` §FR-006
