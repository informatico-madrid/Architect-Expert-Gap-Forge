# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""Minimal Python test fixtures for adapter selection tests."""

PYTHON_CODE = """
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b

def calculate_total(items: list) -> float:
    '''Calculate total price from items.'''
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
"""

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

YAML_CODE = """# Home Assistant automation
automation:
  - alias: "Light Control"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.toggle
"""
