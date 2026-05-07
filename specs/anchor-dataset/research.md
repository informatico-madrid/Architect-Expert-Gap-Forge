---
spec: anchor-dataset
phase: research
created: 2026-04-25T00:00:00Z
---

# Research: Anchor Dataset Builder — API Comparison, Prompt Strategies, Structured Output

## Executive Summary

MIPROv2 requires 50-200 domain-specific anchor samples with ground truth to compile DSPy signatures. Three API backends are viable: OpenAI (best structured output guarantees, per-token cost), vLLM (self-hosted, free after hardware, JSON mode available via `response_format`), and Gemini (good JSON mode, cheaper than OpenAI for large batches). **Recommendation**: Start with vLLM for cost efficiency since the project already runs a local server at `localhost:8000`, with automatic circuit breaker → OpenAI fallback if quality thresholds are breached. vLLM model (`qwen3-5-35b-a3b-nvfp4`) JSON mode capability must be validated before committing to this strategy.

## External Research

### DSPy MIPROv2 Requirements (source: `.github/skills/dspy/references/optimizers.md`)

| Parameter | Value | Note |
|-----------|-------|------|
| Training examples | 50-200 | Per signature (TrajectorySignature, JudgeSignature, CalibrationSignature) |
| Validation set | 20-50 examples | Separate from training, used during optimization |
| Num trials | 100-200 | More trials = better quality, longer optimization |
| Training time | 10-30 min typical | Depends on model, dataset size |
| Example format | `dspy.Example(...).with_inputs("field")` | Each example must declare inputs |

**Critical finding**: MIPROv2 iteratively searches for better instructions and evaluates each candidate on the validation set. It requires a separate `valset` parameter in `optimizer.compile()`.

### Prompt Engineering for Anchor Generation

**Pattern observed in existing code** (`legacy/generate_batch_test_chunked.py`, `src/research/generate_batch_distilabel.py`):

1. **Few-shot in system prompt**: The project already embeds complete few-shot examples in the system prompt using a formal grammar specification (`RESPONSE ::= THINK_BLOCK TOOL_BLOCK`).
2. **Multi-turn trajectory generation**: 4 turns per sample — user, assistant (with tool_call), tool response, assistant (with attempt_completion).
3. **Logic Density Index (LDI)**: Ratio > 2.5:1 (code/logic tokens vs prose tokens) is the quality target.
4. **Post-generation filtering**: Anti-laziness filter rejects samples containing `...`, `# resto del código`, `pass # TODO`.

**Recommended prompt pattern for anchors**:

```
System: Role + domain context + output schema + few-shot examples (2-3) + quality constraints
User: domain_context + difficulty + specific generation task
```

Key prompt components:
- Domain context (Home Assistant, PHP Legacy, Generic)
- Difficulty level (easy/medium/hard)
- Turn count constraint
- Expected legacy pattern
- Output schema specification
- 2-3 few-shot examples in the target format
- Quality constraints (no lazy code, complete implementations)

### Cost Estimates

#### Generation Cost (API/Hardware)

Assuming 50-200 samples, each with:
- System prompt: ~2000 tokens
- User prompt: ~1500 tokens
- Response: ~3000 tokens (multi-turn trajectory with tool calls)

**OpenAI GPT-4o** (per 1M tokens):
- Input: $2.50/M, Output: $10.00/M
- Per sample: ~6500 input + ~3000 output = $0.016-$0.065
- 100 samples: $1.60-$6.50
- 200 samples: $3.20-$13.00

**Gemini 2.0 Flash** (per 1M tokens):
- Input: $0: $0.10/M, Output: $0.40/M
- Per sample: ~$0.001-$0.004
- 100 samples: $0.10-$0.40
- 200 samples: $0.20-$0.80

**vLLM (self-hosted)**:
- Cost: electricity + GPU depreciation
- Latency: ~2-10s per sample on local GPU
- No per-token cost

#### Human Verification Cost (Critical — previously omitted)

The BMAD story claims "100-200 manually verified samples = ~100-200 human-hours." Each anchor sample requires:
- Reading the generated trajectory
- Validating tool calls are executable and correct
- Verifying ground truth labels (coherence, quality_score)
- Checking domain assignment accuracy

| Samples | Estimated human-hours | Estimated cost (@$50/hr) |
|---------|----------------------|-------------------------|
| 50 | 25-50h | $1,250-$2,500 |
| 100 | 50-100h | $2,500-$5,000 |
| 200 | 100-200h | $5,000-$10,000 |

**Implication**: Human verification is 100-500x more expensive than generation. The architecture must minimize verification effort through:
- Automated pre-validation (JSON schema, field completeness, basic quality heuristics)
- Sampling-based review (verify first 20 fully, then spot-check remaining)
- Progressive verification (verify during generation, not as a separate batch)

### Structured Output Formats Comparison

| Feature | OpenAI | Gemini | vLLM |
|---------|--------|--------|------|
| JSON mode | `response_format: {"type": "json_object"}` | `response_mime_type: "application/json"` | `response_format: {"type": "json_object"}` (via extra_body) |
| Schema enforcement | `response_format: {"type": "json_schema", "json_schema": {...}}` | `response_schema: {...}` | `response_format: {"type": "json_schema"}` (via extra_body, enforcement quality varies by model) |
| Structural tags | **Not supported** | Not supported | **Not supported** |
| Function calling | `tools: [{function: {...}}]` | `tools: [{functionDeclarations: [...]}]` | Via OpenAI-compatible `tools` param |
| Schema support level | Strong (guided decoding) | Good (constrained generation) | Adequate (runtime accepts schema, quality depends on model's instruction-following) |
| Best for anchors | **Highest fidelity** | Good balance of cost/quality | Adequate for structured output |

**Recommendation**: For anchor generation, use **JSON mode** (not function calling) because we need to generate static data records, not execute functions. The schema should match the JSONL record format from the spec.

## Codebase Analysis

### Existing Infrastructure (source: project codebase)

**Already available and reusable**:
- `TeacherModelClient` / `TeacherProvider` strategy pattern — provides OpenAI, Anthropic, Gemini backends with retry, backoff, checkpoints
- `VLLMClient` / `InferenceRouter` in `src/audit/inference.py` — vLLM and Gemini clients with retry logic
- `AgenticTrajectory` Pydantic model — defines trajectory structure with turns and tool calls
- `src/factory/config.py` — `TeacherModelConfig` dataclass with provider, model, retries, timeouts
- `src/curation/anchor_dataset_downloader.py` — existing pattern for downloading, parsing, exporting datasets to JSONL
- Seed fixtures: `tests/fixtures/seed_examples.yaml` (8 HA + 5 PHP legacy seeds)
- Calibration fixtures: `tests/fixtures/calibration_examples.json` (5 prompts with scoring)

**CRITICAL SEED GAP**: The 4-domain distribution (40% HA, 30% PHP, 20% Generic, 10% Other) has 0 seeds for `generic_domain` and `other`. Seed data is only available for `home_assistant` and `php_legacy`. This means:
- HA samples: Can generate from 8 real seeds × 5 variants = 40 samples ✓
- PHP samples: Can generate from 5 real seeds × 6 variants = 30 samples ✓
- Generic samples: Must use reference corpus (5 HA repos) for domain context inspiration, but no direct seeds. Use "generic code review / migration assistance" as the domain.
- Other samples: Must synthesize from general programming knowledge. Use "python_legacy", "javascript_angular", etc. as examples.
- **Recommendation**: For generic_domain and other, generate prompts from patterns observed in the 5 Home Assistant reference repos, treating them as generic code patterns rather than HA-specific.
- Existing generation pattern: 4-turn conversations with tool calls and XML format

**Existing OpenAI client usage** (from `legacy/generate_batch_test_chunked.py`):
```python
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key=os.environ.get("VLLM_API_KEY")  # from config.py DEFAULT_MODEL config
)
```

### Anchor Dataset Record Schema (from spec)

```json
{
  "id": "anchor_001",
  "domain": "home_assistant|php_legacy|generic_domain|other",
  "difficulty": "easy|medium|hard",
  "turn_count": 4,
  "legacy_pattern": "string",
  "domain_context": "string",
  "expected_trajectory": "string",
  "expected_tool_usage_patterns": ["string"],
  "expected_coherence": 0.85,
  "expected_overall": 0.80,
  "expected_optimized_parameters": {},
  "expected_quality_score": 0.82,
  "verified": true,
  "verified_by": "string"
}
```

### API Comparison

| Aspect | OpenAI | Gemini | vLLM |
|--------|--------|--------|------|
| Structured output | Strongest (guided decoding) | Good (constrained gen) | Good (model-dependent) |
| Schema enforcement | JSON Schema type | response_schema | extra_body + model |
| Latency (1 sample) | ~1-3s (GPT-4o) | ~1-5s | ~2-10s (local) |
| Cost per 100 samples | $1.60-$6.50 | $0.10-$0.40 | Free (own hardware) |
| API key required | Yes | Yes | No (localhost) |
| Rate limits | Yes | Yes | Only hardware limit |
| Model flexibility | GPT-4o, o-series | Gemini 2.0 Flash, Pro | Any HuggingFace model |
| Existing integration | TeacherProvider | TeacherProvider, VLLMClient | InferenceRouter |

### Recommended Generation Strategy

**Primary approach: vLLM first with circuit breaker → OpenAI fallback**

1. **Phase 1** (cost-efficient): Generate all anchors via vLLM local server
   - Use `response_format: {"type": "json_object"}` for structured output
   - Temperature 0.3-0.5 for deterministic output
   - max_tokens 4096 for complete trajectories
   - Multi-turn: generate full trajectory in one call (system prompt + few-shot + user request)

2. **Circuit Breaker Pattern** (MUST IMPLEMENT):
   - After every N samples (batch of 10), run automated quality checks:
     - JSON schema validation (100% pass required)
     - Field completeness (all required fields present)
     - Anti-laziness filter (no `...`, `# TODO`, `pass # implement`)
     - **Trajectory quality heuristic**: tool call validity + turn count compliance + field completeness (NOT LDI — LDI measures code density, not trajectory quality)
   - **Fallback threshold**: `≥2/10` is an initial default; make this **parametrizable** (`CIRCUIT_BREAKER_THRESHOLD = 0.2` by default). Calibrate empirically during first 20 samples.
   - **Automatic degradation**: Route remaining samples to OpenAI (or Gemini) until vLLM is verified
   - **Quality criteria for vLLM pass**: Valid tool calls, no lazy patterns, all required fields present, turn count within ±1 of target, self-assessed quality score ≥ 0.3 (catches garbage that passes structural checks)
   - **Failed sample log**: NOT a full dead letter queue — for a one-off dataset generation, a simple JSONL log (`outputs/failed_samples.jsonl`) with reason codes is sufficient. Supports manual review and retry with OpenAI if needed.

3. **Phase 2** (quality boost): If circuit breaker triggers, fall back to OpenAI
   - Higher structured output guarantees (guided decoding)
   - Better reasoning in generated trajectories
   - Cost impact: up to $13.00 for 200 samples via OpenAI fallback

4. **Phase 3** (alternative): Use Gemini for additional diversity if needed
   - Cheaper than OpenAI, good JSON mode
   - Good for generating PHP legacy samples where reasoning is less critical

### dspy.Example Schema Mapping (CRITICAL — John PM flagged this as architectural decision)

**Problem**: The spec outputs JSONL records, but MIPROv2 requires `dspy.Example(...).with_inputs("field")` format.

**Two approaches evaluated:**

1. **Converter module** (separate layer): Generate JSONL → convert to dspy.Example. Risk: type information lost in conversion, parsing bugs, two atomic operations with friction point.

2. **dspy-compatible schema from the start** (recommended): The anchor record schema includes fields explicitly mapped to dspy input/label. JSONL is storage format; schema understands its dspy destination. Eliminates the conversion layer entirely.

**Recommendation**: Approach 2. Add explicit field mapping to the anchor record schema:
```
Input fields (passed to signature): domain_context, expected_trajectory, difficulty, turn_count, legacy_pattern
Label fields (used as ground truth): expected_tool_usage_patterns, expected_coherence, expected_overall, expected_quality_score, expected_optimized_parameters
```

**DISCREPANCY RESOLVED**: The BMAD plan.md acceptance criteria lists `difficulty`, `turn_count`, and `legacy_pattern` as DSPy inputs alongside `domain_context` and `expected_trajectory`. These MUST be included in the DSPY_FIELD_MAP, not omitted as initially planned.
The generation pipeline writes JSONL (storage format) but the schema defines dspy mapping. The "conversion" is a field selector, not a parser. This means `anchor_dataset_schema.py` must include a `DSPY_FIELD_MAP` constant.

**MIPROv2 total sample count clarification**: The optimizers.md says "50-200 training examples PER SIGNATURE." There are 3 signatures (TrajectorySignature, JudgeSignature, CalibrationSignature). This could mean 50-200 × 3 = 150-600 total. However, DSPy examples are often shared across signatures (the same trajectory is used as input for multiple signatures). The spec's "100-200 total" appears correct if examples are shared. **Action**: Confirm with TrajectorySignature/JudgeSignature definitions in the codebase before implementation.

### Prompt Pattern for Anchor Generation

**System prompt structure**:
```
You are a domain expert tasked with generating training anchor samples for AI model optimization.

DOMAIN: {domain}
DOMAIN CONTEXT: {context_description}
DIFFICULTY: {difficulty}
EXPECTED TURN COUNT: {turn_count}
LEGACY PATTERN TO DETECT/MIGRATE: {legacy_pattern}

OUTPUT FORMAT:
Generate a JSON object with this exact schema:
{schema_definition}

FEW-SHOT EXAMPLES:
{2-3 examples matching the domain}

QUALITY CONSTRAINTS:
- Complete code implementations (no stubs or placeholders)
- Follow {domain} best practices and standards
- Include proper error handling
- Tool calls must be valid and executable
- No lazy patterns: ... , # TODO, pass # implement here
```

**User prompt structure**:
```
Generate an anchor sample for the following scenario:

Task: {specific_generation_instruction}
Domain: {domain}
Difficulty: {difficulty}

Include:
1. A realistic domain_context
2. Expected trajectory (multi-turn conversation)
3. Tool usage patterns
4. Ground truth labels (coherence, overall, quality_score)
```

## Label Generation Methodology (Heuristic-Assisted, NOT Ground Truth)

**Critical distinction**: The labels produced by the generation prompt are **heuristic-assisted scores**, not ground truth. Ground truth is established by human verification of the first 20 samples per domain. The self-assessed labels serve as a structural sanity filter (rejecting garbage) and provide a first-pass dataset for MIPROv2 bootstrap.

**Approach: self-assessment via LLM**

The anchor generation prompt itself produces the labels. The same model that generates the trajectory also assesses its own output:

```
After generating the trajectory, produce the following self-assessment:

{
  "expected_tool_usage_patterns": [...],
  "expected_coherence": <float 0.0-1.0>,
  "expected_overall": <float 0.0-1.0>,
  "expected_quality_score": <float 0.0-1.0>,
  "expected_optimized_parameters": {...}
}

Assessment criteria:
- coherence: How well does the trajectory flow? Does each turn logically follow from the previous?
- overall: How useful would this sample be for training an AI model to handle migrations?
- quality_score: Does the sample meet all quality constraints (complete code, valid tool calls, no lazy patterns)?
- expected_optimized_parameters: {
    "trajectory_instruction_template": "string — prompt template for trajectory generation",
    "judge_instruction_template": "string — prompt template for coherence/overall judgment",
    "quality_threshold": float — the minimum quality_score to consider a sample valid
  }
```

**Why this approach works:**
1. **Cost**: No additional API calls — labels are produced in the same generation call
2. **Consistency**: The same model that generated the trajectory assesses it, ensuring internal consistency

**Calibration phase** (CRITICAL — do not skip):
1. **Warmup (5 samples)**: Generate 5 samples with no circuit breaker. Log all scores.
2. **Calibration (first 20 samples)**: Review self-assessed score distribution. If >70% score >0.7, raise threshold to 0.4. If <30% score >0.3, lower threshold to 0.2. Adjust prompt wording (not the threshold number) based on score distribution.
3. **Production (remaining samples)**: Apply calibrated threshold. Circuit breaker at 0.2.

**Quality gate**: Samples with self-assessed quality < 0.3 are rejected and retried. This is a heuristic filter — it catches garbage but lets mediocre samples through.

**Limitation acknowledged**: Self-assessed scores are biased (models tend to overestimate their own quality). Acceptable for anchor generation because:
1. The circuit breaker filters out clearly bad samples (≤20% failure rate)
2. The first 20 samples per domain get full human verification — these human-corrected values become the calibration baseline for MIPROv2
3. The self-assessed labels for unverified samples are "good enough" for a bootstrap optimizer
4. The goal is MIPROv2 bootstrapping, not production-grade ground truth

**Human vs self-assessed labels for MIPROv2**: For the first 20 verified samples per domain, use human-corrected labels. For all other samples, use self-assessed labels. The human verification step (US-12) is the only step that produces actual ground truth.

## Recommendations for Design Phase (NOT Requirements)

**Note for handoff**: These are technical design preferences, not requirements. The requirements phase should translate these into "what" not "how."

1. **Pydantic v2 models** for anchor record validation — the project already uses Pydantic v2 consistently. Create models in `infrastructure/anchor_dataset_schema.py`.

2. **Separate AnchorProvider** (NOT inheriting from TeacherProvider) — `TeacherProvider` is designed for agentic execution. Anchor generation is static data production. Build a thin HTTP client wrapper reusing the underlying clients (OpenAI, vLLM, Gemini) with different error handling: validation failures → failed sample log (not retry), network failures → retry.

3. **JSON mode** (not function calling) for structured output — we're generating static data, not executing functions.

4. **Generate one trajectory per API call** — put the full trajectory (all turns) in a single field as a string or conversation array. Faster, cheaper, full context.

5. **Seed from existing fixtures** — ⚠️ **Seed gap**: Only 8 HA + 5 PHP seeds exist. For `generic_domain` and `other`, generate prompts from patterns in the 5 HA reference repos. See "CRITICAL SEED GAP" section above.

6. **Batch size** is a configuration parameter, not a requirement. Default 10-20 per run for rate limit safety.

7. **JSONL output format** — one record per line, matching the spec schema. Atomic write (.tmp → rename). Each record is a JSON object with the schema defined above. **Note**: This defines a single record's structure; the file is JSONL (one object per line, no wrapper array).


## Open Questions → Design Phase Carryover

These are resolved design decisions (not open questions) and remaining items for the design phase:

### Resolved in Research

| # | Question | Resolution | Rationale |
|---|----------|-----------|-----------|
| 1 | vLLM JSON mode? | Validate with test sample before commit. If fails, use OpenAI. | Circuit breaker handles this gracefully. |
| 2 | JSON Schema vs JSON Object? | JSON Object + post-validation. Upgrade to Schema if quality insufficient. | Cheaper; post-validation catches errors. |
| 3 | Trajectory format? | String (full multi-turn conversation serialized to a single string). | Matches the AnchorRecord schema field type. Parsing into turns is a post-processing step. |
| 4 | Quality metric? | Tool call validity + turn count compliance + field completeness. LDI replaced (code density ≠ trajectory quality). | Directly relevant to MIPROv2 needs. |
| 5 | Checkpoint granularity? | Per-batch (10 samples), idempotent by sample id. | Balance between resume frequency and overhead. |
| 6 | Verification coverage? | Full verify first 20/domain + random 10% of remaining. Log to `verification_log.json`. | Pragmatic tradeoff given human bottleneck. |

### Architectural Risk — Verification Gap

**Issue**: MIPROv2 optimizes on ground truth labels. If only 30-50 of 200 samples are verified, the remaining 150-170 have unverified ground truth. **This is an architectural constraint, not a project management concern.** MIPROv2 with dirty ground truth optimizes toward noise.

**Mitigations**:
1. Automated pre-validation (schema, completeness, quality heuristics) catches obvious errors before human review
2. First 20 per domain fully verified establish "ground truth baseline" — human can identify error patterns
3. If automated pre-validation passes >95% of samples, human verification burden drops significantly
4. **If verification gap is unacceptable**: Reduce total to 100 samples, verify 100% of first 20 domains + 100% random sample of remaining

### For Design Phase to Resolve

| # | Item | Impact |
|---|------|--------|
| 7 | vLLM server `qwen3-5-35b-a3b-nvfp4` running status | If not running, start with OpenAI |
| 8 | MIPROv2 signatures definition | Need TrajectorySignature, JudgeSignature, CalibrationSignature definitions |
| 9 | `expected_optimized_parameters` schema field | Review what MIPROv2 actually optimizes |
| 10 | AnchorProvider interface contract | Define HTTP client abstraction |

## Sources

| Source | Key Point |
|--------|-----------|
| `.github/skills/dspy/references/optimizers.md` | MIPRO needs 50-200 examples, separate valset, 100-200 trials |
| `.github/skills/dspy/SKILL.md` | DSPy signatures, modules, LM providers, structured output patterns |
| `.github/skills/dspy/references/examples.md` | DSPy example patterns, training data format |
| `specs/anchor-dataset/plan.md` | Anchor dataset requirements, schema, domain distribution |
| `specs/anchor-dataset/.progress.md` | Smart Ralph session status, key claims to verify |
| `src/factory/agentic_teacher_client.py` | TeacherProvider strategy pattern, retry logic, providers |
| `src/factory/config.py` | TeacherModelConfig, default model, retry settings |
| `src/factory/schema.py` | AgenticTrajectory, Turn, TrajectoryMode models |
| `src/audit/inference.py` | VLLMClient, GeminiClient, BaseInferenceClient |
| `src/curation/anchor_dataset_downloader.py` | Existing dataset download/export pattern |
| `tests/fixtures/seed_examples.yaml` | 8 HA seeds + 5 PHP legacy seeds |
| `tests/fixtures/anchor_dataset_examples.json` | Anchor dataset test fixtures, multiple formats |
| `tests/fixtures/calibration_examples.json` | Calibration prompts with judge scoring |
| `legacy/generate_batch_test_chunked.py` | Existing generation patterns, LDI metric, anti-laziness filter |
| `src/research/generate_batch_distilabel.py` | Distilabel pipeline, tool definitions, system prompt patterns |
| Gemini API docs (ai.google.dev) | response_mime_type, response_schema, function calling |
| vLLM docs (docs.vllm.ai) | JSON mode via response_format in extra_body |

## Latency Estimates

*Per sample: OpenAI ~2s, Gemini ~3s, vLLM ~5-10s (GPU dependent)*

For a 200-sample generation run:
- OpenAI: ~400s (~7 minutes) generation + human verification time
- Gemini: ~600s (~10 minutes) generation + human verification time
- vLLM: ~2000s (~33 minutes) generation + human verification time

## Testing Strategy

The research phase has not defined a testing strategy. The following tests are needed:

1. **Schema validation tests**: Verify all generated records pass Pydantic validation
2. **JSON mode reliability tests**: Test each API backend (vLLM, OpenAI, Gemini) with 20 samples and measure JSON parse success rate
3. **Circuit breaker tests**: Verify circuit breaker triggers correctly when quality threshold is breached
4. **Dead letter queue tests**: Verify failed samples are routed correctly and not lost
5. **Idempotency tests**: Verify that re-running generation for the same seed produces consistent results
6. **JSONL export tests**: Verify atomic write (.tmp → rename), file integrity after partial writes
7. **Conversion tests**: Verify `jsonl_to_dspy_examples()` produces valid `dspy.Example.with_inputs()` declarations
8. **Edge cases**: Test with 0 seeds (generic_domain), with extreme difficulty levels, with malformed API responses

## Next Steps

1. Create `infrastructure/anchor_dataset_schema.py` with Pydantic models matching the spec schema. Include `DSPY_FIELD_MAP` constant mapping JSONL fields to dspy input/label.

2. Create `infrastructure/anchor_dataset_builder.py` with:
   - **New AnchorProvider abstraction** (NOT inheriting from TeacherProvider — separate HTTP client wrapper)
   - Seed loading from fixtures
   - **Seed gap handling**: Synthesize prompts for generic_domain/other from reference corpus patterns
   - Prompt generation per domain/difficulty
   - API call with JSON mode response_format
   - Validation against Pydantic schema
   - **Circuit breaker**: Quality checks per batch (parametrizable threshold, empirically calibrated), automatic fallback to OpenAI if breached
   - **Failed sample log**: Simple JSONL log (`outputs/failed_samples.jsonl`) with reason codes — NOT a full dead letter queue
   - JSONL export with atomic write
   - Checkpoint/resume support (per-batch, idempotent by sample id)

3. **Add comprehensive tests** (8 test categories listed above)

4. Manual verification workflow for generated anchors (20 per domain full + 10% random sample, with `verification_log.json`)
