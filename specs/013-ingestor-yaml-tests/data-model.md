# Data Model: Tests de Carga YAML para Ingestor

## Entidades

### 1. YAMLConfigFile (Archivo de Configuración YAML)

**Descripción**: Representa un archivo de configuración YAML que se carga en el sistema.

**Atributos**:
- `path`: Path - Ruta al archivo YAML en disco
- `content`: str - Contenido completo del archivo
- `is_valid`: bool - Indica si el archivo tiene sintaxis YAML válida

**Relaciones**:
- Se carga usando `yaml.safe_load()` 
- Se convierte a `DiscoveryConfig` después de la carga

---

### 2. DiscoveryConfig (Modelo Pydantic)

**Descripción**: Modelo de validación de configuración existente en el proyecto.

**Atributos** (del código fuente):
- `category`: str (REQUIRED) - Nombre del subdirectorio objetivo
- `mode`: Literal["dynamic", "static"] - Modo de descubrimiento
- `profile`: Optional[str] - Nombre de perfil para filtrado
- `profile_extensions`: Optional[Set[str]] - Extensiones de archivo a filtrar
- `profile_ignored_paths`: Optional[Set[str]] - Paths a ignorar
- `search_query`: Optional[str] - Query para búsqueda dinámica
- `min_stars`: int - Mínimo de estrellas (default: 0)
- `limit`: int - Límite de resultados (default: 50)
- `per_page`: int - Resultados por página (default: 100)
- `static_repos`: List[str] - Lista de repositorios estáticos
- `base_dir`: Path - Directorio base
- `raw_subdir`: str - Subdirectorio raw
- `github_token`: Optional[str] - Token de autenticación

**Validaciones**:
- Si `mode == "static"`, debe tener `static_repos` no vacío
- Si `mode == "dynamic"`, debe tener `search_query` no vacío

---

### 3. YAMLLoadResult (Resultado de Carga YAML)

**Descripción**: Resultado de intentar cargar un archivo YAML.

**Atributos**:
- `success`: bool - Indica si la carga fue exitosa
- `data`: Optional[dict] - Datos cargados (si exitoso)
- `error`: Optional[str] - Mensaje de error (si falla)
- `error_type`: Optional[str] - Tipo de error (yaml.YAMLError, ValidationError, FileNotFoundError, etc.)

---

## Reglas de Validación para Tests

1. **Test de carga exitosa**: Un archivo YAML válido con todos los campos requeridos debe cargar sin errores
2. **Test de campo requerido faltante**: Un archivo sin `category` debe fallar con `ValidationError`
3. **Test de modo inválido**: Un archivo con `mode: dynamic` pero sin `search_query` debe fallar
4. **Test de YAML inválido**: Un archivo con sintaxis YAML incorrecta debe fallar con `YAMLError`
5. **Test de bug específico `---`**: Un archivo con `---` después del copyright debe ser detectado

---

## Estado de Transiciones

```
YAMLFile (en disco)
    |
    v
[YAML Load] --> YAMLLoadResult
    |
    v (success)
dict Python
    |
    v
[DiscoveryConfig(**dict)]
    |
    v (success)
DiscoveryConfig (Pydantic)
```
