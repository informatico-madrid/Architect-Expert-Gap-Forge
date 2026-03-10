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

print("DEBUG: API_URL=", ARGILLA_API_URL)
print("DEBUG: Using workspace=", WORKSPACE)

client = rg.Argilla(api_url=ARGILLA_API_URL, api_key=ARGILLA_API_KEY)

dataset_name = f"debug_chatfield_{uuid.uuid4().hex[:8]}"

settings = rg.Settings(
    fields=[
        rg.ChatField(name="conversation", title="Conversación", use_markdown=True),
        rg.TextField(name="instruction", title="Instruction", use_markdown=True),
        rg.TextField(name="context", title="Context", use_markdown=True),
    ]
)

print("DEBUG: Creating dataset", dataset_name)
try:
    ds = rg.Dataset(name=dataset_name, settings=settings, workspace=WORKSPACE)
    ds.create()
    print("DEBUG: Dataset created")
except Exception as e:
    print("DEBUG: Create failed:", repr(e))
    try:
        ds = client.datasets(name=dataset_name, workspace=WORKSPACE)
        print("DEBUG: Got dataset via client.datasets()")
    except Exception as e2:
        print("DEBUG: client.datasets() failed:", repr(e2))
        ds = None

# Build a minimal record
record = rg.Record(
    fields={
        "conversation": [
            {"role": "user", "content": "Hola, genera un ejemplo simple"},
            {
                "role": "assistant",
                "content": 'Aquí tienes:\n```python\nprint("Hola Mundo")\n```',
            },
        ],
        "instruction": "Genera un ejemplo",
        "context": "",
    },
    metadata={"debug": True},
)

print("DEBUG: Logging record")
try:
    ds.records.log([record])
    print("DEBUG: Record logged successfully")
except Exception as e:
    print("DEBUG: Error logging record:", repr(e))
    traceback.print_exc()

print("DEBUG: Done")
