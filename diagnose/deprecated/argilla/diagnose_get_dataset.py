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
print('client ok')
try:
    ds = client.datasets(name='hacs_platinum_v1_final', workspace=WS)
    print('client.datasets returned:', type(ds))
    try:
        print('repr:', repr(ds))
    except Exception:
        print('repr fail')
    # Try to inspect attributes
    try:
        print('has delete?:', hasattr(ds, 'delete'))
        print('has records?:', hasattr(ds, 'records'))
    except Exception as e:
        print('inspect fail', e)
except Exception as e:
    print('client.datasets error:', e)
    raise
