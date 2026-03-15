## 🔎 Self-Audit — Key Deviations (actionable)
The following issues were discovered during an automated/manual scan. These are prioritized by impact and mapped to simple remediation actions.

1) Monolith modules
    - Examples: `src/factory/production_v11.py` (~2k+ LOC), `src/audit/model_evaluator.py` (~1.2k+ LOC).
    - Impact: Violates §3.1 guidance (modules should be small and single-responsibility). Hard to test and maintain.
    - Remediation: Split into smaller modules. Add typed interfaces for each submodule.

2) `src/merger/` is empty
    - Impact: README and some docs mention a merger; the folder exists but contains no implementation.
    - Remediation: Either add the intended implementation (`surgical_merge.py`) or remove the empty folder and update docs to avoid confusion.

3) Formatting tool mismatch in docs
    - `Makefile` and `README` recommend `ruff` for formatting; some docs and `AGENTS.md` historically referenced `black`.
    - Remediation: Declare canonical formatter in `pyproject.toml` and `requirements-dev.txt` (e.g., add `ruff` and optionally `black`), and add a `pre-commit` config if desired.

4) Secrets & CI behaviour
    - The repository uses `google-genai` optionally; `GOOGLE_API_KEY` controls whether the `GeminiClient` is used. CI intentionally leaves `GOOGLE_API_KEY` unset and uses local mocks/vLLM.
    - Remediation: Keep API keys out of source and document `AEGF_*` env var patterns in `configs/*.example`.

5) Default inference backend should be local vLLM
     - Detail: Make the default inference engine `vllm` (local/OpenAI-compatible HTTP) instead
        of auto-selecting `gemini`. Configuration should allow overriding via `.env` (e.g.
        `AEGF_PROFESSOR_BACKEND`) or `configs/stage_5_evaluation/eval_config.yaml`.
     - Impact: Prevent accidental use of Gemini in environments that have the SDK/API key
        available; aligns with CI expectations and local development workflows.
     - Remediation: Update the router/defaults and document the env/config option.
    
6) Refactor tests

## 🚀 Pruebas Rápidas y Bucle de Optimización (propuesta)

Objetivo: permitir experimentación rápida y reproducible sobre configuraciones de `stage_1`/`stage_2` (generación) y `stage_4` (entrenamiento) usando un tokenizador BPE canónico y la métrica `val_bpb` como proxy barato de calidad de LM.

- [ ] Entrenar/guardar tokenizador BPE canónico (`rustbpe`/`tiktoken`) y `token_bytes.pt` (Stage 3 — Curation). Script sugerido: `src/research/train_tokenizer.py`.
- [ ] Implementar `evaluate_bpb(model, tokenizer, batch_size)` reutilizable (Stage 5 — Evaluation). Script sugerido: `src/audit/eval_bpb.py`.
- [ ] Crear loop de experimentos de dataset (Factory → Curation): generar variantes parametrizadas (ej. `dedup_threshold`, `gold_injection_rate`, `min_length`, `sample_weighting`) y versionarlas con metadatos.
- [ ] Implementar `fast-mode` runner (Stage 4) para probes rápidos: modelos pequeños, short TIME_BUDGET, pocos shards, val shards fijos; registrar `val_bpb`, `peak_vram_mb`, `mfu_percent`, `total_tokens_M` en TSV/DB.
- [ ] Orquestador de experimentos: `src/research/experiment_orchestrator.py` que coordine: generar variante → empaquetar → tokenizar (reusar tokenizer canónico) → entrenar fast-mode → evaluar → registrar resultados.
- [ ] Añadir checklist de compatibilidad Axolotl: cómo cambiar tokenizer sin romper embeddings (opciones: usar tokenizer base; añadir `added_tokens`; expandir embeddings con cuidado). Documentar en `configs/stage_4_training/axolotl/README.md`.
- [ ] Tests de reproducibilidad y smoke checks: seed determinista, pruebas que confirmen que `evaluate_bpb` funciona y que el pipeline no rompe con config rápidas.
- [ ] Documentación: `docs/experiments.md` con flujo de trabajo, criterios para escalar (de probes → runs medianos → runs completos) y recomendaciones de validación adicional (múltiples shards y evaluación humana/juez para SFT).

Notas rápidas:
- No reentrenar el tokenizador en cada iteración (costoso y rompe compatibilidad de embeddings); reentrenar solo cuando la distribución cambie mucho.
- Usar múltiples shards de validación para reducir riesgo de sobreajuste al shard único.
- Fast‑mode es una estrategia de búsqueda (no reemplaza validación a escala): sirve para encontrar direcciones prometedoras antes de escalar.

---

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