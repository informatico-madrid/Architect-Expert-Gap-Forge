// Sample Lit component with i18n and service calls for integration testing

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

// Home Assistant dialog component
@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';
  @state() private _loading = false;

  // i18n keys for localization
  private _confirmText = this.localize('ui.dialog.confirm');
  private _cancelText = this.hass.localize('ui.dialog.cancel');
  private _templateKey = this.localize(`ui.card.actions.${this._action}`);

  private _action = 'close';

  // Service call
  private async _closeDialog() {
    this.hass.callService('dialog', 'close', {
      entity_id: 'dialog.home_assistant'
    });
  }

  private async _confirmAction() {
    await this.hass.callService('homeassistant', 'turn_off', {
      entity_id: 'light.living_room'
    });
  }

  protected render() {
    return html`
      <div class="dialog">
        <h2>${this.dialogTitle}</h2>
        <button @click=${this._closeDialog}>${this._cancelText}</button>
        <button @click=${this._confirmAction}>${this._confirmText}</button>
      </div>
    `;
  }
}

// Another component using context._hass pattern
@customElement('bubble-card')
export class BubbleCard extends HTMLElement {
  public static get properties() {
    return {
      _hass: { type: Object },
      cardTitle: { type: String },
    };
  }

  private _hass: any;

  connectedCallback() {
    this.context._hass.callService('climate', 'set_temperature', {
      entity_id: 'climate.living_room',
      temperature: 22
    });
  }
}