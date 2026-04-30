#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

from llmcompressor.modifiers.quantization import QuantizationModifier
from llmcompressor import oneshot  # <--- EL CAMBIO ESTÁ AQUÍ
from transformers import AutoModelForCausalLM, AutoTokenizer

modelo_origen = "/models_dir/qwen3-30b-a3b-thinking-fase3-final"
modelo_destino = "/models_dir/qwen3-30b-a3b-thinking-fase3-FP8"

print("1. Cargando el modelo fusionado con Offload a CPU por seguridad...")
tokenizer = AutoTokenizer.from_pretrained(modelo_origen)

# EL SALVAVIDAS ESTÁ AQUÍ:
limites_memoria = {
    0: "28GB",  # Límite GPU 1
    1: "28GB",  # Límite GPU 2
    "cpu": "120GB",  # Límite RAM del sistema
}

model = AutoModelForCausalLM.from_pretrained(
    modelo_origen, device_map="auto", torch_dtype="auto", max_memory=limites_memoria
)

print("2. Configurando esquema FP8 DYNAMIC para vLLM...")
modifier = QuantizationModifier(
    targets="Linear", scheme="FP8_DYNAMIC", ignore=["lm_head"]
)

print("3. Aplicando compresión a 8-bits (Puede tardar un poco más por usar RAM)...")
oneshot(model=model, recipe=modifier)

print("4. Guardando el nuevo modelo FP8...")
model.save_pretrained(modelo_destino)
tokenizer.save_pretrained(modelo_destino)

print(f"¡Éxito! El modelo FP8 está listo en {modelo_destino}")
