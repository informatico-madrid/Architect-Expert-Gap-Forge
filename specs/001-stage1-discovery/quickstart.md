# Quickstart — Stage 1 (Discovery)

These quick commands demonstrate how to run the existing scripts with the new `profile` and `on_parse_error` settings.

## Run discovery (dry-run)

```bash
python src/discovery/ingestor.py --config configs/stage_1_discovery/examples/homeassistant.yaml --dry-run
```

## Run processor with profile (default parse policy: abort)

```bash
python src/discovery/processor.py --config configs/stage_1_discovery/examples/homeassistant.yaml
```

Available profile examples: `homeassistant.yaml` and `php_hexagonal.yaml` in `configs/stage_1_discovery/examples/`.

To override the `on_parse_error` at runtime, edit the profile example yaml under `configs/stage_1_discovery/examples/` and set:

```yaml
on_parse_error: skip  # or 'abort' or 'fallback'
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
