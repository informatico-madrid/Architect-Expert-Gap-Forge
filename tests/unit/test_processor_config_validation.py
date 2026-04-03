# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import sys
import subprocess
import tempfile
import os

PY = sys.executable

# Minimal config for testing - no external file dependencies
MINIMAL_CONFIG = """
category: test
mode: static
module_discovery_strategy: directory
extensions:
  - ".py"
ignore_patterns:
  - ".git"
  - "__pycache__"
static_repos: []
min_stars: 0
limit: 0
base_dir: .
raw_subdir: data/raw
output_subdir: data/output
output_category: test
on_parse_error: skip
"""


def run_cli_with_config(config_content: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "test_config.yaml")
        with open(config_path, "w") as f:
            f.write(config_content)

        raw_dir = os.path.join(tmpdir, "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)

        output_dir = os.path.join(tmpdir, "data", "output")
        os.makedirs(output_dir, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONPATH"] = f"/mnt/bunker_data/ai/data_factory:{env.get('PYTHONPATH', '')}"

        return subprocess.run(
            [PY, "-m", "src.discovery.processor_cli", "--config", config_path],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )


def test_processor_cli_homeassistant_should_succeed_but_fails():
    """Test TDD: CLI procesa repositorios vacíos correctamente.
    Usamos un config minimal para evitar dependencias de archivos externos.
    """
    res = run_cli_with_config(MINIMAL_CONFIG)
    assert res.returncode == 0, f"CLI exited {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


def test_processor_cli_php_hexagonal_should_succeed_but_fails():
    """Test TDD: CLI procesa repositorios vacíos correctamente.
    Usamos un config minimal para evitar dependencias de archivos externos.
    """
    res = run_cli_with_config(MINIMAL_CONFIG)
    assert res.returncode == 0, f"CLI exited {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
