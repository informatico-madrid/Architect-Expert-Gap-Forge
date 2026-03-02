#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

import os
import json
import traceback
import argilla as rg

ARGILLA_API_URL = os.getenv("ARGILLA_API_URL", "http://localhost:6900")
ARGILLA_API_KEY = os.getenv("ARGILLA_API_KEY", "argilla.apikey")
WORKSPACE = os.getenv("ARGILLA_WORKSPACE", "admin")
DATASET_NAME = "hacs_platinum_v1_final"
ARGILLA_RECORD_ID = "0607936c-e63a-4593-bbd5-2ddd3845a118"
SAMPLE_ID = "gold_test_currency"

print('Connecting to Argilla:', ARGILLA_API_URL, 'workspace=', WORKSPACE)
client = rg.Argilla(api_url=ARGILLA_API_URL, api_key=ARGILLA_API_KEY)

ds = None
try:
    ds = rg.Dataset(name=DATASET_NAME, workspace=WORKSPACE)
    print('rg.Dataset returned:', type(ds))
except Exception as e:
    print('rg.Dataset(...) failed:', repr(e))
    try:
        ds = client.datasets(name=DATASET_NAME, workspace=WORKSPACE)
        print('client.datasets returned:', type(ds))
    except Exception as e2:
        print('client.datasets failed:', repr(e2))

if ds is None:
    print('Could not obtain dataset object')
    raise SystemExit(1)

print('\n--- dataset object quick dir ---')
print([k for k in dir(ds) if not k.startswith('_')])

recs = getattr(ds, 'records', None)
print('\n--- dataset.records ---', type(recs))
print([k for k in dir(recs) if not k.startswith('_')])

# Try to fetch by Argilla record id
found = False
try:
    if hasattr(recs, 'get'):
        print('\nTrying records.get(id)')
        try:
            r = recs.get(ARGILLA_RECORD_ID)
            print('recs.get returned type:', type(r))
            found = True
            record_obj = r
        except Exception as e:
            print('recs.get failed:', repr(e))
    # try search by metadata/sample_id
    if not found and hasattr(recs, 'search'):
        print('\nTrying records.search by sample_id metadata')
        try:
            # search expects query dict or kwargs; try filter
            results = recs.search(sample_id=SAMPLE_ID)
            print('recs.search returned type:', type(results))
            if hasattr(results, '__iter__'):
                results_list = list(results)
                print('results count:', len(results_list))
                if results_list:
                    found = True
                    record_obj = results_list[0]
        except Exception as e:
            print('recs.search failed:', repr(e))
    # try iterator read() or iterate
    if not found:
        print('\nTrying records.read() (first 200)')
        try:
            it = recs.read()
            # if it is iterator/generator
            from itertools import islice
            sample = list(islice(it, 200))
            print('read returned count:', len(sample))
            for rr in sample:
                try:
                    # try to inspect metadata or fields
                    rid = None
                    if hasattr(rr, 'id'):
                        rid = getattr(rr, 'id')
                    elif isinstance(rr, dict):
                        rid = rr.get('id')
                    print(' - item id repr:', rid)
                    if rid == ARGILLA_RECORD_ID or (isinstance(rr, dict) and rr.get('metadata', {}).get('sample_id') == SAMPLE_ID):
                        found = True
                        record_obj = rr
                        break
                except Exception:
                    pass
        except Exception as e:
            print('recs.read failed:', repr(e))
except Exception as e:
    print('Error while fetching records:', repr(e))
    traceback.print_exc()

if not found:
    print('\nRecord not found via get/search/read. Trying client API list...')
    try:
        ds_list = client.datasets()
        for d in ds_list:
            try:
                if getattr(d, 'name', None) == DATASET_NAME:
                    print('Found dataset via client.datasets():', d.name)
                    if hasattr(d, 'records'):
                        recs2 = d.records
                        try:
                            it2 = recs2.read()
                            from itertools import islice
                            sample2 = list(islice(it2, 500))
                            for rr in sample2:
                                if isinstance(rr, dict) and rr.get('metadata', {}).get('sample_id') == SAMPLE_ID:
                                    record_obj = rr
                                    found = True
                                    break
                        except Exception as e:
                            print('error reading recs2:', e)
            except Exception:
                pass
    except Exception as e:
        print('client.datasets() failed to list datasets:', repr(e))

if not found:
    # Try listing all records via records.to_list() and search metadata/sample_id
    try:
        print('\nTrying records.to_list() to scan all records (may be large)')
        all_recs = recs.to_list()
        print('to_list returned count:', len(all_recs))
        for rr in all_recs:
            try:
                if hasattr(rr, 'to_dict'):
                    d = rr.to_dict()
                elif isinstance(rr, dict):
                    d = rr
                else:
                    try:
                        d = rr.__dict__
                    except Exception:
                        continue

                meta = d.get('metadata') if isinstance(d, dict) else None
                if isinstance(meta, dict) and meta.get('sample_id') == SAMPLE_ID:
                    record_obj = rr
                    found = True
                    break
                # also check top-level id
                rid = d.get('id') if isinstance(d, dict) else None
                if rid == ARGILLA_RECORD_ID:
                    record_obj = rr
                    found = True
                    break
            except Exception:
                continue
    except Exception as e:
        print('records.to_list() failed:', repr(e))

if found:
    print('\n--- Record RAW (attempt to to_dict / __dict__) ---')
    try:
        if hasattr(record_obj, 'to_dict'):
            print(json.dumps(record_obj.to_dict(), ensure_ascii=False, indent=2)[:10000])
        elif hasattr(record_obj, 'dict'):
            print(json.dumps(record_obj.dict(), ensure_ascii=False, indent=2)[:10000])
        else:
            try:
                print(json.dumps(record_obj.__dict__, ensure_ascii=False, indent=2)[:10000])
            except Exception:
                print(repr(record_obj)[:10000])
    except Exception as e:
        print('Error serializing record_obj:', repr(e))
else:
    print('\nNo se encontró el registro en Argilla con id o sample_id solicitados')

print('\nDone')
