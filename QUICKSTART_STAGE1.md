# 🚀 Guía Rápida: Stage 1 Discovery - PHP Legacy a Hexagonal

## ¿Qué es el Stage 1 Discovery?

El **Stage 1 Discovery** es la primera fase del pipeline AEGF que **extrae código fuente** de repositorios PHP legacy y lo transforma en **entidades lógicas estructuradas** para entrenamiento de modelos.

**Objetivo**: Forzar al modelo a deducir lógica desde docstrings y firmas, no copiar código literal.

---

## 📋 Paso a Paso para Empezar

### **Paso 1: Preparar el Entorno**

```bash
# Navega al workspace
cd /mnt/bunker_data/ai/data_factory

# Activa el entorno virtual
source .venv/bin/activate
```

---

### **Paso 2: Ingesta Automática de Repositorios PHP Legacy**

**El sistema tiene un ingestor automático que clona los repositorios definidos en la configuración.**

**Opción A: Usar el script de ingestión (Recomendado)**

```bash
# Ejecuta el script de ingestión
./scripts/ingest-repos.sh

# O en modo dry-run para ver qué se clonará
./scripts/ingest-repos.sh --dry-run
```

**Opción B: Clonar manualmente (si necesitas un repositorio específico)**

```bash
cd /mnt/bunker_data/ai/data_factory/data/raw
git clone https://github.com/oscommerce/oscommerce.git
```

---

### **Paso 3: Ejecutar el Stage 1 Processor**

**Comando principal:**

```bash
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose
```

---

### **Paso 4: Verificar Resultados**

**Output esperado:**

```bash
# Listar bundles generados
ls -lh data/outputs/php-legacy/

# Ver contenido de un bundle
head -100 data/outputs/php-legacy/oscommerce/FUNCTIONAL_UNIT_*.txt
```

**Ejemplo de bundle tipado:**

```
# FILE: includes/modules/payment/cod.php
# TYPE: FUNCTIONAL_UNIT
# PATTERNS: global $order, MODULE_PAYMENT_COD_STATUS
# CONTEXT: Cash on Delivery payment module — procedural, no DI

<?php
class cod {
  function __construct() {
    global $order;
    $this->enabled = MODULE_PAYMENT_COD_STATUS == 'True';
    // ... código legacy
  }
}
```

---

## 🎯 Configuración del Perfil

El archivo de configuración está en:
```
configs/stage_1_discovery/examples/php_hexagonal.yaml
```

**Parámetros clave:**

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `profile` | `php_hexagonal` | Perfil de procesamiento |
| `adapter` | `php_adapter` | Parser para código PHP legacy |
| `strategy` | `manifest` | Detecta módulos via `composer.json` |
| `on_parse_error` | `abort` | Manejo de errores: abort \| skip \| fallback |

---

## 📊 Output Generated

**Estructura de salidas:**

```
data/outputs/php-legacy/
├── oscommerce/
│   ├── FUNCTIONAL_UNIT_*.txt      # Módulos con lógica + tests
│   ├── LOGIC_ONLY_*.txt           # Módulos sin tests
│   ├── MODULE_BLUEPRINT_*.txt     # Anclas + README
│   └── GOVERNANCE_RULES_*.txt     # CLAUDE.md, AGENTS.md
```

**Tipos de bundles:**

- **FUNCTIONAL_UNIT**: Módulos completos con lógica y tests
- **LOGIC_ONLY**: Módulos sin tests asociados
- **MODULE_BLUEPRINT**: Archivos ancla + documentación
- **GOVERNANCE_RULES**: Archivos de configuración de código

---

## 🐛 Troubleshooting

### **Error: "Parse error on line X"**

**Solución**: Cambiar en config YAML:
```yaml
on_parse_error: skip  # en lugar de abort
```

### **Error: "Repository not found"**

**Solución**: Asegurar que el repositorio está en `data/raw/`:
```bash
ls data/raw/
```

---

## 📚 Documentación Completa

- **Tutorial completo**: `TUTORIAL_STAGE1_PHP_LEGACY.md`
- **Metodología**: `docs/METHODOLOGY.md`
- **Case Study PHP**: `docs/case_studies/PHP_MODERNIZATION_FORGE.md`
- **Configuración YAML**: `configs/stage_1_discovery/examples/php_hexagonal.yaml`

---

## 🚀 Próximos Pasos

Una vez procesado el Stage 1:

1. **Stage 2 (Factory)**: Generar prompts con el código extraído
2. **Stage 3 (Curation)**: Filtrar y curar el corpus
3. **Stage 4 (Training)**: Entrenar el modelo
4. **Stage 5 (Evaluation)**: Evaluar calidad
5. **Stage 6 (Calibration)**: Calibrar respuestas

---

## 💡 Tips

- ✅ Usa `--verbose` para debugging detallado
- ✅ Revisa `data/audit/` para archivos con errores
- ✅ Ajusta `size_limits` según tu hardware
- ✅ Monitorea `logs/` para progreso en tiempo real

---

**¿Listo para empezar?**

```bash
# Comienza el Stage 1
source .venv/bin/activate
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose
```

🚀 **¡Buen viaje en la modernización de código legacy!**
