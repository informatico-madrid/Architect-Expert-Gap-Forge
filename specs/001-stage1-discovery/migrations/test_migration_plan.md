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

## Prioritized tests to migrate (auto-generated)

La siguiente lista se generó a partir de `specs/001-stage1-discovery/ast_fallback_audit.json`. Clasifica los ficheros de tests que referencian comportamiento de "fallback" detectado por la auditoría. Para cada entrada se propone una estrategia de migración (A/B/C) conforme a las plantillas definidas en este documento.

- **tests/test_production_v11.py** — Priority: High
    - Observaciones: contiene referencias a `_ast_fragment_list` y a tests con nombres `*_fallback_*`.
    - Recomendación: A (migrar a `ParseError`-first). Actualizar tests que esperan fragmentos whole-file para que esperen `ParseError` o parametrizar `on_parse_error` si la intención es validar `skip`/`mark_and_continue`.

- **tests/test_model_evaluator_integration_paths.py** — Priority: High
    - Observaciones: múltiples pruebas sobre fallbacks de carga/adapter/ejemplos; puede contener casos no relacionados con AST (p. ej. fallback de carga de examenes o tool_call).
    - Recomendación: Revisar y clasificar primero. Si el test valida `_ast_fragment_list` o fragmentación, aplicar A; en caso contrario migrar según su semántica de fallback (B) o dejar fuera si es unrelated.

- **tests/test_production_v11_helpers.py** — Priority: High
    - Observaciones: llamadas directas a `pv11._ast_fragment_list(...)` y pruebas `test_ast_fragment_list_fallback_on_error`.
    - Recomendación: A (migrar a `ParseError`-first). Actualizar fixture y asserts para capturar `ParseError` y validar campos (`file_path`, `error`, `diagnosis`).

- **tests/test_sampling.py** — Priority: High
    - Observaciones: test `test_missing_id_gets_fallback` usa fallback para ids; este fallback no es estrictamente AST-related.
    - Recomendación: Revisar y clasificar. Si es ajeno a AST, no es bloqueante para el refactor AST; documentar clasificación.

- **tests/test_model_evaluator_extended_paths.py** — Priority: High
    - Observaciones: pruebas sobre propagación de errores y lógica de fallback en el evaluador de modelos.
    - Recomendación: Revisar. Probablemente unrelated al AST fallback; confirmar y clasificar.

- **tests/fixtures/production_v11_mocks.py** — Priority: Medium
    - Observaciones: contiene utilidades de fixtures que pueden simular tool_call fallback responses.
    - Recomendación: Revisar fixtures consumidas por tests de `production_v11` y actualizar mocks según nueva semántica (A/B según caso).

- **tests/test_clean_lora.py** — Priority: Medium
    - Observaciones: referencia a comportamientos fallback en lógica de LORA.
    - Recomendación: Revisar y clasificar; aplicar B si valida políticas distintas de ParseError.

- **tests/test_inference.py** — Priority: Medium
    - Observaciones: test `test_base_class_backend_name_is_fallback` puede ser unrelated al AST fallback.
    - Recomendación: Revisar y clasificar.

- **tests/test_nemo_curator_extra.py** — Priority: Medium
    - Observaciones: menciona fallback en contexto de curation pipelines.
    - Recomendación: Revisar; no es bloqueante para el adapter refactor si no depende de `_ast_fragment_list`.

- **tests/test_nemo_curator_suite.py** — Priority: Medium
    - Observaciones: menciona naive fallback en dedup; probablemente unrelated al AST.
    - Recomendación: Revisar y clasificar.

- **tests/test_production_v11_additional.py** — Priority: Low
    - Observaciones: contiene aserciones sobre `LOCAL_IMPORTS` (por ejemplo `LOCAL_IMPORTS: []`).
    - Recomendación: Migrar solo si falla tras la eliminación de fallback; probablemente requiera ajustes menores de fixtures o valores esperados.

- **tests/test_production_v11_end_to_end.py** — Priority: Low
    - Observaciones: E2E que verifica `LOCAL_IMPORTS` en salidas.
    - Recomendación: Revisar y migrar en última instancia; mantener en backlog hasta que unit tests principales se migren.

### Notas operativas

- Para cada fichero marcado **High**, crear una entrada en la checklist de migración con:
    1. Línea(s) de test afectadas (copiar desde `ast_fallback_audit.json`).
    2. Patrón de migración (A/B/C) aplicado y snippet de ejemplo (ver plantilla en este documento).
    3. Resultado esperado y pruebas locales a ejecutar.

- Documentar cualquier test que se deje temporalmente bajo `legacy_compat` y asignar una fecha de expiración (no más de 90 días).

---

Fin de la lista priorizada (auto-generada).

## Detalle de migración — Tests Priority: High

Las siguientes subsecciones aportan instrucciones concretas (spec-only) para migrar cada fichero marcado como **High**. Cada bloque incluye: contexto, clasificación (A/B/C), snippet de ejemplo `antes` y `después`, pasos TDD y riesgos.

### tests/test_production_v11.py

- Contexto: contiene múltiples casos que ejercitan `_ast_fragment_list` y pruebas que esperaban un fallback whole-file cuando el código es inválido.
- Clasificación recomendada: **A — Migrar a `ParseError`-first**.

Antes (ejemplo simplificado):
```py
frags = v11._ast_fragment_list("bad.py", "def broken(::", "ctx", {"virtual_filename": "bad.py"})
assert len(frags) == 1
```

Después (especificación de prueba):
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

Pasos TDD (espec):
1. Actualizar el test como se muestra (crear una rama de tests). Ejecutar `pytest` para confirmar que falla (red).
2. Documentar en la PR que el test fue modificado por FR-006 y enlazar `specs/001-stage1-discovery/spec.md` §FR-006.
3. El equipo de implementación hará los cambios en el adapter/`production_v11` para lanzar `ParseError` y pasar la prueba.

Riesgos / Notas:
- Verificar si el test intentaba comprobar comportamiento de alta resiliencia (p.ej. emitir fragmento whole-file intencionadamente). Si ese era el caso, considerar parametrizar la prueba para cubrir `on_parse_error='skip'/'mark_and_continue'` (patrón B) en pruebas separadas.

### tests/test_production_v11_helpers.py

- Contexto: contiene `test_ast_fragment_list_fallback_on_error` y llamadas directas a `pv11._ast_fragment_list(...)`.
- Clasificación recomendada: **A — Migrar a `ParseError`-first**.

Antes (extracto):
```py
fragments = factory_v11._ast_fragment_list("module.py", "invalid code..", "ctx", {})
assert len(fragments) == 1
```

Después (especificación de prueba):
```py
def test_ast_fragment_list_raises_on_invalid_code():
    with pytest.raises(ParseError):
        factory_v11._ast_fragment_list("module.py", "invalid code..", "ctx", {})
```

Pasos TDD:
1. Actualizar el test localmente y verificar que falla.
2. Añadir aserciones sobre campos del `ParseError` si se desea granularidad en el diagnóstico.
3. Implementador: adaptar `_ast_fragment_list` o su adapter a la nueva excepción.

Riesgos:
- Algunos helpers/mocks pueden necesitar actualización (fixtures que esperaban fragmentos enteros). Documentar y listar fixtures afectadas.

### tests/test_model_evaluator_integration_paths.py

- Contexto: mezcla pruebas de carga/evaluación que mencionan múltiples formas de fallback; no todos los casos son AST-related.
- Clasificación recomendada: **Revisión previa + A/B**: identificar sub-pruebas que llaman a `_ast_fragment_list` y aplicar A; otros fallback semantics seguirán patrón B.

Acción recomendada (espec):
1. Filtrar en el fichero los tests que referencian directamente `_ast_fragment_list` o `LOCAL_IMPORTS`.
2. Para cada test AST-related aplicar el patrón A y usar `pytest.raises(ParseError)`.
3. Para pruebas que verifican fallback de carga de recursos (no AST) documentar como B y mantener la semántica existente o parametrizar `on_parse_error` según corresponda.

Ejemplo (antes/después) — AST-related:
```py
# Antes: test que asume fallback a muestra
frags = some_v11_call(...)
assert some_condition_on_fragments

# Después: esperar ParseError si procede
with pytest.raises(ParseError):
    some_v11_call(...)
```

### tests/test_sampling.py

- Contexto: `test_missing_id_gets_fallback` aparenta usar fallback para generar IDs; no es explícitamente AST-related.
- Clasificación recomendada: **Revisar y clasificar** — probablemente **no** bloqueará el refactor de adapters.

Acción recomendada (spec-only):
1. Inspeccionar si el test depende de `_ast_fragment_list` o `LOCAL_IMPORTS`. Si no, marcar como no-ast y dejar para posterior limpieza.
2. Si el test sí está indirectamente vinculado a producciones de `production_v11`, aplicar revisión y migración apropiada.

### tests/test_model_evaluator_extended_paths.py

- Contexto: pruebas amplias sobre la propagación de errores y fallback en el engine de evaluación.
- Clasificación recomendada: **Revisión y clasificación** — puede incluir casos unrelated al AST.

Acción recomendada (spec-only):
1. Identificar tests AST-specific y aplicar patrón A.
2. Para los tests de evaluación general que asumen fallback en lógica de scoring, tratar con patrón B o dejar como está y documentar su alcance.

---

## Checklist de entrega por test (plantilla)

Para cada test migrado, incluir en la especificación/propuesta de PR los siguientes elementos:
1. `file` y `lines` exactas afectadas (copiar desde `ast_fallback_audit.json`).
2. Patrón aplicado (A/B/C) y justificación breve.
3. Snippet `antes` y `después` (como en este documento).
4. Pruebas locales a correr (`pytest tests/<file>::<testname>`).
5. Estimación de esfuerzo (small/medium/large).

## Criterios de aceptación (migración completa)

- Todos los tests marcados Priority: High están migrados y pasan en CI bajo la semántica `FR-006` (ParseError por defecto).
- No queda comportamiento silent-fallback en los módulos de fragmentación; cualquier compatibilidad temporal queda documentada y sujeta a expiración (≤90 días).


