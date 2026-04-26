# Tasks: Anchor Dataset Builder

## Phase 1: Make It Work (POC)

Focus: Prove the core pipeline works end-to-end. Schema + basic provider + simple CLI generating 5 samples dry-run. Accept hardcoded values, skip quality circuit breaker and synthesis.

- [x] 1.1 [P] Create package init file
  - **Do**: Create `infrastructure/anchor_dataset/__init__.py` with `__version__ = "0.1.0"`, `__all__` listing all public symbols (AnchorRecord, AnchorManifest, AnchorsConfig, DSPY_FIELD_MAP, etc.)
  - **Files**: infrastructure/anchor_dataset/__init__.py
  - **Done when**: File exists, empty import succeeds
  - **Verify**: `python -c "from infrastructure.anchor_dataset import __version__; print(__version__)"`
  - **Commit**: `feat(anchor-dataset): add package init`

- [ ] 1.2 [P] Create exception hierarchy
  - **Do**: Create `infrastructure/anchor_dataset/errors.py` with `AnchorDatasetError(RuntimeError)` base + 6 subclasses (ValidationError, ProviderError, SerializationError, ConfigurationError, SeedError, CheckpointError). Follow existing pattern from `src/utils/exceptions.py`.
  - **Files**: infrastructure/anchor_dataset/errors.py
  - **Done when**: All exception classes exist and inherit correctly
  - **Verify**: `python -c "from infrastructure.anchor_dataset.errors import *; assert issubclass(ValidationError, AnchorDatasetError); assert issubclass(ProviderError, AnchorDatasetError); assert issubclass(SeedError, AnchorDatasetError)"`
  - **Commit**: `feat(anchor-dataset): add exception hierarchy`

- [x] 1.3 [P] Create AnchorsConfig dataclass
  - **Do**: Create `infrastructure/anchor_dataset/config.py` with frozen dataclass `AnchorsConfig` including all fields from design (total_samples=50, output_dir, provider, vllm_url, temperature=0.4, max_tokens=8192, etc.), QualitySettings dataclass (mutable), and apply_calibration function.
  - **Files**: infrastructure/anchor_dataset/config.py
  - **Done when**: Config loads with defaults, env var validation works
  - **Verify**: `python -c "from infrastructure.anchor_dataset.config import AnchorsConfig, QualitySettings, apply_calibration; c = AnchorsConfig(); assert c.total_samples == 50; assert c.provider == 'vllm'; qs = QualitySettings(); assert qs.check_threshold == 0.3"`
  - **Commit**: `feat(anchor-dataset): add AnchorsConfig dataclass`

- [x] 1.4 [P] Create AnchorRecord Pydantic model
  - **Do**: Create `infrastructure/anchor_dataset/anchor_dataset_schema.py` with `AnchorRecord` Pydantic v2 model (frozen=True, all fields from spec with constraints), `AnchorManifest` Pydantic model, and `DSPY_FIELD_MAP` constant.
  - **Files**: infrastructure/anchor_dataset/anchor_dataset_schema.py
  - **Done when**: Model validates correctly, rejects invalid data
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord, DSPY_FIELD_MAP
r = AnchorRecord(id='anchor_001_00', domain='home_assistant', difficulty='easy', turn_count=3, legacy_pattern='test', domain_context='test', expected_trajectory='[ROLE:user]\ntest\n\n[ROLE:assistant]\ntool\n', expected_tool_usage_patterns=[], expected_coherence=0.8, expected_overall=0.7, expected_quality_score=0.75, expected_optimized_parameters={}, verified=True, verified_by='test')
print('VALID:', r.id)
try:
    AnchorRecord(id='bad', domain='home_assistant', difficulty='easy', turn_count=3, legacy_pattern='test', domain_context='test', expected_trajectory='[ROLE:user]\ntest', expected_tool_usage_patterns=[], expected_coherence=0.8, expected_overall=0.7, expected_quality_score=0.75, expected_optimized_parameters={}, verified=True, verified_by='test')
    assert False, 'Should have raised'
except Exception:
    print('REJECTED: bad id pattern')
print('FIELD_MAP inputs:', len(DSPY_FIELD_MAP['inputs']), 'labels:', len(DSPY_FIELD_MAP['labels']))
"`
  - **Commit**: `feat(anchor-dataset): add AnchorRecord Pydantic model`

- [x] 1.5 [P] Create DSPy converter stub
  - **Do**: Add `jsonl_to_dspy_examples(path: str) -> list[dspy.Example]` to schema.py. Import dspy lazily; raise ImportError with guidance if not installed. Handle empty files returning [].
  - **Files**: infrastructure/anchor_dataset/anchor_dataset_schema.py
  - **Done when**: Function exists, raises ImportError when dspy unavailable, returns [] for empty file
  - **Verify**: `python -c "
import sys, tempfile, os
with tempfile.NamedTemporaryFile(suffix='.jsonl', mode='w', delete=False) as f:
    name = f.name
from infrastructure.anchor_dataset.anchor_dataset_schema import jsonl_to_dspy_examples
result = jsonl_to_dspy_examples(name)
os.unlink(name)
assert result == [], f'Expected empty list, got {result}'
print('PASS: empty file returns []')
# Test that function exists and has correct signature (ImportError tested in test_schema.py)
import inspect
sig = inspect.signature(jsonl_to_dspy_examples)
assert 'path' in sig.parameters, 'Missing path parameter'
print('PASS: function signature correct')
"`
  - **Commit**: `feat(anchor-dataset): add jsonl_to_dspy_examples stub`

- [ ] 1.6 [P] Create seed loader
  - **Do**: Create `infrastructure/anchor_dataset/seed_loader.py` with `NormalizedSeed` dataclass and `load_seeds()` function. Load from `tests/fixtures/seed_examples.yaml`. Tag by domain. Handle missing file gracefully (log INFO, return []).
  - **Files**: infrastructure/anchor_dataset/seed_loader.py
  - **Done when**: Loads existing YAML, returns NormalizedSeed objects with domain tags
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.seed_loader import load_seeds
seeds = load_seeds()
assert len(seeds) >= 13, f'Expected >=13 seeds, got {len(seeds)}'
domains = set(s.domain for s in seeds)
assert 'home_assistant' in domains, 'Missing home_assistant seeds'
assert 'php_legacy' in domains, 'Missing php_legacy seeds'
print(f'Loaded {len(seeds)} seeds across {domains}')
"`
  - **Commit**: `feat(anchor-dataset): add seed loader`

- [ ] 1.7 [P] Create sample config generator
  - **Do**: Create `infrastructure/anchor_dataset/sample_generator.py` with `SampleConfig` frozen dataclass and `SampleConfigGenerator` class. Implement distribution math: floor-based rounding so total matches count exactly. HA=40%, PHP=30%, generic_domain=20%, other=10%. Difficulty: easy=30%, medium=50%, hard=20%. Turn count: easy=3, medium=4, hard=5. Deterministic ordering via random seed.
  - **Files**: infrastructure/anchor_dataset/sample_generator.py
  - **Done when**: Generates correct distribution for count=50 (HA=20, PHP=15, Generic=10, Other=5)
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.sample_generator import SampleConfigGenerator
from infrastructure.anchor_dataset.seed_loader import load_seeds
seeds = load_seeds()
gen = SampleConfigGenerator(seeds, seed=42)
configs = gen.generate_configs(50)
assert len(configs) == 50, f'Expected 50, got {len(configs)}'
from collections import Counter
d = Counter(c.domain for c in configs)
print('Domain dist:', dict(d))
assert d['home_assistant'] == 20, f'HA expected 20, got {d[\"home_assistant\"]}'
assert d['php_legacy'] == 15, f'PHP expected 15, got {d[\"php_legacy\"]}'
assert d['generic_domain'] == 10, f'Generic expected 10, got {d[\"generic_domain\"]}'
assert d['other'] == 5, f'Other expected 5, got {d[\"other\"]}'
print('PASS: distribution correct')
"`
  - **Commit**: `feat(anchor-dataset): add sample config generator`

- [x] 1.8 [P] Create PromptBuilder
  - **Do**: Add `PromptBuilder` class to `sample_generator.py` (co-located). Build system and user prompts with few-shot examples from matching seeds. SYSTEM_TEMPLATE and USER_TEMPLATE as class constants.
  - **Files**: infrastructure/anchor_dataset/sample_generator.py
  - **Done when**: build(config) returns (system_prompt, user_prompt) tuple with all template variables filled
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.seed_loader import load_seeds
from infrastructure.anchor_dataset.sample_generator import SampleConfigGenerator, PromptBuilder
seeds = load_seeds()
gen = SampleConfigGenerator(seeds, seed=42)
configs = gen.generate_configs(1)
pb = PromptBuilder(seeds)
system, user = pb.build(configs[0])
assert 'DOMAIN:' in system
assert 'FEW-SHOT EXAMPLES:' in system
assert 'QUALITY CONSTRAINTS:' in system
assert 'Generate an anchor sample' in user
print('PASS: prompt contains required sections')
"`
  - **Commit**: `feat(anchor-dataset): add PromptBuilder`

- [ ] 1.9 [VERIFY] Quality checkpoint: schema + config + seed loader + generator
  - **Do**: Run quality checks on all Phase 1 foundation modules
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && ruff check infrastructure/anchor_dataset/ && pyright infrastructure/anchor_dataset/ --pythonversion 3.12`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(anchor-dataset): pass quality checkpoint phase 1 foundation`

## Phase 2: Refactor

Focus: Add all provider implementations, quality system, persistence, and orchestration. Generate full 50 samples.

- [ ] 2.1 [P] Create AnchorProvider ABC + VLLMProvider
  - **Do**: Create `infrastructure/anchor_dataset/anchor_providers.py` with `AnchorProvider` ABC (name property, generate method returning AnchorRecord|None), and `VLLMProvider` implementation using `requests.post()` to localhost:8000/v1/chat/completions with response_format json_object. Include retry loop on ConnectionError/Timeout (exponential backoff 1,2,4s). Auth fallback to "sk-master-bunker-2026" when VLLM_API_KEY missing.
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: VLLMProvider imports, constructor accepts config, generate() returns None for unreachable server
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_providers import AnchorProvider, VLLMProvider
assert hasattr(AnchorProvider, 'generate')
assert hasattr(AnchorProvider, 'name')
p = VLLMProvider()
assert p.name == 'vllm'
# Provider returns None on unreachable server (no exception)
result = p.generate('sys', 'user', timeout=1)
assert result is None, 'Should return None for unreachable server'
print('PASS: VLLMProvider basic behavior correct')
"`
  - **Commit**: `feat(anchor-dataset): add AnchorProvider ABC and VLLMProvider`

- [ ] 2.2 [P] Create OpenAIProvider
  - **Do**: Add `OpenAIProvider` to anchor_providers.py. Uses httpx.Client (sync). response_format json_object. Model configurable (default gpt-4o). API key from OPENAI_API_KEY env var. Same retry pattern as VLLMProvider.
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: OpenAIProvider imports, returns None when OPENAI_API_KEY missing
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_providers import OpenAIProvider
p = OpenAIProvider()
assert p.name == 'openai'
print('PASS: OpenAIProvider basic behavior correct')
"`
  - **Commit**: `feat(anchor-dataset): add OpenAIProvider`

- [ ] 2.3 [P] Create GeminiProvider
  - **Do**: Add `GeminiProvider` to anchor_providers.py. Uses google-genai SDK (genai.Client). response_mime_type application/json. Model configurable (default gemini-2.0-flash). API key from GOOGLE_API_KEY env var. Parse response.text as JSON -> AnchorRecord.
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: GeminiProvider imports, returns None when GOOGLE_API_KEY missing
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_providers import GeminiProvider
p = GeminiProvider()
assert p.name == 'gemini'
print('PASS: GeminiProvider basic behavior correct')
"`
  - **Commit**: `feat(anchor-dataset): add GeminiProvider`

- [ ] 2.4 [P] Create Provider factory map
  - **Do**: Add PROVIDER_MAP dict mapping 'vllm'/'openai'/'gemini' to provider classes in anchor_providers.py. Add a `get_provider(provider_name: str, config) -> AnchorProvider` factory function.
  - **Files**: infrastructure/anchor_dataset/anchor_providers.py
  - **Done when**: get_provider() returns correct provider type, raises ConfigurationError for unknown provider
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_providers import get_provider, PROVIDER_MAP
assert 'vllm' in PROVIDER_MAP
p = get_provider('vllm', None)
assert p.name == 'vllm'
print('PASS: provider factory correct')
"`
  - **Commit**: `feat(anchor-dataset): add provider factory`

- [ ] 2.5 [P] Create QualityChecker
  - **Do**: Create `infrastructure/anchor_dataset/quality.py` with `QualityResult` frozen dataclass and `QualityChecker` class. Check: anti-laziness patterns (no "...", "# TODO", "pass # implement", "# resto del codigo"), turn count within +/-1 of target, self-assessed quality >= threshold (default 0.3), tool call syntactic validity via regex on [TOOL_CALL:...] markers. Also add `check_raw()` method for pre-construction validation on raw dict.
  - **Files**: infrastructure/anchor_dataset/quality.py
  - **Done when**: checker.check(record, target) returns QualityResult with correct pass/fail
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.quality import QualityChecker
import json
checker = QualityChecker(threshold=0.3)
# Valid record
r = AnchorRecord(id='anchor_001_00', domain='home_assistant', difficulty='easy', turn_count=3, legacy_pattern='test', domain_context='test', expected_trajectory='[ROLE:user]\\ntest\\n\\n[ROLE:assistant]\\ntool\\n', expected_tool_usage_patterns=['test'], expected_coherence=0.8, expected_overall=0.7, expected_quality_score=0.8, expected_optimized_parameters={}, verified=False)
result = checker.check(r, 3)
assert result.passed, f'Expected pass, got: {result.reasons}'
# Record with anti-laziness failure
r2 = AnchorRecord(id='anchor_001_00', domain='home_assistant', difficulty='easy', turn_count=3, legacy_pattern='test', domain_context='test', expected_trajectory='... # TODO pass # implement', expected_tool_usage_patterns=[], expected_coherence=0.8, expected_overall=0.7, expected_quality_score=0.8, expected_optimized_parameters={}, verified=False)
result2 = checker.check(r2, 3)
assert not result2.passed
assert 'anti_laziness' in result2.reasons
print('PASS: QualityChecker correctly detects anti-laziness')
"`
  - **Commit**: `feat(anchor-dataset): add QualityChecker`

- [ ] 2.6 [P] Create CircuitBreaker state machine
  - **Do**: Add `CircuitBreaker` class to quality.py (co-located). 3 phases: warmup (0-4), calibration (5-19), production (20+). record_result(passed), should_switch(), try_reset(), get_failure_rate(), _evaluate_batch(), _transition_phase(). threshold=0.2, batch_size=10, consecutive_pass_threshold=10.
  - **Files**: infrastructure/anchor_dataset/quality.py
  - **Done when**: State machine transitions correctly, triggers at threshold in production only
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.quality import CircuitBreaker
cb = CircuitBreaker()
assert cb.phase == 'warmup'
# Warmup (5 samples): no switch ever
for _ in range(5):
    cb.record_result(False)
assert not cb.should_switch()
# Calibration (15 more = 20 total): no switch
for _ in range(10):
    cb.record_result(True)
assert cb.phase == 'calibration'
assert not cb.should_switch()
# Production: trigger with 3 failures in last 10
for _ in range(5):
    cb.record_result(True)
for _ in range(3):
    cb.record_result(False)
assert cb.phase == 'production'
assert cb.should_switch()
print('PASS: CircuitBreaker phase transitions and switch logic correct')
"`
  - **Commit**: `feat(anchor-dataset): add CircuitBreaker state machine`

- [ ] 2.7 [P] Create FailedSampleLogger
  - **Do**: Create `infrastructure/anchor_dataset/failed_sample_logger.py` with `FailedSampleEntry` frozen dataclass and `FailedSampleLogger` class. Log to `outputs/failed_samples.jsonl`. Each entry: sample_id, domain, difficulty, failure_reason, provider, attempt, raw_response (truncated to 2000 chars). Append mode, one JSON per line.
  - **Files**: infrastructure/anchor_dataset/failed_sample_logger.py
  - **Done when**: Logger appends entries, entries are valid JSONL, truncation works
  - **Verify**: `python -c "
import tempfile, json
from pathlib import Path
from infrastructure.anchor_dataset.failed_sample_logger import FailedSampleLogger
tmp = Path(tempfile.mkdtemp()) / 'test.jsonl'
logger = FailedSampleLogger(log_path=tmp)
logger.log('test_id', 'home_assistant', 'easy', 'schema_validation', 'vllm', 0, 'short response')
logger.log('test_id2', 'other', 'hard', 'api_error', 'openai', 1, 'x' * 3000)
with open(tmp) as f:
    lines = f.readlines()
assert len(lines) == 2
e1 = json.loads(lines[0])
assert e1['raw_response'] == 'short response'
e2 = json.loads(lines[1])
assert len(e2['raw_response']) == 2000  # truncated
print('PASS: FailedSampleLogger correct')
"`
  - **Commit**: `feat(anchor-dataset): add FailedSampleLogger`

- [ ] 2.8 [P] Create CheckpointManager
  - **Do**: Create `infrastructure/anchor_dataset/checkpoint.py` with `CheckpointData` dataclass and `CheckpointManager` class. Methods: save(path, data) with atomic write (temp+rename+fsync), load(path) returns data or None if missing/corrupted. Resume logic: skip completed_ids, re-attempt failed_ids.
  - **Files**: infrastructure/anchor_dataset/checkpoint.py
  - **Done when**: save/load round-trip works, corrupted file returns None, atomic write verified
  - **Verify**: `python -c "
import tempfile, os
from pathlib import Path
from infrastructure.anchor_dataset.checkpoint import CheckpointManager, CheckpointData
tmp = tempfile.mkdtemp()
cp = CheckpointManager()
data = CheckpointData(completed_ids={'id1', 'id2'}, failed_ids={'id3': 'api_error'}, provider_active='vllm', sample_counter=3, domain_allocation_remaining={'home_assistant': 18}, timestamp='2026-01-01T00:00:00', circuit_breaker_triggered=False, next_variant_map={})
path = Path(tmp) / '.checkpoint.json'
cp.save(path, data)
loaded = cp.load(path)
assert loaded is not None
assert 'id1' in loaded.completed_ids
assert loaded.failed_ids['id3'] == 'api_error'
# Corrupted file
with open(path, 'w') as f:
    f.write('not json{{{')
assert cp.load(path) is None
print('PASS: CheckpointManager save/load/corruption correct')
"`
  - **Commit**: `feat(anchor-dataset): add CheckpointManager`

- [ ] 2.9 [P] Create JSONLExporter
  - **Do**: Create `infrastructure/anchor_dataset/exporter.py` with `JSONLExporter` class. `write_all(records, path)` atomic write (tmp+rename+fsync). `generate_manifest(records, provider_name, cb_triggered, failed_count) -> AnchorManifest`. Write manifest to `<path>_manifest.json`.
  - **Files**: infrastructure/anchor_dataset/exporter.py
  - **Done when**: Export writes valid JSONL, manifest has correct counts, atomic write pattern verified
  - **Verify**: `python -c "
import tempfile, json
from pathlib import Path
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.exporter import JSONLExporter
tmp = Path(tempfile.mkdtemp())
exporter = JSONLExporter()
recs = [AnchorRecord(id='anchor_001_00', domain='home_assistant', difficulty='easy', turn_count=3, legacy_pattern='test', domain_context='test', expected_trajectory='test', expected_tool_usage_patterns=[], expected_coherence=0.8, expected_overall=0.7, expected_quality_score=0.8, verified=False)]
output = tmp / 'test.jsonl'
exporter.write_all(recs, output)
manifest = tmp / 'test_manifest.json'
manifest_obj = exporter.generate_manifest(recs, 'vllm', False, 0)
import os; json.dump(manifest_obj.model_dump(), open(manifest, 'w'))
with open(output) as f:
    line = f.readline()
data = json.loads(line)
assert data['id'] == 'anchor_001_00'
with open(manifest) as f:
    m = json.loads(f.read())
assert m['total_samples'] == 1
print('PASS: JSONLExporter correct')
"`
  - **Commit**: `feat(anchor-dataset): add JSONLExporter`

- [ ] 2.10 [VERIFY] Quality checkpoint: providers + quality + persistence
  - **Do**: Run quality checks on all Phase 2 modules
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && ruff check infrastructure/anchor_dataset/ && pyright infrastructure/anchor_dataset/ --pythonversion 3.12`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(anchor-dataset): pass quality checkpoint phase 2`

- [ ] 2.11 [P] Create StartupValidator
  - **Do**: Create `infrastructure/anchor_dataset/startup.py` with `StartupValidator` class implementing 4-step sequence: (1) validate CLI args — count 1-200, provider in {vllm,openai,gemini}, distribution JSON parses; (2) validate API keys — required env var for provider; (3) health-check vLLM endpoint — HTTP GET /v1/models if vLLM; (4) pre-flight seed validation — load seeds, warn if generic_domain/other without reference corpus.
  - **Files**: infrastructure/anchor_dataset/startup.py
  - **Done when**: All 4 steps execute in order, dry_run returns warnings instead of exiting
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.startup import StartupValidator
from infrastructure.anchor_dataset.config import AnchorsConfig
sv = StartupValidator()
# Dry run should not exit
sv.dry_run(AnchorsConfig(provider='openai'))  # won't fail on missing key in dry_run mode
print('PASS: StartupValidator dry_run works')
"`
  - **Commit**: `feat(anchor-dataset): add StartupValidator`

- [ ] 2.12 [P] Create main CLI builder script
  - **Do**: Create `infrastructure/anchor_dataset_builder.py` at project root. 12 CLI arguments via argparse. Orchestration flow: startup validation -> seed loading -> synthesis -> config generation -> generation loop -> export. KeyboardInterrupt handling: save checkpoint, log, exit 1. --dry-run mode: validate seeds, compute distribution, log planned generation, exit 0 without writing. --no-overwrite: exit 1 if output exists. Apache-2.0 license header.
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: Script runs --dry-run, exits 0, logs planned distribution
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python infrastructure/anchor_dataset_builder.py --dry-run --count 50 2>&1 | grep -q 'Would generate' && grep -q 'HA=' && echo PASS || echo FAIL`
  - **Commit**: `feat(anchor-dataset): add main CLI builder script`

- [ ] 2.13 [VERIFY] E2E verification: dry-run end-to-end
  - **Do**:
    1. Run full dry-run with count=50: `python infrastructure/anchor_dataset_builder.py --dry-run --count 50`
    2. Verify it logs planned distribution
    3. Run with --resume on empty output: verify it starts from scratch
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python infrastructure/anchor_dataset_builder.py --dry-run --count 50 --seed 42 2>&1 | grep -E '(Would generate|home_assistant|php_legacy|generic_domain|other)' && echo VE2_PASS`
  - **Done when**: Dry-run produces expected distribution in output
  - **Commit**: None
  - **Skills**: cli-execution

- [ ] 2.14 [P] Create SeedSynthesizer
  - **Do**: Create `infrastructure/anchor_dataset/seed_synthesizer.py` with `SeedSynthesizer` class. 5-step pipeline: reference_scan (read code files), abstract_seeds (LLM call), classify_domains (LLM call), filter_leakage (regex check), validate_freshness (NormalizedSeed conversion). ValidateNo_leakage checks forbidden strings. On synthesis failure, log warning and fall back gracefully.
  - **Files**: infrastructure/anchor_dataset/seed_synthesizer.py
  - **Done when**: synthesizes seeds from reference corpus, validates no HA/IoT leakage
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.seed_synthesizer import SeedSynthesizer
from infrastructure.anchor_dataset.seed_loader import NormalizedSeed
synth = SeedSynthesizer.__new__(SeedSynthesizer)  # no __init__ call (avoids needing vLLM)
# validate_no_leakage with clean seeds
clean = NormalizedSeed(seed_id='test', domain='python', category='config', complexity='nominal_easy', context='python config management', question='handle config reload', expected_patterns=[])
assert synth.validate_no_leakage([clean])
# validate_no_leakage with leaking seed
leak = NormalizedSeed(seed_id='test2', domain='home_assistant', category='sensor', complexity='nominal_medium', context='home_assistant config', question='test', expected_patterns=[])
assert not synth.validate_no_leakage([leak])
print('PASS: SeedSynthesizer leakage detection correct')
"`
  - **Commit**: `feat(anchor-dataset): add SeedSynthesizer`

## Phase 3: Quality

Focus: Add circuit breaker, quality checker, failed sample log, checkpoint integration into builder.

- [ ] 3.1 [VERIFY] Quality checkpoint: all modules pass linting and types
  - **Do**: Run linting and type checking on all anchor_dataset modules
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && ruff check infrastructure/anchor_dataset/ && pyright infrastructure/anchor_dataset/ --pythonversion 3.12`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(anchor-dataset): pass quality checkpoint phase 3`

- [ ] 3.2 [P] Integrate circuit breaker into builder generation loop
  - **Do**: Modify `anchor_dataset_builder.py` generation loop: after each batch, call QualityChecker.check(), then CircuitBreaker.record_result(). If cb.should_switch(), log event, switch to fallback provider. Handle phase transitions.
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: Builder uses circuit breaker during generation, switches provider at threshold
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.quality import CircuitBreaker
cb = CircuitBreaker()
# Simulate production with 3 failures in 10
for _ in range(7):
    cb.record_result(True)
for _ in range(3):
    cb.record_result(False)
# Should have triggered
assert cb.should_switch()
print('PASS: circuit breaker integration correct')
"`
  - **Commit**: `feat(anchor-dataset): integrate circuit breaker into builder`

- [ ] 3.3 [P] Integrate checkpoint save into builder
  - **Do**: In builder loop, after each batch: call CheckpointManager.save() with current completed_ids, failed_ids, provider_active, sample_counter, domain_allocation_remaining. On --resume: load checkpoint, skip completed IDs, re-attempt failed IDs.
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: Checkpoint saved after batches, resume skips completed IDs
  - **Verify**: `python -c "
from pathlib import Path
from infrastructure.anchor_dataset.checkpoint import CheckpointManager, CheckpointData
import tempfile
cp = CheckpointManager()
tmp = tempfile.mkdtemp()
path = Path(tmp) / '.checkpoint.json'
data = CheckpointData(completed_ids={'id1', 'id2'}, failed_ids={}, provider_active='vllm', sample_counter=2, domain_allocation_remaining={'home_assistant': 18}, timestamp='2026-01-01T00:00:00', circuit_breaker_triggered=False, next_variant_map={})
cp.save(path, data)
loaded = cp.load(path)
assert loaded is not None
assert 'id1' in loaded.completed_ids
print('PASS: checkpoint save/load/resume correct with pathlib.Path')
"`
  - **Commit**: `feat(anchor-dataset): integrate checkpoint into builder`

- [ ] 3.4 [P] Integrate failed sample log into builder
  - **Do**: In builder loop, when provider.generate() returns None: call FailedSampleLogger.log() with reason code. Handle auto-retry for json_parse_error and api_error (retry with fallback provider).
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: Failed samples logged with correct reason codes, auto-retry works for API errors
  - **Verify**: `python -c "
import tempfile, json
from pathlib import Path
from infrastructure.anchor_dataset.failed_sample_logger import FailedSampleLogger
tmp = Path(tempfile.mkdtemp()) / 'fail.jsonl'
logger = FailedSampleLogger(log_path=tmp)
logger.log('id1', 'home_assistant', 'easy', 'schema_validation', 'vllm', 0, 'bad response')
logger.log('id2', 'other', 'hard', 'api_error', 'openai', 0, 'timeout')
with open(tmp) as f:
    entries = [json.loads(l) for l in f]
assert len(entries) == 2
assert entries[0]['failure_reason'] == 'schema_validation'
assert entries[1]['failure_reason'] == 'api_error'
print('PASS: failed sample log integration correct')
"`
  - **Commit**: `feat(anchor-dataset): integrate failed sample log into builder`

## Phase 4: Polish

Focus: CLI args, dry-run completeness, atomic writes, license headers, --no-overwrite, idempotency.

- [ ] 4.1 [P] Implement SeedSynthesizer fully in builder
  - **Do**: Wire SeedSynthesizer into builder pre-generation phase. Call synthesize() for generic_domain and other domains. If synthesis fails, log warning and use template-based generation.
  - **Files**: infrastructure/anchor_dataset_builder.py, infrastructure/anchor_dataset/seed_synthesizer.py
  - **Done when**: Builder synthesizes seeds for unseeded domains, handles synthesis failure gracefully
  - **Verify**: `python -c "
from infrastructure.anchor_dataset.seed_synthesizer import SeedSynthesizer
synth = SeedSynthesizer.__new__(SeedSynthesizer)  # no __init__ (avoids needing vLLM)
synth._reference_path = 'tests/fixtures/reference_corpus/homeassistant/'
patterns = synth.reference_scan()
assert len(patterns) > 0, f'Expected patterns, got {len(patterns)}'
print(f'PASS: reference_scan found {len(patterns)} patterns')
"`
  - **Commit**: `feat(anchor-dataset): integrate SeedSynthesizer into builder`

- [ ] 4.2 [P] Implement --resume flag fully
  - **Do**: Wire --resume flag in argparse. Load checkpoint if flag present. Skip completed IDs in generation loop. Re-attempt failed IDs with fallback provider. Log "Resuming from checkpoint: N samples completed, M failed".
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: --resume flag loads checkpoint and skips completed samples
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python infrastructure/anchor_dataset_builder.py --dry-run 2>&1 | grep -q 'Would generate' && echo 'PASS: dry-run works' && python infrastructure/anchor_dataset_builder.py --help | grep -q -- '--resume' && echo PASS || echo FAIL`
  - **Commit**: `feat(anchor-dataset): implement --resume flag`

- [ ] 4.3 [P] Add --no-overwrite and output warning
  - **Do**: Add --no-overwrite flag. If output file exists and --no-overwrite is set, print to stderr and exit 1. If output exists and --no-overwrite not set, print warning to stderr: 'Output file exists: {path}. Overwriting.'
  - **Files**: infrastructure/anchor_dataset_builder.py
  - **Done when**: --no-overwrite prevents overwrite, warning printed when overwriting
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && mkdir -p /tmp/anchor_test && touch /tmp/anchor_test/anchor_dataset.jsonl && python infrastructure/anchor_dataset_builder.py --count 1 --output-dir /tmp/anchor_test/ --no-overwrite 2>&1; echo $? | grep -q '1' && echo PASS || echo FAIL`
  - **Commit**: `feat(anchor-dataset): add --no-overwrite flag`

- [ ] 4.4 [P] Add Apache-2.0 license headers
  - **Do**: Add 4-line license header to all new Python files: `#!/usr/bin/env python3`, copyright line, SPDX tag. Ensure header is within first 4096 bytes (3 tokens required).
  - **Files**: infrastructure/anchor_dataset/*.py, infrastructure/anchor_dataset_builder.py
  - **Done when**: All files have license header
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && for f in infrastructure/anchor_dataset_builder.py infrastructure/anchor_dataset/*.py; do head -5 "$f" | grep -q 'Apache-2.0' || echo "MISSING: $f"; done && echo PASS`
  - **Commit**: `chore(anchor-dataset): add Apache-2.0 license headers`

- [ ] 4.5 [VERIFY] Quality checkpoint: all modules pass linting and types
  - **Do**: Run full linting and type checking
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && ruff check infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py && pyright infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py --pythonversion 3.12`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(anchor-dataset): pass quality checkpoint phase 4`

## Phase 5: Tests

Focus: Unit tests, integration tests, ruff + pyright compliance on tests.

- [ ] 5.1 [P] Create test factories
  - **Do**: Create `tests/factories.py` with `build_anchor_record(**overrides)` factory function. Default creates a valid AnchorRecord for home_assistant/easy. Overrides merge into defaults. Used across all test modules.
  - **Files**: tests/factories.py
  - **Done when**: Factory creates valid records, overrides work correctly
  - **Verify**: `python -c "
import sys; sys.path.insert(0, '.')
from tests.factories import build_anchor_record
r = build_anchor_record()
assert r.id == 'anchor_001_00'
r2 = build_anchor_record(domain='php_legacy', difficulty='hard')
assert r2.domain == 'php_legacy'
assert r2.difficulty == 'hard'
print('PASS: factories correct')
"`
  - **Commit**: `test(anchor-dataset): add test factories`

- [ ] 5.2 [P] Schema validation tests
  - **Do**: Create `tests/unit/test_schema.py` testing: (1) valid record passes validation, (2) out-of-range float raises, (3) invalid id pattern raises, (4) extra field raises (model_config extra='forbid'), (5) round-trip model_dump_json -> model_validate works, (6) DSPY_FIELD_MAP has correct keys and field counts, (7) jsonl_to_dspy_examples with valid JSONL, empty file, invalid record.
  - **Files**: tests/unit/test_schema.py
  - **Done when**: All schema tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_schema.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): schema validation tests`

- [ ] 5.3 [P] Provider unit tests
  - **Do**: Create `tests/unit/test_providers.py` testing: (1) VLLMProvider returns AnchorRecord on valid JSON, None on parse error, retries on connection error (mock requests.post), auth fallback works, (2) OpenAIProvider similar tests, (3) GeminiProvider similar tests, (4) name property for all providers, (5) PROVIDER_MAP correctness, (6) get_provider factory correctness.
  - **Files**: tests/unit/test_providers.py
  - **Done when**: All provider tests pass with mocked HTTP
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_providers.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): provider unit tests`

- [ ] 5.4 [P] QualityChecker and CircuitBreaker tests
  - **Do**: Create `tests/unit/test_quality.py` testing: (1) QualityChecker returns passed=True for valid record, passed=False for anti-laziness, turn_count_mismatch, low quality score, (2) QualityChecker with custom threshold, (3) CircuitBreaker phases: warmup (no switch), calibration (no switch), production (switch at threshold), (4) CircuitBreaker try_reset after consecutive passes, (5) CircuitBreaker get_failure_rate, (6) CircuitBreaker _evaluate_batch.
  - **Files**: tests/unit/test_quality.py
  - **Done when**: All quality tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_quality.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): quality checker and circuit breaker tests`

- [ ] 5.5 [P] Seed loader and SeedSynthesizer tests
  - **Do**: Create `tests/unit/test_seed_loader.py` testing: (1) Loads existing YAML with correct NormalizedSeed objects, (2) Missing file returns empty list with INFO log, (3) Idempotent loads, (4) Malformed YAML handling. Create `tests/unit/test_seed_synthesizer.py` testing: (1) validate_no_leakage returns correct booleans, (2) reference_scan reads files, (3) synthesize() returns seeds with domain labels.
  - **Files**: tests/unit/test_seed_loader.py, tests/unit/test_seed_synthesizer.py
  - **Done when**: All seed tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_seed_loader.py tests/unit/test_seed_synthesizer.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): seed loader and synthesizer tests`

- [ ] 5.6 [P] Distribution and SampleConfig tests
  - **Do**: Create `tests/unit/test_distribution.py` testing: (1) count=50: HA=20, PHP=15, Generic=10, Other=5; (2) count=110: HA=44, PHP=33, Generic=22, Other=11; (3) count=200: HA=80, PHP=60, Generic=40, Other=20; (4) difficulty distribution per domain: 30/50/20; (5) deterministic ordering with same seed; (6) turn_count by difficulty: easy=3, medium=4, hard=5.
  - **Files**: tests/unit/test_distribution.py
  - **Done when**: All distribution math tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_distribution.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): distribution and sample config tests`

- [ ] 5.7 [P] Persistence tests (checkpoint, exporter, failed log)
  - **Do**: Create `tests/unit/test_persistence.py` testing: (1) CheckpointManager save/load/resume with tmp_path, (2) corrupted checkpoint returns None, (3) JSONLExporter atomic write (tmp+rename), (4) manifest generation with correct counts, (5) FailedSampleLogger appends correct JSONL entries, truncation to 2000 chars.
  - **Files**: tests/unit/test_persistence.py
  - **Done when**: All persistence tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_persistence.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): persistence tests`

- [ ] 5.8 [P] StartupValidator and CLI tests
  - **Do**: Create `tests/unit/test_startup.py` testing: (1) valid CLI args pass all 4 steps, (2) missing API key fails at step 2, (3) invalid count fails at step 1, (4) dry_run returns warnings. Create `tests/unit/test_cli.py` testing: (1) --count 50, (2) --provider openai, (3) --dry-run writes nothing, (4) --no-overwrite exits 1 when file exists, (5) --domain-distribution override, (6) --difficulty-distribution override, (7) default values correct.
  - **Files**: tests/unit/test_startup.py, tests/unit/test_cli.py
  - **Done when**: All startup and CLI tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_startup.py tests/unit/test_cli.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): startup and CLI tests`

- [ ] 5.9 [P] Integration test for full pipeline
  - **Do**: Create `tests/integration/test_pipeline.py` testing: (1) Full pipeline with stubbed providers: load seeds -> generate configs -> build prompts -> call providers (stub) -> export to temp dir -> verify JSONL + manifest. (2) Idempotency: two runs with same seed produce same (id, domain, difficulty) tuples.
  - **Files**: tests/integration/test_pipeline.py
  - **Done when**: Integration test passes with stubbed providers
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/integration/test_pipeline.py -v -m integration --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): full pipeline integration test`

- [ ] 5.10 [P] Edge case tests
  - **Do**: Create `tests/unit/test_edge_cases.py` testing: (1) 0 seeds for generic_domain -> template generation produces valid samples, (2) very long trajectory (>10000 chars) not truncated, (3) malformed API responses handled gracefully, (4) empty seed file handled gracefully, (5) KeyboardInterrupt saves checkpoint and exits 1.
  - **Files**: tests/unit/test_edge_cases.py
  - **Done when**: All edge case tests pass
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && python -m pytest tests/unit/test_edge_cases.py -v --tb=short && echo PASS`
  - **Commit**: `test(anchor-dataset): edge case tests`

- [ ] 5.11 [VERIFY] Final quality gate: full CI
  - **Do**: Run the complete local CI suite: lint, types, all tests
  - **Verify**: `cd /mnt/bunker_data/ai/data_factory && ruff check infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py && ruff format --check infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py && pyright infrastructure/anchor_dataset/ infrastructure/anchor_dataset_builder.py --pythonversion 3.12 && python -m pytest tests/unit/ tests/integration/test_pipeline.py -v --tb=short && echo PASS`
  - **Done when**: All commands pass with no errors
  - **Commit**: `chore(anchor-dataset): pass final quality gate`

## Notes

- **POC shortcuts taken**: Circuit breaker calibration logic simplified; synthesis returns stub seeds; provider retry uses basic exponential backoff without jitter
- **Production TODOs**: Rate limit coordinator for shared API keys, cross-model judge assessment, progressive verification UX, SIGKILL resilience integration test, threshold oscillation detection, label disagreement logging
- **E2E approach**: CLI tool verified via command execution (--dry-run, --resume, distribution check)
- **Test dependencies**: Stub all HTTP API calls — no real vLLM/OpenAI/Gemini calls during tests
- **Test coverage target**: P0 = schema, providers, circuit breaker, JSONL export, distribution math; P1 = seed loader, synthesizer, persistence, startup, CLI, edge cases
