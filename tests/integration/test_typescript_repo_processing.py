# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration Test for TypeScript Repo Processing
=================================================

Verifies TypeScript repo (.ts/.tsx files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT.

Requirements: FR-5, AC-5.1 to AC-5.5
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestTypeScriptRepoProcessing:
    """Integration tests for TypeScript repo processing."""

    def test_typescript_module_detection(self, tmp_path: Path) -> None:
        """Test that TypeScript modules are detected and processed.

        AC-5.1: TypeScript files should be processed with TypeScript adapter.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory
        component = owner_dir / "components" / "button-card"
        component.mkdir(parents=True)

        # Create TypeScript file with decorators
        (component / "button-card.ts").write_text("""
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';
  @state() private _count = 0;

  private handleClick() {
    this._count++;
  }

  render() {
    return html`
      <button @click=${this.handleClick}>${this.label} (${this._count})</button>
    `;
  }

  static styles = css`
    button {
      padding: 8px 16px;
      background: #0078d4;
      color: white;
    }
  `;
}
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should emit MODULE_BLUEPRINT"
        )

        # Verify TypeScript-specific metadata
        blueprint = blueprint_files[0].read_text()
        assert 'customElement' in blueprint, (
            "MODULE_BLUEPRINT should capture @customElement decorator"
        )
        assert 'property' in blueprint, (
            "MODULE_BLUEPRINT should capture @property decorator"
        )

    def test_typescript_decorators_extraction(self, tmp_path: Path) -> None:
        """Test that TypeScript decorators are extracted into MODULE_BLUEPRINT.

        AC-5.2: Decorators (@customElement, @property, @state) should be extracted.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory
        component = owner_dir / "components" / "dialog"
        component.mkdir(parents=True)

        # Create TypeScript file with multiple decorators
        (component / "dialog.ts").write_text("""
import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';
  @state() private _loading = false;
  @query('.dialog-content') private content?: HTMLElement;

  private async _closeDialog() {
    this.open = false;
  }

  protected render() {
    return html`
      <div class="dialog">
        <h2>${this.dialogTitle}</h2>
        <div class="dialog-content">${this.content?.innerHTML}</div>
        <button @click=${this._closeDialog}>Close</button>
      </div>
    `;
  }
}
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should emit MODULE_BLUEPRINT"
        )

        # Verify all decorator patterns are captured
        blueprint = blueprint_files[0].read_text()
        assert 'customElement' in blueprint, (
            "MODULE_BLUEPRINT should capture @customElement"
        )
        assert 'property' in blueprint, (
            "MODULE_BLUEPRINT should capture @property"
        )
        assert 'state' in blueprint, (
            "MODULE_BLUEPRINT should capture @state"
        )
        assert 'query' in blueprint, (
            "MODULE_BLUEPRINT should capture @query"
        )

    def test_typescript_imports_extraction(self, tmp_path: Path) -> None:
        """Test that TypeScript imports are extracted into MODULE_BLUEPRINT.

        AC-5.3: Import statements should be extracted as dependencies.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory
        component = owner_dir / "components" / "card"
        component.mkdir(parents=True)

        # Create TypeScript file with imports
        (component / "card.ts").write_text("""
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { classMap } from 'lit/directives/class-map.js';
import { styleMap } from 'lit/directives/style-map.js';

@customElement('ha-card')
export class HaCard extends LitElement {
  @property({ type: String }) private title = '';
  @property({ type: Boolean }) private highlighted = false;

  render() {
    return html`
      <div class="card ${classMap({ highlighted: this.highlighted })}">
        <h2>${this.title}</h2>
        <slot></slot>
      </div>
    `;
  }

  static styles = css`
    .card {
      padding: 16px;
    }
  `;
}
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT with dependencies
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should emit MODULE_BLUEPRINT"
        )

        # Verify imports are captured as dependencies
        blueprint = blueprint_files[0].read_text()
        assert 'lit' in blueprint, (
            "MODULE_BLUEPRINT should capture 'lit' import"
        )
        assert 'lit/decorators' in blueprint or 'lit/decorators.js' in blueprint, (
            "MODULE_BLUEPRINT should capture lit decorators import"
        )

    def test_typescript_typescript_only_no_type1(self, tmp_path: Path) -> None:
        """Test that TypeScript files without tests generate TYPE 3 (LOGIC_ONLY).

        AC-5.4: TypeScript files without test files should not generate TYPE 1.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory
        component = owner_dir / "utils" / "format"
        component.mkdir(parents=True)

        # Create large TypeScript file (>= 1000 chars)
        (component / "format.ts").write_text("""
export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(amount);
}

export function formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}

export function formatPercentage(value: number, precision: number = 2): string {
    return (value * 100).toFixed(precision) + '%';
}

export function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    const parts: string[] = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    parts.push(`${secs}s`);

    return parts.join(' ');
}

export function validateInput(input: string): boolean {
    if (!input || input.trim() === '') {
        return false;
    }
    return true;
}

export function sanitizeInput(input: string): string {
    return input.trim().replace(/[<>]/g, '');
}

export function truncateString(str: string, maxLength: number): string {
    if (str.length <= maxLength) {
        return str;
    }
    return str.substring(0, maxLength) + '...';
}
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should NOT have FUNCTIONAL_UNIT (no test files)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) == 0, (
            "TypeScript files without tests should not generate TYPE 1"
        )

        # Should have LOGIC_ONLY (TYPE 3) for large file
        logic_only_files = [
            f for f in bundle_files
            if 'LOGIC_ONLY' in f.read_text()
        ]

        assert len(logic_only_files) > 0, (
            "Large TypeScript file should generate TYPE 3 LOGIC_ONLY"
        )

        # Should have MODULE_BLUEPRINT (TYPE 4)
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should always emit MODULE_BLUEPRINT"
        )

    def test_typescript_adapter_selection(self, tmp_path: Path) -> None:
        """Test that TypeScript files use TypeScriptAdapter, not repo profile.

        AC-5.5: Per-file adapter selection should use .ts/.tsx extension.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory
        component = owner_dir / "components" / "card"
        component.mkdir(parents=True)

        # Create TypeScript file
        (component / "card.ts").write_text("""
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-card')
export class HaCard extends LitElement {
  @property({ type: String }) private title = '';

  render() {
    return html`<div>${this.title}</div>`;
  }
}
""".strip())

        # Use filesystem profile (not typescript)
        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",  # Not typescript profile
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should still process TypeScript files despite profile mismatch
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should be processed regardless of repo profile"
        )
