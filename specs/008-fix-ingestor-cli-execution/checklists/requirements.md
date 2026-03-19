# Requirements Quality Checklist: Fix Ingestor CLI Execution

**Purpose**: Valida la calidad, completitud y claridad de los requisitos documentados para la feature 008. Cada ítem es un "test unitario" sobre los requisitos escritos — NO sobre la implementación.
**Created**: 2026-03-19
**Feature**: [specs/008-fix-ingestor-cli-execution/spec.md](../spec.md)
**Audience**: Autor (pre-implementación) + Revisor (PR)
**Depth**: Standard — gating mínimo antes de que el agente implemente

---

## Requisito Completitud — ¿Están todos los requisitos necesarios documentados?

- [ ] CHK001 — ¿Describe el spec el problema COMPLETO? La raíz del bug tiene DOS causas (`ModuleNotFoundError` por `--import-mode=importlib` en pytest Y `FileNotFoundError` por rutas relativas), pero el spec solo menciona el `FileNotFoundError`. ¿Está la causa de `ModuleNotFoundError` documentada? [Completeness, Gap]

- [ ] CHK002 — ¿Tiene el spec las secciones del template canónico del proyecto (como `001-stage1-discovery/spec.md`)? El spec 001 incluye `Feature Branch`, `Created`, `Status`, `User Scenarios & Testing`, `Requisitos (testables)`, `Clarifications`. El spec 008 no tiene metadatos de cabecera (`Feature Branch`, `Status`). [Completeness, Gap]

- [ ] CHK003 — ¿Están definidas User Stories con formato GIVEN/WHEN/THEN para todos los escenarios de ejecución? El spec 001 usa esta estructura obligatoria; el spec 008 NO tiene ninguna User Story explícita. [Completeness, Gap, Spec §T001-T003]

- [ ] CHK004 — ¿Hay un requisito funcional explícito que exija añadir un paso de CI/CD en `.github/workflows/python-tests.yml` para verificar la ejecución directa de `python3 -m src.discovery.ingestor`? El spec no menciona CI/CD en ningún requisito FR-00x. [Completeness, Gap]

- [ ] CHK005 — ¿Están documentados los requisitos de comportamiento cuando el módulo es importado por pytest (sin `os.chdir`)? La constitution prohíbe side-effects en tiempo de importación; `os.chdir()` en el nivel de módulo es un side-effect. ¿Hay un requisito que aclare si esto es aceptable o propone una alternativa? [Completeness, Gap, Conflict]

- [ ] CHK006 — ¿Está especificado el comportamiento esperado cuando `Path(__file__).resolve().parent.parent.parent` no resuelve al root del proyecto (packaging externo, symlinks)? [Completeness, Edge Case, Gap]

- [ ] CHK007 — ¿Existen requisitos no-funcionales (NFR) documentados? El spec no tiene sección NFR para rendimiento, seguridad o retrocompatibilidad con entornos CI. [Completeness, Gap]

- [ ] CHK008 — ¿Está documentado el requisito de que `tasks.md` debe existir para este feature? El directorio de la feature no contiene `tasks.md`. [Completeness, Gap]

---

## Claridad de Requisitos — ¿Son los requisitos específicos e inequívocos?

- [ ] CHK009 — ¿Está cuantificado "Must work with `python3 -m src.discovery.ingestor`" con criterios de éxito/fallo objetivos? El requisito FR-004 no define qué salida concreta indica éxito (¿exit code 0? ¿un log específico?) [Clarity, Spec §T001]

- [ ] CHK010 — ¿Está clarificado qué significa "from any directory" en FR-001? ¿Incluye `/tmp`, `/home/user`, directorios sin permisos de escritura, directorios con otro repositorio git? El spec da ejemplos pero no define el alcance. [Clarity, Spec §FR-001]

- [ ] CHK011 — ¿Es "No PYTHONPATH required" (FR-003) verificable objetivamente? ¿Define el spec **cómo** se demuestra su ausencia en CI? [Clarity, Measurability, Spec §FR-003]

- [ ] CHK012 — ¿Está definido qué significa `os.chdir(PROJECT_ROOT)` cuando se ejecutan múltiples tests en paralelo? El cambio de directorio de trabajo es global al proceso; ¿el spec aclara el impacto en tests que dependan del directorio actual? [Clarity, Spec §T002, Conflict]

- [ ] CHK013 — ¿Están los criterios de aceptación del spec expresados en forma GIVEN/WHEN/THEN o equivalente verificable, en lugar de comentarios narrativos como "Should work"? [Clarity, Measurability, Spec §Acceptance Criteria]

- [ ] CHK014 — ¿Está especificado el comportamiento cuando el módulo es importado múltiples veces en el mismo proceso Python (re-`chdir` en cada import)? [Clarity, Edge Case, Spec §Step 1]

---

## Consistencia de Requisitos — ¿Los requisitos se alinean entre sí sin conflictos?

- [ ] CHK015 — ¿Es consistente FR-003 ("No import-time side-effects" de la constitution) con la solución propuesta `os.chdir(PROJECT_ROOT)` en nivel de módulo? El `plan.md` dice "No import-time side effects ✅ PASS" pero `os.chdir()` a nivel de módulo ES un side-effect. ¿Se resuelve esta contradicción en el spec? [Consistency, Conflict, Spec §Constitution Check]

- [ ] CHK016 — ¿Son consistentes los criterios de aceptación del spec con los del plan? El spec dice "Execute from any directory" (con ruta relativa) pero el plan añade "Test execution from any directory" con ruta absoluta — ¿cuál es el comportamiento requerido con rutas relativas desde `/tmp`? [Consistency, Spec §Acceptance Criteria, Plan §Phase 2]

- [ ] CHK017 — ¿Son consistentes los requisitos de tests entre el spec (T002, FR-005/FR-007) y el plan? El spec dice "All 21 existing tests should pass" pero si se requiere también un nuevo test CI, ¿se actualiza el conteo? [Consistency, Spec §T002, Plan §Phase 2]

---

## Calidad de Criterios de Aceptación — ¿Son los criterios de éxito medibles?

- [ ] CHK018 — ¿Son los criterios de aceptación del spec medibles sin ambigüedad? "Should work without PYTHONPATH" no es objetivamente medible. ¿Define el spec el exit code, la ausencia de tracebacks o una salida específica como criterio? [Acceptance Criteria, Measurability, Spec §Acceptance Criteria]

- [ ] CHK019 — ¿Hay un criterio de aceptación explícito para CI/CD? Los tres criterios de aceptación del spec cubren ejecución local únicamente. No hay ningún criterio de aceptación que requiera que GitHub Actions pase con ejecución directa de CLI. [Acceptance Criteria, Gap]

- [ ] CHK020 — ¿Están definidos los criterios mínimos de documentación? FR-008/FR-009 requieren actualizar el README, pero no definen qué secciones, qué texto exacto eliminar, ni cómo verificar su ausencia (grep en CI). [Acceptance Criteria, Clarity, Spec §T003]

---

## Cobertura de Escenarios — ¿Están todos los flujos cubiertos?

- [ ] CHK021 — ¿Cubre el spec el escenario "ejecutar desde terminal sin PYTHONPATH + sin ningún venv activo"? Los requisitos asumen un entorno virtual, pero un desarrollador podría ejecutar con Python del sistema. [Coverage, Scenario]

- [ ] CHK022 — ¿Tiene el spec un escenario para el flujo CI/CD completo (push a main → GitHub Actions ejecuta `python3 -m src.discovery.ingestor` → paso pasa)? Este es el flujo crítico descrito en el contexto del usuario y no existe como escenario documentado. [Coverage, Gap, CI/CD]

- [ ] CHK023 — ¿Está el escenario de pytest en CI/CD cubierto explícitamente en el spec? El workflow actual ejecuta `pytest` con `--import-mode=importlib`; el spec debería requerir que los tests sigan pasando bajo esas mismas condiciones. [Coverage, Scenario, Gap]

- [ ] CHK024 — ¿Cubre el spec el escenario de fallo del `__main__.py` cuando `src` no está en `sys.path` (ejecución con `python3 src/discovery/ingestor.py` en lugar de `python3 -m src.discovery.ingestor`)? [Coverage, Edge Case]

- [ ] CHK025 — ¿Están definidos requisitos para el comportamiento bajo Python 3.12 y 3.13 (versiones actuales de CI)? La matrix de CI usa 3.12 y 3.13 pero el spec requiere sólo Python 3.11+. [Coverage, Consistency, Spec §FR-001]

---

## Cobertura de Casos Límite (Edge Cases)

- [ ] CHK026 — ¿Está definido el comportamiento cuando `__file__` no está disponible (módulo compilado `.pyc`, ejecutado con `-c`)? [Edge Case, Completeness]

- [ ] CHK027 — ¿Define el spec el comportamiento esperado cuando el config YAML no existe en la ruta especificada (ruta relativa vs absoluta tras el `chdir`)? El error original era `FileNotFoundError`; la solución lo resuelve implícitamente pero ¿hay un requisito explicito? [Edge Case, Spec §Problem]

- [ ] CHK028 — ¿Define el spec qué ocurre si el `os.chdir()` falla por permisos en el PROJECT_ROOT? [Edge Case, Gap, NFR]

---

## Cobertura CI/CD — ¿Están los requisitos de integración continua completamente especificados?

- [ ] CHK029 — **[CRÍTICO]** ¿Hay algún requisito en el spec o plan que exija **añadir** un paso en `.github/workflows/python-tests.yml` para ejecutar `python3 -m src.discovery.ingestor --config ...` directamente? El workflow actual NO tiene este paso y ningún documento de la feature lo requiere explícitamente. [Gap, CI/CD, CRITICAL]

- [ ] CHK030 — ¿Está especificado qué comando exacto debe ejecutarse en CI para validar la ejecución directa? (¿`--dry-run`? ¿con config real? ¿con mock?) [Clarity, Gap, CI/CD]

- [ ] CHK031 — ¿Define el plan en qué fase (Phase 0/1/2) se añade el paso CI/CD? Sin esto la tarea podría quedar fuera del alcance del plan de implementación. [Completeness, Plan, Gap]

- [ ] CHK032 — ¿Está documentado que el paso de CI debe ejecutarse sin `PYTHONPATH` exportado, y que el workflow NO debe añadir `PYTHONPATH` como variable de entorno en ese paso? [Clarity, CI/CD, Gap]

- [ ] CHK033 — ¿Están definidos los requisitos para ambas versiones de Python en matrix (3.12 y 3.13) al ejecutar el CLI directamente en CI? [Coverage, CI/CD, Gap]

---

## Completitud del Plan — ¿Cubre el plan todos los pasos necesarios?

- [ ] CHK034 — ¿Incluye el plan un paso explícito para añadir el job/step de validación CLI directa en `.github/workflows/python-tests.yml`? El plan lista tareas hasta "Run existing unit tests" pero no añade un paso de CI para `python3 -m src.discovery.ingestor`. [Plan Completeness, Gap]

- [ ] CHK035 — ¿Especifica el plan cómo se verificará que `pytest` sigue pasando con `--import-mode=importlib` DESPUÉS de añadir `os.chdir()` en nivel de módulo? [Plan Completeness, Spec §T002]

- [ ] CHK036 — ¿Tiene el plan una tarea explícita para verificar la ausencia de `PYTHONPATH` en la documentación actualizada? FR-009 lo requiere pero el plan no tiene tarea de verificación. [Plan Completeness, Spec §FR-009]

- [ ] CHK037 — ¿Define el plan el criterio de verificación (Verify command) para cada tarea siguiendo el patrón Do/Files/Done-when/Verify/Commit del proyecto? El plan describe pasos pero no sigue el formato de tasks.md del proyecto. [Plan Completeness, Gap]

---

## Dependencias y Suposiciones

- [ ] CHK038 — ¿Está documentada la suposición de que la estructura de directorios del repositorio es siempre `repo_root/src/discovery/ingestor.py` (tres niveles arriba)? Si el proyecto se reorganiza, el cálculo de PROJECT_ROOT se rompe silenciosamente. [Assumption, Spec §research.md Decision 3]

- [ ] CHK039 — ¿Está documentada la dependencia de que `configs/stage_1_discovery/php_legacy.yaml` exista en CI para el test de CLI directo? El workflow CI crea mocks para `configs/stage_5_evaluation/` pero no para `configs/stage_1_discovery/`. [Dependency, Gap, CI/CD]

- [ ] CHK040 — ¿Documenta el spec la dependencia de que NO se debe configurar `PYTHONPATH` en el entorno host donde se ejecuta el CLI? [Dependency, Assumption]

---

## Ambigüedades y Conflictos

- [ ] CHK041 — **[CRÍTICO]** ¿Resuelve el spec la contradicción entre "No import-time side-effects" (constitution §III) y `os.chdir(PROJECT_ROOT)` ejecutado al importar el módulo? El plan dice "✅ PASS" sin justificación técnica. [Ambiguity, CRITICAL, Conflict]

- [ ] CHK042 — ¿Clarifica el spec si `python3 -m src.discovery.ingestor` y `python3 src/discovery/ingestor.py` son equivalentes o si solo uno es el modo de ejecución soportado? Los criterios de aceptación usan `python3 -m`, pero el mensaje de error original usa `python3 src/discovery/ingestor.py`. [Ambiguity, Spec §Problem]

- [ ] CHK043 — ¿Define el spec con precisión qué se considera "any directory"? ¿Aplica solo si `src` está en `sys.path` (i.e., con `python3 -m` desde cualquier lugar)? Desde `/tmp` sin PYTHONPATH, `python3 -m src.discovery.ingestor` fallará con `ModuleNotFoundError` si el repo no está instalado. [Ambiguity, CRITICAL, Spec §Acceptance Criteria]

- [ ] CHK044 — ¿Está clarificado si el `__main__.py` propuesto importa `from src.discovery.ingestor import main` (requiere `src` en sys.path) o usa importación relativa `from .ingestor import main`? Esta distinción determina si la solución funciona sin PYTHONPATH. [Ambiguity, Gap, research.md Decision 2]

---

## Rastreabilidad

- [ ] CHK045 — ¿Tienen los requisitos FR-001..FR-009 IDs únicos y persistentes en el spec que el plan, tasks y tests puedan referenciar de forma inequívoca? Los IDs existen pero no hay trazabilidad inversa desde el plan hacia los FRs. [Traceability]

- [ ] CHK046 — ¿Está la causa raíz del bug (`--import-mode=importlib` de pytest) trazada a un requisito específico que exija que la solución funcione con y sin esa bandera? [Traceability, Gap]

---

## GAP SUMMARY — Brechas críticas que deben resolverse

Los siguientes gaps son **bloqueantes** (CRITICAL) o **de alto impacto** para conseguir que el feature pase tanto en terminal manual como en CI/CD:

### 🔴 CRITICAL — Bloqueantes

| ID | Brecha | Req. afectado | Acción |
|----|--------|---------------|--------|
| **CHK029** | No existe ningún requisito que exija añadir un paso CI/CD en `python-tests.yml` para validar `python3 -m src.discovery.ingestor` directamente | Spec: ninguno | Añadir FR-010 al spec y tarea en plan Phase 2 |
| **CHK041** | Contradicción no resuelta entre `os.chdir()` en tiempo de importación y la constitution §III "No import-time side-effects" | Plan §Constitution Check | Resolución explícita en spec: justificación técnica o propuesta de alternativa (lazy init, `__main__` guard) |
| **CHK043** | Los criterios de aceptación "Execute from any directory" son falsos sin PYTHONPATH si se usa `python3 -m` desde `/tmp` y el repo no está instalado. El `__main__.py` no resuelve `ModuleNotFoundError` | Spec §Acceptance Criteria | Aclarar el scope: la solución solo funciona si el cwd es el repo root O si se ejecuta con `python3 -m` desde dentro del repo en sys.path |

### 🟠 HIGH — Impacto significativo

| ID | Brecha | Req. afectado | Acción |
|----|--------|---------------|--------|
| **CHK001** | La causa raíz completa (doble fallo: `ModuleNotFoundError` + `FileNotFoundError`) no está documentada en el spec | Spec §Problem | Actualizar §Problem con ambas causas |
| **CHK003** | Ausencia de User Stories GIVEN/WHEN/THEN (patrón obligatorio según template del proyecto) | Spec: ninguno | Añadir User Stories para escenarios: terminal manual, CI pytest, CI CLI directo |
| **CHK015** | `os.chdir()` en nivel de módulo viola "No import-time side-effects" sin justificación en el spec | Spec §Requirements, Plan | Documentar decisión explícita o proponer lazy init bajo `if __name__ == "__main__"` |
| **CHK022** | El flujo CI/CD completo (push → GA ejecuta CLI → pasa) no existe como escenario cubierto | Spec: ninguno | Añadir User Story 3 con este escenario |
| **CHK039** | `configs/stage_1_discovery/php_legacy.yaml` no se crea como mock en CI; el test de CLI directo en GA fallará con FileNotFoundError | Plan §Phase 2, workflow | Añadir creación del mock config en el workflow o usar `--dry-run` |

### 🟡 MEDIUM — Calidad y mantenibilidad

| ID | Brecha | Acción |
|----|--------|--------|
| **CHK004** | Sin FR para añadir el step CI/CD | Añadir FR-010 |
| **CHK008** | `tasks.md` no existe | Crear tasks.md con tareas Phase 2 |
| **CHK019** | Sin criterio de aceptación para CI/CD | Añadir AC-4 al spec |
| **CHK044** | Ambigüedad importación relativa vs absoluta en `__main__.py` | Aclarar en research.md Decision 2 |
| **CHK030** | Comando exacto del CI step no definido (¿`--dry-run`? ¿config real?) | Definir en plan Phase 2 |
