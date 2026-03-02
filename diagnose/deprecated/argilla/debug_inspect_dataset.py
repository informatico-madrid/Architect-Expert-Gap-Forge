# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import os
import argilla as rg

ARGILLA_API_URL = os.getenv("ARGILLA_API_URL", "http://localhost:6900")
ARGILLA_API_KEY = os.getenv("ARGILLA_API_KEY", "argilla.apikey")
WORKSPACE = os.getenv("ARGILLA_WORKSPACE", "admin")
DATASET_NAME = "hacs_platinum_v1_final"

client = rg.Argilla(api_url=ARGILLA_API_URL, api_key=ARGILLA_API_KEY)

print("Inspecting dataset:", DATASET_NAME, "workspace:", WORKSPACE)
try:
    ds = rg.Dataset(name=DATASET_NAME, workspace=WORKSPACE)
    print("Dataset object type:", type(ds))
    try:
        settings = ds.settings
        print("Dataset settings available")
        try:
            for f in settings.fields:
                print(" - field:", getattr(f, 'name', str(f)), "type:", type(f).__name__)
                try:
                    print("    repr:", repr(f))
                except Exception:
                    pass
        except Exception as e:
            print("Could not iterate settings.fields:", e)
    except Exception as e:
        print("Could not access ds.settings:", e)
except Exception as e:
    print("rg.Dataset() raised:", e)

# try via client.datasets()
try:
    ds2 = client.datasets(name=DATASET_NAME, workspace=WORKSPACE)
    print("client.datasets returned:", type(ds2))
    try:
        # ds2 may be a Dataset object or a list/dict
        if hasattr(ds2, 'settings'):
            for f in ds2.settings.fields:
                print("client.datasets - field:", getattr(f, 'name', str(f)), "type:", type(f).__name__)
        else:
            print('client.datasets did not return settings')
    except Exception as e:
        print('Error reading settings from client.datasets():', e)
except Exception as e:
    print('client.datasets() error:', e)
