 - - [ ] crte un archivo todo2.md que tenga el mismo contenido que TODO.md## 1. Contexto y Problema a Resolver
Tenemos un problema de alineación en nuestro modelo: **razona perfectamente, pero luego escribe código legacy**. 
El modelo base tiene un sesgo muy fuerte hacia código antiguo de Home Assistant. Actualmente, nuestro dataset V11 (`data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl`) tiene muestras de alta calidad, pero la forma en que le enseñamos no vence este sesgo. Simplemente le damos la respuesta perfecta, por lo que el modelo no aprende a corregir su propio impulso probabilístico de escribir código viejo.

**Objetivo:** Transformar el dataset V11 en un nuevo dataset aplicando la técnica de **"Autocorrección y Backtracking"** demostrada en los reportes de *OpenCodeReasoning* y *AgentMath*.
Según el reporte de OpenCodeReasoning, el simple hecho de razonar no garantiza el éxito; los patrones de razonamiento que estadísticamente producen código correcto son la Autoevaluación (Self-Evaluation) y el Retroceso (Backtracking).
En lugar de que el bloque <think> diga simplemente: "Debo usar la nueva API según el changelog", debes forzar al modelo a que simule cometer el error legacy en su mente y lo corrija antes de escribir el código real.
Ejemplo de cómo reescribir tus muestras del dataset:
<think> El usuario pide actualizar la entidad. Voy a preparar el código. Mi primer instinto es usar await hass.helpers.entity_registry.async_get_registry(hass) porque es la forma estándar de obtener el registro. Espera, autoevaluación: En el contexto y changelog provisto se indica que async_get_registry ha sido eliminado en la versión 2025.X por ser bloqueante. Corrección (Backtracking): Si uso eso, el código fallará. Debo descartar esa idea. La mejor práctica actual es usar el singleton síncrono er.async_get(hass). Voy a estructurar el código final usando exclusivamente esta nueva importación. </think>
Al incluir este "diálogo interno" de corrección, creas un puente matemático entre el sesgo legacy del modelo y la sintaxis moderna. El modelo aprende a atraparse a sí mismo.

## 2. Estrategia de Datos (Trabajar Inteligente)
El dataset /mnt/bunker_data/ai/data_factory/data/synthetic/v11_diversified_20260226_031536_DISTILLED.jsonl (aprox 2'000 registros) ya contiene un tesoro de metadatos. Ya sabemos qué muestras son nominales, de contraste o de error. Ya sabemos cuáles activaron un "gold injection" (reemplazo artificial) y cuáles son "gold skipped" (el modelo lo hizo bien por sí solo). incluso no se si estan marcados como codigo legacy. si no, hay patrones para detectar el codigo legacy. en otros scripts

**No vamos a re-evaluar todo con vLLM desde cero.** Tu tarea es:
1. **Explorar proactivamente** la estructura del .jsonl para identificar cómo están marcados estos metadatos

2. **Filtrar y Purgar:** Descartar todos los examplos de mas de 4000 tokens . Descarta las muestras que no nos sirven para enseñar alineación real (por ejemplo, reemplazos directos que causan saltos antinaturales en la probabilidad) y quédate con las valiosas (ej. las que el modelo resolvió bien o los escenarios de error/contraste útiles). Osea Para el gold injection podemos usar esta tecnica :"El método: Le das al modelo maestro el problema original y tu código gold, y le das esta instrucción: "Aquí tienes un problema de Home Assistant y la solución perfecta en código moderno. Escribe la traza de razonamiento paso a paso (...</think>) que un desarrollador experto seguiría para llegar EXACTAMENTE a este código, explicando por qué se evitan las funciones legacy."" 
3. **Transformar (Reescribir el blo think):** A las muestras que sobrevivan al filtro, les vamos a reescribir su bloque think usando nuestro vLLM local para inyectar el proceso de Backtracking. Recuerda que solo tiene que existir el tag de cierre de think. tal cual esta ahora mismo 

## 3. La Regla de Oro de la Transformación: Backtracking
Para que el modelo traslade su buen razonamiento al código final, su bloque de pensamiento debe simular el error y corregirlo antes de escribir el código real., hay que revisar todos los ejemplos de error para aplicar esta solucion en ellos los que aun no esten alineados con esta solución. 
El script que construyas debe pedirle al vLLM local que reescriba el `...<\think>` de las muestras seleccionadas siguiendo este flujo estricto:

1. **Instinto Legacy:** Proponer internamente la solución antigua (ej. `async_get_registry`).
2. **Autoevaluación:** Recordar el contexto/gobernanza de HA 2026. (En todos los dataset ya se inyecta el contexto de homeassistant2026)
3. **Backtracking (Corrección):** Rechazar explícitamente la idea anterior (*"Espera, si uso async_get_registry el código fallará porque es bloqueante"*).
4. **Resolución Moderna:** Estructurar la solución final con la API correcta antes de cerrar el `</think>`.

## 4. Plan de Ejecución (Paso a Paso)
Actúa como un Ingeniero de Datos Autónomo. Sigue este orden:

* **Paso 1: Análisis Exploratorio.** mapear exactamente qué campos y metadatos existen.
* **Paso 2: Escribir la Spec.** Crea un archivo Markdown breve (`docs/specs/stage_1_5_backtracking_alignment.md`) definiendo los criterios exactos de filtrado basados en lo que encontraste, y el prompt del sistema que usaremos para reescribir los `<\think>`. Usa este paso tambien para recopilar y documentar en la spec las clases y scripts de pyton que ya existen y te pueden ayudar y como usarlos. 
* **Paso 3: Implementación.** Desarrolla el script o scripts(Recuerda seguir la arquitectura del proyecto (quizas ya tienes herramientas y scripts))  que procese el jsonl, filtre, llame al vLLM para reescribir los pensamientos necesarios, y guarde el resultado en un nuevo dataset destilado y alineado.

Usa tus herramientas, revisa las guías del proyecto que ya conoces, manten el agnosticismo. y configuraciones independientes en los scripts. usa TDD escribe primero el test y luego el codigo. Vete haciendo pruebas con conjuntos pequeños de ejemplos hasta que los dataset resultantes sean de la calidad y requisitos que se han mencionado