# Profile adapters mapping — especificación (v1)

Propósito: describir el formato de mapeo entre `profile` y el `adapter` a usar. Este fichero es **especificación**; no crea ni modifica `configs/` ni implementaciones.

Schema recomendado (v1):

```yaml
# profile_adapters.yaml (spec)
profiles:
  homeassistant:
    adapter: python_ast
    notes: "Recommended for HA profiles; builtin python ast adapter."
  php_hexagonal:
    adapter: php_native
    notes: "Use a PHP-native parser adapter."
  legacy_minimal:
    adapter: generic_regex
    notes: "Minimal best-effort regex extractor for legacy repos."
```

Resolución (get_adapter) — contract (spec-only):
- La fábrica (`get_adapter(profile: str)`) resolverá en el siguiente orden:
  1. Si existe un `profile_adapters.yaml` mantenido por operaciones, usar su mapeo.
  2. Si no existe, usar la tabla interna v1 (especificada abajo).
  3. Si no se encuentra adaptador, lanzar `RuntimeError` con mensaje claro.

Tabla interna recomendada (v1):
- `homeassistant` → `python_ast`
- `php_hexagonal` → `php_native`
- `default` → `python_ast` (si el perfil no se reconoce)

Identificadores canónicos (v1)
- `python_ast` — Python builtin `ast` adapter
- `tree_sitter` — tree-sitter multi-language adapter (requiere grammars)
- `php_native` — PHP parser adapter
- `generic_regex` — best-effort regex extractor (degraded)

Notas de gobernanza
- Cambios en esta especificación requieren justificar compatibilidad y pruebas.
- Cualquier adición de identificadores debe incluir la implementación del adapter y pruebas unitarias.
