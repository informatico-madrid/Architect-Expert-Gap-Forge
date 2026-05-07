# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

# Home Assistant Jinja & YAML Guide

## Overview

This guide covers Jinja template syntax and YAML configuration patterns used
throughout the Architect-Expert-Gap-Forge system.

## Jinja Template Syntax

### Variable Output

```jinja
{{ variable_name }}
{{ user.name }}
{{ config.get('mode', 'default') }}
```

### Filters

```jinja
{{ value | upper }}
{{ value | lower }}
{{ value | default('fallback') }}
{{ value | round(2) }}
{{ value | int }}
{{ value | float }}
{{ value | tojson }}
{{ value | regex_replace('pattern', 'replacement') }}
{{ value | strftime('%Y-%m-%d') }}
```

### Control Structures

#### If/Else

```jinja
{% if condition %}
  Content when true
{% else %}
  Content when false
{% endif %}

{% if temperature > 25 %}
  "Hot"
{% elif temperature > 20 %}
  "Warm"
{% else %}
  "Cold"
{% endif %}
```

#### For Loops

```jinja
{% for item in items %}
  - {{ item.name }}
{% endfor %}

{% for key, value in config.items() %}
  {{ key }}: {{ value }}
{% endfor %}
```

#### Comments

```jinja
{# This is a comment - not rendered #}
```

## YAML Configuration Patterns

### Home Assistant Automations

```yaml
automation:
  - alias: "Automation Name"
    trigger:
      platform: state
      entity_id: light.living_room
    condition:
      condition: numeric_state
      entity_id: sensor.temperature
      above: 20
    action:
      service: light.turn_on
      target:
        area_id: living_room
```

### Home Assistant Scripts

```yaml
script:
  morning_routine:
    alias: "Morning Routine"
    sequence:
      - service: light.turn_on
        target:
          area_id: bedroom
      - service: notification.notify
        data:
          message: "Good morning!"
```

### Home Assistant Sensors

```yaml
sensor:
  - platform: template
    sensors:
      room_temperature:
        value_template: "{{ state('sensor.bedroom_temperature') }}"
        unit_of_measurement: "°C"
        icon: "mdi:thermometer"
```

### Home Assistant Switches

```yaml
switch:
  - platform: template
    switches:
      morning_mode:
        value_template: "{{ is_state('switch.morning', 'on') }}"
        turn_on:
          service: light.turn_on
          target:
            area_id: bedroom
        turn_off:
          service: light.turn_off
          target:
            area_id: bedroom
```

## Best Practices

1. **Use meaningful aliases** for automations and scripts
2. **Group entities by area_id** for consistent targeting
3. **Use templates** for dynamic values and conditions
4. **Validate YAML syntax** before applying configurations
5. **Test automations** in development mode first

## References

- Home Assistant Documentation: https://www.home-assistant.io/docs/automation/
- Jinja2 Documentation: https://jinja.palletsprojects.com/
- YAML Specification: https://yaml.org/spec/
