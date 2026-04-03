# Jinja Template Guide

## Overview

Guía de uso de plantillas Jinja en Home Assistant.

## Syntax

### Variables

```
{{ variable_name }}
```

### Filters

```
{{ variable | filter }}
```

### Conditions

```
{% if condition %}
  Content
{% endif %}
```

### Loops

```
{% for item in items %}
  {{ item }}
{% endfor %}
```

## Examples

- State templates: `{{ state('sensor.temperature') }}`
- Attribute templates: `{{ state_attr('light.bedroom', 'brightness') }}`
- Time filters: `{{ now() | strftime('%Y-%m-%d') }}`
