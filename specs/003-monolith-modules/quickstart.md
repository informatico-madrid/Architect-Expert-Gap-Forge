# Quickstart: Refactorización de Módulos Monolíticos

**Audience**: Desarrollador que va a implementar o revisar esta refactorización  
**Date**: 2026-03-12

---

## Contexto rápido

Esta feature divide dos módulos monolíticos en submódulos de responsabilidad única:

| Monolito | LOC | Submódulos resultantes |
|---------|-----|----------------------|
| `src/factory/production_v11.py` | 2 565 | `config`, `prompt_builder`, `fragment_extractor`, `ldi_validator`, `checkpoint`, `pipeline_runner`, `cli` |
| `src/audit/model_evaluator.py` | 1 425 | `config`, `gap_generator`, `exam_builder`, `judge`, `scorecard`, `report_writer`, `cli` |

---

## Prerrequisitos

```bash
# Verificar que el baseline de tests pasa antes de empezar
cd /mnt/bunker_data/ai/data_factory
source .venv/bin/activate
make test   # debe terminar con 0 fallos
```

---

## Proceso de implementación por fase

### Fase A — `src/factory/production_v11.py`

```bash
# 1. Crear los ficheros nuevos (vacíos con cabecera del proyecto)
touch src/factory/{config,prompt_builder,fragment_extractor,ldi_validator,checkpoint,pipeline_runner,cli}.py

# 2. Mover código bloque a bloque (ver data-model.md para la asignación)
#    Orden recomendado: config → prompt_builder → fragment_extractor
#                       → ldi_validator → checkpoint → pipeline_runner → cli

# 3. Tras cada fichero movido, verificar que los tests siguen pasando:
python -m pytest tests/test_production_v11*.py --tb=short -q

# 4. Actualizar imports en todos los test files
grep -rl "from src.factory.production_v11" tests/ | xargs sed -i 's|src.factory.production_v11|src.factory.<nuevo_modulo>|g'

# 5. Actualizar src/factory/__init__.py para re-exportar la API pública
# 6. Eliminar src/factory/production_v11.py
# 7. Verificar cobertura:
make coverage
```

### Fase B — `src/audit/model_evaluator.py`

```bash
# Mismo proceso que Fase A, en este orden:
# config → gap_generator → exam_builder → judge → scorecard → report_writer → cli

python -m pytest tests/test_model_evaluator*.py --tb=short -q
make coverage
```

### Fase C — Archivos secundarios (P2, fuera del alcance inmediato)

```
src/curation/backtracking_rewriter.py  (1 539 LOC)
src/curation/nemo_curator_suite.py     (1 315 LOC)
src/discovery/processor.py             (1 227 LOC)
src/factory/agentic_gen.py             (1 204 LOC)
```

Misma metodología: una fase por archivo, tests en verde antes de la siguiente.

---

## Reglas de cada nuevo fichero `.py`

1. **Cabecera obligatoria** — shebang + project id + copyright + SPDX (ver `src/factory/production_v11.py` líneas 1–8 como referencia).
2. **Un logger por módulo**: `logger = logging.getLogger(__name__)` — no `logging.getLogger("root")`.
3. **Sin side-effects en import-time**: no `load_dotenv()`, no `_CONFIG = load_config()` a nivel de módulo.
4. **Tipos explícitos** en todas las funciones públicas.
5. Si el fichero supera 400 LOC, añadir `# ARCH-NOTE: <justificación>` en la cabecera.

---

## Verificación final

```bash
# Tests completos
make test

# Cobertura >= 90%
make coverage

# Sin side-effects en import (se puede testear manualmente importando cada submódulo)
python -c "import src.factory.prompt_builder"
python -c "import src.audit.judge"

# Check de cabeceras de proyecto
python scripts/check_headers.py --check

# Check de tipos estáticos (si mypy está configurado)
make lint
```

---

## Archivos de referencia

| Artefacto | Path |
|-----------|------|
| Especificación | [spec.md](spec.md) |
| Research | [research.md](research.md) |
| Data model | [data-model.md](data-model.md) |
| Tasks | [tasks.md](tasks.md) *(generado por `/speckit.tasks`)* |
| Baseline de tests `factory` | `tests/test_production_v11*.py` (16 archivos) |
| Baseline de tests `audit` | `tests/test_model_evaluator*.py` (7 archivos) |
