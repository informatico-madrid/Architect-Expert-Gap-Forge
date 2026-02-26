# Home Assistant — Jinja2 & YAML Changes Guide 2024.10 → 2026.2

> **Uso:** Este documento es un Master Document inyectado por `production_v10.py` como contexto de API Delta para el entrenamiento de plantillas Jinja2 y YAML en Home Assistant 2026.

El ecosistema de Home Assistant ha experimentado una evolución arquitectónica muy profunda respecto a YAML y el motor de plantillas (Jinja2) entre finales de 2024 y principios de 2026. La plataforma ha transicionado de un enfoque puramente técnico basado en "estados" a una configuración más semántica y orientada al contexto.

A continuación se detallan todos los breaking changes y cambios importantes en plantillas Jinja y YAML desde la versión 2024.10 hasta la 2026.2, clasificados cronológicamente.

---

## Versión 2024.10

### [Mejora / Cambio de sintaxis] Pluralización y claridad en la sintaxis YAML de automatizaciones

**Descripción:** Se modificó la sintaxis principal de las automatizaciones en YAML. La clave principal `trigger` pasó a ser `triggers` (plural), `condition` pasó a ser `conditions` y `action` pasó a `actions`. Además, dentro de la definición de un disparador, la clave `platform` se renombró a `trigger`.

**Motivación e Implicaciones:** El objetivo era hacer que la sintaxis fuera más natural, semántica y fácil de leer, reflejando que estas secciones casi siempre contienen listas de elementos. No es un breaking change estricto (la sintaxis antigua sigue funcionando), pero la nueva sintaxis es el estándar recomendado y el editor visual migrará automáticamente el código al guardar.

**Ejemplo — Sintaxis antigua (2024.9 y anterior):**
```yaml
automation:
  - alias: "Luz entrada al llegar"
    trigger:
      - platform: state
        entity_id: person.john
        to: "home"
    condition:
      - condition: sun
        after: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.entrada
```

**Ejemplo — Sintaxis nueva (2024.10+, estándar recomendado):**
```yaml
automation:
  - alias: "Luz entrada al llegar"
    triggers:
      - trigger: state
        entity_id: person.john
        to: "home"
    conditions:
      - condition: sun
        after: sunset
    actions:
      - action: light.turn_on
        target:
          entity_id: light.entrada
```

---

### [Breaking Change] Límite de tamaño en la salida de plantillas

**Descripción y Motivación:** Se limitó el tamaño máximo de renderizado de una plantilla a **256 KiB** para evitar que las plantillas inyecten cantidades irrazonables de datos en el sistema y provoquen cuelgues (crashes).

**Implicaciones:** Si tienes plantillas que generan bloques de texto masivos (por ejemplo, iterando sobre miles de entidades para generar logs), estas fallarán si superan este límite.

**Ejemplo — Plantilla que puede fallar con el límite:**
```yaml
# PELIGROSO si hay muchas entidades — puede superar 256 KiB
template:
  - sensor:
      - name: "Reporte completo"
        state: >
          {% for entity in states %}
            {{ entity.entity_id }}: {{ entity.state }}
          {% endfor %}
```

**Solución recomendada:** Filtrar por dominio o limitar el número de entidades procesadas:
```yaml
template:
  - sensor:
      - name: "Reporte luces"
        state: >
          {% for entity in states.light | list | selectattr('state', 'eq', 'on') %}
            {{ entity.entity_id }}: {{ entity.state }}
          {% endfor %}
```

---

## Versión 2024.12

### [Breaking Change] Modificación de la variable `this` en integraciones basadas en plantillas

**Descripción:** En algunos helpers (`command_line`, `rest`, `scrape`, `snmp`, `sql`), la variable de plantilla `this` basaba su estado en el nuevo estado en lugar del estado actual.

**Implicaciones:** Los usuarios cuyas plantillas dependían de la variable `this` en estas integraciones deben actualizarlas para usar la variable `value` si necesitan referirse al nuevo valor entrante.

**Ejemplo — Código antiguo (incorrecto en 2024.12+):**
```yaml
command_line:
  - sensor:
      name: "Temperatura exterior"
      command: "curl -s http://sensor.local/temp"
      value_template: >
        {% if this.state | float > 30 %}
          calor
        {% else %}
          {{ value }}
        {% endif %}
```

**Ejemplo — Código corregido:**
```yaml
command_line:
  - sensor:
      name: "Temperatura exterior"
      command: "curl -s http://sensor.local/temp"
      value_template: >
        {% if value | float > 30 %}
          calor
        {% else %}
          {{ value }}
        {% endif %}
```

---

### [Breaking Change] Estandarización de unidades y atributos en YAML

**Descripción y Motivación:** Para mejorar la coherencia de los datos, integraciones como Brother Printer cambiaron sus unidades (de `p` a `pages`) y componentes como `history_stats` ajustaron su lógica para no "asumir" estados pasados inventados. Además, múltiples integraciones pasaron los valores de estado a formato `snake_case` (por ejemplo en Unifi, de `Heartbeat Missed` a `heartbeat_missed`).

**Implicaciones:** Cualquier plantilla Jinja que hiciera comparaciones de texto estricto o que dependiera del filtro de unidad con la letra `p` fallará y debe ser ajustada.

**Ejemplo — Código antiguo (rompe en 2024.12+):**
```yaml
# ROMPE: el estado ya no incluye mayúsculas ni espacios
template:
  - binary_sensor:
      - name: "Unifi sin heartbeat"
        state: "{{ states('sensor.unifi_status') == 'Heartbeat Missed' }}"
```

**Ejemplo — Código corregido:**
```yaml
template:
  - binary_sensor:
      - name: "Unifi sin heartbeat"
        state: "{{ states('sensor.unifi_status') == 'heartbeat_missed' }}"
```

---

## Versión 2025.3

### [Breaking Change] Propagación del alcance (scope) de variables en automatizaciones

**Descripción:** Las variables definidas con `response_variable` (al llamar a un servicio/acción) o con `wait` dentro de un bloque interno de un script o automatización, ahora se propagan a los bloques externos (incluso si hay una acción `variables` presente en el interior). También se propagan desde secuencias paralelas (`parallel`).

**Motivación e Implicaciones:** Se corrigió un comportamiento antiguo y defectuoso. Los scripts en YAML que dependían del "olvido" de estas variables al salir del bloque interno tendrán que ser revisados, ya que ahora la variable seguirá existiendo en el flujo principal.

**Ejemplo — Comportamiento que cambia:**
```yaml
script:
  verificar_puerta:
    sequence:
      - if:
          - condition: state
            entity_id: binary_sensor.puerta
            state: "on"
        then:
          - action: notify.mobile_app
            response_variable: resultado_notify  # En 2025.3+ esta variable
                                                 # es visible FUERA del bloque "then"
          - variables:
              resultado_notify: "ignorado"       # Ya no sobreescribe el response_variable
                                                 # del contexto externo de forma aislada

      # ADVERTENCIA: resultado_notify aquí puede tener el valor del response_variable
      # del bloque then anterior, a diferencia de versiones < 2025.3
      - condition: template
        value_template: "{{ resultado_notify is defined }}"
```

---

## Versión 2025.4

### [Mejora] Nuevas funciones y filtros en Jinja2

**Descripción:** Se añadieron potentes funciones para manipular datos, diccionarios y listas directamente desde Jinja2, eliminando la necesidad de macros complejas.

**Nuevas funciones:**
- `combine` — unir diccionarios
- `difference`, `intersect`, `union`, `symmetric_difference` — operaciones de conjuntos con listas
- `flatten` — aplanar listas anidadas
- `shuffle` — desordenar listas aleatoriamente
- `typeof` — depuración de tipos de variable
- `md5`, `sha1`, `sha256`, `sha512` — funciones de hash

**Ejemplo — `combine` para unir configuraciones:**
```yaml
template:
  - sensor:
      - name: "Config fusionada"
        state: >
          {% set defaults = {'color': 'blue', 'brightness': 128} %}
          {% set overrides = {'brightness': 255, 'effect': 'pulse'} %}
          {{ defaults | combine(overrides) }}
          {# Resultado: {'color': 'blue', 'brightness': 255, 'effect': 'pulse'} #}
```

**Ejemplo — Operaciones de conjuntos con `difference` e `intersect`:**
```yaml
template:
  - sensor:
      - name: "Luces encendidas no esperadas"
        state: >
          {% set encendidas = states.light | selectattr('state','eq','on')
               | map(attribute='entity_id') | list %}
          {% set permitidas = ['light.salon', 'light.cocina'] %}
          {% set inesperadas = encendidas | difference(permitidas) %}
          {{ inesperadas | join(', ') if inesperadas else 'ninguna' }}
```

**Ejemplo — `flatten` para listas anidadas:**
```yaml
template:
  - sensor:
      - name: "Todos los dispositivos"
        state: >
          {% set grupos = [['light.salon', 'light.cocina'], ['switch.router']] %}
          {{ grupos | flatten | join(', ') }}
          {# Resultado: 'light.salon, light.cocina, switch.router' #}
```

**Ejemplo — `typeof` para depuración:**
```yaml
template:
  - sensor:
      - name: "Tipo de temperatura"
        state: >
          {% set temp = states('sensor.temperatura') %}
          {{ typeof(temp) }}
          {# Devuelve 'string', 'float', 'int', etc. #}
```

---

## Versión 2025.8

### [Breaking Change] Los `binary_sensor` basados en plantillas ya no asumen `None` como `off`

**Descripción:** Si la plantilla de estado de un sensor binario devuelve `None`, Home Assistant ahora lo interpreta como estado `unknown` (desconocido) en lugar de estado `off`.

**Motivación e Implicaciones:** Mejora la precisión de los datos (un sensor fallando no debería marcarse automáticamente como apagado). Los usuarios deben revisar sus plantillas de `binary_sensor`. Si se desea explícitamente que el estado sea apagado en caso de error o de variables nulas, la plantilla debe devolver `False` explícitamente.

**Ejemplo — Código antiguo (comportamiento cambia en 2025.8):**
```yaml
template:
  - binary_sensor:
      - name: "Dispositivo activo"
        state: >
          {% set val = state_attr('sensor.dispositivo', 'activo') %}
          {{ val }}
          {# Si val es None → antes: off | ahora: unknown #}
```

**Ejemplo — Código corregido (explícito):**
```yaml
template:
  - binary_sensor:
      - name: "Dispositivo activo"
        state: >
          {% set val = state_attr('sensor.dispositivo', 'activo') %}
          {{ val if val is not none else false }}
          {# Ahora None → false (off) explícitamente #}
```

---

### [Breaking Change] Eliminación del estado `standby` y atributos de batería

**Descripción:** Múltiples reproductores multimedia (Apple TV, ADB, etc.) dejaron de reportar el estado `standby` y pasaron a usar `off`. Además, se eliminó el atributo `battery` de las entidades de aspiradoras (Ecovacs, Miele, Roborock) en favor de sensores independientes.

**Implicaciones:** Plantillas que verificaban `is_state(..., 'standby')` o extraían `state_attr(..., 'battery_level')` dejarán de funcionar y devolverán `None`. Deben cambiarse por estados `off` y por `states('sensor.robot_battery_level')` respectivamente.

**Ejemplo — Código antiguo (rompe en 2025.8):**
```yaml
template:
  - binary_sensor:
      - name: "TV en standby"
        state: "{{ is_state('media_player.tv_salon', 'standby') }}"

  - sensor:
      - name: "Batería aspiradora"
        state: "{{ state_attr('vacuum.robot_aspirador', 'battery_level') }}"
        unit_of_measurement: "%"
```

**Ejemplo — Código corregido:**
```yaml
template:
  - binary_sensor:
      - name: "TV apagada"
        state: "{{ is_state('media_player.tv_salon', 'off') }}"

  - sensor:
      - name: "Batería aspiradora"
        # El atributo battery_level se eliminó — ahora es un sensor independiente
        state: "{{ states('sensor.robot_aspirador_battery_level') }}"
        unit_of_measurement: "%"
```

---

## Versión 2025.12

### [Gran Breaking Change / Deprecación] Deprecación de las Entidades de Plantilla Legacy (`platform: template`)

**Descripción:** El formato Legacy para configurar plantillas en `configuration.yaml` (donde se agrupaban bajo dominios como `sensor:`, `binary_sensor:`, etc., usando `platform: template`) ha sido oficialmente deprecado y **dejará de funcionar en la versión 2026.6**.

**Motivación:** La sintaxis legacy causaba problemas arquitectónicos para permitir plantillas asignadas a dispositivos, disparadores (triggers) basados en plantillas y Blueprints de UI.

**Implicaciones:** Todos los usuarios deben migrar a la "sintaxis moderna", la cual se agrupa bajo una clave raíz única llamada `template:`.

**Punto crítico para IDs (`default_entity_id`):** Al migrar, para que los `entity_id` históricos no cambien y rompan paneles y estadísticas, se debe usar la clave `default_entity_id` especificando el ID antiguo explícitamente.

**Ejemplo — Sintaxis Legacy (DEPRECADA, deja de funcionar en 2026.6):**
```yaml
# configuration.yaml — LEGACY, NO USAR
sensor:
  - platform: template
    sensors:
      temperatura_media:
        friendly_name: "Temperatura Media"
        unit_of_measurement: "°C"
        value_template: >
          {{ (states('sensor.temp_salon') | float +
              states('sensor.temp_cocina') | float) / 2 }}

binary_sensor:
  - platform: template
    sensors:
      ventana_abierta:
        friendly_name: "Ventana Abierta"
        value_template: "{{ is_state('binary_sensor.ventana', 'on') }}"
        device_class: window
```

**Ejemplo — Sintaxis Moderna (2025.12+, obligatoria tras 2026.6):**
```yaml
# configuration.yaml — SINTAXIS MODERNA
template:
  - sensor:
      - name: "Temperatura Media"
        unit_of_measurement: "°C"
        default_entity_id: sensor.temperatura_media   # Preserva el entity_id histórico
        state: >
          {{ (states('sensor.temp_salon') | float +
              states('sensor.temp_cocina') | float) / 2 }}

  - binary_sensor:
      - name: "Ventana Abierta"
        default_entity_id: binary_sensor.ventana_abierta  # Preserva el entity_id histórico
        device_class: window
        state: "{{ is_state('binary_sensor.ventana', 'on') }}"
```

---

### [Mejora] Nuevas funciones matemáticas en Jinja2

**Descripción:** Se introdujeron las funciones `clamp(v, min, max)` (para limitar un valor), `wrap(v, min, max)` (aritmética modular), y `remap(v, in_min, in_max, out_min, out_max)` (interpolación lineal para mapear un rango a otro).

**Motivación:** Facilita cálculos complejos en YAML sin tener que escribir fórmulas matemáticas largas, muy útil para brillo de luces, colores o interpolación de sensores raw.

**Ejemplo — `clamp` para limitar brillo:**
```yaml
automation:
  - alias: "Ajustar brillo según temperatura"
    triggers:
      - trigger: state
        entity_id: sensor.temperatura_exterior
    actions:
      - action: light.turn_on
        target:
          entity_id: light.terraza
        data:
          brightness_pct: >
            {# Mapea temperatura (0°C→50°C) a brillo (20%→100%), con límites #}
            {{ clamp(states('sensor.temperatura_exterior') | float, 0, 50)
               | remap(0, 50, 20, 100) | round(0) | int }}
```

**Ejemplo — `wrap` para ciclo de colores (tono 0-360°):**
```yaml
template:
  - sensor:
      - name: "Tono luz rotante"
        state: >
          {% set paso = (now().minute * 6) %}
          {{ wrap(paso, 0, 360) }}
```

**Ejemplo — `remap` para convertir rango de sensor raw:**
```yaml
template:
  - sensor:
      - name: "Nivel de CO2 normalizado"
        unit_of_measurement: "%"
        state: >
          {# Sensor raw: 400ppm (mínimo) a 2000ppm (máximo) → escala 0-100% #}
          {{ remap(states('sensor.co2_raw') | float, 400, 2000, 0, 100) | round(1) }}
```

---

### [Breaking Change] Cambio en la función `issues()`

**Descripción:** La función de plantilla `issues()` ahora solo devuelve incidencias **activas**, dejando de devolver aquellas que ya han sido resueltas o reparadas.

**Ejemplo — Uso correcto en 2025.12+:**
```yaml
template:
  - sensor:
      - name: "Incidencias activas"
        state: "{{ issues() | count }}"
        # Sólo cuenta las incidencias aún pendientes de resolución
        # En versiones anteriores también incluía las ya resueltas
```

---

## Versión 2026.1 y 2026.2

### [Mejora] Disparadores y Condiciones Semánticas (Purpose-specific triggers)

**Descripción:** Se introdujeron "Disparadores orientados al propósito" que permiten escribir automatizaciones en lenguaje natural en lugar de cambios técnicos de estado (ej. "Cuando la luz se enciende" en lugar de `trigger: state, to: 'on'`). En 2026.1 y 2026.2 esto se extendió a condiciones ("Si el clima está calentando" en lugar de `state: heating`).

**Motivación:** Hacer la automatización más accesible, centrándose primero en "qué" se quiere automatizar y luego el "cómo".

**Ejemplo — Sintaxis técnica tradicional (sigue funcionando):**
```yaml
automation:
  - alias: "Notificación luz encendida"
    triggers:
      - trigger: state
        entity_id: light.salon
        to: "on"
    conditions:
      - condition: state
        entity_id: climate.salon
        state: "heating"
    actions:
      - action: notify.mobile_app_telefono
        data:
          message: "La luz del salón está encendida mientras calienta"
```

**Ejemplo — Nueva sintaxis semántica (2026.1+):**
```yaml
automation:
  - alias: "Notificación luz encendida"
    triggers:
      - trigger: light.turned_on      # Semántico: "cuando la luz se enciende"
        entity_id: light.salon
    conditions:
      - condition: climate.is_heating # Semántico: "si el clima está calentando"
        entity_id: climate.salon
    actions:
      - action: notify.mobile_app_telefono
        data:
          message: "La luz del salón está encendida mientras calienta"
```

---

### [Mejora] Previsualizaciones en vivo (Live Inline Previews) en el editor YAML

**Descripción:** Al escribir plantillas Jinja2 dentro de los editores de scripts o automatizaciones, ahora aparece un recuadro debajo de la línea que pre-evalúa y muestra el resultado en tiempo real (Live preview).

**Motivación:** Elimina la necesidad de estar saltando constantemente a la sección de Developer Tools → Templates para probar la lógica de la plantilla.

**Impacto en desarrollo:** Las plantillas como la siguiente se pueden verificar directamente en el editor sin salir del contexto de la automatización:

```yaml
actions:
  - action: notify.mobile_app_telefono
    data:
      message: >
        La temperatura es {{ states('sensor.temp_salon') | float | round(1) }}°C.
        {# ↑ El editor muestra en vivo: "La temperatura es 21.3°C." #}
```

---

## Resumen de Breaking Changes por Versión

| Versión | Cambio | Impacto |
|---------|--------|---------|
| 2024.10 | `trigger`→`triggers`, `platform`→`trigger` | Medio (sin migración automática de YAML manual) |
| 2024.10 | Límite 256 KiB en salida de plantillas | Medio (solo plantillas masivas) |
| 2024.12 | `this` → `value` en `command_line`, `rest`, etc. | Alto para integraciones afectadas |
| 2024.12 | Unidades y estados a `snake_case` | Alto para comparaciones de texto exacto |
| 2025.3  | Propagación de scope de variables | Medio (scripts complejos con bloques anidados) |
| 2025.8  | `None` en `binary_sensor` → `unknown` (no `off`) | Alto para sensores con plantillas no seguras |
| 2025.8  | `standby` → `off` en media players | Alto para automatizaciones de TV/media |
| 2025.8  | Atributo `battery` eliminado de aspiradoras | Alto para dashboards y automatizaciones de batería |
| 2025.12 | `platform: template` deprecado (fin en 2026.6) | **Crítico** — migración obligatoria |
| 2025.12 | `issues()` solo activas | Bajo |
