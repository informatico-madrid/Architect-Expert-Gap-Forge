# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import sys
import subprocess


PY = sys.executable


def run_cli(config_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-m", "src.discovery.processor_cli", "--config", config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_processor_cli_homeassistant_should_succeed_but_fails():
    """Test TDD: esperamos que el CLI corra correctamente.
    Actualmente falla por ValidationError (falta `output_subdir`), por tanto el test quedará en rojo.
    """
    res = run_cli("configs/stage_1_discovery/examples/homeassistant.yaml")
    assert res.returncode == 0, f"CLI exited {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


def test_processor_cli_php_hexagonal_should_succeed_but_fails():
    """Test TDD: esperamos que el CLI corra correctamente.
    Actualmente falla por ValidationError (faltan `category`, `raw_subdir`, `output_subdir`).
    """
    res = run_cli("configs/stage_1_discovery/examples/php_hexagonal.yaml")
    assert res.returncode == 0, f"CLI exited {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
