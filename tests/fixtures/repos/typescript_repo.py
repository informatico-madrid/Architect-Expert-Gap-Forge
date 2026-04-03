# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""TypeScript repository fixture for testing TypeScript processing."""

TYPESCRIPT_COMPONENT = """import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';

  render() {
    return html`<button>${this.label}</button>`;
  }
}
"""

TYPESCRIPT_COMPONENT_WITH_IMPORTS = """import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { someFunction } from './utils.js';

@customElement('ha-custom-card')
export class HaCustomCard extends LitElement {
  @property({ type: String }) private title = 'Title';
  @property({ type: Number }) private count = 0;

  render() {
    return html`
      <div class="card">
        <h2>${this.title}</h2>
        <p>Count: ${this.count}</p>
        <button @click=${this.handleClick}>Click</button>
      </div>
    `;
  }

  private handleClick() {
    this.count++;
    this.requestUpdate();
  }
}
"""

TYPESCRIPT_UTIL = """export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatTime(time: number): string {
  return new Date(time).toLocaleTimeString();
}
"""

TYPESCRIPT_MANIFEST = """{
  "name": "Test TypeScript Integration",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "lit": "^3.0.0"
  }
}
"""

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
