#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
RESEARCH/DIAGNOSTIC SCRIPT — Experimental

Status: Research / diagnostic only — not production-ready.
Scope: Logical chunking of large Home Assistant modules and generation of
    multi-turn 'distilabel' conversations for downstream curation and
    NeMo/Curator workflows.
Usage: Run locally as a diagnostic tool. Requires a local OpenAI/vLLM-compatible
    API endpoint at http://localhost:8000/v1 and taxonomy files under
    configs/stage_2_factory/taxonomy/. Outputs are for human review only.

Notes:
- Experimental heuristics; outputs must be validated by humans before use.
- This script intentionally fails fast if taxonomy files are missing to
  increase visibility in test environments.
"""

import yaml
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from openai import OpenAI

# ============================================================================
# TOKEN-AWARE CONFIGURATION (LIMITS)
# ============================================================================
MAX_TRAINING_TOKENS = 4096
MAX_CONTEXT_TOKENS = 2500  # Leave room for reasoning and output code
TOKENS_PER_CHAR = 0.25  # Approximation: 1 token ≈ 4 characters

# Target file for local testing
TARGET_FILE = Path("data/raw/integration_hass-xiaomi-miot_alarm_control_panel.txt")


# ============================================================================
# 1. LOGICAL CHUNKING - NO CHARACTER SPLITS
# ============================================================================
def estimate_tokens(text: str) -> int:
    """Estimate tokens using approximation 1 token ≈ 4 characters."""
    return int(len(text) * TOKENS_PER_CHAR)


def split_code_logically(
    file_content: str, max_tokens: int = MAX_CONTEXT_TOKENS
) -> List[Dict[str, Any]]:
    """
    Split a file into logical chunks that preserve complete functions/classes.

    Example for alarm_control_panel.py (~527 lines) might produce:
    - Chunk A: Base structure, imports and async_setup_entry
    - Chunk B: MiotAlarmEntity class and state methods
    - Chunk C: Action methods (async_alarm_*)
    """
    lines = file_content.split("\n")

    # Detect header (lines before the first import)
    header_lines = []
    code_start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            code_start_idx = i
            break
        header_lines.append(line)

    header = "\n".join(header_lines)

    # Extract logical sections
    chunks = []

    # ---- CHUNK A: Imports + Setup Functions ----
    setup_end_idx = code_start_idx
    for i in range(code_start_idx, len(lines)):
        if lines[i].strip().startswith("class "):
            setup_end_idx = i
            break

    chunk_a_content = "\n".join(lines[code_start_idx:setup_end_idx])
    chunk_a_tokens = estimate_tokens(header + chunk_a_content)

    if chunk_a_tokens < max_tokens:
        chunks.append(
            {
                "id": "chunk_A",
                "title": "Estructura base, imports y async_setup_entry",
                "context": header + chunk_a_content,
                "instruction": "Implementa async_setup_entry para la integración",
                "tokens": chunk_a_tokens,
            }
        )

    # ---- CHUNK B: Class Definition + State Methods ----
    class_start_idx = setup_end_idx
    state_methods_end_idx = class_start_idx

    # Find the end of the state methods (before async_alarm_*)
    for i in range(class_start_idx, len(lines)):
        if (
            "async def async_alarm_" in lines[i]
            or "async def async_set_arm_mode" in lines[i]
        ):
            state_methods_end_idx = i
            break

    if state_methods_end_idx == class_start_idx:
        state_methods_end_idx = len(lines)

    # Include essential imports in chunk B
    essential_imports = []
    for line in lines[code_start_idx:setup_end_idx]:
        if any(
            keyword in line
            for keyword in [
                "import logging",
                "from homeassistant",
                "from .",
                "from .core",
            ]
        ):
            essential_imports.append(line)

    chunk_b_imports = "\n".join(essential_imports[:10])  # first 10 imports
    chunk_b_content = (
        chunk_b_imports
        + "\n\n"
        + "\n".join(lines[class_start_idx:state_methods_end_idx])
    )
    chunk_b_tokens = estimate_tokens(chunk_b_content)

    if chunk_b_tokens < max_tokens:
        chunks.append(
            {
                "id": "chunk_B",
                "title": "Clase MiotAlarmEntity y métodos de estado",
                "context": chunk_b_content,
                "instruction": "Implementa los métodos de estado y actualización para MiotAlarmEntity",
                "tokens": chunk_b_tokens,
            }
        )

    # ---- CHUNK C: Action Methods ----
    if state_methods_end_idx < len(lines):
        chunk_c_content = (
            chunk_b_imports + "\n\n" + "\n".join(lines[state_methods_end_idx:])
        )
        chunk_c_tokens = estimate_tokens(chunk_c_content)

        if chunk_c_tokens < max_tokens:
            chunks.append(
                {
                    "id": "chunk_C",
                    "title": "Métodos de acción (async_alarm_disarm, arm_home, arm_away, etc.)",
                    "context": chunk_c_content,
                    "instruction": "Implementa los métodos de control de alarma (disarm, arm_home, arm_away, arm_night, trigger)",
                    "tokens": chunk_c_tokens,
                }
            )

    return chunks


# ============================================================================
# 2. LOAD TARGET FILE AND CHUNK
# ============================================================================
print(f"📂 Loading file: {TARGET_FILE}")
with open(TARGET_FILE, "r", encoding="utf-8") as f:
    file_content = f.read()

seeds = split_code_logically(file_content)
print(f"✅ File split into {len(seeds)} logical chunks")
for seed in seeds:
    print(f"  - {seed['id']}: {seed['title']} ({seed['tokens']} tokens)")

TARGET_SAMPLES = len(seeds)

# ============================================================================
# 3. OPENAI/vLLM CLIENT CONFIGURATION
# ============================================================================
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-master-bunker-2026")

MODEL_NAME = "qwen3-30b-a3b-thinking-fp8"
GENERATION_PARAMS = {
    "temperature": 0.3,
    "presence_penalty": 1.3,
    "max_tokens": 8192,
    "stop": ["<|im_end|>"],
}

# 3b. LOAD TAXONOMY (moved to configs/)
# If missing, a FileNotFoundError is raised intentionally to surface config issues.
TAXONOMY_PATH = Path(
    "configs/stage_2_factory/taxonomy/home_assistant/hacs_expert/plugin_architecture.yaml"
)
with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
    taxonomy = yaml.safe_load(f)


# ============================================================================
# 4. TOOL DEFINITIONS (Roo-like)
# ============================================================================
TOOLS_DEFINITION = [
    {
        "name": "write_to_file",
        "description": "Escribe contenido a un archivo Python o YAML en el proyecto.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa del archivo (ej: custom_components/xiaomi/manifest.json)",
                },
                "content": {
                    "type": "string",
                    "description": "Contenido completo del archivo a escribir",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Lee el contenido de un archivo existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del archivo a leer"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "ask_followup_question",
        "description": "Pregunta al usuario cuando necesitas más información o confirmación.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "La pregunta específica para el usuario",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "attempt_completion",
        "description": "Marca la tarea como completada con un resultado final. USA ESTA HERRAMIENTA cuando hayas terminado exitosamente.",
        "parameters": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "Resumen del trabajo completado y archivos creados",
                },
                "command": {
                    "type": "string",
                    "description": "Comando opcional para ejecutar (ej: pytest, black)",
                },
            },
            "required": ["result"],
        },
    },
]


# 4. SYSTEM PROMPT - SERIALIZATION PROTOCOL
def build_system_prompt():
    task_desc = taxonomy["task_description"]
    tools_json = json.dumps(TOOLS_DEFINITION, indent=2, ensure_ascii=False)

    return f"""Eres un agente de ejecución pura para Home Assistant.

HERRAMIENTAS DISPONIBLES:
{tools_json}

OUTPUT_FORMAT - PROTOCOLO DE SERIALIZACIÓN:
Toda respuesta debe seguir esta gramática formal:

RESPONSE ::= THINK_BLOCK TOOL_BLOCK
THINK_BLOCK ::= "<think>" REASONING "</think>"
TOOL_BLOCK ::= "<tool_call>" JSON_OBJECT "</tool_call>"
JSON_OBJECT ::= {{"name": TOOL_NAME, "arguments": TOOL_ARGS}}

REGLAS DE SERIALIZACIÓN:
1. THINK_BLOCK es obligatorio y contiene tu razonamiento interno
2. TOOL_BLOCK es obligatorio y contiene la llamada a herramienta en JSON válido
3. No hay espacios entre </think> y <tool_call>
4. Cuando recibas resultado de herramienta (rol: tool), aplica la misma gramática

TAREA DE ENTRENAMIENTO:
{task_desc}

ESTÁNDAR 2026 - ZERO META-SPEECH:
- PROHIBIDO: "Entiendo tu petición", "Aquí tienes", "Voy a", "Procedo a"
- OBLIGATORIO: Logic Density > 2.5:1 (más código/lógica que texto)
- Solo razonamiento técnico directo en <think>

FEW-SHOT EXAMPLE - Interacción completa:

User: "Crea el manifest.json para una integración de luces Xiaomi"

Assistant:
<think>
Necesito crear el archivo manifest.json en la ruta custom_components/xiaomi_light/.
Debo incluir: domain, name, version, requirements (xiaomi library), y config_flow.
Usaré write_to_file con el contenido JSON estructurado.
</think><tool_call>
{{"name": "write_to_file", "arguments": {{"path": "custom_components/xiaomi_light/manifest.json", "content": "{{\\n  \\"domain\\": \\"xiaomi_light\\",\\n  \\"name\\": \\"Xiaomi Light\\",\\n  \\"version\\": \\"1.0.0\\",\\n  \\"requirements\\": [\\"python-miio==0.5.12\\"]\\n}}"}}}}
</tool_call>

Tool (role: tool, name: write_to_file):
{{
  "status": "success",
  "message": "Archivo creado correctamente"
}}

Assistant:
<think>
El manifest.json ha sido creado exitosamente. La integración está configurada con:
- Domain: xiaomi_light
- Dependencia: python-miio 0.5.12
La tarea está completa. Usaré attempt_completion para cerrar.
</think><tool_call>
{{"name": "attempt_completion", "arguments": {{"result": "Creado manifest.json para xiaomi_light con dependencias correctas", "command": "cat custom_components/xiaomi_light/manifest.json"}}}}
</tool_call>

Aplica esta misma gramática a todas tus respuestas."""


# 4.1. OUTPUT SANITIZER
def sanitize_output(text: str) -> str:
    """Fix common formatting issues in model responses."""

    # 1. If there's a <tool_call> but no preceding </think>, insert it.
    if "<tool_call>" in text and "</think>" not in text:
        text = text.replace("<tool_call>", "</think><tool_call>")

    # 2. If there's a <tool_call> but no closing </tool_call>, add it at the end.
    if "<tool_call>" in text and "</tool_call>" not in text:
        text = text.rstrip() + "\n</tool_call>"

    # 3. If there's a <think> but no closing </think> (and a <tool_call> exists),
    #    ensure </think> precedes <tool_call>.
    if "<think>" in text and "</think>" not in text and "<tool_call>" in text:
        text = text.replace("<tool_call>", "</think><tool_call>")

    return text


# 5. MULTI-TURN GENERATION
def generate_agentic_conversation(seed, sample_id):
    """Generate a multi-turn conversation with tool calls and responses."""
    context = seed["context"]
    instruction = seed["instruction"]

    conversation = []

    # TURN 1: User makes the initial request
    user_message = f"""Contexto técnico:
{context}

Petición:
{instruction}

Usa tus herramientas para completar esta tarea."""

    conversation.append({"role": "user", "content": user_message})

    # TURN 2: Agent responds with a tool_call
    response_1 = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": build_system_prompt()}, *conversation],
        **GENERATION_PARAMS,
    )

    agent_response_1 = response_1.choices[0].message.content
    agent_response_1 = sanitize_output(agent_response_1)  # sanitize format
    conversation.append({"role": "assistant", "content": agent_response_1})

    # Extract tool name from the tool_call (APIGen-MT-5k standard)
    tool_name = "write_to_file"  # Default
    if "write_to_file" in agent_response_1:
        tool_name = "write_to_file"
    elif "read_file" in agent_response_1:
        tool_name = "read_file"
    elif "ask_followup_question" in agent_response_1:
        tool_name = "ask_followup_question"

    # Generate a coherent tool_call_id (simulated but consistent)
    tool_call_id = f"call_{hash(instruction) % 10000}_{tool_name}"

    # TURN 3: Tool response (role: tool) (APIGen-MT-5k)
    tool_response = json.dumps(
        {
            "status": "success",
            "message": "Operación completada correctamente",
            "details": "Archivo creado/modificado según especificaciones",
        },
        indent=2,
        ensure_ascii=False,
    )

    conversation.append(
        {
            "role": "tool",
            "name": tool_name,
            "tool_call_id": tool_call_id,
            "content": f"{tool_response}\n\nOperación completada. Procede a verificación final con attempt_completion siguiendo el protocolo de serialización.",
        }
    )

    # TURN 4: Agent closes the conversation with attempt_completion

    # System prompt for Turn 4: technical reminder
    system_prompt_turn4 = (
        build_system_prompt()
        + """

--- VERIFICACIÓN FINAL ---
Tarea realizada exitosamente. Procede a cerrar usando attempt_completion.
Recuerda aplicar la gramática definida: THINK_BLOCK + TOOL_BLOCK sin espacios intermedios.
Formato: </think><tool_call>
{{"name": "attempt_completion", "arguments": {{"result": "..."}}}}
</tool_call>"""
    )

    response_2 = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system_prompt_turn4}, *conversation],
        **GENERATION_PARAMS,
    )

    agent_response_2 = response_2.choices[0].message.content
    agent_response_2 = sanitize_output(agent_response_2)  # sanitize format
    conversation.append({"role": "assistant", "content": agent_response_2})

    # Golden Triplet: Instruction, Reasoning (context), Result (conversation)
    return {
        "id": f"sample_{sample_id}",
        "instruction": instruction,
        "context_snippet": context[:500],
        "conversation": conversation,
        "metrics_2026": {
            "turns": len(conversation),
            "format_compliance": all(
                [
                    "<think>" in msg["content"] and "<tool_call>" in msg["content"]
                    for msg in conversation
                    if msg["role"] == "assistant"
                ]
            ),
            "has_attempt_completion": "attempt_completion" in agent_response_2,
            "nemo_curator_ready": True,
        },
    }


# 6. RUN THE DISTILABEL AGENTIC PIPELINE
if __name__ == "__main__":
    print("=" * 80)
    print("DISTILABEL PIPELINE - BLACKWELL AI FACTORY 2026")
    print("=" * 80)
    print(f"Model: {MODEL_NAME}")
    print(f"Samples: {TARGET_SAMPLES} (controlled test)")
    print(f"Framework: Distilabel + local vLLM")
    print("Metrics: Logic Density > 2.5:1, Zero Meta-Speech")
    print("=" * 80)

    results = []

    for idx, seed in enumerate(seeds):
        print(
            f"\n📝 Processing seed {idx + 1}/{len(seeds)}: {seed['instruction'][:60]}..."
        )

        try:
            conversation = generate_agentic_conversation(seed, idx)
            results.append(conversation)
            print(f"  ✅ Conversation generated (4 turns)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Save results
    output_path = Path("data/synthetic/batch_01_distilabel.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # QUALITY METRICS 2026
    print("\n" + "=" * 80)
    print("QUALITY METRICS 2026")
    print("=" * 80)

    # Validate format
    format_valid = 0
    attempt_completion_count = 0
    logic_density_estimates = []

    for r in results:
        turn2 = r["conversation"][1]["content"]
        turn4 = r["conversation"][3]["content"]

        if all(
            [
                "<think>" in turn2,
                "</think>" in turn2,
                "<tool_call>" in turn2,
                "</tool_call>" in turn2,
                "<think>" in turn4,
                "</think>" in turn4,
                "<tool_call>" in turn4,
                "</tool_call>" in turn4,
            ]
        ):
            format_valid += 1

        if "attempt_completion" in turn4:
            attempt_completion_count += 1

        # Estimate Logic Density (code/logic vs prose)
        code_chars = sum(1 for c in turn2 if c in "{}[]():;=")
        text_chars = len(turn2) - code_chars
        if text_chars > 0:
            logic_density_estimates.append(code_chars / text_chars)

    avg_logic_density = (
        sum(logic_density_estimates) / len(logic_density_estimates)
        if logic_density_estimates
        else 0
    )

    print(
        f"Valid format (4 turns): {format_valid}/{len(results)} ({(100 * format_valid) // len(results)}%)"
    )
    print(
        f"attempt_completion present: {attempt_completion_count}/{len(results)} ({(100 * attempt_completion_count) // len(results)}%)"
    )
    print(f"Average Logic Density Index: {avg_logic_density:.2f}:1 (Target: >2.5:1)")
    print(f"\n📁 Saved to: {output_path}")
    print(f"✅ NeMo-Curator compatible for downstream curation")
    print(
        f"APIGen-MT-5k roles: [user, assistant, tool, assistant] x {len(results)} conversations"
    )
    print("=" * 80)
