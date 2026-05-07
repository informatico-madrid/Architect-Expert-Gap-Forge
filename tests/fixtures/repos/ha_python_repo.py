# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""Home Assistant Python repository fixture for testing.

This fixture creates a properly structured HA integration repository
that the RepoProcessor can successfully process.

Repository structure:
    owner/
        myrepo/
            __init__.py
            manifest.json
            component.py
            tests/
                test_component.py
"""


# Python component code
PYTHON_COMPONENT_CODE = """
"""

PYTHON_TEST_CODE = """
import module

def test_calculate_total():
    '''Test calculate_total function with various input scenarios.'''
    # Test with simple price list
    items = [{'price': 10.0}, {'price': 20.0}, {'cost': 30.0}]
    result = module.calculate_total(items)
    assert result == 60.0, f"Expected 60.0 but got {result}"

    # Test with empty list
    empty_result = module.calculate_total([])
    assert empty_result == 0.0, f"Expected 0.0 for empty list but got {empty_result}"

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100.0, 'cost': 50.0},
        {'cost': 200.0, 'price': 150.0}
    ]
    total = module.calculate_total(mixed_items)
    assert total == 250.0, f"Expected 250.0 but got {total}"

def test_apply_discount():
    '''Test apply_discount function with edge cases.'''
    # Test 10% discount
    total = 100.0
    result = module.apply_discount(total, 10)
    assert result == 90.0, f"Expected 90.0 but got {result}"

    # Test 0% discount (no discount)
    no_discount = module.apply_discount(100.0, 0)
    assert no_discount == 100.0, f"Expected 100.0 but got {no_discount}"

    # Test 100% discount (free)
    free_item = module.apply_discount(50.0, 100)
    assert free_item == 0.0, f"Expected 0.0 but got {free_item}"

def test_validate_input():
    '''Test validate_input function for proper validation.'''
    # Test positive numbers
    assert module.validate_input(100) == 100
    assert module.validate_input(0.5) == 0.5
    assert module.validate_input(0) == 0

    # Test negative should raise
    import pytest
    with pytest.raises(ValueError):
        module.validate_input(-1)

def test_process_items():
    '''Test process_items function with multiplier.'''
    items = [{'price': 10}, {'price': 20}]
    result = module.process_items(items, 2.0)
    assert len(result) == 2
    assert result[0]['price'] == 20.0
    assert result[1]['price'] == 40.0

    # Test with no multiplier (default)
    default_result = module.process_items(items)
    assert default_result[0]['price'] == 10.0
    assert default_result[1]['price'] == 20.0
"""

PYTHON_COMPONENT_CODE = """
DOMAIN = 'test_component'

def calculate_total(items):
    '''Calculate total price from list of items.'''
    total = 0.0
    for item in items:
        if 'price' in item:
            total += item['price']
        elif 'cost' in item:
            total += item['cost']
    return total

def apply_discount(total, discount_pct):
    '''Apply percentage discount to total.'''
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount must be between 0 and 100")
    return total * (1 - discount_pct / 100.0)

def validate_input(value):
    '''Validate numeric input.'''
    if not isinstance(value, (int, float)):
        raise TypeError("Value must be numeric")
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value

def process_items(items, multiplier=1.0):
    '''Process items with multiplier.'''
    if not isinstance(items, list):
        raise TypeError("Items must be a list")
    results = []
    for item in items:
        price = item.get('price', 0) or item.get('cost', 0)
        results.append({'price': price * multiplier})
    return results
"""

PYTHON_MANIFEST = """{
    "name": "Test Component",
    "version": "1.0.0",
    "domain": "test_component",
    "homeassistant": "2024.1.0"
}
"""

PYTHON_INIT = """
from . import component  # noqa: F401

DOMAIN = 'test_component'
"""

TYPESCRIPT_COMPONENT_CODE = """
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

TYPESCRIPT_TEST_CODE = """
import { expect } from '@open-wc/testing';
import { html } from 'lit';
import '../src/button-card.js';

describe('HaButtonCard', () => {
  it('renders label', async () => {
    const el = document.createElement('ha-button-card');
    el.label = 'Test Label';
    await el.updateComplete;

    const button = el.renderRoot.querySelector('button');
    expect(button).to.exist;
    expect(button.textContent).to.equal('Test Label');
  });

  it('renders default label', async () => {
    const el = document.createElement('ha-button-card');
    await el.updateComplete;

    const button = el.renderRoot.querySelector('button');
    expect(button).to.exist;
    expect(button.textContent).to.equal('Click me');
  });
});
"""

TYPESCRIPT_MANIFEST = """{
    "name": "Test Frontend Integration",
    "version": "1.0.0",
    "domain": "test_frontend",
    "homeassistant": "2024.1.0"
}
"""

TYPESCRIPT_INIT = """
export * from './button-card';
"""

PHP_COMPONENT_CODE = """<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }

    public function findUser(string $email): ?User {
        foreach ($this->users as $user) {
            if ($user->email === $email) {
                return $user;
            }
        }
        return null;
    }

    public function deleteUser(string $email): bool {
        $index = array_search($email, array_column($this->users, 'email'));
        if ($index !== false) {
            unset($this->users[$index]);
            return true;
        }
        return false;
    }
}
"""

PHP_MODEL_CODE = """<?php

namespace App\\Models;

class User {
    public string $name;
    public string $email;

    public function __construct(string $name, string $email) {
        $this->name = $name;
        $this->email = $email;
    }
}
"""

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

YAML_AUTOMATION_CODE = """# Home Assistant automation configurations
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

YAML_SCRIPT_CODE = """# Home Assistant script configurations
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

YAML_SENSOR_CODE = """# Home Assistant sensor configurations
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

YAML_JINJA_CODE = """# Home Assistant templates with Jinja
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
