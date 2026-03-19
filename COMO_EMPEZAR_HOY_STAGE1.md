# 🎯 INSTRUCCIONES PASO A PASO - Empezar Stage 1 HOY

> **Guía práctica para comenzar a usar el Stage 1 Discovery con el caso de uso: PHP Legacy → Hexagonal Architecture**

---

## 📋 Resumen del Caso de Uso

**Objetivo**: Procesar código PHP legacy (osCommerce, WordPress, etc.) y extraer entidades lógicas estructuradas para entrenar un modelo que aprenda a modernizarlo a Hexagonal Architecture.

**Repositorio de ejemplo**: osCommerce (plataforma e-commerce legacy desde 1999)

---

## 🚀 PASO A PASO COMPLETO (5 PASOS)

### **PASO 1: Preparar el Entorno (1 minuto)**

```bash
# Navega al workspace
cd /mnt/bunker_data/ai/data_factory

# Activa el entorno virtual
source .venv/bin/activate

# Verifica que está activo
which python
# Debe mostrar: /mnt/bunker_data/ai/data_factory/.venv/bin/python
```

**Verificación**: Si ves el prompt de Python o no hay errores, estás listo.

---

### **PASO 2: Preparar Repositorios (2 minutos)**

**El sistema tiene un script de ayuda que automatiza todo el proceso.**

#### **Opción A: Usar el script de ayuda (Recomendado)**

```bash
# Navega al workspace
cd /mnt/bunker_data/ai/data_factory

# Clona un repositorio PHP legacy (ejemplo: osCommerce)
./scripts/stage1-quickstart.sh clone https://github.com/oscommerce/oscommerce.git

# Verifica que se clonó
ls data/raw/
# Debe mostrar: oscommerce/
```

#### **Opción B: Clonar manualmente**

```bash
# Navega al directorio de datos raw
cd /mnt/bunker_data/ai/data_factory/data/raw

# Clona el repositorio de osCommerce
git clone https://github.com/oscommerce/oscommerce.git

# Vuelve al workspace
cd /mnt/bunker_data/ai/data_factory
```

**Verificación**:
```bash
# Debe mostrar los repositorios clonados
ls /mnt/bunker_data/ai/data_factory/data/raw/
# Debe mostrar: oscommerce/ o el repositorio que clonaste
```

---

### **PASO 3: Ejecutar el Stage 1 Processor (5-10 minutos)**

**Opción A: Usar el script de ayuda (Recomendado)**

```bash
# Ejecuta todo el pipeline automáticamente
./scripts/stage1-quickstart.sh run
```

**Opción B: Ejecutar el processor directamente**

```bash
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose
```

**Explicación del comando:**
- `python -m src.discovery.processor_cli`: Ejecuta el processor CLI
- `--config .../php_hexagonal.yaml`: Usa la configuración para PHP legacy
- `--verbose`: Muestra logging detallado (útil para ver qué está pasando)

**Qué hace este comando:**
1. Lee la configuración YAML
2. Escanea los repositorios en `data/raw/`
3. Detecta módulos PHP (via `composer.json`)
4. Extrae entidades lógicas (funciones, clases, módulos)
5. Reemplaza cuerpos de funciones con docstrings de alta seniority
6. Emite bundles tipados en `data/outputs/`

**Tiempo estimado**: 
- osCommerce (~850 archivos): 5-10 minutos
- Repositorio pequeño (~50 archivos): 1-2 minutos

---

### **PASO 4: Verificar Resultados (1 minuto)**

**Usando el script de ayuda:**

```bash
# Ver resultados y métricas
./scripts/stage1-quickstart.sh show
```

**O manualmente:**

**Listar bundles generados:**

```bash
# Ver estructura de output
ls -lh data/outputs/php-legacy/

# Deberías ver algo como:
# FUNCTIONAL_UNIT_payment_cod.txt
# FUNCTIONAL_UNIT_shipping_usps.txt
# LOGIC_ONLY_general.php
# MODULE_BLUEPRINT_composer.json
# GOVERNANCE_RULES_php-cs-fixer.dist.php
```

**Ver contenido de un bundle:**

```bash
# Ver los primeros 100 líneas de un bundle
head -100 data/outputs/php-legacy/oscommerce/FUNCTIONAL_UNIT_payment_cod.txt
```

**Ver métricas:**

```bash
# Ver archivos con errores de parsing
ls -lh data/audit/needs_manual_review.json

# Ver logs detallados
tail -50 logs/processor_*.log
```

---

### **PASO 5: Analizar el Output (10 minutos)**

**Ejemplo de bundle tipado:**

```
# FILE: includes/modules/payment/cod.php
# TYPE: FUNCTIONAL_UNIT
# VIRTUAL_FILENAME: oscommerce/catalog/includes/modules/payment/cod.php
# PATTERNS: global $order, MODULE_PAYMENT_COD_STATUS, tep_redirect()
# CONTEXT: Cash on Delivery payment module — procedural, no DI, hardcoded constants

<?php
class cod {
  function __construct() {
    global $order;
    $this->enabled = MODULE_PAYMENT_COD_STATUS == 'True';
    // ... 300 líneas de caos procedural
  }
}

# END FILE
```

**Patrones detectados automáticamente:**

| Patrón | Significado |
|--------|-------------|
| `global $order` | Variable global (anti-patrón) |
| `MODULE_PAYMENT_COD_STATUS` | Constante hardcodeada |
| `tep_redirect()` | Función legacy de redirección |

**¿Qué significa esto?**

El Stage 1 ha:
1. ✅ Extraído el módulo de pago COD
2. ✅ Detectado 3 patrones legacy
3. ✅ Etiquetado el contexto (procedural, sin DI)
4. ✅ Preparado el bundle para Stage 2 (Factory)

---

## 📊 Métricas Esperadas

**Para osCommerce (~850 archivos):**

| Métrica | Valor Esperado |
|---------|----------------|
| Archivos procesados | ~800-850 |
| Bundles generados | ~50-100 |
| Patrones legacy detectados | 15-20 tipos |
| Tokens extraídos | ~2-5M tokens |
| Tiempo de procesamiento | 5-10 minutos |

**Para repositorio pequeño (~50 archivos):**

| Métrica | Valor Esperado |
|---------|----------------|
| Archivos procesados | ~40-50 |
| Bundles generados | ~10-20 |
| Patrones legacy detectados | 5-10 tipos |
| Tokens extraídos | ~200K-500K tokens |
| Tiempo de procesamiento | 1-2 minutos |

---

## 🐛 Troubleshooting Rápido

### **Problema: "ModuleNotFoundError: No module named 'src'"**

**Solución**:
```bash
# Asegúrate de estar en el workspace correcto
cd /mnt/bunker_data/ai/data_factory

# Activa el entorno virtual
source .venv/bin/activate

# Intenta de nuevo
python -m src.discovery.processor_cli ...
```

### **Problema: "Config not found"**

**Solución**:
```bash
# Verifica que el archivo existe
ls -lh configs/stage_1_discovery/examples/php_hexagonal.yaml

# Si no existe, verifica la ruta correcta
find configs -name "*.yaml" | grep php
```

### **Problema: "Repository not found"**

**Solución**:
```bash
# Verifica que el repositorio está en data/raw/
ls data/raw/

# Si no está, clónalo manualmente
cd data/raw
git clone https://github.com/oscommerce/oscommerce.git
```

### **Problema: "Parse error on line X"**

**Solución**:
```bash
# Edita la configuración para skip en lugar de abort
vim configs/stage_1_discovery/examples/php_hexagonal.yaml

# Cambia esta línea:
# on_parse_error: abort
# Por esta:
on_parse_error: skip

# Intenta de nuevo
python -m src.discovery.processor_cli ...
```

---

## 🎯 Próximos Pasos

Una vez que hayas completado el Stage 1 exitosamente:

### **Stage 2: Factory (Generación de Prompts)**

```bash
# Este paso genera prompts con el código extraído
# (se documentará en la guía de Stage 2)
```

### **Stage 3: Curation (Filtrado y Curación)**

```bash
# Filtra el corpus para eliminar duplicados y ruido
# (se documentará en la guía de Stage 3)
```

### **Stage 4: Training (Entrenamiento del Modelo)**

```bash
# Entrena el modelo con LLaMA-Factory o Axolotl
# (se documentará en la guía de Stage 4)
```

---

## 📚 Recursos Adicionales

### **Documentación Completa**

1. **Tutorial detallado**: `TUTORIAL_STAGE1_PHP_LEGACY.md`
   - Explicación profunda de cada componente
   - Configuraciones avanzadas
   - Casos de uso específicos

2. **Guía rápida**: `QUICKSTART_STAGE1.md`
   - Instrucciones concisas
   - Troubleshooting común
   - Tips para producción

3. **Resumen ejecutivo**: `RESUMEN_STAGE1.md`
   - Estado de alineación
   - Casos de uso
   - Métricas esperadas

4. **Script de ayuda**: `scripts/stage1-quickstart.sh`
   - Automatización del proceso
   - Comandos rápidos

### **Documentación Técnica**

- **Metodología**: `docs/METHODOLOGY.md`
- **Case Study PHP**: `docs/case_studies/PHP_MODERNIZATION_FORGE.md`
- **Configuración YAML**: `configs/stage_1_discovery/examples/php_hexagonal.yaml`
- **Código fuente**: `src/discovery/`

---

## 💡 Tips para Producción

1. **Usa `--verbose`**: Te permite ver qué está pasando en tiempo real
2. **Revisa `data/audit/`**: Ver qué archivos necesitan atención manual
3. **Ajusta `size_limits`**: Más RAM = archivos más grandes
4. **Monitorea `logs/`**: Progreso en tiempo real
5. **Guarda métricas**: En `progress.txt` para tracking de iteraciones

---

## 🎉 ¡Listo para Empezar!

**Comando final para empezar HOY:**

```bash
# 1. Navega al workspace
cd /mnt/bunker_data/ai/data_factory

# 2. Activa el entorno
source .venv/bin/activate

# 3. Ingresa los repositorios automáticamente
./scripts/ingest-repos.sh

# 4. Ejecuta el Stage 1
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose

# 5. Verifica los resultados
ls -lh data/outputs/php-legacy/
```

**Tiempo total estimado**: 15-20 minutos

---

## 📞 ¿Necesitas Ayuda?

Si encuentras algún problema:

1. **Revisa los logs**: `tail -50 logs/processor_*.log`
2. **Verifica la configuración**: `configs/stage_1_discovery/examples/php_hexagonal.yaml`
3. **Consulta el troubleshooting**: En `QUICKSTART_STAGE1.md`
4. **Revisa la documentación completa**: `TUTORIAL_STAGE1_PHP_LEGACY.md`

---

**🚀 ¡Buen viaje en la modernización de código legacy!**

**Fecha de creación**: 19 de marzo de 2026  
**Versión**: 1.0  
**Estado**: ✅ ALINEADO CON EL CÓDIGO
