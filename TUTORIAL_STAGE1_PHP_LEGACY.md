# Tutorial: Stage 1 Discovery - PHP Legacy a Hexagonal

> **Guía práctica para procesar código PHP legacy (osCommerce, WordPress, etc.) y extraer entidades lógicas para entrenamiento de modelos**

---

## 📋 Resumen del Stage 1 Discovery

El **Stage 1 (Discovery)** es la primera fase del pipeline AEGF que:

1. **Ingesta** repositorios de código PHP legacy
2. **Procesa** y fragmenta el código fuente
3. **Extrae** "Entidades Lógicas" estructuradas (funciones, clases, módulos)
4. **Emite** bundles tipados que alimentan el Stage 2 (Factory)

**Objetivo**: Crear un corpus de alto-fidelidad que fuerce al modelo a deducir lógica desde docstrings y firmas, no copiar código literal.

---

## 🏗️ Arquitectura del Stage 1

```
┌─────────────────────────────────────────────────────────┐
│           STAGE 1.0: INGESTA (ingestor.py)              │
├─────────────────────────────────────────────────────────┤
│ • Lee configuración YAML                                │
│ • Clona repositorios Git (GitHub API o lista estática) │
│ • Maneja rate-limit con backoff adaptativo             │
│ • Crea: data/raw/{category}/{owner}/{repo}/            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│        STAGE 1.5: PROCESAMIENTO (processor_cli.py)      │
├─────────────────────────────────────────────────────────┤
│ 1. discover_modules()  → detecta anclas (composer.json)│
│ 2. classify_role()     → roles semánticos de archivos  │
│ 3. parse_file()        → extrae AST/con contenido      │
│ 4. emit_bundle()       → emite bundles .txt tipados    │
│ • TIPO 1: FUNCTIONAL_UNIT (logic + test)               │
│ • TIPO 3: LOGIC_ONLY (sin tests)                       │
│ • TIPO 4: MODULE_BLUEPRINT (anclas + README)           │
│ • TIPO 5: GOVERNANCE_RULES (CLAUDE.md, AGENTS.md)      │
│ • Crea: data/outputs/{category}/{module}/              │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Paso a Paso para Empezar

### **Paso 0: Preparación del Entorno**

```bash
# Navega al workspace
cd /mnt/bunker_data/ai/data_factory

# Activa el entorno virtual
source .venv/bin/activate

# Instala dependencias si es necesario
pip install -r requirements.txt
```

---

### **Paso 1: Configurar el Perfil PHP Hexagonal**

El archivo de configuración está en:
```
configs/stage_1_discovery/examples/php_hexagonal.yaml
```

**Contenido clave del YAML:**

```yaml
# Perfil de procesamiento
profile: php_hexagonal
display_name: "PHP Hexagonal Architecture Expert"

# Adaptador de parser para PHP legacy
extractor:
  adapter: php_adapter
  on_parse_error: abort  # abort | skip | mark_and_continue | fallback
  extensions:
    - .php
    - .md
  ignore_patterns:
    - .git
    - vendor
    - node_modules
    - tests
    - var
    - cache

# Estrategia de descubrimiento de módulos
module_discovery:
  strategy: manifest  # Detecta módulos via composer.json
  anchor_filenames:
    - composer.json
    - phpunit.xml
    - di.yaml

# Límites de tamaño (bytes)
size_limits:
  backend: 200000
  frontend: 100000

# Patrones de arquitectura hexagonal
domain_patterns:
  - Entity
  - ValueObject
  - Aggregate
  - DomainEvent
  - RepositoryInterface
  - Service

# Archivos de gobernanza a capturar
governance_filenames:
  - CLAUDE.md
  - AGENTS.md
  - .cursorrules
  - php-cs-fixer.dist.php
  - phpcs.xml
```

---

### **Paso 2: Preparar un Repositorio de Ejemplo**

**Opción A: Usar un repositorio público existente**

```bash
# Ejemplo: osCommerce público
cd /mnt/bunker_data/ai/data_factory/data/raw

# Clonar manualmente o dejar que lo haga el ingestor
git clone https://github.com/oscommerce/oscommerce.git
cd oscommerce
```

**Opción B: Usar tu propio repositorio local**

```bash
# Copiar repositorio local al directorio raw
cp -r /ruta/a/tu/repo/php-legacy /mnt/bunker_data/ai/data_factory/data/raw/php-legacy/
```

---

### **Paso 3: Ejecutar el Ingestor (Stage 1.0)**

**Ejemplo con repositorio estático:**

```bash
# Crear un archivo de configuración de ingestión
cat > /tmp/ingest_config.yaml << 'EOF'
category: php-legacy
mode: static
source_root: /mnt/bunker_data/ai/data_factory/data/raw/php-legacy
output_root: /mnt/bunker_data/ai/data_factory/data/raw
profile: php_hexagonal
EOF

# Ejecutar ingestor (si está implementado)
python -m src.discovery.ingestor --config /tmp/ingest_config.yaml
```

**Opción manual (recomendado para empezar):**
```bash
# Asegurar que el repositorio está en data/raw/
ls /mnt/bunker_data/ai/data_factory/data/raw/

# Debe mostrar: oscommerce/ o tu-repo/
```

---

### **Paso 4: Ejecutar el Procesador (Stage 1.5)**

**Comando principal:**

```bash
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose
```

**Parámetros disponibles:**

| Parámetro | Descripción |
|-----------|-------------|
| `--config, -c` | Ruta al archivo YAML de configuración (OBLIGATORIO) |
| `--verbose, -v` | Modo verbose (logging detallado) |

**Ejemplo con repositorio específico:**

```bash
# El procesador detecta automáticamente repos en data/raw/
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml
```

---

### **Paso 5: Verificar Resultados**

**Salidas esperadas:**

```
data/outputs/php-legacy/
├── oscommerce/
│   ├── FUNCTIONAL_UNIT_*.txt      # Módulos con lógica + tests
│   ├── LOGIC_ONLY_*.txt           # Módulos sin tests
│   ├── MODULE_BLUEPRINT_*.txt     # Anclas + README
│   └── GOVERNANCE_RULES_*.txt     # CLAUDE.md, AGENTS.md
```

**Verificar con:**

```bash
# Listar bundles generados
ls -lh data/outputs/php-legacy/oscommerce/

# Ver contenido de un bundle
head -100 data/outputs/php-legacy/oscommerce/FUNCTIONAL_UNIT_payment_cod.txt

# Ver metadatos
tail -50 data/outputs/php-legacy/oscommerce/FUNCTIONAL_UNIT_payment_cod.txt
```

---

### **Paso 6: Analizar el Output**

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
| `global $var` | Variable global (anti-patrón) |
| `mysql_query()` | SQL injection vector |
| `tep_redirect()` | Función legacy de redirección |
| `MODULE_*_STATUS` | Constantes hardcodeadas |

---

## 🔧 Configuraciones Avanzadas

### **Estrategias de Descubrimiento de Módulos**

| Estrategia | Identificador | Uso Recomendado |
|------------|---------------|-----------------|
| `manifest` | Detecta `composer.json` | Paquetes PHP, osCommerce |
| `init` | Detecta `__init__.py` | Paquetes Python |
| `directory` | Estructura `app/`, `src/` | Proyectos con layout estándar |
| `manual_mapping` | Tablas YAML explícitas | Repos con estructura no-estándar |

### **Políticas de Manejo de Errores**

| Valor | Comportamiento |
|-------|----------------|
| `abort` | Aborta y marca para revisión manual (default) |
| `skip` | Salta el archivo y continúa |
| `fallback` | Intenta parsing alternativo |
| `mark_and_continue` | Marca con error pero continúa |

---

## 📊 Métricas y Monitoreo

**Métricas capturadas:**

- Total de archivos procesados
- Archivos con errores de parsing
- Archivos marcados para revisión manual
- Tokens extraídos por tipo
- Patrones legacy detectados

**Ver métricas:**

```bash
# Revisar logs
tail -f logs/processor_*.log

# Ver reporte de errores
cat data/audit/needs_manual_review.json
```

---

## 🐛 Troubleshooting Común

### **Error: "Parse error on line X"**

**Causa**: Código PHP legacy con sintaxis obsoleta.

**Solución**:
```yaml
# Cambiar en config YAML
on_parse_error: skip  # en lugar de abort
```

### **Error: "Repository not found"**

**Causa**: Repositorio no clonado en `data/raw/`.

**Solución**:
```bash
# Verificar directorio
ls data/raw/

# Clonar manualmente si es necesario
git clone <repo-url> data/raw/<repo-name>/
```

### **Error: "Rate limit exceeded"**

**Causa**: Demasiadas peticiones a GitHub API.

**Solución**:
```bash
# Esperar y reintentar
# O usar modo estático con repos locales
```

---

## 🎯 Próximos Pasos

Una vez procesado el Stage 1:

1. **Stage 2 (Factory)**: Generar prompts con el código extraído
2. **Stage 3 (Curation)**: Filtrar y curar el corpus
3. **Stage 4 (Training)**: Entrenar el modelo con LLaMA-Factory / Axolotl
4. **Stage 5 (Evaluation)**: Evaluar calidad de modernización
5. **Stage 6 (Calibration)**: Calibrar respuestas del modelo

---

## 📚 Referencias

- **Documentación completa**: `docs/METHODOLOGY.md`
- **Case Study PHP Modernization**: `docs/case_studies/PHP_MODERNIZATION_FORGE.md`
- **Configuración de ejemplo**: `configs/stage_1_discovery/examples/php_hexagonal.yaml`
- **Código fuente**: `src/discovery/`

---

## 💡 Tips para Producción

1. **Usa `--verbose`** para debugging detallado
2. **Revisa `data/audit/`** para ver qué archivos necesitan atención manual
3. **Ajusta `size_limits`** según tu hardware (más RAM = archivos más grandes)
4. **Monitorea `logs/`** para ver el progreso en tiempo real
5. **Guarda métricas** en `progress.txt` para tracking de iteraciones

---

**¿Listo para empezar?**

```bash
# Comienza el Stage 1
source .venv/bin/activate
python -m src.discovery.processor_cli \
  --config configs/stage_1_discovery/examples/php_hexagonal.yaml \
  --verbose
```

🚀 **Buen viaje en la modernización de código legacy!**
