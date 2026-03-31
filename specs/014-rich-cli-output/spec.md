# Feature Specification: Rich Terminal Output para CLI

**Feature Branch**: `014-rich-cli-output`  
**Created**: 2026-03-20  
**Status**: Draft  
**Input**: User description: "Aplicar rich terminal output a todos los scripts Python que se ejecutan por terminal en src. El concepto es CLI UX (Command Line Interface User Experience). La idea es que cuando se implemente en cada task de la implementación esté claro que se tiene que usar la skill de rich terminal output para mejorar la salida de los comandos. Y por supuesto que todos los tests tienen que seguir pasando como hasta ahora."

## Resumen Ejecutivo

Esta especificación define los requisitos para mejorar la experiencia de usuario (UX) en la interfaz de línea de comandos (CLI) del proyecto AEGF mediante la integración de la biblioteca Rich. El objetivo es estandarizar la salida visual de todos los scripts Python ejecutables en el directorio `src`, proporcionando output más legible, profesional y visualmente atractivo mediante el uso de tablas, barras de progreso, paneles y resaltado de sintaxis.

## User Scenarios & Testing

### User Story 1 - Adoptar Rich en Scripts CLI Principales (Priority: P1)

Como desarrollador o operador que ejecuta scripts CLI del proyecto, quiero ver una salida formateada y visualmente atractiva cuando ejecuto comandos, para poder interpretar más fácilmente el progreso y los resultados de las operaciones.

**Why this priority**: Es la funcionalidad central de esta feature y afecta a todos los usuarios que interactúan con la CLI del proyecto.

**Independent Test**: Se puede probar ejecutando cada script CLI identificado y verificando que la salida usa componentes Rich (tablas, paneles, progreso) en lugar de print() básico.

**Acceptance Scenarios**:

1. **Given** El script `curator_cli.py` se ejecuta con argumentos válidos, **When** el comando produce salida de progreso, **Then** se muestra una barra de progreso visual en lugar de texto plano.
2. **Given** El script `processor_cli.py` completa una operación exitosamente, **When** termina la ejecución, **Then** muestra un panel de éxito con resumen de la operación.
3. **Given** El script `factory/cli.py` encuentra un error, **When** ocurre una excepción, **Then** muestra un traceback formateado con Rich.

---

### User Story 2 - Documentar Uso de Rich en Tasks de Implementación (Priority: P2)

Como implementador de futuras features, quiero que las tareas de implementación incluyan explícitamente la obligación de usar Rich para mejorar la salida CLI, para garantizar consistencia en la experiencia de usuario en todo el proyecto.

**Why this priority**: Asegura que la mejora de UX CLI sea una consideración explícita en el desarrollo futuro.

**Independent Test**: Se puede verificar revisando que las tasks en `tasks.md` de cada spec incluyan el requerimiento de usar Rich.

**Acceptance Scenarios**:

1. **Given** Se crea una nueva tarea de implementación, **When** la tarea involucra output de CLI, **Then** la descripción de la tarea incluye el requerimiento de usar la skill de rich-terminal-output.
2. **Given** Un desarrollador revisa tareas pendientes del proyecto, **When** busca tareas relacionadas con scripts CLI, **Then** encuentra guidance claro sobre el uso de Rich.

---

### User Story 3 - Mantener Compatibilidad con Tests Existentes (Priority: P1)

Como mantenedor del proyecto, quiero que la integración de Rich no rompa los tests existentes, para garantizar que la calidad del código no se degrade durante la mejora de UX.

**Why this priority**: Es un requisito no negociable establecido por el usuario.

**Independent Test**: Se puede verificar ejecutando `pytest` y confirmando que todos los tests pasan.

**Acceptance Scenarios**:

1. **Given** Se modifica un script CLI para usar Rich, **When** se ejecutan los tests del proyecto, **Then** todos los tests pasan exitosamente.
2. **Given** Un script usa Rich para output, **When** la salida es piped a otro proceso, **Then** el comportamiento es equivalente al output anterior (sin breaking change).

---

### Edge Cases

- **Salida en entornos no-TTY**: Cuando la salida es piped o redirigida, el output debe degr gracefully a texto plano sin formatting Rich.
- **Scripts con logging**: Los scripts que usan logging deben mantener compatibilidad con RichHandler.
- **Long-running operations**: Las barras de progreso deben funcionar correctamente con operaciones que toman varios minutos.
- **Output de errores**: Los errores deben mostrarse en paneles rojos con información clara y accionable.

## Requirements

### Functional Requirements

- **FR-001**: La totalidad de scripts CLI ejecutables en `src/` deben utilizar la biblioteca Rich para formatear su salida estándar.
- **FR-002**: Cada script CLI debe implementar barras de progreso para operaciones que tarden más de 2 segundos.
- **FR-003**: Cada script CLI debe usar paneles para mostrar resultados finales de operaciones (éxito o error).
- **FR-004**: Las tablas deben utilizarse para mostrar datos estructurados (listas de archivos, métricas, resultados).
- **FR-005**: Los tracebacks de excepciones deben formatearse con Rich para facilitar la depuración.
- **FR-006**: La integración de Rich debe mantener compatibilidad completa con los tests existentes (no debe romper ninguna prueba).
- **FR-007**: Las tareas de implementación en `tasks.md` deben incluir explícitamente el requerimiento de usar la skill rich-terminal-output cuando involucren output de CLI.
- **FR-008**: Los scripts deben detectar automáticamente si el output es a un terminal o pipe/redirección y ajustar el output apropiadamente.

### Scripts CLI Objetivo

Los siguientes scripts deben ser migrados a usar Rich:

1. `src/audit/cli.py` - CLI principal de auditoría
2. `src/audit/calibration.py` - CLI de calibración
3. `src/curation/curator_cli.py` - CLI de curación
4. `src/curation/rewrite_cli.py` - CLI de reescritura
5. `src/discovery/ingestor.py` - CLI de ingestión
6. `src/discovery/processor_cli.py` - CLI de procesamiento
7. `src/factory/cli.py` - CLI principal de fábrica
8. `src/factory/agentic_cli.py` - CLI de agente
9. `src/merger/analisis_avanzado.py`
10. `src/merger/check_alignment.py`
11. `src/merger/clean_dna.py`
12. `src/merger/diagnostico.py`
13. `src/merger/dna_fix_v2.py`
14. `src/merger/dna_strict.py`
15. `src/merger/final_ignition.py`
16. `src/merger/fusionar_final.py`
17. `src/merger/guardar_tokenizador.py`
18. `src/merger/merge_shards.py`
19. `src/merger/repara_stage2.py`
20. `src/merger/repair_dna.py`
21. `src/merger/repair_triple_dna.py`
22. `src/merger/shotgun_dna.py`
23. `src/research/generate_batch_distilabel.py`

### Key Entities

- **Script CLI**: Cualquier archivo Python en `src/` que contenga un bloque `if __name__ == "__main__"` con argparse o click para procesamiento de argumentos.
- **Componente Rich**: Elemento visual de la biblioteca Rich (Console, Table, Panel, Progress, Syntax, etc.).
- **Skill rich-terminal-output**: Documentación y patrones de uso de la biblioteca Rich disponibles en `.roo/skills/rich-terminal-output/SKILL.md`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: El 100% de los scripts CLI listados en FR-002 utilizan al menos un componente Rich para su salida.
- **SC-002**: Todos los tests existentes del proyecto pasan (100% pass rate) después de la integración de Rich.
- **SC-003**: El tiempo de ejecución de los scripts no aumenta más del 5% por la sobrecarga de Rich.
- **SC-004**: El 100% de las nuevas tareas de implementación que involucren output CLI incluyen el requerimiento de usar la skill rich-terminal-output.
- **SC-005**: La salida de todos los scripts es legible tanto en terminal interactivo como cuando se redirige a archivo.

## Assumptions

- La biblioteca Rich ya está disponible en el entorno o será añadida como dependencia.
- Los scripts existentes no tienen output formateado complexo que requiera migración manual extensiva.
- El usuario tiene权限 para modificar los scripts y agregar dependencias.
