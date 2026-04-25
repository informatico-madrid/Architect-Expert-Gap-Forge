# Informe de Issues: Spec dependency-compatibility (v2.0)

**Fecha:** 2026-04-23
**Modo:** Party Mode v4.0 — 3 Agentes Reales (Winston, Amelia, Mary)
**Spec:** `specs/dependency-compatibility/`
**BMad Source:** Story 0.4 — `_bmad-output/planning-artifacts/epics.md:290-324`
**Alcance:** 4 issues filtrados (excluyendo los 4 ya documentados en BMad Story 0.4)

---

## Resumen Ejecutivo

Se analizaron **4 issues** de la spec `dependency-compatibility` mediante invocación real de 3 agentes BMAD (Winston-Architect, Amelia-Developer, Mary-Business Analyst). Los issues 1, 3, 7 y 8 fueron evaluados contra la spec, BMad Story 0.4 y el estado real del workspace.

| # | Issue | Winston | Amelia | Mary | Consenso |
|---|-------|--------|--------|------|----------|
| 1 | datasets pinning: spec `==2.21.0` vs epics.md `>=2.19,<3.0` | Won't fix (perception issue) | HIGH severity (trazabilidad) | HIGH severity (single source of truth) | **DISACUERDO — requiere decisión** |
| 3 | langchain-core exclusion list | AC incompleto, agregar pin | DEACUERDO, agregar pin | CRITICAL (gap en elicitation) | **ACUERDO parcial — agregar pin** |
| 7 | silent downgrades (packaging, fsspec) | NO es issue, AC ya lo maneja | DISCUELDO, rango ≠ pin exacto | HIGH severity (downgrade de 2 años) | **DISACUERDO — requiere pins exactos** |
| 8 | infrastructure/ race condition | NO es issue, ya existe | VERIFICADO, ya existe | Low, AC incompletos | **NO ES ISSUE — invalidado** |

---

## Issue 1: Contradicción datasets — spec `==2.21.0` vs epics.md `>=2.19,<3.0`

### Descripción

Existe una contradicción de trazabilidad entre la spec y BMad:

- [`requirements.md:31`](../specs/dependency-compatibility/requirements.md:31) FR-1 dice: `datasets==2.21.0` (pin exacto)
- [`epics.md:317`](../_bmad-output/planning-artifacts/epics.md:317) dice: *"Must pin `>=2.19,<3.0` to prevent 4.x API breakage"* (rango con upper bound)
- [`plan.md:69`](../specs/dependency-compatibility/plan.md:69) dice: `datasets==2.21.0` (exact pin)
- [`research.md:258`](../specs/dependency-compatibility/research.md:258) recomienda: `datasets>=2.19,<3.0` (rango)

El source canónico BMad (epics.md) recomienda rango; la spec usa pin exacto.

### Evidencia

| Archivo | Línea | Valor |
|---------|-------|-------|
| `requirements.md` | 31 | `datasets==2.21.0` |
| `epics.md` | 317 | `datasets>=2.19,<3.0` |
| `research.md` | 258 | `datasets>=2.19,<3.0` |
| `deep-research.md` | 573 | `datasets>=2.19,<3.0` |

### Estado en BMad

Story 0.4 en [`epics.md:317`](../_bmad-output/planning-artifacts/epics.md:317) dice explícitamente: *"Pre-existing bug: datasets `>=2.19` allows 4.8.4. Must pin `>=2.19,<3.0`."* BMad recomienda rango con upper bound.

### Opiniones de Agentes

#### 🏗️ Winston (Architect)

> "Spec AC `==2.21.0` es CORRECTO. epics.md:317 dice `>=2.19,<3.0` que es un rango, no una contradicción. La spec tiene `==2.21.0` que es más restrictivo que el rango. Esto es deliberado — previene 4.x Y previene patches. Cerrar como **won't fix — perception issue**."

**Razonamiento:** El pin exacto es más seguro que el rango. Si epics.md recomienda `<3.0`, y la spec usa `==2.21.0`, la spec está siendo más conservative. No hay contradicción funcional.

#### 💻 Amelia (Developer)

> "DISCUELTO con Winston. Spec AC `==2.21.0` CONTRADICE epics.md:317 'Must pin `>=2.19,<3.0`'. Si el **source canonical es epics.md**, entonces el spec tiene un **defecto de trazabilidad**. Severity: **HIGH**."

**Razonamiento:** Cuando hay dos documentos fuente con versiones diferentes, se viola el principio de "single source of truth". La spec debería rastrear a epics.md como source canónico. Un implementador podría preguntarse: "¿sigo la spec o sigo epics?"

#### 📊 Mary (Business Analyst)

> "Severity **HIGH**. Defecto de trazabilidad de requisitos. Cuando hay dos documentos fuente (spec vs epics) con versiones diferentes, se viola el principio de 'single source of truth'. Debe resolverse **antes de implementación**."

**Razonamiento:** El equipo de implementación necesita una respuesta clara. Si la spec contradice BMad, ¿cuál gana? Esta ambigüedad puede causar que el código se implemente de manera inconsistente.

### Veredicto

| Agente | Severidad | Recomendación |
|--------|-----------|---------------|
| Winston | -- | Won't fix (perception issue) |
| Amelia | **HIGH** | Fix defect — alinear con epics.md |
| Mary | **HIGH** | Fix defect — resolver antes de implementación |

**Consenso: DISACUERDO.** Se requiere decisión de product owner. La spec contradice explícitamente a BMad epics.md:317.

**Recomendación técnica:** Si el source canónico es epics.md (BMad), entonces la spec debe actualizarse a `datasets>=2.19,<3.0`. Si la spec es el source canónico (override de BMad), entonces epics.md debe actualizarse. No puede haber dos verdades.

---

## Issue 3: langchain-core 0.3.84 en exclusion list de langgraph

### Descripción

[`deep-research.md:199-204`](../specs/dependency-compatibility/deep-research.md:199) documenta que `langchain-core==0.3.84` está en la lista de exclusión de `langgraph==0.2.76`. La spec documenta esto como "known fragility" pero no agrega un pin explícito.

### Evidencia

| Archivo | Línea | Claim |
|---------|-------|-------|
| `deep-research.md` | 199-204 | langgraph excluye 23 patches de 0.3.x |
| `research.md` | 70 | langchain-core 0.3.84 is in langgraph exclusion list |
| `requirements.md` | 46 | Document as known fragility to monitor |

### Estado en BMad

Story 0.4 en [`epics.md:300`](../_bmad-output/planning-artifacts/epics.md:300) menciona `langgraph==0.2.76` con `<1.0` upper bound pero **NO menciona la exclusion list** de langchain-core. Winston lo cataloga como "parcialmente en BMad (tabla de riesgos existe) pero AC incompleto."

### Opiniones de Agentes

#### 🏗️ Winston (Architect)

> "Parcialmente en BMAD (tabla de riesgos existe) pero AC incompleto. Debe agregar `langchain-core==0.3.84` a las pins exactas en requirements.txt."

**Razonamiento:** La solución es simple: pinear explícitamente para eliminar la ambigüedad del resolver.

#### 💻 Amelia (Developer)

> "DEACUERDO con Winston. Agregar `langchain-core==0.3.84` a pins exactas."

**Razonamiento:** El pin explícito es la única manera de garantizar reproducibilidad. Sin él, el resolver podría elegir una versión diferente en un entorno limpio.

#### 📊 Mary (Business Analyst)

> "Severity **CRITICAL**. BMAD debería haber cubierto langchain-core en la investigación de dependencias transitivas. Esto es un **gap en el proceso de elicitation**."

**Razonamiento:** Que BMad no haya identificado este riesgo en su investigación original indica un problema en el proceso de elicitation. El deep research lo encontró, pero nunca debió llegar a deep research sin ser detectado en la primera pasada.

### Veredicto

| Agente | Severidad | Recomendación |
|--------|-----------|---------------|
| Winston | -- | Agregar `langchain-core==0.3.84` a pins exactas |
| Amelia | **HIGH** | Agregar `langchain-core==0.3.84` a pins exactas |
| Mary | **CRITICAL** | Gap en proceso — agregar pin + mejorar proceso |

**Consenso: ACUERDO parcial.** Los tres aceptan que se debe agregar el pin. Mary añade que esto revela un gap en el proceso de elicitation de BMad.

**Recomendación:** Agregar `langchain-core==0.3.84` a requirements.txt y FR-1 AC debe verificar que el pin está presente.

---

## Issue 7: Silent downgrades (packaging 26.0→25.0, fsspec 2026.3.0→2024.6.1)

### Descripción

La instalación causa downgrades silenciosos documentados en [`requirements.md:43-45`](../specs/dependency-compatibility/requirements.md:43):
- `packaging` 26.0 → 25.0 (enforced by langgraph `<26.0`)
- `fsspec` 2026.3.0 → 2024.6.1 (enforced by datasets `<=2024.6.1`)

La spec dice "documented" pero no mitiga con pins explícitos.

### Evidencia

| Archivo | Línea | Contenido |
|---------|-------|-----------|
| `requirements.md` | 43-45 | Documenta downgrades esperados |
| `research.md` | 155-158 | Tabla de downgrades observados |
| `deep-research.md` | 527-537 | Gotchas: fsspec y packaging downgrade |

### Estado en BMad

Story 0.4 en [`epics.md`](../_bmad-output/planning-artifacts/epics.md) **NO menciona explícitamente** los downgrades de packaging y fsspec. Este es un hallazgo del deep research que BMad no cubrió en detalle.

### Opiniones de Agentes

#### 🏗️ Winston (Architect)

> "NO es un issue. Los AC ya lo manejan correctamente con bounded ranges (`packaging>=25.0,<26.0`, `fsspec>=2023.1.0,<2025.0.0`). Cerrar."

**Razonamiento:** El bounded range ES la mitigación correcta. No se necesita un pin exacto — el rango ya garantiza que no habrá breaking changes. Los downgrades están documentados y los ranges previenen regressions.

#### 💻 Amelia (Developer)

> "DISCUELTO con Winston. Rango acotado (`>=2.0.0,<2026.0.0`) NO es equivalente a pin exacto (`==25.0`). Para **reproducibilidad absoluta** se necesitan pins exactas. Severity: **Medium**."

**Razonamiento:** Un rango permite actualizaciones menores dentro del bound. Para una spec de dependency compatibility cuyo objetivo es reproducibilidad, el pin exacto es la única opción que garantiza que todos los entornos tengan exactamente la misma versión.

#### 📊 Mary (Business Analyst)

> "Severity **HIGH**. Riesgo de seguridad/funcional. fsspec downgrade de 2 años (2026.3.0→2024.6.1) es inaceptable sin análisis de compatibilidad explícito."

**Razonamiento:** El downgrade de fsspec de 2026.3.0 a 2024.6.1 es un salto de ~2 años. Esto podría perder features ofixes de seguridad. Mary no entiende por qué se aceptaría un downgrade tan agresivo sin justificación explícita de compatibilidad.

### Veredicto

| Agente | Severidad | Recomendación |
|--------|-----------|---------------|
| Winston | -- | No es issue, bounded ranges son suficientes |
| Amelia | **MEDIUM** | Pins exactos necesarios para reproducibilidad |
| Mary | **HIGH** | Downgrade de 2 años inaceptable sin análisis |

**Consenso: DISACUERDO.** Winston cree que ranges son suficientes; Amelia y Mary requieren pins exactos.

**Recomendación técnica:** La spec debería usar pins exactos (`packaging==25.0`, `fsspec==2024.6.1`) o el rango debe justificarse con análisis de compatibilidad. El downgrade de 2 años en fsspec requiere justificación explícita.

---

## Issue 8: infrastructure/ no existe — race condition potencial

### Descripción

La spec asume que `infrastructure/dependency_check.py` vivirá en un directorio `infrastructure/` que **no existe actualmente**. Spec 1 (baseline-measurement) y Spec 4 (dependency-compatibility) necesitan este directorio.

### Evidencia

```
# specs/_epics/aegf-infrastructure/epic.md:94 dice: "infrastructure/ directory does NOT exist -- must be created"
# epics.md:321 dice: "Dependencies: none — this spec is independent and should run FIRST"
```

### Estado en BMad

BMad Story 0.4 en [`epics.md:321`](../_bmad-output/planning-artifacts/epics.md:321) dice: *"Dependencies: none — this spec is independent and should run FIRST."* Esto implicitamente significa que Spec 4 corre primero y crea el directorio.

### Verificación en workspace

**Amelia verificó:** `infrastructure/__init__.py` **ya existe** en el workspace (visible en Git Status: `?? infrastructure/__init__.py`). El directorio fue creado.

### Opiniones de Agentes

#### 🏗️ Winston (Architect)

> "NO es un issue. Spec 4 se ejecuta primero, infrastructure/ ya existe. Cerrar."

#### 💻 Amelia (Developer)

> "VERIFICADO que `infrastructure/__init__.py` ya existe en el workspace. **Issue invalidado**."

#### 📊 Mary (Business Analyst)

> "Low severity. No es una race condition real pero los AC son incompletos — deberían verificar existencia del directorio."

### Veredicto

| Agente | Severidad | Recomendación |
|--------|-----------|---------------|
| Winston | -- | No es issue, cerrar |
| Amelia | -- | Invalidado, ya existe |
| Mary | **Low** | AC incompletos, añadir verificación |

**Consenso: NO ES ISSUE.** El directorio ya existe en el workspace. Issue cerrado.

---

## Tabla Comparativa de Opiniones

| Issue | Winston | Amelia | Mary | Veredicto |
|-------|---------|--------|------|------------|
| **1. datasets pinning** | Won't fix (perception issue) | HIGH — defecto trazabilidad | HIGH — single source of truth | **DISACUERDO** |
| **3. langchain-core** | AC incompleto, agregar pin | Agregar pin | CRITICAL — gap elicitation | **ACUERDO parcial** |
| **7. downgrades** | No es issue (ranges OK) | MEDIUM — rango ≠ pin | HIGH — downgrade 2 años | **DISACUERDO** |
| **8. infrastructure/** | No es issue | Invalidado (ya existe) | Low (AC incompletos) | **NO ES ISSUE** |

---

## Conclusiones y Próximos Pasos

### Decisiones Requeridas (P0)

| # | Decision | Responsabilidad |
|---|----------|------------------|
| 1 | **datasets pinning:** ¿Pin exacto (`==2.21.0`) o rango (`>=2.19,<3.0`)? BMad epics.md dice rango; spec dice pin. ¿Cuál es el source of truth? | Tech Lead / Product Owner |
| 7 | **silent downgrades:** ¿Bounded ranges son suficientes o se requieren pins exactos para `packaging` y `fsspec`? | Tech Lead |

### Acciones Inmediatos (P1)

| # | Acción | Severidad |
|---|--------|-----------|
| 3 | Agregar `langchain-core==0.3.84` a pins exactas en requirements.txt | HIGH |
| 8 | Issue cerrado — directorio ya existe | N/A |

### Mejoras de Proceso (P2)

| # | Mejora | Detectado por |
|---|--------|---------------|
| 3 | Gap en elicitation: BMad no identificó langchain-core exclusion list en investigación original | Mary |
| 1 | Proceso de trazabilidad: Cuando spec contradice BMad, ¿cuál gana? Necesitamos resolver la jerarquía de documentos | Amelia |

---

## Metodología

1. Lectura de [`plan.md`](../specs/dependency-compatibility/plan.md), [`requirements.md`](../specs/dependency-compatibility/requirements.md), [`research.md`](../specs/dependency-compatibility/research.md), [`deep-research.md`](../specs/dependency-compatibility/deep-research.md)
2. Contraste contra Story 0.4 en [`epics.md:290-324`](../_bmad-output/planning-artifacts/epics.md:290)
3. **Invocación real de 3 agentes BMAD:**
   - Winston (Architect) — perspectiva arquitectónica
   - Amelia (Developer) — perspectiva de implementación
   - Mary (Business Analyst) — perspectiva de negocio
4. Recopilación de opiniones divergentes y consensos

---

*Informe generado por Party Mode v4.0 (3 agentes reales) — 2026-04-23*
