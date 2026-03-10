# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import runpy
import os

os.environ.setdefault("ARGILLA_API_URL", "http://localhost:6900")
os.environ.setdefault("ARGILLA_API_KEY", "argilla.apikey")
os.environ.setdefault("ARGILLA_WORKSPACE", "admin")

g = runpy.run_path("src/upload_master_platinum.py")
clear_fn = g.get("clear_argilla_dataset")
create_fn = g.get("create_argilla_dataset")
if not clear_fn or not create_fn:
    print("Funciones necesarias no encontradas en el módulo")
    raise SystemExit(1)

ds_name = "hacs_platinum_v1_final"
print("Intentando limpiar dataset:", ds_name)
clear_fn(ds_name)
print("Ahora (re)creando dataset:", ds_name)
ds = create_fn(ds_name)
print("Resultado create ->", type(ds))
try:
    print("has records attr:", hasattr(ds, "records"))
    print("repr:", repr(ds))
except Exception as e:
    print("repr failed:", e)
