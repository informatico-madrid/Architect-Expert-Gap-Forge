# data_factory Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-08

## Active Technologies
- Bash 5.x (GNU/Linux), Python 3.x (para scripts auxiliares ya existentes) + git 2.43.0 (disponible en sistema), `merge_state.py` (ya existente), `count_tasks.py` (ya existente) (002-ralph-worktree)
- `.ralph/state.json` (4 campos nuevos), `.gitignore` (1 entrada nueva), `.worktrees/` (directorios temporales) (002-ralph-worktree)
- Python 3.11 + asyncio, openai (AsyncOpenAI), pydantic, pytest, tqdm, yaml (003-monolith-modules)
- Archivos JSONL en `data/synthetic/` y `data/audit/`; configs YAML en `configs/` (003-monolith-modules)
- Python 3.11+ + re (stdlib), pathlib (stdlib), dataclasses (stdlib), pydantic (existente en proyecto) (004-php-legacy-driver)
- Filesystem local — bundles `.txt` en `data/outputs/`, repositorios fuente en `data/raw/multi_legacy/` (004-php-legacy-driver)
- Python 3.11 + Python standard library (concurrent.futures, dataclasses, typing, pathlib, re, hashlib), `pytest` for tests; optional local vLLM/judge for Validation Judge (sampling). (004-php-legacy-driver)
- Local filesystem — `data/raw/`, `data/outputs/*_bundles/`, `needs_manual_review.json`, bundle cache for preambles. (004-php-legacy-driver)

- Python 3.12 (existing repo uses 3.12+) + PyYAML, pydantic, requests, pytest, ruff. Optional: `tree-sitter` (for future adapters). (001-stage1-discovery)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12 (existing repo uses 3.12+): Follow standard conventions

## Recent Changes
- 004-php-legacy-driver: Added Python 3.11 + Python standard library (concurrent.futures, dataclasses, typing, pathlib, re, hashlib), `pytest` for tests; optional local vLLM/judge for Validation Judge (sampling).
- 004-php-legacy-driver: Added Python 3.11+ + re (stdlib), pathlib (stdlib), dataclasses (stdlib), pydantic (existente en proyecto)
- 003-monolith-modules: Added Python 3.11 + asyncio, openai (AsyncOpenAI), pydantic, pytest, tqdm, yaml


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
