# Requirements: Anchor Dataset

**Spec**: anchor-dataset
**Epic**: aegf-infrastructure (Epic 0, Story 0.3)
**Goal**: As an ML Engineer, I want a domain-specific anchor dataset of 100-200 samples with ground truth labels, so that DSPy MIPROv2 can compile and optimize signatures effectively.
**Status**: pending (blocked on: baseline-measurement, prompt-externalization)
**BMAD Source**: Story 0.3 -- Anchor Dataset Creation (severity 9/10, Party Mode consensus 4/4 -- "without anchors, MIPROv2 compiles to vacuum")

---

## User Stories

### US-1: Anchor dataset schema definition
**Priority**: MUST
**Dependencies**: None

As an ML Engineer, I want a Pydantic-based anchor record schema with DSPy field mapping, so that generated samples are structurally valid and directly consumable by MIPROv2 without a conversion layer.

**Acceptance Criteria:**
- [ ] AC-1.1: `AnchorRecord` Pydantic model exists at `infrastructure/anchor_dataset_schema.py`
- [ ] AC-1.2: Model fields match the JSONL record schema: `id` (str, pattern `anchor_\d+`), `domain` (Literal["home_assistant", "php_legacy", "generic_domain", "other"]), `difficulty` (Literal["easy", "medium", "hard"]), `turn_count` (int), `legacy_pattern` (str), `domain_context` (str), `expected_trajectory` (str), `expected_tool_usage_patterns` (list[str]), `expected_coherence` (float, range 0.0-1.0), `expected_overall` (float, range 0.0-1.0), `expected_optimized_parameters` (dict[str, Any]), `expected_quality_score` (float, range 0.0-1.0), `verified` (bool), `verified_by` (str)
- [ ] AC-1.3: `AnchorManifest` Pydantic model exists with fields: `version` (str), `created` (ISO8601 str), `total_samples` (int), `domain_distribution` (dict[str, int]), `difficulty_distribution` (dict[str, int])
- [ ] AC-1.4: `DSPY_FIELD_MAP` constant maps JSONL fields to DSPy input/label roles:
  - Input fields: `domain_context`, `expected_trajectory`, `difficulty`, `turn_count`, `legacy_pattern`
  - Label fields: `expected_tool_usage_patterns`, `expected_coherence`, `expected_overall`, `expected_quality_score`, `expected_optimized_parameters`
  - Note: `expected_optimized_parameters` maps to the CalibrationSignature label output; `difficulty` and `turn_count` are inputs used by the TrajectorySignature to control generation complexity
- [ ] AC-1.5: Float fields (`expected_coherence`, `expected_overall`, `expected_quality_score`) validate range [0.0, 1.0] with a custom validator
- [ ] AC-1.6: `id` field validates format with regex `r"^anchor_\d+_\d+$"` (two non-negative integers separated by underscore, e.g. `anchor_001_03`). Implementation MUST use raw string prefix to avoid escape confusion.
- [ ] AC-1.7: Model serializes to JSON matching the spec schema exactly (no extra fields, no missing fields)

### US-2: Seed data loader
**Priority**: MUST
**Dependencies**: None

As the dataset builder, I want to load and normalize seed data from existing fixtures so that generation uses real project data where available.

**Acceptance Criteria:**
- [ ] AC-2.1: Seeds loaded from `tests/fixtures/seed_examples.yaml` (currently 8 HA seeds + 5 PHP legacy seeds)
- [ ] AC-2.2: Seed normalization extracts: `seed_id`, `category`, `context`, `question`, `complexity`, `expected_patterns` into a uniform representation
- [ ] AC-2.3: Seeds tagged by domain: `home_assistant` for HA seeds, `php_legacy` for PHP seeds
- [ ] AC-2.4: When seed file is missing: log INFO-level warning message "Seed file not found, continuing with empty seed list", return empty normalized seed list, continue generation without error (exit code 0)
- [ ] AC-2.5: Seed loading is idempotent (re-reading produces identical normalized output)

### US-3: Domain distribution controller
**Priority**: MUST
**Dependencies**: US-2 (seed data)

As the dataset builder, I want to enforce a domain distribution of 40% HA / 30% PHP / 20% Generic / 10% Other so that the anchor dataset covers the target taxonomy structure.

**Acceptance Criteria:**
- [ ] AC-3.1: Total sample count is configurable, defaulting to 50 (v0.1 minimum viable for MIPROv2 bootstrap) with an upper bound of 200 (v0.2 full scale)
- [ ] AC-3.2: Distribution enforced: home_assistant = 40%, php_legacy = 30%, generic_domain = 20%, other = 10% (rounded so total equals requested count)
- [ ] AC-3.3: v0.1 targets 50 samples minimum: home_assistant=20, php_legacy=15, generic_domain=10, other=5
- [ ] AC-3.4: Distribution is parameterizable via CLI argument or config (for experimentation)
- [ ] AC-3.5: Difficulty distribution per domain: easy=30%, medium=50%, hard=20% (applied within each domain allocation)

### US-4: Seed-based sample generation (HA and PHP)
**Priority**: MUST
**Dependencies**: US-2 (seed data), US-5 (API provider), US-6 (quality circuit breaker)

As the dataset builder, I want to generate anchor samples from real seed data for home_assistant and php_legacy domains so that ground truth labels reflect actual project patterns.

**Acceptance Criteria:**
- [ ] AC-4.1: For each HA seed, generate 4-5 variants by varying: difficulty level, legacy pattern specificity, and trajectory detail level
- [ ] AC-4.2: For each PHP legacy seed, generate 5-6 variants by varying: PHP version target, migration aggressiveness, and error handling depth
- [ ] AC-4.3: Per-seed variant counts scale with target sample count: for v0.1 (50 samples), each HA seed produces 2-3 variants (total HA=20), each PHP seed produces 3 variants (total PHP=15). For full scale (200 samples), each HA seed produces 5 variants (total HA=40), each PHP seed produces 6 variants (total PHP=30). Variant counts are parameterizable via `--variants-per-seed` CLI argument.
- [ ] AC-4.4: Each generated sample includes a complete set of expected labels (trajectory, tool_usage_patterns, coherence, overall, quality_score)
- [ ] AC-4.5: Seeds are used to construct few-shot examples in generation prompts (2-3 seeds per prompt for domain context)
- [ ] AC-4.6: Generated samples preserve the architectural intent of the seed while creating novel scenarios

### US-5: API provider abstraction
**Priority**: MUST
**Dependencies**: None

As the dataset builder, I want an `AnchorProvider` abstraction that supports multiple API backends (vLLM, OpenAI, Gemini) with unified interface so that backend selection is swappable and fallback is automatic.

**Acceptance Criteria:**
- [ ] AC-5.1: `AnchorProvider` defines interface with method: `generate(sample_config: dict) -> AnchorRecord | None`
- [ ] AC-5.2: `VLLMProvider` implementation connects to `localhost:8000` with `response_format: {"type": "json_object"}`
- [ ] AC-5.3: `OpenAIProvider` implementation uses `response_format: {"type": "json_object"}` with configurable model (default GPT-4o)
- [ ] AC-5.4: `GeminiProvider` implementation uses `response_mime_type: "application/json"` with configurable model (default Gemini 2.0 Flash)
- [ ] AC-5.5: Provider is configurable via CLI argument `--provider vllm|openai|gemini` (default: vllm)
- [ ] AC-5.6: Each provider supports temperature 0.3-0.5, max_tokens 8192, and configurable batch size
  - Justification: research.md analyzed 3000 estimated response tokens + ~2000 system prompt + ~1500 user prompt = ~6500 input+output. 4096 was too tight. 8192 provides 170% headroom.
- [ ] AC-5.7: Provider does NOT inherit from `TeacherProvider` -- it is a separate abstraction for static data production with different error handling (validation failures -> failed sample log, not retry)
- [ ] AC-5.8: Provider reuses HTTP connection infrastructure from existing code: `VLLMClient` and `GeminiClient` from `src/audit/inference.py` for raw HTTP POST patterns with JSON response handling; `TeacherModelConfig` from `src/factory/config.py` for configuration patterns. Note: does NOT reuse method contracts (existing clients return `str`, AnchorProvider returns `AnchorRecord | None`).

### US-6: Quality circuit breaker with circuit breaker fallback
**Priority**: MUST
**Dependencies**: US-5 (API provider), US-9 (failed sample log)

As the dataset builder, I want an automated quality circuit breaker that switches to a higher-quality backend if the primary backend produces too many invalid samples so that dataset quality is maintained without manual intervention.

**Acceptance Criteria:**
- [ ] AC-6.1: Quality check runs after every 10 samples (batch_size configurable, default 10)
- [ ] AC-6.2: Quality criteria evaluated per sample:
  - JSON schema validation passes (Pydantic model validation)
  - Field completeness: all required fields present
  - Anti-laziness: no occurrences of `...`, `# TODO`, `pass # implement`, `# resto del codigo`
  - Turn count compliance: generated turn_count within +/-1 of target
  - Self-assessed quality score >= 0.3 (sample includes a self-rating field)
  - Tool call validity: tool call names and arguments are syntactically valid
- [ ] AC-6.3: Failure rate threshold is parametrizable (`CIRCUIT_BREAKER_THRESHOLD`, default 0.2 = 2 failures per 10 samples)
- [ ] AC-6.4: If failure rate >= threshold: switch remaining samples to fallback provider (vLLM -> OpenAI)
- [ ] AC-6.5: Fallback threshold is calibrated empirically during the first 20 samples
- [ ] AC-6.6: Switched provider logs which provider is active and why
- [ ] AC-6.7: Circuit breaker resets if the primary provider passes a batch of 10 quality checks after fallback
- [ ] AC-6.8: Failed samples are logged with reason codes (see US-9)

### US-7: Generic and other domain synthesis
**Priority**: MUST (changed from SHOULD — without this, 30% of the domain distribution is impossible since generic_domain and other have 0 seeds)
**Dependencies**: US-3 (domain distribution), US-5 (API provider)

As the dataset builder, I want to synthesize samples for `generic_domain` and `other` categories from code patterns observed in reference repos and general programming knowledge so that all four target domains are covered.

**Acceptance Criteria:**
- [ ] AC-7.1: `generic_domain` samples are generated by treating patterns from the 5 HA reference repos as generic code migration scenarios (percentage of total, not fixed count — see US-3)
- [ ] AC-7.2: `other` samples are synthesized from general programming knowledge covering: `python_legacy`, `javascript_angular`, `yaml_configs`, `ha_addons` (percentage of total, not fixed count — see US-3)
- [ ] AC-7.3: No seeds required for these categories; generation prompts are constructed from domain templates
- [ ] AC-7.4: Domain templates specify: target legacy pattern, difficulty level, tool usage expectations, and expected trajectory characteristics
- [ ] AC-7.5: Generated samples for generic_domain and other are clearly labeled with their synthetic origin in metadata
- [ ] AC-7.6: At least 2 difficulty levels represented per sub-category (python_legacy, javascript_angular, etc.)

### US-8: Checkpoint and resume
**Priority**: MUST (changed from SHOULD — checkpoint is essential for a long-running generation process of 50-200 samples. Without it, any interruption loses all progress and the generator wastes API cost.)
**Dependencies**: US-5 (API provider), US-9 (failed sample log)

As the dataset builder, I want checkpoint/resume support so that generation can be paused and resumed without losing progress or duplicating samples.

**Acceptance Criteria:**
- [ ] AC-8.1: Checkpoint saved after every batch (default 10 samples) to `datasets/anchors/v1/.checkpoint.json`
- [ ] AC-8.2: Checkpoint includes: completed sample IDs, current domain/difficulty allocation, failed sample IDs, provider state, sample counter
- [ ] AC-8.3: Resume skips all completed sample IDs (idempotent by sample ID)
- [ ] AC-8.4: Resume skips all failed sample IDs that were logged in the failed sample log (same ID reused with fallback provider)
- [ ] AC-8.5: Checkpoint file is written atomically: write to `<path>.tmp` then `os.rename(tmp, path)` then `os.fsync(fd)`. If rename or fsync fails, `.tmp` file is deleted and error is raised. This ensures no partially-written checkpoint on disk.
- [ ] AC-8.6: If checkpoint is missing or corrupted, generation starts from scratch (logs warning)
- [ ] AC-8.7: `--resume` CLI flag restores from last checkpoint

### US-9: Failed sample log
**Priority**: MUST (changed from SHOULD — failed sample log is the only mechanism to track what went wrong and retry with fallback. Without it, quality assurance during generation is impossible.)
**Dependencies**: US-6 (circuit breaker)

As the dataset builder, I want failed samples logged with reason codes so that manual review and retry (with fallback provider) is possible.

**Acceptance Criteria:**
- [ ] AC-9.1: Failed samples written to `outputs/failed_samples.jsonl` (one JSON object per line)
- [ ] AC-9.2: Each entry includes: `sample_id`, `domain`, `difficulty`, `failure_reason` (enum: "schema_validation", "field_incomplete", "anti_laziness", "turn_count_mismatch", "self_assessed_quality", "tool_call_invalid", "json_parse_error", "api_error"), `provider` (which provider generated it), `attempt` (number of retries, 0 for first attempt), `raw_response` (truncated to 2000 chars)
- [ ] AC-9.3: Failed sample log is NOT a full dead letter queue -- it is a simple JSONL file for manual review and targeted retry
- [ ] AC-9.4: Retry with fallback provider is automatic for samples that failed due to provider-specific issues (json_parse_error, api_error)
- [ ] AC-9.5: Manual review required for semantic failures (schema_validation, anti_laziness, tool_call_invalid)
- [ ] AC-9.6: Failed sample log is created at project root (`outputs/failed_samples.jsonl`), not in the dataset directory

### US-10: JSONL export with manifest
**Priority**: MUST
**Dependencies**: US-1 (schema), US-6 (circuit breaker), US-8 (checkpoint)

As the dataset builder, I want generated samples exported to JSONL format with a manifest file so that the output is in the format expected by MIPROv2.

**Acceptance Criteria:**
- [ ] AC-10.1: Samples written to `datasets/anchors/v1/anchor_dataset.jsonl` (one JSON object per line, no wrapper array)
- [ ] AC-10.2: Atomic write: write to `<output>.tmp` then `os.rename(tmp, output)`, open the output file, call `os.fsync(fd)` on its file descriptor, then close the file
- [ ] AC-10.3: Each line is a valid JSON object matching the `AnchorRecord` Pydantic schema
- [ ] AC-10.4: Manifest written to `datasets/anchors/v1/anchor_manifest.json` with: `version` ("v1"), `created` (ISO8601 timestamp), `total_samples`, `domain_distribution` (dict with counts per domain), `difficulty_distribution` (dict with counts per difficulty), `provider_used` (string), `circuit_breaker_triggered` (bool), `failed_sample_count` (int)
- [ ] AC-10.5: Manifest includes domain_distribution and difficulty_distribution matching the enforced distribution (US-3)
- [ ] AC-10.6: Output directory (`datasets/anchors/v1/`) is created if it does not exist
- [ ] AC-10.7: Re-running generation with the same seeds produces identical sample IDs (idempotent IDs), though content may vary (non-deterministic generation is acceptable)

### US-11: DSPy Example conversion
**Priority**: SHOULD
**Dependencies**: US-1 (schema with DSPY_FIELD_MAP)

As an ML Engineer, I want a utility function that converts JSONL anchor samples to `dspy.Example(...).with_inputs("field")` format so that the generated dataset can be directly consumed by MIPROv2 optimizers.

**Acceptance Criteria:**
- [ ] AC-11.1: `jsonl_to_dspy_examples(path: str) -> list[dspy.Example]` function exists in `infrastructure/anchor_dataset_schema.py`
- [ ] AC-11.2: Function reads JSONL file, validates each record against `AnchorRecord` schema
- [ ] AC-11.3: Converts using `DSPY_FIELD_MAP`: input fields passed to `dspy.Example(...).with_inputs(...)`, label fields stored as example attributes
- [ ] AC-11.4: Returns a list of `dspy.Example` objects ready for `optimizer.compile()`
- [ ] AC-11.5: Function raises `ValueError` if any record fails schema validation
- [ ] AC-11.6: Function handles empty JSONL file gracefully (returns empty list)

### US-12: Manual verification workflow
**Priority**: SHOULD (changed from MUST — manual verification is a quality process, not a software feature. The builder works perfectly without it.)
**Dependencies**: US-10 (JSONL export)

As an ML Engineer, I want a documented verification workflow with a structured log so that ground truth labels can be manually validated without modifying the dataset files.

**Acceptance Criteria:**
- [ ] AC-12.1: `verification_log.json` records which samples have been verified, by whom, and when
- [ ] AC-12.2: Verification workflow documented: first 20 samples per domain fully verified, then 10% random spot-check of remaining
- [ ] AC-12.3: Each verification entry includes: `sample_id`, `verified_by` (name/initials), `verified_at` (ISO8601), `label_corrections` (optional dict of corrected fields), `confidence` (0.0-1.0)
- [ ] AC-12.4: Verification does NOT modify the dataset files -- corrections are recorded separately in the log
- [ ] AC-12.5: Verification workflow is documented in `docs/anchor-dataset-verification.md` including step-by-step checklist of what to verify per sample
- [ ] AC-12.6: Human verification cost is documented and communicated to the engineer before generation starts: the documented cost range appears in `docs/anchor-dataset-verification.md`

---

## Functional Requirements

### FR-001: Anchor record Pydantic schema
- [FR-001.1] `AnchorRecord` Pydantic model MUST be defined in `infrastructure/anchor_dataset_schema.py`
- [FR-001.2] Model fields: `id` (str, regex `r"^anchor_\d+_\d+$"`), `domain` (Literal["home_assistant", "php_legacy", "generic_domain", "other"]), `difficulty` (Literal["easy", "medium", "hard"]), `turn_count` (int, gt 0), `legacy_pattern` (str, min_length 1), `domain_context` (str, min_length 1), `expected_trajectory` (str, min_length 1), `expected_tool_usage_patterns` (list[str]), `expected_coherence` (float, ge 0.0, le 1.0), `expected_overall` (float, ge 0.0, le 1.0), `expected_optimized_parameters` (dict[str, Any], default_factory=dict), `expected_quality_score` (float, ge 0.0, le 1.0), `verified` (bool, default False), `verified_by` (str, default "")
- [FR-001.3] `AnchorManifest` Pydantic model MUST include: `version` (str, default "v1"), `created` (str, ISO8601 format), `total_samples` (int, gt 0), `domain_distribution` (dict[str, int]), `difficulty_distribution` (dict[str, int]), `provider_used` (str), `circuit_breaker_triggered` (bool, default False), `failed_sample_count` (int, default 0)
- [FR-001.4] `DSPY_FIELD_MAP` constant: `{"inputs": ["domain_context", "expected_trajectory", "difficulty", "turn_count", "legacy_pattern"], "labels": ["expected_tool_usage_patterns", "expected_coherence", "expected_overall", "expected_quality_score", "expected_optimized_parameters"]}`. The 5 label fields map to the three DSPy Signatures: TrajectorySignature uses `expected_tool_usage_patterns`, JudgeSignature uses `expected_coherence` + `expected_overall`, CalibrationSignature uses `expected_quality_score` + `expected_optimized_parameters`.
- [FR-001.5] Model MUST be strict: any field not defined in the model MUST cause validation failure

### FR-002: Dataset builder main script
- [FR-002.1] Script MUST exist at `infrastructure/anchor_dataset_builder.py`
- [FR-002.2] Script MUST accept CLI arguments: `--count` (total samples, default 50 for v0.1, upper bound 200 for v0.2), `--provider` (vllm|openai|gemini, default vllm), `--batch-size` (default 10), `--output-dir` (default `datasets/anchors/v1/`), `--resume` (flag), `--dry-run` (flag), `--seed` (random seed for reproducibility), `--timeout` (request timeout in seconds, default 60), `--max-retries` (max retries for rate-limited API responses, default 3), `--no-overwrite` (exit 1 if output file already exists), `--domain-distribution` (JSON string, e.g. `--domain-distribution '{"home_assistant":50,"php_legacy":25,"generic_domain":15,"other":10}'` to override default 40/30/20/10), `--difficulty-distribution` (JSON string, e.g. `--difficulty-distribution '{"easy":30,"medium":50,"hard":20}'` to override default 30/50/20)
- [FR-002.3] Script MUST provide a complete CLI with configurable arguments, pre-flight validation, structured user output, and semantic exit codes
- [FR-002.4] Script MUST create output directory if missing: `os.makedirs(output_dir, exist_ok=True)`
- [FR-002.5] Script MUST load seeds from `tests/fixtures/seed_examples.yaml` (graceful if missing)
- [FR-002.6] Script MUST enforce domain distribution: home_assistant=40%, php_legacy=30%, generic_domain=20%, other=10%
- [FR-002.7] Script MUST enforce difficulty distribution per domain: easy=30%, medium=50%, hard=20%
- [FR-002.8] Script MUST write JSONL output atomically: write to `.tmp` file then `os.rename()` then `os.fsync()`
- [FR-002.9] Script MUST support `--resume` flag to restore from checkpoint
- [FR-002.10] Script MUST support `--dry-run` flag: validate seeds, compute expected distribution, log planned generation, exit 0 without writing files
- [FR-002.11] Script MUST include Apache-2.0 license header (3 tokens within first 4096 bytes)
- [FR-002.12] Script MUST pass `ruff format` and `pyright` type checking
- [FR-002.13] Script MUST handle KeyboardInterrupt: save checkpoint, log clean shutdown, exit 1 with note that checkpoint exists for resume
- [FR-002.14] If output file exists and is non-empty, print warning to stderr: "Output file exists: {path}. Overwriting." Include a `--no-overwrite` flag that exits 1 instead of overwriting.

### FR-003: Seed data loader
- [FR-003.1] Seeds MUST be loaded from `tests/fixtures/seed_examples.yaml`
- [FR-003.2] Each seed normalized to: `id` (str), `domain` (str: "home_assistant" or "php_legacy"), `category` (str), `context` (str), `question` (str), `complexity` (str), `expected_patterns` (list[str])
- [FR-003.3] If seed file missing: log warning at INFO level, return empty list, continue generation (do not fail)
- [FR-003.4] Seed loading MUST be idempotent (multiple loads produce identical normalized output)

### FR-004: Sample configuration generator
- [FR-004.1] Generate `SampleConfig` dicts matching domain distribution (FR-002.6) and difficulty distribution (FR-002.7)
- [FR-004.2] Each config includes: `domain`, `difficulty`, `turn_count` (target, default 4), `legacy_pattern` (description string), `seed_id` (if available, synthetic pool name like "synthetic_generic_005" for unseeded domains), `variant_index` (per-seed variant number), `seed_pool` (numeric pool index: 1-8 HA, 9-13 PHP, 100+ generic_domain, 200+ other)
- [FR-004.3] HA/PHP configs derive `legacy_pattern` and `domain_context` from seed data
- [FR-004.4] Generic/other configs derive `legacy_pattern` and `domain_context` from domain templates (no seeds)
- [FR-004.5] `turn_count` varies by difficulty: easy=3, medium=4, hard=5-6 (configurable)
- [FR-004.6] Configs are deterministic given the same seed (for reproducibility)

### FR-005: Generation prompt construction
- [FR-005.1] System prompt includes: role definition, domain context, output schema specification, 2-3 few-shot examples, quality constraints
- [FR-005.2] User prompt includes: `domain_context`, `difficulty`, `turn_count`, `legacy_pattern`, specific generation instruction
- [FR-005.3] Output schema embedded in prompt matches the `AnchorRecord` Pydantic model fields
- [FR-005.4] Few-shot examples selected from seeds matching the target domain (if available)
- [FR-005.5] Quality constraints explicit: no lazy code (`...`, `# TODO`), complete implementations, valid tool calls, domain-specific best practices
- [FR-005.6] For generic_domain and other domains, few-shot examples sourced from HA reference repos as generic code patterns

### FR-006a: Provider connectivity and configuration
Startup sequence (strict ordering, all checked before generation begins):
1. **Validate CLI arguments** — parse and validate all arguments, fail with exit code 1 on invalid values
2. **Validate API keys** — check required env var for requested provider: `VLLM_API_KEY` for vllm, `OPENAI_API_KEY` for openai, `GOOGLE_API_KEY` for gemini. Missing key: fail with clear error message, exit code 1
3. **Health-check provider endpoint** — if `--provider vllm`, verify connectivity to `localhost:8000` via HTTP GET. If unreachable: fail with error message suggesting `--provider openai` fallback. For openai/gemini, no endpoint health check needed (cloud providers).
4. **Pre-flight seed validation** — load seeds, verify at least some exist for requested domains. Warn if generic_domain or other requested but no reference corpus available.
After startup passes all four steps, generation begins. API request-level behavior:
- [FR-006a.5] API requests MUST have configurable timeout (default 60s per request, via `--timeout` CLI argument)
- [FR-006a.6] Rate limit handling: exponential backoff with jitter for 429 responses (configurable max retries via `--max-retries`)

### FR-006: Provider implementations
- [FR-006.1] `AnchorProvider` interface defines: `generate(sample_config: dict) -> AnchorRecord | None`, `name` property (str)
- [FR-006.2] `VLLMProvider`: connects to `localhost:8000` with API key from `VLLM_API_KEY` env var (with documented development fallback), uses `response_format: {"type": "json_object"}`, model default `qwen3-5-35b-a3b-nvfp4`
- [FR-006.3] `OpenAIProvider`: uses `response_format: {"type": "json_object"}`, model configurable (default GPT-4o), API key from `OPENAI_API_KEY` env var
- [FR-006.4] `GeminiProvider`: uses `response_mime_type: "application/json"`, model configurable (default Gemini 2.0 Flash), API key from `GOOGLE_API_KEY` env var
- [FR-006.5] Provider retries only on network errors (connection refused, timeout, 429 rate limit) up to `--max-retries` times (default 3). Provider MUST NOT retry on semantic failures (schema validation failure, anti-laziness rejection, field incompleteness). After `--max-retries` network retries are exhausted, the provider returns `None` with an error classification (`"api_error"` or `"json_parse_error"` for network/parse, or any other reason for semantic failures).
- [FR-006.6] Provider MUST NOT inherit from `TeacherProvider` (separate abstraction)
- [FR-006.7] Provider returns `None` on any failure (network after retries exhausted, or semantic validation failure); caller routes to failed sample log with the appropriate `failure_reason` from FR-008.3. If the `failure_reason` is `"api_error"` or `"json_parse_error"`, the caller automatically retries with the fallback provider (per FR-008.4).

### FR-007: Quality circuit breaker
- [FR-007.1] Quality check runs after every `batch_size` samples (default 10)
- [FR-007.2] Quality checks per sample: (a) Pydantic validation, (b) field completeness (all required fields), (c) anti-laziness filter (no `...`, `# TODO`, `pass # implement`, `# resto del codigo`), (d) turn count within +/-1 of target, (e) tool call syntactic validity, (f) self-assessed quality >= 0.3
- [FR-007.3] Failure rate threshold: `CIRCUIT_BREAKER_THRESHOLD = 0.2` (2 failures per 10 samples)
- [FR-007.4] If failure rate >= threshold: switch to fallback provider (vLLM -> OpenAI), log switch event
- [FR-007.5] Circuit breaker resets if primary provider passes 10 consecutive quality checks after fallback
- [FR-007.6] Threshold calibrated empirically during first 20 samples (logs observed failure rate)
- [FR-007.7] Quality metrics are NOT LDI (code density != trajectory quality)

### FR-008: Failed sample logging
- [FR-008.1] Failed samples written to `outputs/failed_samples.jsonl` at project root
- [FR-008.2] Each entry: `sample_id`, `domain`, `difficulty`, `failure_reason` (enum), `provider`, `attempt` (int), `raw_response` (str, truncated to 2000 chars)
- [FR-008.3] Failure reasons: "schema_validation", "field_incomplete", "anti_laziness", "turn_count_mismatch", "self_assessed_quality", "tool_call_invalid", "json_parse_error", "api_error"
- [FR-008.4] Failed samples with `json_parse_error` or `api_error` are automatically retried with the fallback provider (per FR-006.7 retry routing). After fallback retry exhaustion, if still failing, the sample is logged with an additional `fallback_exhausted` flag.
- [FR-008.5] Failed samples with semantic reasons require manual review

### FR-009: Checkpoint/resume
- [FR-009.1] Checkpoint saved to `datasets/anchors/v1/.checkpoint.json` after each batch
- [FR-009.2] Checkpoint content: `completed_ids` (set of str), `failed_ids` (set of str with reason), `provider_active` (str), `sample_counter` (int), `domain_allocation_remaining` (dict), `timestamp` (ISO8601)
- [FR-009.3] Resume skips all completed IDs (no duplication)
- [FR-009.4] Resume re-tries failed IDs with fallback provider
- [FR-009.5] Checkpoint written atomically (temp file + rename)
- [FR-009.6] Corrupted/missing checkpoint: log warning, start from scratch

### FR-010: JSONL and manifest export
- [FR-010.1] JSONL written to `datasets/anchors/v1/anchor_dataset.jsonl` (one JSON per line)
- [FR-010.2] Manifest written to `datasets/anchors/v1/anchor_manifest.json`
- [FR-010.3] Manifest fields: `version`, `created`, `total_samples`, `domain_distribution`, `difficulty_distribution`, `provider_used`, `circuit_breaker_triggered`, `failed_sample_count`
- [FR-010.4] Both files written atomically (temp + rename + fsync)
- [FR-010.5] Re-run with same seeds produces same sample IDs (deterministic ID generation). ID format: `anchor_{seed_pool:03d}_{variant:02d}` where `seed_pool` is the seed index for seeded domains (HA=1-8, PHP=9-13) and a synthetic pool for unseeded domains: `generic_domain` uses pool 100-119, `other` uses pool 200-219. Example: `anchor_001_03` (HA seed 1 variant 3), `anchor_100_05` (generic_domain synthetic seed 5). ID format validated by regex `^anchor_\d+_\d+$`.

### FR-011: DSPy Example conversion utility
- [FR-011.1] `jsonl_to_dspy_examples(path: str) -> list[dspy.Example]` function in `infrastructure/anchor_dataset_schema.py`
- [FR-011.2] Reads JSONL, validates against `AnchorRecord`, maps fields per `DSPY_FIELD_MAP`
- [FR-011.3] Input fields passed to `.with_inputs(...)`, label fields set as attributes
- [FR-011.4] Raises `ValueError` on schema validation failure
- [FR-011.5] Returns empty list for empty JSONL file

### FR-012: Verification workflow and logging
- [FR-012.1] `verification_log.json` records: `sample_id`, `verified_by`, `verified_at`, `label_corrections` (optional dict[str, str] of corrected field names to their values), `confidence` (float 0.0-1.0)
- [FR-012.2] Verification workflow: first 20 samples per domain fully verified, then 10% random spot-check
- [FR-012.3] Verification does NOT modify dataset files
- [FR-012.4] Human verification cost documented and communicated before generation starts

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-001 | Generation throughput | Samples per hour (vLLM) | >= 120 samples/hour on local GPU |
| NFR-002 | Generation throughput | Samples per hour (OpenAI) | >= 300 samples/hour (respecting rate limits) |
| NFR-003 | Quality pass rate | Samples passing all quality checks per batch | >= 80% (circuit breaker triggers at 20% failure rate / 80% pass rate) |
| NFR-004 | Schema compliance | Samples passing Pydantic validation | 100% of exported samples |
| NFR-005 | File integrity | Atomic write success rate | 100% (temp + rename + fsync pattern) |
| NFR-006 | Idempotency | Re-run with same seeds produces same sample IDs | 100% (deterministic ID generation) |
| NFR-007 | Checkpoint reliability | Checkpoint file valid after interrupt | 100% (atomic checkpoint writes) |
| NFR-008 | API resilience | Automatic fallback on provider failure | Circuit breaker triggers within 1 batch (10 samples) |
| NFR-009 | Output size | JSONL file size for 200 samples | < 5 MB (each record ~20-25 KB average) |
| NFR-010 | Script conventions | ruff format + pyright compliance | All new scripts pass both tools |
| NFR-011 | License compliance | Apache-2.0 header present | All scripts have 3 required tokens within first 4096 bytes |
| NFR-012 | Human verification cost | Estimated hours per sample | 0.5-1.0 hours per sample for full verification |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Anchor Dataset** | Domain-specific training dataset of 100-200 samples with ground truth labels, used to bootstrap DSPy MIPROv2 optimization |
| **MIPROv2** | DSPy's automated prompt/Signature optimization algorithm. Compiles externalized prompts into optimized signatures using a training dataset and validation set |
| **DSPy** | Deep Learning Prompt You framework (v3.2.0) -- uses Python class docstrings for prompts, `dspy.Example` for training data |
| **dspy.Example** | DSPy data container. Created via `dspy.Example(field1=val1, field2=val2).with_inputs("field1", "field2")` where inputs are provided at compile time and labels are ground truth |
| **DSPY_FIELD_MAP** | Constant mapping JSONL record fields to DSPy input/label roles. Input fields passed to signatures, label fields used as ground truth for optimization |
| **TrajectorySignature** | DSPy Signature (defined in Epic 1, aegf-dspy-integration) — maps domain_context + expected_trajectory + difficulty + turn_count + legacy_pattern -> expected_tool_usage_patterns. Field-level definition deferred to Epic 1. |
| **JudgeSignature** | DSPy Signature (defined in Epic 1, aegf-dspy-integration) — maps expected_trajectory + domain_context -> expected_coherence + expected_overall. Field-level definition deferred to Epic 1. |
| **CalibrationSignature** | DSPy Signature (defined in Epic 1, aegf-dspy-integration) — maps expected_trajectory + expected_tool_usage_patterns -> expected_optimized_parameters + expected_quality_score. Field-level definition deferred to Epic 1. |
| **vLLM** | Self-hosted LLM inference server. Project runs `qwen3-5-35b-a3b-nvfp4` at `localhost:8000`. Primary backend for anchor generation |
| **OpenAI GPT-4o** | Cloud LLM with strongest structured output guarantees (guided decoding). Fallback backend |
| **Gemini 2.0 Flash** | Google's LLM with good JSON mode and lower cost. Secondary fallback / diversity source |
| **Circuit Breaker** | Quality monitoring pattern: check every N samples; if failure rate >= threshold, switch to fallback provider |
| **JSONL** | JSON Lines format: one JSON object per line, no wrapper array. Used for dataset storage |
| **Pydantic** | Python library for data validation using type annotations. Project uses Pydantic v2 |
| **AnchorRecord** | Pydantic model defining the structure of a single anchor dataset sample |
| **AnchorManifest** | Pydantic model defining the metadata about the generated dataset |
| **SampleConfig** | Internal configuration dict for a single sample generation task |
| **Seed Data** | Real project examples from `tests/fixtures/seed_examples.yaml` used as basis for generating variants |
| **Domain Distribution** | Target percentage breakdown: home_assistant=40%, php_legacy=30%, generic_domain=20%, other=10% |
| **Difficulty Distribution** | Per-domain breakdown: easy=30%, medium=50%, hard=20% |
| **Turn Count** | Number of conversation turns in the expected trajectory (default 4, varies by difficulty) |
| **Anti-laziness Filter** | Post-generation filter rejecting samples containing `...`, `# TODO`, `pass # implement`, `# resto del codigo` |
| **LDI (Length Density Index)** | Code quality metric measuring ratio of code/logic tokens to prose tokens. Explicitly NOT used as anchor quality metric (code density != trajectory quality) |
| **TeacherProvider** | Existing strategy pattern for agentic LLM execution (multi-turn tool use with side effects). NOT used for anchor generation |
| **AnchorProvider** | New abstraction for static data production. Reuses HTTP clients but has different error handling (validation failures -> failed sample log, not retry) |
| **v0.1** | Minimum viable dataset of 50 samples (bootstrap threshold for MIPROv2) |
| **V0.2** | Scaled dataset of 100-200 samples (full coverage) |
| **Verification Gap** | Risk that MIPROv2 optimizes on unverified ground truth labels. Mitigated by full verification of first 20 samples per domain |

---

## Out of Scope

- **DSPy Signature definitions** -- TrajectorySignature, JudgeSignature, CalibrationSignature definitions are in Epic 1 (aegf-dspy-integration)
- **Running MIPROv2 optimization** -- This spec generates the dataset; running the optimizer is a downstream spec
- **Running the optimized pipeline** -- Using optimized signatures is Epic 1 scope
- **Actual code migration** -- Anchor samples describe migration scenarios; this spec does not perform migrations
- **Modifying existing production code** -- Dataset generation is a standalone infrastructure tool
- **Automated quality scoring via judge.py** -- Ground truth labels are generated by LLMs and verified by humans; not scored by the project's judge system
- **LDI metric for anchor quality** -- LDI measures code density, not trajectory quality. Quality uses tool call validity, turn count compliance, field completeness, and self-assessed quality
- **Multi-turn generation for anchor data** -- Each sample's full trajectory is generated in a single API call (not iterative multi-turn)
- **Dead letter queue** -- Failed samples logged to JSONL for manual review, not stored in a formal DLQ system
- **Test suite** -- Integration tests requiring DSPy (US-11) are deferred to Epic 1. **EXCEPTION**: Schema validation tests (US-1 Pydantic model tests) are IN SCOPE -- they test the deliverable itself, not DSPy integration. Verification Contract explicitly lists "Schema validation" as P0.
- **CI/CD integration** -- Dataset generation is a manual/occasional operation, not a CI pipeline step
- **Historical dataset comparison or versioning** -- Manifest records version but no diffing or comparison tools
- **Deleting or modifying existing fixture files** -- Seed data is read-only input

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Spec: dependency-compatibility | Completed | numpy, scipy declared; ensures runtime environment supports Pydantic v2 |
| Spec: baseline-measurement | Completed | Baseline results provide quality reference for anchor validation |
| Spec: prompt-externalization | Completed | `.example.yaml` files provide English prompt templates for generation |
| `tests/fixtures/seed_examples.yaml` | Available | 8 HA seeds + 5 PHP legacy seeds (13 total) |
| `tests/fixtures/reference_corpus/homeassistant/` | Available | 5 HA repos (repo1-repo5) for generic_domain inspiration |
| `tests/fixtures/anchor_dataset_examples.json` | Available | Format reference fixtures for dataset downloader tests |
| `src/factory/agentic_teacher_client.py` | Available | `TeacherModelClient`, `TeacherProvider` -- underlying HTTP clients reused |
| `src/factory/config.py` | Available | `TeacherModelConfig` -- config pattern |
| `src/audit/inference.py` | Available | `VLLMClient`, `GeminiClient` -- underlying clients |
| `src/curation/anchor_dataset_downloader.py` | Available | Existing JSONL export pattern reference |
| vLLM server at `localhost:8000` | Required | `qwen3-5-35b-a3b-nvfp4` -- must be running before primary provider can be used |
| OpenAI API key (`OPENAI_API_KEY`) | Required for fallback | Fallback provider, required if circuit breaker triggers |
| Google API key (`GOOGLE_API_KEY`) | Optional | Gemini provider for diversity; not required for core generation |

---

## Success Criteria

- [ ] `infrastructure/anchor_dataset_builder.py` exists and runs without errors against seed data in dry-run mode (exits 0, logs planned generation)
- [ ] `infrastructure/anchor_dataset_schema.py` exists with `AnchorRecord`, `AnchorManifest`, `DSPY_FIELD_MAP`, and `jsonl_to_dspy_examples()`
- [ ] Running builder produces `datasets/anchors/v1/anchor_dataset.jsonl` with sample count equal to `--count` argument value
- [ ] Running builder produces `datasets/anchors/v1/anchor_manifest.json` with domain_distribution matching target (home_assistant=40%, php_legacy=30%, generic_domain=20%, other=10%, tolerance ±5 percentage points) and difficulty_distribution matching target (easy=30%, medium=50%, hard=20%)
- [ ] All samples in JSONL pass `AnchorRecord` Pydantic validation (0 validation failures in exported file)
- [ ] Domain distribution matches: home_assistant=40%, php_legacy=30%, generic_domain=20%, other=10% (±5 percentage points)
- [ ] Circuit breaker switches to fallback provider when failure rate >= CIRCUIT_BREAKER_THRESHOLD (default 0.2) across EVALUATION_BATCH_SIZE (default 10) samples, with log entry recording the switch event and active provider
- [ ] Checkpoint/resume works: interrupt during generation produces valid `.checkpoint.json`; resume with `--resume` flag produces no duplicate sample IDs (verified by checking all IDs in resumed output are new)
- [ ] `jsonl_to_dspy_examples()` produces valid `dspy.Example` objects with correct input/label mapping per `DSPY_FIELD_MAP` (stub in this spec: function exists, raises ImportError if DSPy not installed)
- [ ] Failed samples are logged to `outputs/failed_samples.jsonl` with valid JSON per line, each entry containing `sample_id`, `domain`, `difficulty`, `failure_reason` (valid enum value), `provider`, `attempt`, `raw_response` (truncated to 2000 chars)
- [ ] All new scripts pass `ruff format --check` and `pyright` with zero errors/warnings
- [ ] All new scripts include Apache-2.0 license header (3 required tokens within first 4096 bytes)
- [ ] Verification workflow is documented in `docs/anchor-dataset-verification.md` with step-by-step checklist
- [ ] Dry-run mode validates seeds and distribution without writing any files (exits 0, logs planned generation count per domain)

---

## Verification Contract

**Project type**: `cli-tool` (data generation tool)

This spec creates a CLI tool (`infrastructure/anchor_dataset_builder.py`) that reads seed data from fixtures and generates anchor dataset files. The tool depends on external LLM inference services (vLLM, OpenAI, Gemini) via HTTP. No HTTP server, no browser UI, no API endpoints.

**Entry points**:
- CLI: `python infrastructure/anchor_dataset_builder.py --count 50 --provider vllm --output-dir datasets/anchors/v1/`
- CLI: `python infrastructure/anchor_dataset_builder.py --dry-run` (pre-flight validation)
- CLI: `python infrastructure/anchor_dataset_builder.py --resume` (resume from checkpoint)
- File reads: `tests/fixtures/seed_examples.yaml`, `src/factory/agentic_teacher_client.py` (for underlying HTTP clients)
- File writes: `datasets/anchors/v1/anchor_dataset.jsonl`, `datasets/anchors/v1/anchor_manifest.json`, `datasets/anchors/v1/.checkpoint.json`, `outputs/failed_samples.jsonl`
- Import: `infrastructure/anchor_dataset_schema.py` (AnchorRecord, AnchorManifest, DSPY_FIELD_MAP)

**Observable signals**:
- PASS: Script exits with code 0, output JSONL file exists with sample count == `--count` argument value (default 50), manifest matches distribution, all records pass Pydantic validation
- FAIL: Script exits with code 1, stderr contains error, output files missing, schema validation fails, or domain distribution deviates from targets
- Quality PASS: >= 80% of samples pass all FR-007.2 quality criteria per batch (Pydantic validation + field completeness + anti-laziness + turn count compliance + tool call validity + self-assessed quality >= 0.3)
- Circuit Breaker PASS: When >= 2/10 samples fail quality checks in a batch, provider switches to fallback with log message
- Idempotency PASS: Re-running with same seeds produces identical sample IDs
- Resume PASS: Interrupted run resumes without duplicating completed samples

**Hard invariants**:
- Auth/session: external API keys from environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`); vLLM uses local config
- Data integrity: output JSONL files written atomically (temp + rename + fsync)
- Import safety: scripts must not modify any files in `tests/fixtures/`, `src/`, `configs/`
- Adjacent flows: seed data is read-only; baseline results are read-only; `.example.yaml` files are read-only
- License compliance: all scripts include Apache-2.0 header (3 tokens within first 4096 bytes)
- Schema compliance: all exported samples MUST pass `AnchorRecord` validation; no exceptions

**Seed data**:
- `tests/fixtures/seed_examples.yaml`: 8 HA seeds + 5 PHP legacy seeds. Used to construct generation prompts with few-shot examples. Required for HA and PHP domain generation.
- `tests/fixtures/reference_corpus/homeassistant/`: 5 repos (repo1-repo5). Used for generic_domain sample synthesis when no seeds are available.
- `tests/fixtures/anchor_dataset_examples.json`: Format reference fixtures. NOT used as ground truth; format reference only.

**Test strategy** (14 categories):

| # | Category | What it tests | Priority |
|---|----------|---------------|----------|
| 1 | Schema validation | All generated records pass `AnchorRecord` Pydantic validation (field types, range checks, regex on `id`) | P0 |
| 2 | JSON mode reliability | Each backend (vLLM, OpenAI, Gemini) produces parseable JSON on 20+ samples with stub/mock responses | P0 |
| 3 | Provider unit tests | VLLMProvider, OpenAIProvider, GeminiProvider: constructor with valid/invalid API key, `generate()` with valid JSON response, `generate()` with non-JSON response (returns None), `generate()` with timeout (mock), `name` property returns correct string | P0 |
| 4 | Circuit breaker | Correctly triggers when failure rate >= threshold; correctly resets after 10 consecutive passes | P0 |
| 5 | Failed sample log | Failed samples logged with correct reason codes; file format valid JSONL; retry routing for api_error/json_parse_error | P1 |
| 6 | Idempotency | Re-running with same seeds produces same sample IDs (not duplicated); generic/other synthetic IDs also deterministic | P1 |
| 7 | JSONL export | Atomic write (.tmp -> rename -> fsync), file integrity after partial writes, error contract on rename/fsync failure | P1 |
| 8 | Seed loader | Correct YAML parsing, graceful handling of missing file (log warning + empty list), idempotent loads, malformed YAML handling | P1 |
| 9 | Domain distribution math | count=50: HA=20, PHP=15, Generic=10, Other=5; count=110: HA=44, PHP=33, Generic=22, Other=11; count=200: HA=80, PHP=60, Generic=40, Other=20; rounding algorithm specified (round half up, distribute remainder to largest domains first) | P1 |
| 10 | Edge cases | (a) 0 seeds for generic_domain/other → template-based generation produces valid samples; (b) valid JSON but garbage trajectory → fails anti-laziness, logged to failed sample log; (c) partial completion → checkpoint is valid JSON, resume skips completed IDs; (d) malformed API responses (503, timeout, empty body) → circuit breaker or fallback triggered appropriately; (e) network timeout during generation → retry with backoff; (f) rate limit 429 → exponential backoff with jitter; (g) read-only output directory → clear error message; (h) API returns valid JSON but schema doesn't match → returns None, logged to failed sample log | P1 |
| 11 | CLI argument parsing | `--count 50` produces 50 samples, `--provider openai` uses OpenAIProvider, `--resume` loads checkpoint, `--dry-run` writes nothing, default values correct, `--domain-distribution` overrides default distribution, `--difficulty-distribution` overrides default | P1 |
| 12 | KeyboardInterrupt | Signal saves checkpoint, logs clean shutdown message, exits with code 1, checkpoint file is valid for resume | P1 |
| 13 | DSPy conversion | `jsonl_to_dspy_examples()` produces valid `dspy.Example.with_inputs()` declarations with correct field mapping per `DSPY_FIELD_MAP` | P0 (deferred to Epic 1 — stub implementation required: validates function exists, raises `ImportError` with guidance if DSPy not installed) |
| 14 | Prompt construction | Generated prompts include: role definition, domain context, output schema, 2-3 few-shot examples from correct domain, quality constraints (no lazy code) | P2 |

**Escalate if**:
- vLLM server is not running and no OpenAI API key is available (no generation possible)
- `qwen3-5-35b-a3b-nvfp4` does not support JSON mode (circuit breaker triggers immediately, falls back to OpenAI for everything)
- Circuit breaker threshold never met but quality is still poor (suggests quality criteria are not discriminating enough)
- Seed data is insufficient for target domain (generic_domain and other have 0 seeds; generation must rely entirely on templates)
- Human verification bottleneck becomes a schedule risk (> 100 hours for 100+ samples)

---

## Next Steps

1. [PREREQ] Verify vLLM server is running at `localhost:8000` with `qwen3-5-35b-a3b-nvfp4` and JSON mode works (test with 1 sample)
2. [PREREQ] Verify OpenAI API key is available (`OPENAI_API_KEY` env var set) for fallback
3. [FR-001] Create `infrastructure/anchor_dataset_schema.py` with `AnchorRecord`, `AnchorManifest`, `DSPY_FIELD_MAP`
4. [FR-003] Implement seed loader for `tests/fixtures/seed_examples.yaml`
5. [FR-005] Implement generation prompt templates for each domain (HA, PHP, Generic, Other)
6. [FR-006] Implement `AnchorProvider` interface + `VLLMProvider` (primary)
7. [FR-006] Implement `OpenAIProvider` (fallback)
8. [FR-007] Implement quality circuit breaker with parametrizable threshold
9. [FR-008] Implement failed sample log (`outputs/failed_samples.jsonl`)
10. [FR-009] Implement checkpoint/resume (`.checkpoint.json`)
11. [FR-010] Implement JSONL + manifest export with atomic writes
12. [FR-011] Implement `jsonl_to_dspy_examples()` conversion utility
13. [FR-012] Document verification workflow and create `verification_log.json` schema
14. [FR-002] Assemble main script `infrastructure/anchor_dataset_builder.py`
15. Run dry-run against seed data to validate distribution
16. Run full generation with vLLM (primary) + circuit breaker monitoring
17. If circuit breaker triggers: verify fallback to OpenAI works correctly
18. Begin human verification (first 20 samples per domain, then 10% spot-check)
19. Commit and push

---

## Sources

- `specs/anchor-dataset/plan.md` -- Story 0.3 acceptance criteria, interface contracts, domain distribution, MVP scope
- `specs/anchor-dataset/research.md` -- API comparison, prompt strategies, DSPY_FIELD_MAP, circuit breaker pattern, seed gap analysis, testing strategy
- `specs/_epics/aegf-infrastructure/epics.md` -- Story 0.3, critical path context (severity 9/10)
- `specs/baseline-measurement/requirements.md` -- Format convention reference (CLI pattern, Rich CLI, file conventions)
- `specs/prompt-externalization/requirements.md` -- Format convention reference (user story structure, verification contract)
- `_bmad-output/planning-artifacts/epics.md` -- BMAD Story 0.3 anchor dataset creation
- `tests/fixtures/seed_examples.yaml` -- 13 seeds (8 HA + 5 PHP legacy)
- `tests/fixtures/reference_corpus/homeassistant/` -- 5 HA repos for generic_domain synthesis
- `tests/fixtures/anchor_dataset_examples.json` -- Format reference fixtures
- `.github/skills/dspy/references/optimizers.md` -- MIPROv2 requirements (50-200 examples, valset, 100-200 trials)
- `src/factory/agentic_teacher_client.py` -- TeacherProvider pattern, HTTP clients
- `src/factory/config.py` -- TeacherModelConfig dataclass
- `src/audit/inference.py` -- VLLMClient, GeminiClient, BaseInferenceClient
- `src/curation/anchor_dataset_downloader.py` -- JSONL export pattern
