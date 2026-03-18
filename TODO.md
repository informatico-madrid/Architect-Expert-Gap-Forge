## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.

### [ ] STAGE 6: Optimización de Paralelismo para Calibración

**Contexto actual**: La calibración secuencialmente:
1. Envía prompt → inferencia → respuesta
2. Envía respuesta → judge → score
3. Decide siguiente parámetro basado en score

**Limitaciones**:
- ~30-60 segundos por iteración (inferencia + judge)
- 540 iteraciones = ~4-8 horas
- GPU/CPU subutilizada durante espera

**Oportunidades de Paralelismo**:

1. **Paralelismo de Inferencia + Judge (FÁCIL - bajo riesgo)**
   - Qué: Ejecutar inferencia y judge en paralelo para el mismo prompt
   - Cómo: Usar `asyncio.gather()` o threads
   - Riesgo: Bajo - son operaciones independientes
   - Speedup: ~1.5-2x

2. **Batch de Mismos Perfiles (MEDIO - riesgo bajo)**
   - Qué: Si el mismo perfil se evalúa contra múltiples prompts, hacer en batch
   - Cómo: Agrupar por profile, enviar múltiples prompts a la vez
   - Riesgo: Medio - requiere gestión de memoria
   - Speedup: ~2-3x

3. **Pipeline Paralelo (AVANZADO - mayor riesgo)**
   - Qué: Mientras se evalúa el profile N+1, ya preparar el profile N+2
   - Cómo: Usar cola de trabajo con workers
   - Riesgo: Alto - complejas condiciones de carrera
   - Speedup: ~3-4x

**Notas de Implementación Segura**:
- Mantener checkpointing frecuente
- Límite de concurrencia: 2-3 requests paralelos máximo
- Fallback secuencial si paralelo falla
- Tests de stress con mock server antes de producción

**ROI Estimado**: Implementación fácil (opción 1): 2 días → 50% tiempo ejecución

---

### [ ] INFRA: Dynamic Context Router para Master Documents (Post-Merge Ralph)
- **Contexto**: Actualmente se inyectan ~53k tokens de $changelog en cada prompt, saturando la atención del modelo y consumiendo VRAM innecesaria.
- **Objetivo**: Implementar un sistema de ruteo dinámico de contexto que segmente el Master Guide y el Changelog.
- **Tareas Técnicas**:
    - Reutilizar la lógica de `get_theory_fragments` para chunking por headers (`#`, `##`).
    - Desarrollar un `KeywordMatcher` que analice el archivo legacy de osCommerce (entrada) y seleccione solo los fragmentos de doctrina relevantes.
    - Modificar `_base_system_block` en `production_v11.py` para aceptar `relevant_changelog` en lugar del string completo.
- **Restricción**: No implementar hasta que el refactor de arquitectura actual en la rama de Ralph-Loop sea mergeado en main.

### [ ] INFRA: Prototipado de PHPLegacyDriver (Regex-based)
- **Razón**: El parsing AST es inestable en código procedural 2000-2010.
- **Objetivo**: Desarrollar extractor basado en firmas de patrones (globals, db_calls, includes).
- **Validación**: Testear extracción en osCommerce, WP y ZenCart.

---

## STAGE 6 — Hallazgos: inconsistencia en filtro `noxious` (PENDIENTE)

- Fecha: 2026-03-16
- Contexto: durante la ejecución/resume de la calibración, el `Active grid` mostrado en la iteración actual es:

    Active grid: temperature=[0.3,0.6,0.7,0.9,1.1] | top_p=[1.0] | top_k=[20] | min_p=[0.0,0.05,0.1] | repetition_penalty=[1.15,1.2] | presence_penalty=[0.0]

- Datos agregados (inspección de checkpoints):
    - Archivos JSON escaneados: 526
    - Entradas únicas agregadas: 522
    - Mejor valor por parámetro (media de `adjusted/composite score`):
        - `temperature`: **0.7** (media=0.8750, n=6)
        - `top_p`: **0.8** (media=0.8662, n=306)
        - `top_k`: **10** (media=0.8684, n=94)
        - `min_p`: **0.0** (media=0.8607, n=168)
        - `repetition_penalty`: **1.15** (media=0.8637, n=139)
        - `presence_penalty`: **0.5** (media=0.8742, n=109)

- Observación crítica:
    - Varias de las mejores opciones calculadas a partir de los checkpoints (p. ej. `top_p=0.8`, `top_k=10`, `presence_penalty=0.5`) **NO aparecen** en el `Active grid` actual — fueron descartadas por el pre-filter o por la lógica de resume.
    - Riesgo: el filtro actual puede estar descartando valores potencialmente buenos debido a heurísticas insuficientes (tamaños de muestra bajos, umbrales absolutos inadecuados o agregación parcial de datos).

- Estado: **PENDIENTE** — tarea de investigación/definición de algoritmo.
    - Descripción de la tarea pendiente: "Diseñar e implementar un algoritmo matemático riguroso de descarte para el `noxious` filter que:
        - agregue resultados históricos de todos los checkpoints;
        - use criterios estadísticos robustos o modelos bayesianos (ANOVA/Kruskal‑Wallis + post‑hoc, o modelo jerárquico bayesiano) para comparar valores;
        - incorpore umbrales dependientes del tamaño de muestra y del tamaño del efecto (no sólo delta absoluto);
        - incluya guardrails que eviten eliminar todas las opciones de un parámetro;
        - defina reglas de persistencia/trazabilidad para decisiones de descarte (audit trail) y export diagnostic CSV/JSON para revisión humana.
    "

- Prioridad: **Alta**. Owner: TBD.

- Nota del equipo: **NO** ejecutar cambios automáticos en los scripts ahora; el objetivo de este ítem es dejar la inconsistencia documentada y pendiente para diseñar un algoritmo matemático de descarte que solucione la discrepancia.
