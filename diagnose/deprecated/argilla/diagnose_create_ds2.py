import runpy
import os

os.environ.setdefault("ARGILLA_API_URL", "http://localhost:6900")
os.environ.setdefault("ARGILLA_API_KEY", "argilla.apikey")
os.environ.setdefault("ARGILLA_WORKSPACE", "admin")

g = runpy.run_path('src/upload_master_platinum.py')
create_fn = g.get('create_argilla_dataset')
if not create_fn:
    print('create_argilla_dataset not found in module')
    raise SystemExit(1)

print("Calling create_argilla_dataset('hacs_platinum_v1_final_debug')")
ds = create_fn('hacs_platinum_v1_final_debug')
print('Returned DS ->', type(ds))
try:
    print('has records attr:', hasattr(ds, 'records'))
    print('repr:', repr(ds))
except Exception as e:
    print('repr failed:', e)
