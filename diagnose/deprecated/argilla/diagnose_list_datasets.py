# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import argilla as rg

API_URL = "http://localhost:6900"
API_KEY = "argilla.apikey"
WS = "admin"
print("Connecting", API_URL)
client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
print("Calling client.datasets()")
try:
    all_ds = client.datasets()
    print("client.datasets() returned type", type(all_ds))
    try:
        for d in all_ds:
            try:
                print("dataset item:", d)
            except Exception:
                print("dataset item repr fail")
    except TypeError:
        print("client.datasets() not iterable, repr:", repr(all_ds))
except Exception as e:
    print("Error listing datasets via client.datasets():", e)
    try:
        # Fallback to rg.datasets() if present
        if hasattr(rg, "datasets"):
            print("rg.datasets() =>", rg.datasets())
    except Exception as e2:
        print("rg.datasets() error:", e2)
