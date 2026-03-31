# Quickstart — Stage 1 (Discovery)

These quick commands demonstrate how to run the existing scripts with the new `profile` and `on_parse_error` settings.

## Run discovery (dry-run)

```bash
# Preferir el modo módulo para evitar problemas de import
python -m src.discovery.ingestor --config configs/stage_1_discovery/examples/homeassistant.yaml --dry-run
```

## Run processor with profile (default parse policy: abort)

```bash
# El "processor" está expuesto como un conjunto de módulos y una CLI.
# Use el módulo CLI `processor_cli` (ejecutar con `-m` para garantizar imports correctos):
python -m src.discovery.processor_cli --config configs/stage_1_discovery/examples/homeassistant.yaml

# Para el perfil PHP legacy use el ejemplo correspondiente:
python -m src.discovery.processor_cli --config configs/stage_1_discovery/examples/php_hexagonal.yaml
```

Available profile examples: `homeassistant.yaml`, `multi_legacy.yaml` and `php_hexagonal.yaml` in `configs/stage_1_discovery/examples/`.

Notes on configuration:

- Ensure your profile YAML provides the processor-required fields (at minimum): `base_dir`, `raw_subdir`, `output_subdir`, and `category`.
- `on_parse_error` can be set in the profile under the `extractor` block (PHP) or top-level for other profiles. Valid values: `abort`, `skip`, `mark_and_continue`, `fallback`.

Example override (inside the profile YAML):

```yaml
# For Python-based profiles (homeassistant) set at top level
on_parse_error: abort

# For PHP-based profiles inside the extractor block
extractor:
	on_parse_error: skip
```

## Developer flow (run tests and checks)

```bash
# activate venv
source .venv/bin/activate

# run unit tests
pytest tests/unit -q

# run integration tests
pytest tests/integration -q

# run formatting and header check
ruff format .
python scripts/check_headers.py --check
```

## Notes

- The `processor` uses the adapter selected by the `profile` setting in the config YAML, which is passed to `get_adapter(profile)`.
- Do not push commits automatically; follow repository governance for reviews and commit messages.
