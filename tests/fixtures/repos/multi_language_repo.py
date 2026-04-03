# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""Multi-language repository fixture for testing cross-language processing."""

# Python code for Home Assistant integration
PYTHON_CODE = """
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

class SmartLight(Entity):
    '''Smart light entity.'''

    def __init__(self, name: str):
        self._name = name
        self._is_on = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self) -> None:
        self._is_on = True
        self.async_schedule_update_ha_state()
"""

# TypeScript code for Home Assistant frontend
TYPESCRIPT_CODE = """
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';

  render() {
    return html`<button>${this.label}</button>`;
  }
}
"""

# PHP code for legacy systems
PHP_CODE = """<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }
}
"""

# YAML automation configuration
YAML_AUTOMATION = """# Home Assistant automation configurations
automation:
  - alias: "Turn off lights"
    trigger:
      platform: time
      at: "23:00:00"
    action:
      service: light.turn_off
      target:
        area_id: living_room

  - alias: "Climate control"
    trigger:
      platform: state
      entity_id: sensor.temperature
      for:
        minutes: 5
    condition:
      condition: numeric_state
      entity_id: sensor.temperature
      above: 22
    action:
      service: climate.set_hvac_mode
      target:
        entity_id: climate.living_room
      data:
        hvac_mode: "cool"
"""

# YAML script configuration
YAML_SCRIPT = """# Home Assistant script configurations
script:
  hello_world:
    alias: "Hello World"
    description: "Say hello world"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.living_room
      - service: persistent_notification.create
        data:
          message: "Hello, World!"

  morning_routine:
    alias: "Morning Routine"
    description: "Start morning routine"
    sequence:
      - service: light.turn_on
        target:
          area_id: bedroom
      - service: light.turn_on
        target:
          area_id: bathroom
      - service: media_player.play_media
        target:
          entity_id: media_player.bedroom_speaker
        data:
          media_content_id: "radio://simple"
          media_content_type: "music"
      - service: notification.notify
        data:
          message: "Good morning! Time to start your day."
"""

# YAML sensor configuration
YAML_SENSOR = """# Home Assistant sensor configurations
sensor:
  - platform: template
    sensors:
      room_temperature:
        value_template: "{{ state('sensor.bedroom_temperature') }}"
        unit_of_measurement: "°C"
        icon: "mdi:thermometer"

      room_humidity:
        value_template: "{{ state('sensor.bedroom_humidity') }}"
        unit_of_measurement: "%"
        icon: "mdi:water-percent"

  - platform: command
    name: "System Load"
    command: "uptime -p"
    unit_of_measurement: "up"
    value_template: >
      {{ value | regex_replace('up (\\d+)', '1') | int }}
    scan_interval: 60

  - platform: rest
    name: "API Status"
    resource: "http://example.com/api/status"
    value_template: "{{ value_json.status }}"
    headers:
      Authorization: "Bearer token"
    sensor:
      - name: "Response Time"
        value_template: "{{ value_json.response_time }}"
        unit_of_measurement: "ms"
"""

# YAML with Jinja templates
YAML_JINJA = """# Home Assistant templates with Jinja
automation:
  - alias: "Dynamic notification"
    trigger:
      platform: state
      entity_id: sensor.system_load
    condition:
      condition: template
      value_template: "{{ state_attr('sensor.system_load', 'load_1m') | float > 0.8 }}"
    action:
      - service: persistent_notification.create
        data:
          title: "High Load Alert"
          message: >
            System load is {{ state_attr('sensor.system_load', 'load_1m') | round(2) }}.
            This is above the threshold of 0.8.
            {{ now() | strftime('%Y-%m-%d %H:%M:%S') }}

script:
  notify_when_offline:
    alias: "Notify when device offline"
    sequence:
      - service: persistent_notification.create
        data:
          message: >
            Device {{ device_name }} is offline.
            Last seen: {{ device_last_seen | default('Unknown') }}.

sensor:
  - platform: template
    sensors:
      device_status:
        value_template: >
          {% if is_state('device_tracker.phone', 'home') %}
            Online
          {% else %}
            Offline
          {% endif %}
        icon_template: >
          {% if is_state('device_tracker.phone', 'home') %}
            mdi:check-circle
          {% else %}
            mdi:close-circle
          {% endif %}
"""

# Python manifest for HA integration
PYTHON_MANIFEST = """{
    "name": "Test Component",
    "version": "1.0.0",
    "homeassistant": "2024.1.0",
    "codeowners": ["@test"],
    "requirements": []
}
"""

# TypeScript manifest for HA integration
TYPESCRIPT_MANIFEST = """{
    "name": "Test Frontend Integration",
    "version": "1.0.0",
    "homeassistant": "2024.1.0",
    "codeowners": ["@test"],
    "requirements": []
}
"""

# PHP composer.json
PHP_COMPOSER = """{
    "name": "app/services",
    "type": "library",
    "autoload": {
        "psr-4": {
            "App\\\\": "src/"
        }
    },
    "require": {
        "php": "^8.0"
    }
}
"""

# Python manifest for filesystem
PYTHON_FILESYSTEM_MANIFEST = """{
    "name": "Python Test Repo",
    "version": "1.0.0"
}
"""

# TypeScript package.json
TYPESCRIPT_PACKAGE_JSON = """{
    "name": "test-typescript-repo",
    "version": "1.0.0",
    "type": "module",
    "main": "index.js",
    "scripts": {
        "test": "echo \\"Error: no test specified\\" && exit 1"
    },
    "dependencies": {
        "lit": "^3.0.0"
    }
}
"""
