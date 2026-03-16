# Feature Specification: Inference Calibration Suite (Stage 6)

**Feature Branch**: `005-inference-calibration`  
**Created**: 2026-03-15  
**Status**: Draft  
**Input**: User description: "Inference Calibration Suite (Stage 6) - Automated sampling parameter optimization using LLM-as-Judge with intelligent parameter_target/evaluation_focus analysis"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Sampling Parameter Discovery (Priority: P1)

Como ingeniero de ML, quiero que el sistema automatice la búsqueda de los parámetros de muestreo óptimos para mi modelo SFT, de modo que maximice la calidad de las respuestas del modelo sin necesidad de ajustes manuales.

**Why this priority**: Este es el flujo principal de la característica. Sin esta capacidad, los usuarios tienen que ajustar manualmente los parámetros de inferencia, lo cual es tedioso e ineficiente.

**Independent Test**: El sistema puede ejecutarse con un conjunto de 5 prompts de prueba y producir un reporte de calibración con los mejores parámetros encontrados. El proceso es completamente automático y no requiere intervención humana.

**Acceptance Scenarios**:

1. **Given** un conjunto de 5-10 prompts de investigación complejos, **When** se ejecuta el script de calibración, **Then** el sistema itera a través de todas las combinaciones de parámetros y genera un reporte JSON con los resultados.
2. **Given** una ejecución de calibración completada, **When** el usuario revisa el calibration_report.json, **Then** encuentra los parámetros óptimos (temperatura, top_k, min_p, repetition_penalty) que maximizan el Composite Score.
3. **Given** el proceso de calibración terminado, **When** el usuario aplica el vllm_config.yaml generado, **Then** el modelo produce respuestas con mayor Reasoning Depth y Functional Accuracy según el Judge.

---

### User Story 2 - Judge Integration for Quality Scoring (Priority: P1)

Como evaluador de modelos, quiero que cada combinación de parámetros sea evaluada por el Professor Judge existente, de modo que pueda cuantificar objetivamente la calidad de las respuestas generadas.

**Why this priority**: Sin la integración del Judge, no hay forma objetiva de comparar diferentes configuraciones de parámetros. El Judge proporciona métricas reproducibles.

**Independent Test**: Se puede ejecutar una única iteración de calibración con un perfil de muestreo conocido y verificar que el Judge devuelve puntuaciones en el formato esperado (ha_modernity, reasoning_depth, functionality, completeness, style).

**Acceptance Scenarios**:

1. **Given** una respuesta del modelo con parámetros específicos, **When** se envía al Professor Judge, **Then** el Judge devuelve puntuaciones normalizadas en todas las dimensiones definidas.
2. **Given** puntuaciones del Judge para múltiples configuraciones, **When** se calcula el Composite Score, **Then** el sistema aplica correctamente los pesos definidos (ha_modernity: 0.30, reasoning_depth: 0.25, functionality: 0.25, completeness: 0.12, style: 0.08).

---

### User Story 3 - Response Length Penalty Enforcement (Priority: P2)

Como asegurador de calidad, quiero que el sistema penalice las respuestas cortas (menos de 200 palabras) en tareas de investigación, de modo que se desaliente la generación de respuestas "lazy" o superficiales.

**Why this priority**: Las respuestas cortas no pueden demostrar Reasoning Depth adecuado, que es crítico para las tareas de investigación complejas. Esta penalización asegura que el modelo proporcione análisis sustanciales.

**Independent Test**: Se puede ejecutar con un prompt de investigación y verificar que las respuestas menores a 200 palabras reciben una penalización measurable en el Composite Score.

**Acceptance Scenarios**:

1. **Given** una respuesta con menos de 200 palabras, **When** se calcula el adjusted_score, **Then** se aplica una penalización proporcional a la escasez de contenido.
2. **Given** una respuesta con 200 o más palabras, **When** se calcula el adjusted_score, **Then** no se aplica ninguna penalización por longitud.

---

### User Story 4 - Output Artifacts Generation (Priority: P2)

Como usuario del sistema, quiero recibir archivos de salida estructurados (calibration_report.json y vllm_config.yaml), de modo que pueda revisar los resultados y aplicar la configuración óptima de forma inmediata.

**Why this priority**: Los archivos de salida permiten auditoría, reproducibilidad y aplicación directa de los resultados.

**Independent Test**: Después de ejecutar la calibración, existen dos archivos en el directorio de salida: calibration_report.json con todos los resultados detallados y vllm_config.yaml con la configuración óptima lista para usar.

**Acceptance Scenarios**:

1. **Given** una ejecución de calibración exitosa, **When** se genera el calibration_report.json, **Then** contiene: timestamp, todos los perfiles probados con sus puntuaciones, el perfil ganador, y estadísticas agregadas.
2. **Given** una ejecución de calibración exitosa, **When** se genera el vllm_config.yaml, **Then** contiene los parámetros óptimos en formato compatible con vLLM.

---

### Edge Cases

- ¿Qué sucede cuando el Judge falla o no puede puntuar una respuesta? El sistema debe registrar el error y continuar con las siguientes configuraciones.
- ¿Cómo maneja el sistema prompts que producen respuestas vacías o extremadamente largas? Se deben definir límites máximos y mínimos de longitud.
- ¿Qué pasa si todas las configuraciones producen puntuaciones muy bajas? El sistema debe reportar esta situación y sugerir revisar los prompts de entrada.
- ¿Cómo se maneja la conexión inestable con el servidor de inferencia? Se debe implementar retry logic similar al resto del sistema.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE aceptar una lista de 5-10 prompts de investigación complejos como entrada.
- **FR-002**: El sistema DEBE crear un SamplingProfile dataclass con los campos: temperature, top_p, top_k, min_p, repetition_penalty, presence_penalty (opcional).
- **FR-003**: El sistema DEBE iterar a través de las siguientes dimensiones de parámetros (grid expandido):
  - temperature: [0.3, 0.5, 0.6, 0.7, 0.9, 1.1]
  - top_p: [0.7, 0.8, 0.9, 0.95, 1.0]
  - top_k: [5, 10, 20, 40, 60, 80]
  - min_p: [0.0, 0.02, 0.05, 0.1, 0.15]
  - repetition_penalty: [1.0, 1.05, 1.1, 1.15, 1.2]
  - presence_penalty: [0.0, 0.5, 1.0, 1.5, 2.0]
- **FR-003b**: El sistema DEBE implementar un filtro de parámetros "noxious" que evalúe cada valor contra el pivot y descarte valores que pierden >80% de las veces.
- **FR-004**: Para cada combinación de parámetros, el sistema DEBE generar respuestas usando el modelo STUDENT con esos parámetros.
- **FR-005**: Para cada respuesta generada, el sistema DEBE enviar la respuesta al Professor Judge existente para su evaluación.
- **FR-006**: El sistema DEBE calcular el Composite Score usando las dimensiones del judge: parameter_effectiveness, task_completion, parameter_alignment, coherence, style.
- **FR-007**: El sistema DEBE penalizar respuestas más cortas de 200 palabras para tareas de investigación, reduciendo el Composite Score proporcionalmente.
- **FR-008**: El sistema DEBE generar un archivo calibration_report.json con estructura definida que incluya todos los perfiles probados, sus puntuaciones, y el perfil ganador.
- **FR-009**: El sistema DEBE generar un archivo vllm_config.yaml con los parámetros óptimos encontrados.
- **FR-010**: El sistema DEBE implementar búsqueda de grid completa (Cartesian product) con soporte para reducir el espacio mediante el filtro noxious.
- **FR-011**: El sistema DEBE parsear los campos `parameter_target` y `evaluation_focus` de cada prompt de calibración para identificar qué parámetros afectan qué aspectos del comportamiento del modelo.
- **FR-012**: El sistema DEBE crear un diccionario de mapeo entre evaluation_focus y estrategias de ajuste de parámetros (ej: "Curiosidad y Exploración" → incrementar top_k y reducir presence_penalty).
- **FR-013**: El sistema DEBE implementar un algoritmo de refinamiento de parámetros que estreche el espacio de búsqueda basándose en el análisis de evaluation_focus.
- **FR-014**: El sistema DEBE generar un archivo calibration_analysis.json que contenga recomendaciones de ajuste de parámetros derivadas del análisis de evaluation_focus.
- **FR-015**: El sistema DEBE mostrar progreso en cada iteración incluyendo: parámetros actuales, score, comparación con iteración anterior (↑/↓), y dimensions del judge.
- **FR-016**: El sistema DEBE soportar resume de ejecuciones interrumpidas mediante checkpoints.

### Key Entities *(include if feature involves data)*

- **SamplingProfile**: Representa una configuración de parámetros de muestreo. Atributos: temperature (float), top_p (float), top_k (int), min_p (float), repetition_penalty (float), presence_penalty (float, opcional).
- **CalibrationResult**: Representa el resultado de una iteración de calibración. Atributos: profile (SamplingProfile), exam_id (str), judge_scores (dict), composite_score (float), adjusted_score (float), response_length (int), timestamp (str).
- **CalibrationReport**: Agrega todos los resultados de la calibración. Atributos: timestamp, total_iterations, best_profile, all_results (list), statistics (dict).
- **CalibrationPrompt**: Representa un prompt de calibración con metadatos. Atributos: id (str), question (str), type (str), parameter_target (list[str]), evaluation_focus (str).
- **CalibrationCheckpoint**: Estado para resume de ejecuciones interrumpidas. Atributos: prompt_idx, profile_idx, timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El sistema completa todas las iteraciones de calibración (6 prompts × 18,750 combinaciones = 112,500 ejecuciones sin filtro, o ~500-2000 con filtro noxious) en un tiempo razonable sin errores fatales.
- **SC-002**: El calibration_report.json contiene todas las combinaciones de parámetros probadas con sus puntuaciones individuales.
- **SC-003**: El vllm_config.yaml generado contiene parámetros válidos que pueden ser usados directamente con vLLM.
- **SC-004**: Las respuestas penalizadas por longitud (menos de 200 palabras) muestran una reducción measurable en su Composite Score ajustado.
- **SC-005**: El perfil ganador maximiza las dimensiones del Judge según las puntuaciones, sin causar alucinaciones detectables.
- **SC-006**: El filtro noxious reduce el grid de 18,750 a ~500-2000 combinaciones manteniendo los valores óptimos.
- **SC-007**: La salida por terminal muestra progreso claro: iteración actual, comparación con anterior (↑/↓), y dimensiones del judge.

---

## Assumptions

1. Se asume que el modelo SFT ya está entrenado y desplegado en un servidor vLLM accesible.
2. Se asume que el Professor Judge está configurado y funciona correctamente (como en Stage 5).
3. Se asume que los prompts de entrada son suficientemente complejos para demostrar diferencias entre configuraciones de parámetros.
4. Se asume que el usuario tiene acceso a los recursos de computación necesarios para ejecutar múltiples inferencias.

## Clarifications

### Session 2026-03-15

- Q: ¿Cuál es el tiempo máximo aceptable para completar una calibración completa (135 ejecuciones)? → A: Sin límite de tiempo - solo hasta completar
- Q: ¿Qué funcionalidades deben ser explícitamente excluidas de esta especificación? → A: Optimización de hyperparameters de entrenamiento (solo inferencia)
- Q: ¿Cómo debe manejarse el estado de la calibración durante la ejecución? → A: Con resume: guardar progreso intermedio en archivo JSON
- Q: ¿Qué nivel de observabilidad debe tener el sistema? → A: Solo logs básicos de progreso (iteración actual, puntuación)
- Q: ¿Qué documentación debe actualizarse o crearse como parte de esta feature? → A: Actualizar docs/METHODOLOGY.md con casos de uso Stage 6, actualizar README.md con nueva sección, y cualquier otro docs relevante
- Q: ¿Cuál es el formato exacto de los prompts de entrada? → A: Seguir la misma arquitectura y estructura de prompts que en las otras inferencias de los otros stages (existente en el proyecto)
- Q: ¿Hay algún requisito de rendimiento específico para la calibración? → A: Sin límite específico - ejecutar hasta completar (el servidor vLLM es el limitante principal)

### Session 2026-03-15 (Actualización)

- Q: ¿Cómo reducir las iteraciones para grids grandes? → A: Implementar filtro "noxious" que evalúa cada valor contra el pivot y descarta valores que pierden >80% de las veces
- Q: ¿Qué valores de pivot usar? → A: temperature=0.6, top_p=0.9, top_k=20, min_p=0.0, repetition_penalty=1.0, presence_penalty=1.0
- Q: ¿Cómo mejorar la observabilidad en terminal? → A: Mostrar en cada iteración: parámetros completos, score, comparación con anterior (↑/↓), y dimensiones del judge
- Q: ¿Qué hacer si el grid es demasiado grande? → A: Usar flag --use-noxious-filter para reducir de ~18,750 a ~500-2000 combinaciones
