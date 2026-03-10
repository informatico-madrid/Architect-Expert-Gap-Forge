#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Blackwell Dataset Auditor V2 - Fragment Aware
---------------------------------------------
Distingue entre Errores Críticos (Syntax Error) y Advertencias de Contexto.
"""

import json
import ast
import re
import sys
from pathlib import Path
from collections import Counter

# Path to the dataset to audit (update before use)
DATASET_FILE = Path("data/synthetic/your_dataset.jsonl")


def check_python_syntax(code):
    try:
        ast.parse(code)
        return True, "Valid Python"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"


def audit_sample(line_num, data):
    critical_errors = []
    warnings = []

    # 1. Estructura Básica
    if "conversation" not in data or not data["conversation"]:
        return ["❌ JSON corrupto"], []

    last_msg = data["conversation"][-1]["content"]

    # 2. Verificar Thinking
    if "<think>" not in last_msg:
        warnings.append("⚠️ Falta <think>")

    # 3. Extraer Tool Call
    match = re.search(r"<tool_call>(.*?)</tool_call>", last_msg, re.DOTALL)
    if not match:
        match = re.search(r"<tool_call>(.*)", last_msg, re.DOTALL)

    if not match:
        critical_errors.append("❌ No se encontró <tool_call>")
        return critical_errors, warnings

    try:
        tool_json_str = match.group(1).strip()
        tool_json_str = tool_json_str.replace("```json", "").replace("```", "")
        # Hack de balanceo de llaves para JSON cortados
        if tool_json_str.count("{") > tool_json_str.count("}"):
            tool_json_str += "}"

        tool_data = json.loads(tool_json_str)

        filename = tool_data["arguments"]["path"]
        content = tool_data["arguments"]["content"]

        # 4. Auditoría Semántica
        if filename.endswith(".py"):
            # A. Validar Sintaxis Python (CRÍTICO)
            is_valid_py, msg = check_python_syntax(content)
            if not is_valid_py:
                critical_errors.append(f"❌ Python Roto: {msg}")

            # B. Buscar Markdown intruso (CRÍTICO)
            if re.search(r"\|\s*---\s*\|", content):
                critical_errors.append(f"❌ ALERTA: Tabla Markdown en Python")
            if "```" in content:  # Fences dentro de fences
                warnings.append(f"⚠️ Posibles fences de markdown en código")

            # C. Verificar Tests (ADVERTENCIA RELAJADA)
            if "test_" in filename:
                # Si es un fragmento (empieza con def o @), no exigimos imports
                if not (
                    content.strip().startswith("def ")
                    or content.strip().startswith("@")
                    or content.strip().startswith("class ")
                ):
                    if "import pytest" not in content:
                        warnings.append(f"ℹ️ Test sin imports (¿Fragmento?)")

        elif filename.endswith(".md"):
            if len(content) < 50:
                warnings.append(f"⚠️ README corto")

    except json.JSONDecodeError:
        critical_errors.append("❌ JSON del tool_call inválido")
    except Exception as e:
        critical_errors.append(f"❌ Error desconocido: {str(e)}")

    return critical_errors, warnings


def main():
    if not DATASET_FILE.exists():
        print("No dataset found.")
        return

    print(f"🔍 Auditoría Inteligente V2: {DATASET_FILE}")

    stats = {
        "total": 0,
        "perfect": 0,
        "valid_fragments": 0,  # Técnicamente válidos pero con warnings (sin imports)
        "critical_failures": 0,
    }

    with open(DATASET_FILE, "r") as f:
        for i, line in enumerate(f):
            stats["total"] += 1
            try:
                data = json.loads(line)
                errors, warns = audit_sample(i, data)

                if errors:
                    stats["critical_failures"] += 1
                    # Mostrar solo errores críticos
                    print(f"[Línea {i + 1}] ❌ {errors}")
                elif warns:
                    stats["valid_fragments"] += 1
                else:
                    stats["perfect"] += 1

            except:
                pass

    print("\n" + "=" * 40)
    print(f"📊 INFORME DE CALIDAD REAL")
    print("=" * 40)
    print(f"Total Procesado:      {stats['total']}")
    print(f"✅ Perfectos (Files): {stats['perfect']}")
    print(
        f"🆗 Fragmentos Válidos: {stats['valid_fragments']} (Código válido, faltan imports)"
    )
    print(f"❌ FALLOS CRÍTICOS:   {stats['critical_failures']}")
    print("-" * 40)

    # El Yield Real es (Perfectos + Fragmentos) / Total
    real_yield = ((stats["perfect"] + stats["valid_fragments"]) / stats["total"]) * 100
    print(f"🚀 YIELD REAL (Aptos para Train): {real_yield:.2f}%")
    print("=" * 40)


if __name__ == "__main__":
    main()
