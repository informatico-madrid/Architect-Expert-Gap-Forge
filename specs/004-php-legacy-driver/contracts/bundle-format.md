# Contract: PHP Legacy Bundle Format

**Feature**: 004-php-legacy-driver | **Date**: 2026-03-12

## Overview

Contrato del formato de bundle `.txt` generado por el PHPLegacyDriver para consumo en Stage 2 (`src/factory/fragment_extractor.py` → `parse_bundle()` + `get_v2_fragments()`). Extiende el formato existente con secciones PHP-específicas.

## Bundle Structure

```text
[ARCH_HEADER]
MODULE: <platform>/<directory_path>
REPO_PREFIX: <repository_name>
FILE_ROLE: source
FRAGMENT_TYPE: FUNCTIONAL_UNIT
LANGUAGE: php
PLATFORM: <detected_platform>
LOCAL_IMPORTS: <include/require list, comma-separated>
DEPENDENCIES: <external dependencies detected>
NEIGHBORS: <adjacent files from IncludeGraph>
LEGACY_ACTION: <LEGACY_ACTION enum value>
IMPLICIT_DEPS: ['$var1', '$var2']
PREAMBLE_REF: <64-char sha256 hex — omitted for bootstrap fragments>

[MODULE_MAP]
<file_path_1>: <one-line description>
<file_path_2>: <one-line description>
...

[LEGACY_SIGNATURES]
CATEGORY: <SIGNATURE_CATEGORY category>
PATTERN: <pattern_name> — <matched_text>
SEVERITY: <critical|warning|info>
MODERN_HINT: <suggested modern equivalent>
---
CATEGORY: <next signature>
...

[INCLUDE_GRAPH]
<source_file> --<include_type>--> <target_file>
<source_file> --<include_type>--> <target_file>
...

--- FILE: <fragment_name> (<fragment_type>) ---
<raw PHP code of the fragment>

--- FILE: <next_fragment_name> (<fragment_type>) ---
<raw PHP code>

```

## Field Specifications

### [ARCH_HEADER] Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| MODULE | Yes | `<platform>/<path>` | `oscommerce/admin/categories` |
| REPO_PREFIX | Yes | String | `oscommerce-2.3.4` |
| FILE_ROLE | Yes | `"source"` | `source` |
| FRAGMENT_TYPE | Yes | Enum | `FUNCTIONAL_UNIT` |
| LANGUAGE | Yes | `"php"` | `php` |
| PLATFORM | Yes | Platform name | `oscommerce` |
| LOCAL_IMPORTS | Yes | Comma-separated | `application_top.php, languages.php` |
| DEPENDENCIES | Yes | Comma-separated | `tep_db_query, tep_redirect` |
| NEIGHBORS | Yes | Comma-separated | `orders.php, customers.php` |
| LEGACY_ACTION | Yes | LEGACY_ACTION enum | `DB_ACCESS` |
| IMPLICIT_DEPS | No | JSON-list string (omit if empty) | `['$db', '$languages_id']` |
| PREAMBLE_REF | No | 64-char lowercase hex (SHA-256) | `3a7f9c2e1b5d4f8a...` |

**New fields** (LANGUAGE, PLATFORM, LEGACY_ACTION) se añaden al ARCH_HEADER como campos obligatorios. IMPLICIT_DEPS y PREAMBLE_REF son opcionales — se emiten solo cuando tienen valor; `parse_bundle()` los captura automáticamente mediante el loop `key.partition(":")` existente. PREAMBLE_REF es el hash SHA-256 del fragmento bootstrap del mismo archivo fuente (R-011); Stage 2 lo usa en `resolve_preamble_ref()` para inyectar el contexto de preámbulo como `${preamble}` en el prompt del Teacher (FR-022).

### [LEGACY_SIGNATURES] Section

**New section** — no existe en bundles Python. Capturada por el generic section parser.

Cada signature se separa por `---` y contiene:
- `CATEGORY`: Una de las 6 categorías SIGNATURE_CATEGORY (`PERSISTENCE_SMELL`, `STATE_POLLUTION`, `MODULE_LINK_SMELL`, `SECURITY_VULN`, `CONSTANT_POLLUTION`, `MODERN_HYBRID`)
- `PATTERN`: `<nombre_patrón> — <texto_matcheado>`
- `SEVERITY`: `critical` | `warning` | `info`
- `MODERN_HINT`: Equivalente moderno sugerido

### [INCLUDE_GRAPH] Section

**New section**. Representa el grafo de dependencias include/require como lista de aristas.

Formato por línea: `<source> --<type>--> <target>`

### Fragment Delimiter

```text
--- FILE: <name> (<type>) ---
<code>
```

Cada fragmento incluye su nombre y tipo entre paréntesis. Se usa el mismo delimitador `--- FILE:` que el parser existente de Stage 2 (`parse_bundle()` en `fragment_extractor.py`) para compatibilidad directa.

## Compatibility Notes

1. `parse_bundle()` usa regex `\[ARCH_HEADER\](.*?)(?=\n\[|\n---|$)` — las nuevas secciones `[LEGACY_SIGNATURES]` y `[INCLUDE_GRAPH]` correctamente terminan el bloque ARCH_HEADER
2. Campos nuevos en ARCH_HEADER (LANGUAGE, PLATFORM) se capturan automáticamente por el loop `key.partition(":")` existente
3. Secciones nuevas requieren el generic section parser (R-005 en research.md)
4. Delimitador `--- FILE:` es el mismo que usa `parse_bundle()` — compatibilidad directa con bundles Python existentes

## Consumers

| Consumer | Fields Used | New Fields Needed |
|----------|------------|-------------------|
| `parse_bundle()` | ARCH_HEADER fields | LANGUAGE, PLATFORM (auto-captured) |
| `get_v2_fragments()` | FRAGMENT_TYPE, extension | Extension Mapper routing by LANGUAGE |
| `build_system_with_blueprint()` | Full bundle text | LEGACY_SIGNATURES via generic section parser |
| `_prompt()` | Profile-based key lookup | `php_legacy` namespace in taxonomy |
