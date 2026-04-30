# Feature Specification: Rediseño del Pipeline de Generación de Datos Sintéticos Agénticos

**Feature Branch**: `010-agentic-dataset-redesign`  
**Created**: 2026-03-19  
**Status**: Draft  
**Input**: Rediseño del pipeline de generación de datos sintéticos (Stage 2: Factory + Stage 3: Curation) para resolver la "pereza de herramientas" del modelo Qwen3-30b-A3B fine-tuneado en Home Assistant 2026. Se incorporan: trayectorias multi-turno agénticas (3–10 turnos), hard queries con objetivos abstractos, formato XML de herramientas (qwen3_coder), data mixing con datasets ancla para prevenir olvido catastrófico, y parámetros de entrenamiento actualizados con NEFTune en Axolotl.

---

## Clarifications

### Session 2026-03-19

- Q: ¿Qué modelo actúa como Teacher para generar las trayectorias (self-distillation, modelo local vía vLLM, API externa, o pipeline actual)? → A: API externa, configurable por parámetro.
- Q: ¿Cuál es el volumen objetivo del dataset final (registros totales)? → A: Por defecto ~40 000–50 000 registros totales; configurable mediante parámetro.
- Q: ¿Cuál es la composición interna del dataset especializado y la proporción global con el ancla? → A: 70% ancla general + 30% especializado HA. **Matiz clave**: Stage 2 genera ÚNICAMENTE trayectorias expertas de Home Assistant (multi-turno con backtracking/recuperación de errores). La variedad de patrones restantes (no-call, llamadas simples a una herramienta, diálogo general) la aportan los datasets ancla externos — en especial `Salesforce/xlam-function-calling-60k` que ya incluye estos patrones curados. Esto evita generar y depurar nuestros propios ejemplos de variedad.
- Q: ¿Cómo produce Stage 3 el artefacto final para Axolotl (archivo único vs. múltiples datasets en YAML)? → A: Stage 3 produce un **único archivo JSONL** pre-procesado, mezclado y barajado de forma determinista. Axolotl consume únicamente este artefacto; la mezcla y el shuffle no se delegan al framework. Máxima reproducibilidad y transparencia, sin «caja negra».
- Q: ¿Cómo gestiona Stage 2 el rate limiting y los fallos de la API externa del modelo Teacher? → A: Tres mecanismos combinados y configurables: (1) **sleep configurable** entre llamadas (`teacher_model.request_delay_ms`, por defecto 500 ms); (2) **reintentos con backoff exponencial** ante errores transitorios de API (`teacher_model.max_retries`, `teacher_model.backoff_factor`); (3) **checkpoint de progreso persistido en disco** que registra cada seed ya generada con éxito, permitiendo reanudar una ejecución interrumpida sin repetir trabajo ni incurrir en costos duplicados.

---

## Contexto y Problema

El modelo actual entrenado sobre el dataset `v11_backtracking_align` presenta **comportamiento de "pereza agéntica"**: se rinde ante obstáculos sin explorar vías alternativas, no encadena múltiples herramientas de forma autónoma y carece de capacidad de recuperación ante fallos en cascada. El dataset actual (19 732 registros, composición 50% nominal / 30% contrast / 20% error_recovery + theory) fue generado con trayectorias de 2 pasos que no ejercitan la navegación por dependencias profundas.

Este rediseño afecta dos stages del pipeline:
- **Stage 2 — Factory**: generación de trayectorias agénticas.
- **Stage 3 — Curation**: mezcla de datasets y normalización de formato.
- **Stage 4 — Training (config Axolotl)**: ajuste de hiperparámetros específicos para Home Assistant.

---

## User Scenarios & Testing

### User Story 1 — Trayectorias Multi-Turno con Backtracking (Priority: P1)

Un investigador de ML ejecuta el Stage 2 para el caso de uso `home_assistant` y obtiene registros JSONL cuyas conversaciones simulan trayectorias agénticas de 3 a 10 turnos. Cada trayectoria incluye al menos un error inyectado y una recuperación explícita (backtracking), enseñando al modelo que fallar no implica rendirse.

**Why this priority**: Es el cambio nuclear que resuelve la pereza. Sin trayectorias profundas que incluyan errores y recuperación, los demás cambios son complementarios pero insuficientes.

**Independent Test**: Ejecutar Stage 2 con `--use-case home_assistant --mode trajectories` sobre un subset de 100 seeds y verificar que el 100% de los registros generados contiene ≥3 turnos y al menos 1 bloque de error seguido de un bloque de corrección.

**Acceptance Scenarios**:

1. **Given** una seed "Migrar una integración de sensor con `TEMP_CELSIUS`", **When** el generador produce una trayectoria, **Then** la conversación tiene entre 3 y 10 pares `user/assistant`, con al menos 1 turno donde el modelo observa un error de herramienta y al menos 1 turno subsiguiente donde propone una corrección diferente.
2. **Given** que el generador inyecta un error de tipo `cascada` (el fix del error A revela el error B), **When** el modelo completa la trayectoria, **Then** el registro contiene turnos secuenciales que resuelven A → B → verificación_final sin abandonar la tarea.
3. **Given** una trayectoria completa, **When** se valida su longitud, **Then** ningún registro tiene menos de 3 turnos (el mínimo garantizado por configuración).

---

### User Story 2 — Hard Queries con Objetivos Abstractos (Priority: P1)

Un investigador de ML genera ejemplos donde el prompt del usuario describe únicamente el **objetivo final** (ej. "Haz que este sensor funcione en HA 2026") sin enumerar los pasos a seguir. El modelo debe inferir autónomamente qué herramientas invocar y en qué orden, desarrollando la habilidad de resolver "puentes lógicos implícitos".

**Why this priority**: Junto con las trayectorias, esta capacidad es la que más directamente ataca el comportamiento perezoso, obligando al modelo a razonar de forma autónoma en lugar de seguir instrucciones explícitas.

**Independent Test**: Generar 50 hard queries para `home_assistant` y verificar que ningún prompt del turno inicial menciona el nombre de ninguna herramienta ni enumera pasos concretos. El evaluador comprobará el prompt contra una lista de términos prohibidos (nombres de tools, verbos imperativos como "llama a", "usa la función").

**Acceptance Scenarios**:

1. **Given** el modo `hard_query` activado, **When** el generador construye el prompt del turno 1, **Then** el texto del usuario describe solo el estado objetivo final ("Quiero que mi integración sea compatible con 2026.1") sin mencionar herramientas ni pasos.
2. **Given** un hard query con objetivo abstracto, **When** el asistente genera su respuesta, **Then** el bloque `<think>` contiene razonamiento sobre qué herramientas son necesarias, con justificación explícita de cada selección.
3. **Given** que Stage 3 incorpora registros ancla de `Salesforce/xlam-function-calling-60k`, **When** se audita el dataset final, **Then** los ejemplos de tipo `no-call` / rechazo están presentes y son aportados por el dataset ancla, sin necesidad de generarlos en Stage 2.

---

### User Story 3 — Data Mixing con Datasets Ancla (Priority: P2)

Un investigador de ML ejecuta el Stage 3 y obtiene un **único archivo JSONL** pre-procesado, mezclado de forma determinista, que combina las trayectorias expertas HA generadas por Stage 2 (**30% de tokens**) con datasets ancla de propósito general descargados de fuentes públicas (**70% de tokens**). El 30% especializado contiene exclusivamente trayectorias multi-turno expert-level de Home Assistant; la variedad de patrones (no-call, llamadas simples, diálogo) la aporta el 70% ancla. Axolotl consume únicamente este artefacto único.

**Why this priority**: Sin esta mezcla el entrenamiento provoca olvido catastrófico; el modelo pierde capacidades de razonamiento general y gramática. Es un requisito de estado del arte para cualquier fine-tuning de Qwen 3.x.

**Independent Test**: Ejecutar Stage 3 sobre un subset de 1 000 registros del dataset especializado y 500 registros de un dataset ancla en formato Alpaca. Verificar que el JSONL de salida contiene ambos orígenes, todos los registros tienen estructura ChatML idéntica (`messages[{role, content}]`), y la proporción de tokens está dentro del rango 60–70 / 30–40.

**Acceptance Scenarios**:

1. **Given** un dataset ancla en formato Alpaca (campos `instruction`, `input`, `output`), **When** Stage 3 lo procesa, **Then** cada registro queda convertido a `messages: [{role: "user", content: ...}, {role: "assistant", content: ...}]` sin pérdida de contenido.
2. **Given** la mezcla de dataset especializado (tool-calling HA) + dataset ancla general, **When** Stage 3 calcula proporciones, **Then** el porcentaje de tokens del dataset tool-calling especializado está entre 28% y 32% y el del ancla general entre 68% y 72% (tolerancia ±2% sobre el objetivo 30/70).
3. **Given** el JSONL final mezclado, **When** se valida la estructura, **Then** el 100% de los registros pasan la validación de esquema ChatML y no existen registros con campos de otros formatos (sin campos `instruction`, `prompt`, `text` sueltos).
4. **Given** el subset de mezcla general, **When** se cuenta la distribución de tipos, **Then** al menos el 15% de los registros del ancla son ejemplos de tipo "no-call" (respuesta conversacional sin invocación de herramienta).
5. **Given** el artefacto JSONL único exportado por Stage 3, **When** se verifica su integridad, **Then** el archivo es reproducible bit-a-bit ejecutando Stage 3 con los mismos parámetros de entrada y semilla, y todos los registros tienen formato ChatML válido.

---

### User Story 4 — Soporte al Formato XML de Herramientas (Priority: P2)

El generador puede producir llamadas a herramientas en formato `qwen3_coder` (estilo XML) además del formato JSON estándar, evitando problemas de escape de caracteres en argumentos que contienen bloques de código PHP o YAML multilínea.

**Why this priority**: Los casos de uso Home Assistant y PHP generan argumentos muy largos con código embebido. El formato JSON puro provoca errores de parsing frecuentes cuando el código contiene comillas o caracteres de escape; el formato XML resuelve este problema estructuralmente.

**Independent Test**: Generar 20 registros con argumentos de herramienta que contengan bloques de código Python ≥ 10 líneas. Verificar que el 100% de los registros con formato `qwen3_coder` son parseables sin errores por el parser XML estándar, y que ningún argumento requiere escaping de comillas dobles.

**Acceptance Scenarios**:

1. **Given** una trayectoria que invoca `read_file` con un argumento de código Python de 30 líneas, **When** el generador usa modo `qwen3_coder`, **Then** la llamada se serializa con tags XML (`<tool_call>`, `<arguments>`) y el contenido del argumento no contiene escapes `\"`.
2. **Given** el mismo registro en formato JSON estándar, **When** se compara con el formato XML, **Then** la semántica es idéntica (misma herramienta, mismos argumentos, mismo valor).
3. **Given** que Stage 3 recibe registros con mezcla de formatos JSON y XML, **When** valida el dataset, **Then** todos los registros se clasifican correctamente por formato y se reporta la distribución al operador.

---

### User Story 5 — Configuración de Entrenamiento NEFTune (Priority: P3)

Un ingeniero de ML actualiza el archivo `axolotl.yaml` para el caso de uso Home Assistant con los nuevos hiperparámetros requeridos: NEFTune `alpha` entre 5 y 15, 2 epochs y los parámetros LoRA sin cambios. El entrenamiento arranca sin errores de configuración y el `alpha` de NEFTune aparece en los logs de WandB.

**Why this priority**: NEFTune es un ajuste puntual de configuración; importante para la calidad final pero desacoplado del trabajo mayor de generación de datos.

**Independent Test**: Ejecutar el entrenamiento sobre 100 pasos con una muestra pequeña del dataset. Verificar en los logs que NEFTune está activo (mensaje de inicialización), que `neftune_noise_alpha` aparece en WandB bajo el run del experimento, y que el entrenamiento completa sin `OOM` ni `NaN`.

**Acceptance Scenarios**:

1. **Given** el archivo `configs/stage_4_training/axolotl/config.homeassistant.yaml` actualizado, **When** Axolotl lo carga, **Then** la inicialización imprime `NEFTune noise alpha: [valor entre 5 y 15]` y no lanza `KeyError` ni `ValidationError`.
2. **Given** que NEFTune está activo, **When** el entrenamiento completa la primera época, **Then** la pérdida de entrenamiento disminuye de forma normal (sin divergencia NaN indicativa de ruido excesivo).

---

### Edge Cases

- ¿Qué ocurre cuando el modelo Teacher falla al generar una trayectoria válida (respuesta truncada o mal formada)? El registro se descarta con log de error; el checkpoint no registra esa seed como completada, permitiendo un reintento en la siguiente ejecución.
- ¿Qué ocurre si la API externa devuelve error 429 (rate limit) de forma sostenida? El backoff exponencial agota `max_retries` intentos; si persiste, Stage 2 guarda el checkpoint del progreso acumulado hasta ese punto, emite un error claro con la seed que falló, y termina la ejecución de forma limpia para permitir reanudación manual.
- ¿Qué ocurre cuando el dataset ancla descargado contiene registros duplicados respecto al dataset especializado? Deben eliminarse por hash de contenido antes de la mezcla.
- ¿Qué ocurre si la proporción de tokens resulta fuera del rango 60–70/30–40 al mezclar datasets de tamaño muy diferente? Stage 3 debe calcular automáticamente un factor de submuestreo para el dataset más grande, con advertencia al operador.
- ¿Qué ocurre cuando un registro del dataset ancla contiene invocaciones de herramienta en un formato no reconocido? Se registra como error de validación, se descarta del dataset ancla sin detener el pipeline.
- ¿Qué ocurre si registros descargados del ancla clasificados como `no-call` contienen en realidad invocaciones de herramienta? El validador de Stage 3 debe detectar y descartar cualquier registro etiquetado como `no-call` que contenga llamadas a herramientas, independientemente de su origen.
- ¿Qué ocurre cuando `neftune_noise_alpha` se configura fuera del rango 5–15? Axolotl debe lanzar un error de validación al inicio, no durante el entrenamiento.

---

## Requirements

### Functional Requirements

#### Stage 2 — Factory: Generación de Trayectorias

- **FR-001**: El generador DEBE producir conversaciones estructuradas en trayectorias de entre 3 y 10 turnos por registro, donde cada turno representa un ciclo Observación → Razonamiento → Acción.
- **FR-002**: Cada trayectoria DEBE incluir al menos un turno de error simulado seguido de al menos un turno de corrección (backtracking), con el bloque `<think>` del asistente describiendo explícitamente el diagnóstico del error.
- **FR-003**: El generador DEBE soportar el modo `hard_query`, en el cual el prompt del usuario en el turno 1 describe únicamente el objetivo final en lenguaje natural, sin mencionar herramientas, funciones o pasos concretos.
- **FR-004**: Stage 2 genera EXCLUSIVAMENTE trayectorias expertas de Home Assistant (multi-turno con backtracking y recuperación de errores). Los ejemplos de tipo `no-call`, llamadas simples a una herramienta y diálogo general NO son responsabilidad de Stage 2; estos patrones de variedad son aportados por los datasets ancla externos descargados en Stage 3.
- **FR-005**: El generador DEBE soportar el formato de serialización `qwen3_coder` (XML-style) para llamadas a herramientas con argumentos que contengan código fuente multilinea.
- **FR-006**: El generador DEBE poder simular errores de tipo `cascade_failure` (el fix del error A expone el error B), generando trayectorias de recuperación de múltiples pasos sin rendirse.
- **FR-007**: El generador DEBE exponer parámetros de configuración para controlar: el número mínimo y máximo de turnos por trayectoria (por defecto: min=3, max=10), la probabilidad de inyectar un error tipo cascade vs. error simple, y el **volumen objetivo de trayectorias expertas HA a generar** (por defecto: ~12 000–15 000 registros, equivalente al 30% de un dataset total de ~40 000–50 000).
- **FR-008**: El generador DEBE mantener compatibilidad con los casos de uso `home_assistant` y `php_legacy` ya definidos en la taxonomía.
- **FR-008b**: El generador DEBE ser configurable en cuanto al proveedor del modelo Teacher (al menos: OpenAI-compatible, Anthropic, Google Gemini) mediante un parámetro único en el archivo de configuración (`teacher_model.provider`, `teacher_model.model_name`, `teacher_model.api_key_env`). Cambiar de proveedor no debe requerir modificaciones de código.
- **FR-008c**: El cliente del modelo Teacher DEBE implementar tres mecanismos de resiliencia configurables independientemente:
  - `teacher_model.request_delay_ms` (por defecto: 500): pausa fija en milisegundos entre llamadas consecutivas a la API.
  - `teacher_model.max_retries` (por defecto: 5) y `teacher_model.backoff_factor` (por defecto: 2): reintentos con backoff exponencial ante errores HTTP 429, 500, 502, 503 y timeouts.
  - `teacher_model.checkpoint_path`: ruta al archivo de checkpoint en disco que registra las seeds ya generadas con éxito. Si el archivo existe al arrancar Stage 2, las seeds ya completadas se omiten sin llamada a la API.

#### Stage 3 — Curation: Data Mixing y Normalización

- **FR-009**: Stage 3 DEBE descargar o aceptar como entrada datasets ancla de propósito general en sus formatos originales. Datasets de referencia recomendados (configurables): `Salesforce/xlam-function-calling-60k` (tool-calling general), `FineTome-100k` (chat/razonamiento), `Magicoder` o `Stack-v2` (código). Se deben soportar al menos los formatos: Alpaca, ShareGPT/ChatML, OpenAI Messages.
- **FR-010**: Stage 3 DEBE convertir **todos** los registros de entrada (tanto especializados como ancla) al formato ChatML estándar (`messages: [{role, content}]`) antes de la mezcla.
- **FR-011**: Stage 3 DEBE rechazar y registrar cualquier registro cuya estructura no sea convertible a ChatML sin pérdida semántica.
- **FR-012**: Stage 3 DEBE calcular la proporción de tokens entre el dataset especializado HA (trayectorias expertas generadas por Stage 2) y los datasets ancla general, y ajustar mediante submuestreo para alcanzar el rango objetivo configurado (por defecto: **30% especializado HA / 70% ancla general**).
- **FR-013**: Stage 3 DEBE exportar el dataset final mezclado como **un único archivo JSONL** barajado con semilla fija reproducible. Este es el único artefacto de entrenamiento que consume Axolotl. La mezcla y el shuffle se ejecutan íntegramente en Stage 3, no se delegan al framework.
- **FR-014**: Stage 3 DEBE eliminar duplicados por hash de contenido tanto dentro de cada dataset como entre datasets, antes de la mezcla.
- **FR-015**: Stage 3 DEBE validar que los registros clasificados como tipo `no-call` — independientemente de su origen (especializado o ancla) — no contienen invocaciones de herramienta. Los que fallen esta validación deben descartarse con log de advertencia.
- **FR-016**: Stage 3 DEBE emitir un reporte de composición final que incluya: número de registros por origen, porcentaje de tokens por origen, distribución de tipos (trajectory, no-call, hard_query, anchor_general), y número de registros descartados con su motivo.

#### Stage 4 — Training Config (Home Assistant)

- **FR-017**: El archivo de configuración de entrenamiento para el caso de uso Home Assistant DEBE incluir el parámetro `neftune_noise_alpha` con un valor dentro del rango [5, 15] (valor por defecto recomendado: 10).
- **FR-018**: La configuración DEBE establecer `num_epochs: 2` para el caso Home Assistant.
- **FR-019**: La configuración DEBE mantener `lora_r: 64` y `peft_use_rslora: true` sin cambios.
- **FR-020**: La configuración de Axolotl DEBE referenciar exclusivamente el **único archivo JSONL** pre-procesado y barajado producido por Stage 3. No se declararán múltiples datasets en el `axolotl.yaml`; toda la lógica de mezcla reside en Stage 3, garantizando un artefacto de entrenamiento auditable y reproducible.
- **FR-021**: El validador de configuración DEBE rechazar valores de `neftune_noise_alpha` fuera del rango [5, 15] con un mensaje de error claro antes de iniciar el entrenamiento.

### Key Entities

- **Trayectoria Agéntica (AgenticTrajectory)**: Secuencia ordenada de 3–10 turnos que representa la resolución de un objetivo. Atributos clave: `turns[]`, `use_case`, `mode` (hard_query/explicit/no-call), `error_type` (cascade/simple/none), `tool_format` (json/xml), `token_count`.
- **Turno (Turn)**: Par `{role, content}` dentro de una trayectoria. El contenido del `assistant` contiene opcionalmente un bloque `<think>` de razonamiento. Tipos de turno: `observe` (lectura de estado), `reason` (planificación), `act` (invocación de herramienta), `error` (resultado de error), `correct` (corrección), `verify` (confirmación de éxito).
- **Registro de Dataset (DatasetRecord)**: Unidad atómica del dataset final. Estructura ChatML: `{messages: [{role, content}], metadata: {origin, type, use_case, token_count, format}}`. Debe ser idénticamente estructurado independientemente de si proviene del dataset especializado o del ancla.
- **Dataset Ancla (AnchorDataset)**: Dataset descargado de fuentes públicas que constituye el **70%** del dataset final y cumple DOS funciones: (1) preservar capacidades fundacionales del modelo (razonamiento, código, diálogo) para evitar olvido catastrófico; (2) aportar la **variedad de patrones de tool-calling** que Stage 2 no genera (no-call, llamadas simples, secuencias genéricas). Datasets de referencia recomendados: `Salesforce/xlam-function-calling-60k` (tool-calling general curado con 60k ejemplos), `FineTome-100k` (diálogo / razonamiento), `Magicoder` / `Stack-v2` (código). Todos deben convertirse a ChatML antes de la mezcla.
- **Error Simulado (SimulatedError)**: Evento inyectado artificialmente en una trayectoria para obligar al modelo a practicar backtracking. Tipos: `tool_failure` (herramienta devuelve error), `wrong_result` (herramienta devuelve resultado incorrecto silencioso), `cascade_failure` (resolver A expone B).
- **Modelo Teacher (TeacherModelClient)**: Componente de Stage 2 que encapsula las llamadas a la API externa para generar trayectorias expertas HA. Configurable: proveedor (OpenAI-compatible, Anthropic, Google Gemini), modelo, clave de API, delay entre llamadas, política de reintentos con backoff exponencial, y ruta de checkpoint. El checkpoint persiste en disco el estado de generación (seeds completadas), permitiendo reanudar ejecuciones interrumpidas sin duplicar costos de API.
- **Checkpoint de Generación (GenerationCheckpoint)**: Artefacto de Stage 2 persistido en disco. Registra el ID/hash de cada seed procesada con éxito y el path del JSONL parcial resultante. Al reanudar, Stage 2 carga el checkpoint, omite las seeds ya completadas y continúa desde el punto de interrupción.
- **Reporte de Composición (CompositionReport)**: Artefacto generado por Stage 3 que documenta la composición del dataset final: proporciones por origen, tipos, formatos y registros descartados.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: El 100% de los registros generados por el modo `trajectories` contienen entre 3 y 10 turnos, y el 100% contiene al menos 1 turno de error + 1 turno de corrección.
- **SC-002**: El 100% de los registros del modo `hard_query` no contienen nombres de herramientas ni pasos explícitos en el prompt del usuario del turno 1, verificable mediante validación léxica.
- **SC-003**: Los ejemplos de tipo `no-call` / rechazo presentes en el dataset final provienen de los datasets ancla externos. Al menos el 15% de los registros del subset ancla son de tipo `no-call` o conversación sin invocación de herramienta (proporción típica en `Salesforce/xlam-function-calling-60k`), garantizando que el modelo no sobreajuste el uso de herramientas.
- **SC-004**: El dataset final mezclado mantiene la proporción de tokens tool-calling-especializado/ancla-general dentro del rango **28–32% / 68–72%** (tolerancia ±2% sobre el objetivo de 30/70).
- **SC-005**: El 100% de los registros del dataset final superan la validación de esquema ChatML sin campos residuales de formatos Alpaca, ShareGPT u otros.
- **SC-006**: El tiempo de ejecución de un entrenamiento de prueba de 100 pasos con NEFTune habilitado no supera en más de un 10% el tiempo de referencia sin NEFTune (el ruido de embedding no debe impactar significativamente la velocidad de entrenamiento).
- **SC-007**: El modelo re-entrenado sobre el nuevo dataset demuestra, en al menos el 80% de las evaluaciones manuales de un evaluador humano, que persiste ante errores con al menos un intento de recoverabilidad antes de declarar inviable la tarea (criterio de evaluación cualitativo: "no se rinde en el primer obstáculo").
- **SC-008**: Stage 3 genera el reporte de composición en menos de 60 segundos para un dataset de hasta 50 000 registros (volumen por defecto configurado).

---

## Assumptions

- El modelo Teacher que genera las trayectorias es una **API externa** (ej. OpenAI, Anthropic, Google). El proveedor, el modelo y las credenciales son configurables mediante parámetros de entorno o archivo de configuración; ningún proveedor concreto está hardcodeado. El pipeline actual de acceso a documentos de referencia (`HA_MASTER_GUIDE_2026.md`, `technical_changelog_2026.md`) se mantiene sin cambios.
- Los datasets ancla seleccionados (Magicoder, FineTome-100k) están disponibles públicamente en HuggingFace Hub y no requieren licencia de pago.
- El volumen objetivo del dataset final mezclado es **~40 000–50 000 registros** por defecto (~12–15k especializados tool-calling HA + ~28–35k ancla general), configurable mediante parámetro `dataset.target_total_records`. La infraestructura de entrenamiento (GPUs, RAM) soporta este volumen sin requerir sharding adicional.
- La proporción de mezcla es **30% tool-calling especializado / 70% ancla general**, siguiendo la receta estándar SFT 2025–2026 para modelos de tool-calling. Datasets ancla de referencia: `Salesforce/xlam-function-calling-60k`, `FineTome-100k`, `Magicoder`/`Stack-v2`.
- El formato `qwen3_coder` (XML-style) es compatible con el tokenizador y el chat template del modelo base Qwen3-30b-A3B; si no, se requiere verificación antes de la implementación.
- La proporción de mezcla **30/70** (trayectorias expertas HA / ancla general) es el punto de partida basado en la receta estándar SFT 2025-2026. Stage 2 genera únicamente trayectorias HA; la variedad de patrones de tool-calling (no-call, llamadas simples, diálogo) la aportan datasets ancla externos ya curados como `Salesforce/xlam-function-calling-60k`. La mezcla y el shuffle son responsabilidad exclusiva de Stage 3 (un único JSONL determinista). El equipo puede ajustar la proporción sin modificar esta especificación.
- NEFTune `alpha=10` es el valor por defecto recomendado; el equipo puede tunearlo en el rango [5, 15] sin requerir un nuevo ciclo de spec.
- Los registros del dataset ancla que no contienen llamadas a herramientas se usan tal cual para los ejemplos `no-call`; no es necesario generarlos sintéticamente en Stage 2.
- La resiliencia de Stage 2 frente a interrupciones de la API externa se gestiona mediante checkpoint en disco + backoff exponencial + sleep configurable, sin necesidad de infraestructura de colas externa (Redis, Celery, etc.).

---

## Out of Scope

- Cambios en Stage 1 (Discovery): la ingesta de documentos fuente no se modifica.
- Cambios en Stage 5 (Evaluation) y Stage 6 (Calibration): el pipeline de evaluación post-entrenamiento no forma parte de esta especificación.
- Caso de uso PHP Legacy: aunque se mantiene compatibilidad, los ajustes de trayectorias y NEFTune documentados son específicos para el caso Home Assistant.
- Generación de un nuevo dataset ancla personalizado: se reutilizan datasets públicos existentes; no se generan datos ancla sintéticos.
