Archivo: AGENTS_ARCHITECTURE.md

Disonancia detectada: Referencia a archivo legado `clear_dataset_force.py` en lugar de usar `src/curation/rewrite_cli`

Impacto: Desconocimiento del cambio de arquitectura hacia pipelines modulares; desarrolladores intentarán ejecutar script obsoleto causando errores en CI.

Acción recomendada: Eliminar todas las referencias a `clear_dataset_force.py` y actualizar ejemplos a usar `src/curation/rewrite_cli`.

---
Archivo: METHODOLOGY.md

Disonancia detectada: Explicación de flujo secuencial "ejecutar etapa 1 entonces etapa 2" sin mencionar Ralph-Loop ni Git Worktrees.

Impacto: Confusión sobre cómo manejar resumen de estado y dependencias entre etapas en entornos colaborativos.

Acción recomendada: Reemplazar descripciones secuenciales con patrón Ralph-Loop usando `git worktree` y `--resume` flags.

---
Archivo: case_studies/php/

Disonancia detectada: Documentación describe PHP como "script aislado" en lugar de adaptador integrado a `fragment_extractor.py`.

Impacto: Malentendido sobre el papel de PHP en el sistema; podría llevar a duplicación de lógica o uso incorrecto.

Acción recomendada: Actualizar caso de estudio para mostrar conexión explícita con `fragment_extractor.py` mediante interfaz definida en `schema.py`.

---
Archivo: docs/specs/stage_1_5_backtracking_alignment.md

Disonancia detectada: Archivo marcado como activo pero eliminado en favor de `stage_2_factory/proxy_generator.py`.

Impacto: Posible búsqueda innecesaria en repositorio histórico; confunde con versión anterior del diseño.

Acción recomendada: Mover a `legacy/archive/` y actualizar enlaces en `SPECIFICATION_INDEX.md`. 
**Acción recomendada:** Eliminar - Este archivo debería ser eliminado o completamente reescrito para reflejar el estado post-refactorización.

---

## 2. CONCEPTOS DE ORQUESTACIÓN

### Disonancia #9

**Archivo:** docs/METHODOLOGY.md (líneas 1-272)  
**Disonancia detectada:** La metodología describe flujos de procesamiento como pipeline secuencial sin mencionar el modelo **Ralph-Loop con Git Worktrees**. No hay referencia a:
- Ejecución paralela de specs
- Worktree isolation
- Stateless iteration

**Impacto:** El documento methodological no refleja la arquitectura de orquestación actual. Desarrolladores no entenderán cómo se ejecuta el sistema en paralelo.  
**Acción recomendada:** Refactorizar - Agregar sección "4.5 Ralph-Loop Orchestration" que explique Git Worktrees, parallelization, y el loop stateless. Referenciar specs/002-ralph-worktree/.

---

### Disonancia #10

**Archivo:** docs/ORCHESTRATION_QUICKSTART.md (líneas 37-54)  
**Disonancia detectada:** El diagrama Mermaid muestra flujo secuencial básico sin Git Worktrees. No representa:
- Worktree branch creation
- Parallel spec execution
- State checkpointing

**Impacto:** Quickstart de orquestación es incompleto para el modelo actual.  
**Acción recomendada:** Refactorizar - Actualizar diagrama para mostrar branching con Git Worktrees y parallel execution.

---

## 3. INTEGRACIÓN DE LENGUAJES

### Disonancia #11

**Archivo:** docs/case_studies/PHP_MODERNIZATION_FORGE.md  
**Disonancia detectada:** El case study no menciona explícitamente que PHP ahora es un **Adaptador** conectado al `fragment_extractor.py`. La arquitectura actual muestra:
- `src/utils/extractors/php_legacy_adapter.py` - Adaptador PHP
- `src/discovery/php_fragmenter.py` - Lógica de fragmentación
- `src/factory/fragment_extractor.py` - Punto de integración

El documento debería reflejar claramente que PHP no es un script aislado sino un Adaptador registrado en el sistema de extractores.

**Impacto:** Desarrolladores no entenderán que PHP sigue el patrón Adapter y intentarán ejecutar php_fragmenter.py como script independiente.  
**Acción recomendada:** Refactorizar - Agregar sección "Arquitectura de Adaptador PHP" que muestre:
```
PHP Legacy Code → PHPFragmenter → PHPLegacyAdapter → FragmentExtractor → Factory
```

---

## 4. HIGIENE DE 'FANTASMAS'

### Disonancia #12

**Archivo:** docs/specs/stage_1_5_backtracking_alignment.md  
**Disonancia detectada:** Archivo huérfano en `docs/specs/`. Este archivo fue reemplazado por:
- Specs en `specs/002-ralph-worktree/` (Ralph Loop)
- Implementación en `src/curation/rewrite_*.py`

**Impacto:** Archivo genera confusión sobre el flujo de trabajo actual.  
**Acción recomendada:** Mover a legacy - `mkdir -p docs/specs/legacy/ && mv docs/specs/stage_1_5_backtracking_alignment.md docs/specs/legacy/`

---

### Disonancia #13

**Archivo:** specs/001-stage1-discovery/ast_fallback_audit.json  
**Disonancia detectada:** Archivo JSON de auditoría en directorio de specs. No parece ser una spec válida ni un archivo de código fuente.  
**Impacto:** Mezcla de tipos de archivo en directorio de especificaciones.  
**Acción recomendada:** Investigar y eliminar o mover a `diagnose/` si es un resultado de auditoría.

---

### Disonancia #14

**Archivo:** diagnose/deprecated/ (directorio completo)  
**Disonancia detectada:** Directorio `diagnose/deprecated/` contiene scripts old con estructura de argumentos que puede no funcionar con la nueva arquitectura (e.g., `debug_argilla_chat_test.py`).  
**Impacto:** Acumula código muerto que confunde sobre qué módulos están activos.  
**Acción recomendada:** Mover a archive - `mkdir -p archive/diagnose_deprecated/ && mv diagnose/deprecated/* archive/diagnose_deprecated/`

---

### Disonancia #15

**Archivo:** src/factory/deprecated/  
**Disonancia detectada:** Directorio `src/factory/deprecated/` contiene `production_v10.py`. Esto está bien, pero la documentación no indica claramente que estos archivos son deprecados.  
**Impacto:** Archivos vivos pero marcados como deprecated pueden causar confusión.  
**Acción recomendada:** Documentar - Agregar README.md en `src/factory/deprecated/` explicando qué archivos contiene y por qué están ahí.

---

### Disonancia #16

**Archivo:** configs/prompts/backtracking_system.txt  
**Disonancia detectada:** Archivo de prompt en configs/prompts/ que parece relacionado con backtracking pero está fuera del flujo principal de Spec 003. No hay referencia activa en código a este archivo.  
**Impacto:** Prompt huérfano sin uso conocido.  
**Acción recomendada:** Investigar uso o eliminar.

---

### Disonancia #17

**Archivo:** src/utils/extractors/php_legacy_adapter.py (líneas 57-59, 358-360)  
**Disonancia detectada:** El adaptador importa dinámicamente `from src.discovery.php_fragmenter import process_php_file`. Esto indica que existe acoplamiento entre el Adapter y el fragmenter, pero la documentación del caso de estudio no refleja esta relación.  
**Impacto:** La arquitectura de acoplamiento no está documentada.  
**Acción recomendada:** Documentar en PHP_MODERNIZATION_FORGE.md.

---

## TABLA RESUMEN DE ACCIONES

| # | Severidad | Categoría | Acción |
|---|-----------|-----------|--------|
| 1 | 🔴 Alta | Geografía | Refactorizar |
| 2 | 🔴 Alta | Geografía | Refactorizar |
| 3 | 🟡 Media | Geografía | Refactorizar |
| 4 | 🔴 Alta | Geografía | Eliminar |
| 5 | 🟡 Media | Geografía | Refactorizar |
| 6 | 🟡 Media | Geografía | Mover a legacy |
| 7 | 🟡 Media | Geografía | Refactorizar |
| 8 | 🟢 Baja | Geografía | Eliminar |
| 9 | 🔴 Alta | Orquestación | Refactorizar |
| 10 | 🟡 Media | Orquestación | Refactorizar |
| 11 | 🔴 Alta | Integración | Refactorizar |
| 12 | 🟡 Media | Fantasmas | Mover a legacy |
| 13 | 🟢 Baja | Fantasmas | Investigar |
| 14 | 🟢 Baja | Fantasmas | Mover a archive |
| 15 | 🟢 Baja | Fantasmas | Documentar |
| 16 | 🟢 Baja | Fantasmas | Investigar |
| 17 | 🟡 Media | Integración | Documentar |

---

## NOTAS ADICIONALES

1. **Specs 002-ralph-worktree/** está correctamente implementada y referenciada desde AGENTS_ARCHITECTURE.md. No hay disonancia.

2. **.github/prompts/** contiene los archivos speckit correctos (e.g., `speckit.analyze.prompt.md`). La referencia en AGENTS_ARCHITECTURE.md línea 103 es correcta.

3. La estructura general del proyecto sigue el patrón de Spec 003 (módulos pequeños con responsabilidad única). Las disonancias son principalmente de **documentación**, no de implementación.

4. **Conclusión:** El codebase está bien estructurado post-Spec 003. Las disonancias son principalmente inconsistencias entre la documentación y la implementación. La acción prioritaria debe ser actualizar README.md, METHODOLOGY.md y el case study de PHP.
