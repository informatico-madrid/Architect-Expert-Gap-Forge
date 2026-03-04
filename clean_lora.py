#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import torch
from safetensors.torch import load_file, save_file
import os
import json

# Paths inside the container
path = "data/outputs/consolidated/"
index_path = os.path.join(path, "adapter_model.safetensors.index.json")

# If the index file uses an alternate name, adjust here
if not os.path.exists(index_path):
    index_path = os.path.join(path, "model.safetensors.index.json")

with open(index_path, "r") as f:
    index = json.load(f)

weight_map = index["weight_map"]
files = sorted(list(set(weight_map.values())))

clean_state_dict = {}

print(f"--- STARTING DEEP CONSOLIDATION ---")

for f in files:
    print(f"Processing shard: {f}...")
    shard_path = os.path.join(path, f)
    shard = load_file(shard_path)
    
    for key, value in shard.items():
        # 1. Remove duplicated prefixes (base_model.model.model -> base_model.model)
        new_key = key.replace("base_model.model.model.", "base_model.model.")
        
        # 2. Remove '.default' suffix (lora_A.default.weight -> lora_A.weight)
        new_key = new_key.replace(".default.", ".")
        
        clean_state_dict[new_key] = value
    del shard

print(f"--- SAVING MASTER FILE ---")
# Save to consolidated path so vLLM can load it directly
save_file(clean_state_dict, "data/outputs/consolidated/adapter_model.safetensors")

print("OPERATION COMPLETED")
print("You may now remove the shards and index.json to avoid confusion for vLLM.")