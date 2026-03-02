# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import os
import traceback
import uuid
import argilla as rg

ARGILLA_API_URL = os.getenv("ARGILLA_API_URL", "http://localhost:6900")
ARGILLA_API_KEY = os.getenv("ARGILLA_API_KEY", "argilla.apikey")
WORKSPACE = os.getenv("ARGILLA_WORKSPACE", "admin")

print("DEBUG2: API_URL=", ARGILLA_API_URL)
print("DEBUG2: Using workspace=", WORKSPACE)

client = rg.Argilla(api_url=ARGILLA_API_URL, api_key=ARGILLA_API_KEY)

dataset_name = f"debug_chatfield2_{uuid.uuid4().hex[:8]}"

settings = rg.Settings(
    fields=[
        rg.ChatField(name="conversation", title="Conversación (multi-turn)", use_markdown=True),
        rg.TextField(name="instruction", title="Instruction", use_markdown=True),
        rg.TextField(name="thought_extracted", title="Think", use_markdown=True),
        rg.TextField(name="code_extracted", title="Code", use_markdown=True),
        rg.TextField(name="context", title="Context", use_markdown=True),
    ],
    questions=[
        rg.RatingQuestion(name="quality", title="Quality", values=[1,2,3,4,5]),
        rg.TextQuestion(name="notes", title="Notes", use_markdown=True),
    ],
    metadata=[
        rg.FloatMetadataProperty(name="ldi_score", title="LDI Score"),
        rg.IntegerMetadataProperty(name="code_tokens", title="Code Tokens")
    ]
)

print("DEBUG2: Creating dataset", dataset_name)
try:
    ds = rg.Dataset(name=dataset_name, settings=settings, workspace=WORKSPACE)
    ds.create()
    print("DEBUG2: Dataset created")
except Exception as e:
    print("DEBUG2: Create failed:", repr(e))
    try:
        ds = client.datasets(name=dataset_name, workspace=WORKSPACE)
        print("DEBUG2: Got dataset via client.datasets() ->", type(ds))
    except Exception as e2:
        print("DEBUG2: client.datasets() failed:", repr(e2))
        ds = None

# Build a minimal record
record = rg.Record(
    fields={
        "conversation": [
            {"role": "user", "content": "Hola, genera un ejemplo simple"},
            {"role": "assistant", "content": "Aquí tienes:\n```python\nprint(\"Hola Mundo\")\n```"}
        ],
        "instruction": "Genera un ejemplo",
        "thought_extracted": "pensamiento...",
        "code_extracted": "print(\"Hola\")",
        "context": ""
    },
    metadata={"ldi_score": 0.5, "code_tokens": 5}
)

print("DEBUG2: Logging record")
try:
    ds.records.log([record])
    print("DEBUG2: Record logged successfully")
except Exception as e:
    print("DEBUG2: Error logging record:", repr(e))
    traceback.print_exc()

print("DEBUG2: Done")
