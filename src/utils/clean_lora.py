import torch
from safetensors.torch import load_file, save_file
import os
import json

# Rutas dentro del contenedor
path = "data/outputs/consolidated/"
index_path = os.path.join(path, "adapter_model.safetensors.index.json")

# Si el índice se llama model.safetensors.index.json, cámbialo aquí
if not os.path.exists(index_path):
    index_path = os.path.join(path, "model.safetensors.index.json")

with open(index_path, "r") as f:
    index = json.load(f)

weight_map = index["weight_map"]
files = sorted(list(set(weight_map.values())))

clean_state_dict = {}

print(f"--- INICIANDO CONSOLIDACIÓN PROFUNDA ---")

for f in files:
    print(f"Procesando shard: {f}...")
    shard_path = os.path.join(path, f)
    shard = load_file(shard_path)
    
    for key, value in shard.items():
        # 1. Limpiamos el exceso de prefijos (base_model.model.model -> base_model.model)
        new_key = key.replace("base_model.model.model.", "base_model.model.")
        
        # 2. Limpiamos el sufijo ".default" (lora_A.default.weight -> lora_A.weight)
        new_key = new_key.replace(".default.", ".")
        
        clean_state_dict[new_key] = value
    del shard

print(f"--- GUARDANDO ARCHIVO MAESTRO (13GB) ---")
# Lo guardamos en la carpeta anterior para que vLLM lo vea directo
save_file(clean_state_dict, "data/outputs/consolidated/adapter_model.safetensors")

print("¡OPERACIÓN COMPLETADA!")
print("Ahora puedes borrar los shards y el index.json para que vLLM no se líe.")