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
name='hacs_platinum_test_upload'
print('Creating dataset', name)
settings = rg.Settings(
    fields=[
        rg.ChatField(name='conversation', title='Conversación', use_markdown=True),
    ],
    metadata=[rg.TermsMetadataProperty(name='sample_id', title='Sample ID')]
)
try:
    ds = rg.Dataset(name=name, settings=settings, workspace=WS)
    ds.create()
    print('Created dataset')
except Exception as e:
    print('Create failed:', e)
    ds = rg.Dataset(name=name, workspace=WS)
    print('Using existing ds')

print('Dataset repr:', repr(ds))
rec = rg.Record(fields={'conversation':[{'role':'user','content':'hola'},{'role':'assistant','content':'<think>analysis</think><tool_call>{"a":1}</tool_call>'}]}, metadata={'sample_id':'test1'})
print('Attempting to log one record')
try:
    ds.records.log([rec])
    print('Logged successfully')
except Exception as e:
    print('Logging failed:', e)
    raise
