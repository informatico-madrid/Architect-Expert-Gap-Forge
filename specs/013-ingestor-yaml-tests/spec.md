# Feature Specification: Tests de Carga YAML para Ingestor

**Feature Branch**: `013-ingestor-yaml-tests`  
**Created**: 2026-03-19  
**Status**: Draft  
**Input**: User description: "Agregar tests de carga YAML desde disco para el ingestor y validar el flujo CLI → YAML → Pydantic"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tests de Carga YAML desde Disco (Priority: P1)

Como desarrollador, quiero que el sistema valide los archivos de configuración YAML del ingestor cargándolos desde disco para detectar errores de sintaxis antes de producción.

**Why this priority**: El bug actual (un `---` después del header de copyright) pasó desapercibido porque ningún test carga archivos YAML reales desde disco. Este es el gap crítico que permite configs rotas en producción.

**Independent Test**: Se puede测试r creando un archivo YAML con sintaxis inválida y verificando que el test falla.

**Acceptance Scenarios**:

1. **Given** un archivo YAML válido en disco, **When** se ejecuta el test de carga, **Then** el objeto Pydantic se crea correctamente con todos los campos requeridos.
2. **Given** un archivo YAML con `---` después del copyright, **When** se ejecuta el test de carga, **Then** el test detecta el error y falla con mensaje descriptivo.
3. **Given** un archivo YAML con sintaxis inválida, **When** se ejecuta el test de carga, **Then** el test detecta el error y falla.

---

### User Story 2 - Tests de Validación de Configuración YAML Inválida (Priority: P1)

Como desarrollador, quiero que el sistema valide que los archivos de configuración YAML tengan todos los campos requeridos por el modelo Pydantic para detectar campos faltantes en tiempo de test.

**Why this priority**: Si falta el campo `category` requerido por `DiscoveryConfig`, el error solo aparecía en runtime. Los tests deben validar esto.

**Independent Test**: Se puede测试r eliminando el campo `category` de un archivo YAML de test y verificando que el test falla.

**Acceptance Scenarios**:

1. **Given** un archivo YAML sin el campo `category` requerido, **When** se carga y valida, **Then** el test falla indicando campo faltante.
2. **Given** un archivo YAML con valor inválido para campo enumerado, **When** se carga y valida, **Then** el test falla indicando valor inválido.

---

### User Story 3 - Tests de Flujo CLI Completo (Priority: P2)

Como desarrollador, quiero que el sistema tenga tests de integración que ejecuten el flujo completo desde CLI hasta la carga del archivo YAML y su conversión a Pydantic.

**Why this priority**: El flujo real del CLI (4 etapas) no está testeado. Los tests actuales solo validan Pydantic con datos hardcodeados, no el pipeline real.

**Independent Test**: Se puede测试r ejecutando el CLI con un archivo de configuración y verificando la salida.

**Acceptance Scenarios**:

1. **Given** una invocación CLI válida con path a config, **When** se ejecuta, **Then** el archivo YAML se carga y convierte a objeto Pydantic correctamente.
2. **Given** una invocación CLI con archivo YAML inexistente, **When** se ejecuta, **Then** el test verifica que se maneja el error apropiadamente.

---

### User Story 4 - Tests de Detección de Bugs Específicos (Priority: P1)

Como desarrollador, quiero que exista un test específico que detecte el bug del `---` en archivos YAML para evitar regresiones.

**Why this priority**: El bug específico de `---` después del copyright debe ser detectado por un test dedicado para evitar que reaparezca.

**Independent Test**: Se puede测试r creando un archivo YAML con el patrón específico y verificando detección.

**Acceptance Scenarios**:

1. **Given** un archivo YAML con `---` después del header de copyright, **When** se carga con yaml.safe_load(), **Then** el test detecta que el contenido antes del `---` fue ignorado.

---

### Edge Cases

- ¿Qué sucede cuando el archivo YAML está vacío?
- ¿Qué sucede cuando el archivo tiene encoding diferente (UTF-8 con BOM)?
- ¿Qué sucede con archivos YAML que tienen múltiples documentos (multi-document YAML con `---`)?
- ¿Qué sucede cuando el archivo tiene permisos incorrectos?
- ¿Qué sucede con paths relativos vs absolutos en la configuración?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE tener tests que carguen archivos YAML desde disco usando `yaml.safe_load()` para validar el flujo real de parsing.
- **FR-002**: El sistema DEBE tener tests que validen que los archivos de configuración YAML tienen todos los campos requeridos por el modelo Pydantic `DiscoveryConfig`.
- **FR-003**: El sistema DEBE tener tests de integración que validen el flujo completo CLI → YAML → Pydantic sin crear objetos Pydantic directamente.
- **FR-004**: El sistema DEBE tener un test específico que detecte el bug del `---` después del header de copyright para evitar regresiones.
- **FR-005**: El sistema DEBE tener tests que validen errores de sintaxis YAML (indentación, tipos inválidos, etc.).
- **FR-006**: El sistema DEBE usar mocking de `open()` y `yaml.safe_load()` para probar casos de error sin necesidad de archivos físicos.
- **FR-007**: Los archivos YAML de configuración en `configs/stage_1_discovery/` deben ser considerados como "código testeado", no solo documentación.

### Key Entities

- **Archivo de Configuración YAML**: Archivos como `discovery.yaml`, `homeassistant.yaml` que contienen la configuración para el ingestor.
- **Modelo Pydantic DiscoveryConfig**: Modelo que valida la estructura de configuración con campos requeridos como `category`.
- **Función de Carga YAML**: Función que lee un archivo YAML del disco y lo convierte a diccionario Python.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los tests de carga YAML deben覆盖率 al menos el 90% de los paths de código en la función de carga de configuración del ingestor.
- **SC-002**: Cualquier archivo YAML de configuración en el repositorio debe poder ser cargado y validado por los tests sin errores.
- **SC-003**: El tiempo de ejecución de los nuevos tests no debe exceder 30 segundos por suite.
- **SC-004**: El bug específico del `---` debe ser detectado por un test automatizado antes de merging a main.
- **SC-005**: Todos los nuevos tests deben pasar en CI/CD antes de permitir merge de cualquier cambio relacionado al ingestor.
