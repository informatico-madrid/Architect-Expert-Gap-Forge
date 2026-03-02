# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import argilla as rg
API_URL='http://localhost:6900'
API_KEY='argilla.apikey'
WS='admin'
client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
print('Getting dataset object...')
ds = client.datasets(name='hacs_platinum_v1_final', workspace=WS)
print('Dataset repr before delete:', repr(ds))
try:
    ds.delete()
    print('ds.delete() invoked successfully')
except Exception as e:
    print('ds.delete() failed:', e)

# Try client.delete_dataset if available
try:
    if hasattr(client, 'delete_dataset'):
        client.delete_dataset(name='hacs_platinum_v1_final', workspace=WS)
        print('client.delete_dataset called')
except Exception as e:
    print('client.delete_dataset failed:', e)

# List datasets to confirm
try:
    all_ds = client.datasets()
    print('Remaining datasets count (client.datasets() call may require args):', all_ds)
except Exception as e:
    print('client.datasets() listing error:', e)
