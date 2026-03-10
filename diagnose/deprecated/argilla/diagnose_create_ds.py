# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

from src.upload_master_platinum import create_argilla_dataset
import os

os.environ.setdefault("ARGILLA_API_URL", "http://localhost:6900")
os.environ.setdefault("ARGILLA_API_KEY", "argilla.apikey")
os.environ.setdefault("ARGILLA_WORKSPACE", "admin")

print("Calling create_argilla_dataset('hacs_platinum_v1_final_debug')")
ds = create_argilla_dataset("hacs_platinum_v1_final_debug")
print("Returned DS ->", type(ds))
try:
    print("has records attr:", hasattr(ds, "records"))
    print("repr:", repr(ds))
except Exception as e:
    print("repr failed:", e)
