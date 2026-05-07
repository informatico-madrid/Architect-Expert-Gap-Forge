# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Merger scripts for combining model weights and adapters.

This module contains scripts for merging LoRA adapters, combining model shards,
and other weight manipulation operations.

Scripts:
    - stage1: check_alignment.py, clean_dna.py, dna_fix_v2.py, dna_strict.py,
              final_ignition.py, merge_shards.py, repair_dna.py, repair_triple_dna.py,
              shotgun_dna.py
    - stage2: analisis_avanzado.py, diagnostico.py, fusionar_final.py,
              repara_stage2.py, guardar_tokenizador.py
"""

from __future__ import annotations

# Stage 1 scripts
from src.merger.check_alignment import check_alignment
from src.merger.clean_dna import clean_dna
from src.merger.dna_fix_v2 import fix_dna as dna_fix_v2
from src.merger.dna_strict import merge_strict as dna_strict
from src.merger.final_ignition import final_ignition
from src.merger.merge_shards import merge_shards
from src.merger.repair_dna import repair_dna
from src.merger.repair_triple_dna import repair_triple_dna
from src.merger.shotgun_dna import shotgun_merge as shotgun_dna

# Stage 2 scripts
from src.merger.analisis_avanzado import advanced_analysis as analisis_avanzado
from src.merger.diagnostico import diagnostico
from src.merger.fusionar_final import fusionar_final
from src.merger.repara_stage2 import repara_stage2
from src.merger.guardar_tokenizador import guardar_tokenizador

__all__ = [
    # Stage 1
    "check_alignment",
    "clean_dna",
    "dna_fix_v2",
    "dna_strict",
    "final_ignition",
    "merge_shards",
    "repair_dna",
    "repair_triple_dna",
    "shotgun_dna",
    # Stage 2
    "analisis_avanzado",
    "diagnostico",
    "fusionar_final",
    "repara_stage2",
    "guardar_tokenizador",
]

__version__ = "0.1.0"
