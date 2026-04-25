# Tasks: Baseline Measurement

**Spec**: baseline-measurement
**Epic**: aegf-infrastructure (Story 0.1)
**Type**: cli-tool
**Estimated**: 5 phases, 45 tasks, ~3 days

---

## Phase 1: Dependency Setup + Working Spearman

Fastest path to a working baseline. Verify scipy, scaffold the package structure, build the shared module, and deliver a complete Spearman script.

### Task 1.1: Verify scipy==1.17.1 installs on Python 3.14.3

**Do**:
1. Run `python -c 'import scipy; print(scipy.__version__)'` in the project environment
2. If import fails, run `pip install scipy==1.17.1` and verify
3. If pip install fails, escalate immediately (gating prerequisite per US-1)
4. Record the result (success or escalation) before proceeding

**Files**:
- No files created

**Done when**:
- `python -c 'import scipy'` succeeds in the project environment
- OR escalation has been filed if it fails

**Verify**:
- `python -c 'import scipy; print(scipy.__version__)'` outputs a version

**Commit**:
- `spec(baseline-measurement): verify scipy==1.17.1 install prerequisite`

**Notes**:
- This is a gating prerequisite per US-1. Do not proceed until scipy is importable.

### Task 1.2: Add scipy==1.17.1 to requirements.txt

**Do**:
1. Read `requirements.txt` to find the numpy line
2. Add `scipy==1.17.1` on the line after `numpy`
3. Verify no duplicate scipy entries exist
4. Check that the file remains sorted alphabetically (scipy comes after numpy)

**Files**:
- Modify: `requirements.txt`

**Done when**:
- `requirements.txt` contains `scipy==1.17.1`
- No duplicate scipy entries

**Verify**:
- `grep scipy requirements.txt` returns exactly one line: `scipy==1.17.1`

**Commit**:
- `spec(baseline-measurement): add scipy==1.17.1 to requirements.txt`

### Task 1.3: Add scipy==1.17.1 to pyproject.toml dependencies

**Do**:
1. Read `pyproject.toml` to find the `[project.dependencies]` section
2. Add `scipy==1.17.1` to the dependencies list
3. Ensure scipy is sorted alphabetically among dependencies
4. Verify the TOML syntax is valid

**Files**:
- Modify: `pyproject.toml`

**Done when**:
- `pyproject.toml` contains `scipy==1.17.1` in the dependencies section
- Valid TOML syntax

**Verify**:
- `grep scipy pyproject.toml` returns the dependency line

**Commit**:
- `spec(baseline-measurement): add scipy==1.17.1 to pyproject.toml dependencies`

### Task 1.4: Add scipy to dependency_check.py PACKAGE_IMPORT_MAP

**Do**:
1. Read `infrastructure/dependency_check.py` to find PACKAGE_IMPORT_MAP
2. Add `'scipy': '1.17.1'` to the PACKAGE_IMPORT_MAP dictionary
3. Verify the dictionary syntax is correct

**Files**:
- Modify: `infrastructure/dependency_check.py`

**Done when**:
- `infrastructure/dependency_check.py` includes `'scipy': '1.17.1'` in PACKAGE_IMPORT_MAP

**Verify**:
- `grep scipy infrastructure/dependency_check.py` returns the map entry

**Commit**:
- `spec(baseline-measurement): add scipy to dependency_check.py PACKAGE_IMPORT_MAP`

### Task 1.5: Create infrastructure/baselines/ package structure

**Do**:
1. Create `infrastructure/baselines/` directory
2. Create `infrastructure/baselines/__init__.py` (can be empty or contain a short docstring)
3. Create `baseline_results/` directory at project root
4. Optionally create `baseline_results/.gitkeep` (directory is gitignored, so this is optional)

**Files**:
- Create: `infrastructure/baselines/__init__.py`
- Create: `baseline_results/` (directory)

**Done when**:
- `infrastructure/baselines/__init__.py` exists
- `baseline_results/` directory exists at project root

**Verify**:
- `test -f infrastructure/baselines/__init__.py && test -d baseline_results`

**Commit**:
- `spec(baseline-measurement): create baselines package and baseline_results directory`

### Task 1.6: Add baseline_results/ to .gitignore

**Do**:
1. Read `.gitignore` to check if `baseline_results/` already exists
2. If not present, add `baseline_results/` as a new line
3. If `baseline_results/` directory already contains tracked files, run `git rm -r --cached baseline_results/` to untrack them
4. Verify the .gitignore line is correct (trailing slash indicates directory)

**Files**:
- Modify: `.gitignore`

**Done when**:
- `.gitignore` contains a line `baseline_results/`
- No files in `baseline_results/` are tracked by git

**Verify**:
- `grep 'baseline_results/' .gitignore` returns the line
- `git ls-files baseline_results/` returns nothing

**Commit**:
- `spec(baseline-measurement): add baseline_results/ to .gitignore`

### Task 1.7: Create shared module infrastructure/baselines/_shared.py

**Do**:
1. Create `infrastructure/baselines/_shared.py` with the following functions:
   - `BaselineError(Exception)` — custom exception for fatal errors
   - `validate_input_file(path, allowed_dirs=None)` — symlink, empty, size, path traversal checks (use `Path.relative_to()` for path traversal, NOT string `startswith`)
   - `write_output_atomic(path, data)` — temp file (mode 0o600) → rename → fsync, with try/finally cleanup, EXDEV fallback via shutil.move
   - `check_output_lock(output_path)` — O_CREAT|O_EXCL with explicit LOCK_FILE_MODE, 30s timeout, stale detection, symlink check on stale lock before removal
   - `release_lock(lock_path)` — best-effort lock cleanup
   - `_is_lock_stale(lock_path)` — mtime-based stale detection, with OSError handling
   - `_make_json_safe(value)` — NaN/inf to None for floats
   - `_sanitize_output_dict(d)` — recursive NaN/inf sanitization for dicts and lists
   - `_sanitize_list_item(v)` — list item sanitization helper
2. Include constants: `MAX_INPUT_SIZE` (10 MB), `DEFAULT_OUTPUT_DIR` ("baseline_results"), `LOCK_TIMEOUT_SECONDS` (30), `LOCK_POLL_INTERVAL` (0.5), `LOCK_STALE_SECONDS` (300), `TEMP_FILE_MODE` (0o600), `LOCK_FILE_MODE` (0o600)
3. Include Apache-2.0 license header within first 4096 bytes (tokens: SPDX-License-Identifier:, Architect-Expert-Gap-Forge, Copyright)
4. Use `from __future__ import annotations` as first line
5. Follow the import organization order: `from __future__`, stdlib alphabetically, third-party, local

**Files**:
- Create: `infrastructure/baselines/_shared.py`

**Done when**:
- All 8+ functions/constants are implemented per the design spec
- License header is present with 3 required tokens
- File passes `ruff format`

**Verify**:
- `cd /mnt/bunker_data/ai/data_factory && python -c 'from infrastructure.baselines._shared import BaselineError, validate_input_file, write_output_atomic, check_output_lock, release_lock'`
- Also verify private functions are importable: `cd /mnt/bunker_data/ai/data_factory && python -c 'from infrastructure.baselines._shared import _is_lock_stale, _sanitize_output_dict, _sanitize_list_item'`

**Commit**:
- `spec(baseline-measurement): create shared utilities module`

### Task 1.8: Implement measure_spearman_baseline.py — CLI scaffold and shared imports

**Do**:
1. Create `infrastructure/baselines/measure_spearman_baseline.py`
2. Add Apache-2.0 license header (first 4096 bytes must contain SPDX-License-Identifier:, Architect-Expert-Gap-Forge, Copyright)
3. Add `from __future__ import annotations` as first line
4. Implement import resolution: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))`
5. Import shared utilities: `from ._shared import BaselineError, validate_input_file, write_output_atomic, check_output_lock, release_lock`
6. Import SCORING_WEIGHTS from `src.audit.schema`
7. Implement `_die(msg)` function printing to stderr and calling `sys.exit(1)`
8. Implement `main(argv=None) -> int` with `logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)`
9. Implement `_impl(argv)` as the actual logic entry point
10. Add `if __name__ == "__main__": raise SystemExit(main())`
11. Set up argparse with:
    - `--dataset` (required, help="Path to JSON file with baseline/adapter composites")
    - `--output` (optional, default="baseline_results/spearman_judge_baseline.json", help="Output JSON path")
    - `--dry-run` (flag, help="Validate input and compute summary without writing output")
    - `--no-overwrite` (flag, exit 1 if output exists)
    - `--verbose` (flag, sets logging to INFO via `logging.getLogger().setLevel(logging.INFO)`)
    - `--quiet` (flag, sets logging to ERROR via `logging.getLogger().setLevel(logging.ERROR)`)
12. Run `ruff format` on the file

**Files**:
- Create: `infrastructure/baselines/measure_spearman_baseline.py`

**Done when**:
- File has correct license header, imports, CLI scaffolding
- argparse defines all required arguments with description and help text
- --verbose/--quiet flags are wired to logging level changes (not just defined as arguments)
- File passes `ruff format`

**Verify**:
- `python infrastructure/baselines/measure_spearman_baseline.py --help` shows all arguments
- Verify SCORING_WEIGHTS is importable (prerequisite for Task 1.9): `python -c 'from src.audit.schema import SCORING_WEIGHTS; print(SCORING_WEIGHTS)'`
- Verify --verbose changes log level: `echo '{"baseline_composites":[0.5],"adapter_composites":[0.6]}' > /tmp/test_verb.json && python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_verb.json --verbose 2>&1 | grep 'INFO'` (should show INFO or more verbose output; do NOT use /dev/null — it is a symlink on most systems and will be rejected)

**Commit**:
- `spec(baseline-measurement): scaffold spearman baseline CLI with argparse`

### Task 1.9: Implement measure_spearman_baseline.py — Input validation and NaN filtering

**Do**:
1. In `_impl()`, implement the full input validation pipeline:
   - Resolve and validate dataset path via `validate_input_file()` (symlink, existence, size, allowed_dirs)
   - Read and parse JSON from dataset file
   - Validate JSON has top-level keys `baseline_composites` and `adapter_composites`
   - Validate both values are lists of floats (exit 1 with descriptive error for type mismatch)
   - Validate lengths are equal (exit 1: "Array length mismatch: baseline has N values, adapter has M values")
   - Handle input with `judge_scores` instead of pre-computed composites: derive composites using SCORING_WEIGHTS (prefer `composite_score` when available per FR-002.5)
   - Filter NaN values from both arrays, preserving index pairing
2. Implement `--dry-run` behavior:
   - Read and validate input (same as above)
   - Print: input file path and size, number of records (n after NaN filtering), expected method (exact for n<10, asymptotic for n>=10)
   - If n < 3 after filtering, print edge case status
   - Final line: "DRY RUN complete. No output file written."
   - Exit 0 without writing, without acquiring lock
3. Implement `--no-overwrite` behavior:
   - Check if output exists and is non-empty
   - If exists and flag NOT provided: print to stderr "Output file exists: {path}. Overwriting."
   - If exists and flag IS provided: exit 1 with "Output file already exists: {path}. Use --no-overwrite to prevent overwriting."
4. Implement output directory creation: `os.makedirs(Path(output).parent, exist_ok=True)`
5. Add `--verbose`/`--quiet` flag handling for log level adjustment

**Files**:
- Modify: `infrastructure/baselines/measure_spearman_baseline.py`

**Done when**:
- Input validation rejects symlinks, empty files, oversized files with exit 1
- NaN filtering preserves index pairing
- Dry-run prints summary and exits 0 without writing
- No-overwrite behavior works correctly
- Composite derivation from judge_scores using SCORING_WEIGHTS works when composite_score is missing

**Verify**:
- `echo '{"baseline_composites":[0.7,0.8],"adapter_composites":[0.75,0.85]}' > /tmp/test_spearman.json && python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_spearman.json --dry-run` exits 0 and prints summary
- Fixture `judge_scoring_response.json` has the wrong structure (single judge response, not composites array). Use a temp file with correct structure for verification.

**Commit**:
- `spec(baseline-measurement): implement spearman input validation and NaN filtering`

### Task 1.10: Implement measure_spearman_baseline.py — Computation and output

**Do**:
1. Implement edge case detection BEFORE calling scipy.stats.spearmanr:
   - n=0 after NaN filtering: status="no_valid_data", score=null, p_value=null, reason="All data points are NaN or non-numeric"
   - n=1 after NaN filtering: status="single_sample_undefined", score=null, p_value=null, reason="Single sample — correlation is undefined"
   - n=2 after NaN filtering: status="insufficient_samples", score=null, p_value=null, reason="rho for 2 points is always ±1.0 (perfect correlation), meaningless for baseline". **Note**: p_value=null is intentional per F12 — even though scipy could compute a value, it is uncomputable for baseline purposes.
   - Constant input (len(set(baseline))<=1 OR len(set(adapter))<=1): score=0.0, p_value=1.0, status="constant_input", reason="One or both arrays contain constant values"
2. Determine method: n<10 → "exact", n>=10 → "asymptotic"
3. Call `scipy.stats.spearmanr(baseline, adapter, method=method)`
4. Clamp rho to [-1.0, 1.0] if outside range (log warning, note in details)
5. Build output JSON:
   ```json
   {
     "schema_version": "1",
     "type": "spearman_baseline",
     "timestamp": "<ISO8601 UTC with Z suffix>",
     "score": <float or null>,
     "status": "<ok or edge case code>",
     "score_description": "rho: Spearman rank correlation, range [-1, 1]",
     "details": {
       "p_value": <float or null>,
       "n": <int>,
       "method": "exact"|"asymptotic",
       "reason": <string or null>
     }
   }
   ```
6. Sanitize output dict with `_sanitize_output_dict()` before writing (NaN/inf → null)
7. Acquire lock via `check_output_lock()`, write output atomically via `write_output_atomic()`, release lock via `release_lock()`
8. Print resolved output path to stdout on success: "Wrote output to <path>"
9. Print timestamp using `datetime.now(timezone.utc)` for UTC output with Z suffix
10. **R1 fix**: Validate output parent directory is not a symlink before calling `write_output_atomic()`

**Files**:
- Modify: `infrastructure/baselines/measure_spearman_baseline.py`

**Done when**:
- All edge cases (n=0,1,2, constant) produce correct structured output
- scipy computation is called with correct method parameter
- Output JSON matches the shared baseline result schema
- Atomic write with lock protection works
- Timestamp uses UTC with Z suffix
- Output parent directory validated for symlink

**Verify**:
- `echo '{"baseline_composites":[0.7,0.8,0.65,0.9],"adapter_composites":[0.78,0.85,0.7,0.92]}' > /tmp/test_spearman.json && python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_spearman.json` exits 0
- Output JSON has all required fields: schema_version, type, timestamp, score, status, score_description, details
- Output JSON contains `"status": "ok"` and `"score_description"` field

**Commit**:
- `spec(baseline-measurement): implement spearman computation and atomic output`

### Task 1.11: [VERIFY] Adversarial Review of Phase 1 Tasks

**Do**:
1. Run `/bmad-review-adversarial-general` with `/bmad-party-mode`
2. Select the most relevant agents for reviewing infrastructure/baselines/_shared.py and measure_spearman_baseline.py
3. The reviewers will produce findings
4. Apply valid findings as follow-up fix tasks
5. Mark this review task complete only after findings are addressed

**Files**:
- No files created (review task)

**Done when**:
- Adversarial review completed
- All valid findings addressed (fix tasks applied or rejected with rationale)

**Verify**:
- Phase 1 scripts exist: `test -f infrastructure/baselines/_shared.py && test -f infrastructure/baselines/measure_spearman_baseline.py`
- Phase 1 scripts are importable: `cd /mnt/bunker_data/ai/data_factory && python -c 'from infrastructure.baselines._shared import BaselineError; from infrastructure.baselines.measure_spearman_baseline import main'`
- Adversarial review report written to `.progress.md` with findings count

**Commit**:
- `spec(baseline-measurement): adversarial review round 1 of dependency and spearman baseline`

**Notes**:
- This task triggers an adversarial review using party mode with the most relevant agents
- Reviewers check for: correctness of _shared.py functions, Spearman edge cases, NaN handling alignment (F12), input validation completeness, lock handling, atomic write correctness
- After review, immediately create follow-up fix tasks for any valid findings
- Do NOT use checkbox grep for verification — these are review tasks, not implemented code tasks

---

## Phase 2: Refactor — Complete All Scripts

Fill in the remaining three scripts using the established pattern from Spearman.

### Task 2.1: Implement run_calibration_baseline.py — CLI scaffold and shared imports

**Do**:
1. Create `infrastructure/baselines/run_calibration_baseline.py`
2. Add Apache-2.0 license header within first 4096 bytes
3. Add `from __future__ import annotations` as first line
4. Implement import resolution: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))`
5. Import shared utilities from `._shared`
6. Import CALIBRATION_GRID from `src.audit.calibration_schema`
7. Implement `_die()`, `main()`, `_impl()` per Rich CLI pattern
8. Set up argparse with:
   - `--dataset` (required, help="Path to JSON file with calibration results")
   - `--ldi-source` (optional, help="Path to JSON/JSONL file with LDI scores")
   - `--ldi-threshold` (optional, default=0.01, type=float, help="LDI pass threshold")
   - `--output` (optional, default="baseline_results/calibration_baseline.json", help="Output JSON path")
   - `--dry-run` (flag)
   - `--no-overwrite` (flag)
   - `--verbose` (flag) — sets logging to INFO via `logging.getLogger().setLevel(logging.INFO)`
   - `--quiet` (flag) — sets logging to ERROR via `logging.getLogger().setLevel(logging.ERROR)`
9. Import `CALIBRATION_SCORING_WEIGHTS` from `src.audit.schema` (same module as SCORING_WEIGHTS for Spearman)
10. Run `ruff format` on the file

**Files**:
- Create: `infrastructure/baselines/run_calibration_baseline.py`

**Done when**:
- File has correct license header, imports, CLI scaffolding
- CALIBRATION_SCORING_WEIGHTS imported for composite score computation
- All arguments have description and help text
- --verbose/--quiet flags are wired to logging level changes
- File passes `ruff format`

**Verify**:
- `python infrastructure/baselines/run_calibration_baseline.py --help` shows all arguments
- Verify --verbose changes log level: `echo '{"calibration_results":[]}' > /tmp/test_cal.json && python infrastructure/baselines/run_calibration_baseline.py --dataset /tmp/test_cal.json --verbose --dry-run 2>&1 | grep 'INFO'` (should show INFO output; do NOT use /dev/null — it is 0 bytes and will be rejected by validate_input_file)

**Commit**:
- `spec(baseline-measurement): scaffold calibration baseline CLI with argparse`

### Task 2.2: Implement run_calibration_baseline.py — Stage detection and coherence extraction

**Do**:
1. Implement `detect_stage(results)` function:
   - STAGE_6_KEYS = {"parameter_effectiveness", "coherence", "parameter_alignment", "task_completion", "style"}
   - Check ALL entries for Stage 6 key presence
   - If ANY entry has Stage 6 keys → "stage6"
   - Detect mixed-stage: if some entries have Stage 6 keys and some don't → log warning "Mixed-stage data detected; using Stage 6 weight set for all entries"
   - Return "stage5" if no Stage 6 keys found
   - Return "unknown" if results is empty
2. Implement input validation:
   - Validate dataset via `validate_input_file()`
   - Parse JSON
   - Handle both formats: `{"calibration_results": [...]}` and top-level `[{...}, ...]`
   - Validate results is a non-empty list
3. Implement coherence extraction:
   - Stage 6: extract `entry["judge_scores"]["coherence"]` for each entry
   - Stage 5: set coherence to null (NOT derived from composite_score)
   - Validate coherence range [0.0, 1.0] — log warning if out of range, still include in mean
4. Implement composite score computation:
   - Stage 6: sum(judge_scores[dim] * weight for dim, weight in CALIBRATION_SCORING_WEIGHTS.items())
   - Stage 5: use pre-computed `composite_score` from fixture (no recalculation)

**Files**:
- Modify: `infrastructure/baselines/run_calibration_baseline.py`

**Done when**:
- Stage detection correctly identifies Stage 5, Stage 6, and mixed-stage data
- Mixed-stage data logs warning and uses Stage 6 weight set
- Coherence extraction returns null for Stage 5 data
- Out-of-range coherence values are logged but included in mean calculation

**Verify**:
- `python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --dry-run 2>&1 | grep 'data_stage'` — outputs "stage6" (known ambiguity: fixture is Stage 5 data but has "style" key which is in STAGE_6_KEYS). This is expected behavior — coherence will be null since Stage 5 has no "coherence" key.
- **Note**: Use synthetic Stage 5-only data (no "style" key, no coherence) for accurate stage detection validation. The fixture is a known edge case due to the shared "style" key.

**Commit**:
- `spec(baseline-measurement): implement calibration stage detection and coherence extraction`

### Task 2.3: Implement run_calibration_baseline.py — LDI sourcing and output

**Do**:
1. Implement LDI source parsing:
   - If `--ldi-source` is provided:
     - Validate via `validate_input_file()` (same checks as dataset)
     - Auto-detect format: try `json.load()` the whole file → if JSONDecodeError, try line-by-line JSONL
     - Parse records with "ldi" float field
     - Skip non-numeric ldi values (log warning, exclude from mean/pass_rate)
     - Compute: `mean_ldi = sum(ldi_values) / len(ldi_values)`
     - Compute: `ldi_pass_rate = count(ldi >= threshold) / len(ldi_values)` (divide by count of valid numeric LDI values, NOT total_records — non-numeric records were skipped and must not penalize the pass rate)
   - If `--ldi-source` is NOT provided: set mean_ldi=null, ldi_pass_rate=null, log warning
   - Handle empty LDI array: mean_ldi=null, ldi_pass_rate=null
2. Implement output JSON construction:
   ```json
   {
     "schema_version": "1",
     "type": "calibration_baseline",
     "timestamp": "<ISO8601 UTC with Z suffix>",
     "score": <float or null>,
     "status": "ok",
     "score_description": "mean_coherence: average coherence score, range [0, 1]",
     "details": {
       "mean_coherence": <float or null>,
       "mean_ldi": <float or null>,
       "ldi_pass_rate": <float or null>,
       "grid_config": { /* from CALIBRATION_GRID */ },
       "data_stage": "stage5"|"stage6",
       "n_entries": <int>
     }
   }
   ```
3. Implement `--dry-run` behavior:
   - Read and validate dataset and LDI source (if provided)
   - Print: input file path and size, number of records, detected stage, LDI records count (if provided)
   - Final line: "DRY RUN complete. No output file written."
   - Include mean_coherence and mean_ldi in dry-run summary (preliminary computation without writing)
4. Implement `--no-overwrite` behavior (same pattern as Spearman)
5. Implement `--verbose`/`--quiet` flag handling for log level adjustment
6. Atomic write with lock, output path confirmation to stdout

**Files**:
- Modify: `infrastructure/baselines/run_calibration_baseline.py`

**Done when**:
- LDI source parsing handles both JSON and JSONL formats
- Non-numeric LDI values are skipped with warning
- Missing LDI source produces null outputs with warning (exit 0)
- Output JSON matches the shared baseline result schema
- Dry-run prints preliminary mean_coherence and mean_ldi before "DRY RUN complete."
- --verbose/--quiet flags are wired to logging level changes
- No-overwrite behavior works correctly

**Verify**:
- `python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --dry-run` exits 0 and outputs "data_stage" in dry-run summary
- Verify --verbose changes log level: `python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --verbose --dry-run 2>&1 | grep 'INFO'` (should show INFO or more verbose output)

**Commit**:
- `spec(baseline-measurement): implement calibration LDI sourcing and output`

### Task 2.4: Implement measure_mipro_compile_baseline.py — CLI scaffold and grid parsing

**Do**:
1. Create `infrastructure/baselines/measure_mipro_compile_baseline.py`
2. Add Apache-2.0 license header within first 4096 bytes
3. Add `from __future__ import annotations` as first line
4. Implement import resolution
5. Import shared utilities from `._shared`
6. Import CALIBRATION_GRID from `src.audit.calibration_schema`
7. Implement `_die()`, `main()`, `_impl()` per Rich CLI pattern
8. Set up argparse with:
   - `--dataset` (optional, help="Path to CalibrationReport JSON (measured mode)")
   - `--num-prompts` (optional, default=6, type=int, help="Number of prompts for estimate")
   - `--avg-latency` (optional, default=0.5, type=float, help="Average latency per iteration")
   - `--output` (optional, default="baseline_results/mipro_compile_baseline.json", help="Output JSON path")
   - `--dry-run` (flag)
   - `--no-overwrite` (flag)
   - `--verbose` (flag)
   - `--quiet` (flag)
9. Validate `--num-prompts >= 1` (exit 1: "num-prompts must be positive")
10. Clamp `--avg-latency < 0` to 0.0 and warn

**Files**:
- Create: `infrastructure/baselines/measure_mipro_compile_baseline.py`

**Done when**:
- File has correct license header, imports, CLI scaffolding
- All arguments have description and help text
- num-prompts validation works (rejects 0 and negatives)
- avg-latency negative values are clamped to 0.0 with warning
- File passes `ruff format`

**Verify**:
- `python infrastructure/baselines/measure_mipro_compile_baseline.py --help` shows all arguments
- `python infrastructure/baselines/measure_mipro_compile_baseline.py --num-prompts 0` exits 1

**Commit**:
- `spec(baseline-measurement): scaffold MIPRO compile baseline CLI with argparse`

### Task 2.5: Implement measure_mipro_compile_baseline.py — Mode selection and computation

**Do**:
1. Implement CALIBRATION_GRID parsing:
   - Compute `profiles_tested = math.prod(len(v) for v in CALIBRATION_GRID.values())`
   - MUST NOT hard-code the value 4500
   - In estimated mode (no --dataset): If CALIBRATION_GRID is empty or missing keys: exit 1 with "CALIBRATION_GRID is empty — cannot compute profiles_tested" (per F11 constraint)
   - In dry-run mode: skip the grid validation and just print: "Would need CALIBRATION_GRID for actual computation"
   - Record grid_config as dict of dimension → values list
2. Implement mode selection:
   - If `--dataset` is provided AND file exists AND is valid JSON:
     - Parse JSON
     - Check for `statistics.execution_time_seconds` key
     - If present and non-null: measured mode → score = execution_time_seconds, source = "measured"
     - If missing/null/malformed: fall back to estimated mode with warning
   - If `--dataset` is NOT provided or file invalid: estimated mode
3. Implement estimated mode:
   - num_prompts priority: (1) --num-prompts CLI arg, (2) default 6
   - total_iterations = profiles_tested × num_prompts
   - avg_latency: --avg-latency CLI arg, default 0.5
   - score = total_iterations × avg_latency
   - MUST print WARNING to stderr about placeholder: "WARNING: This is an ESTIMATED duration based on placeholder values..."
   - Output details must include `"estimated": true`
4. Implement output JSON construction:
   ```json
   {
     "schema_version": "1",
     "type": "mipro_compile",
     "timestamp": "<ISO8601 UTC with Z suffix>",
     "score": <float>,
     "status": "ok",
     "score_description": "duration_seconds: wall-clock compile time in seconds",
     "details": {
       "grid_config": { /* from CALIBRATION_GRID */ },
       "total_iterations": <int>,
       "profiles_tested": <int>,
       "source": "measured"|"estimated",
       "avg_latency_seconds": <float>,
       "duration_seconds": <float>,
       "estimated": <bool>,
       "profiles_tested_computed_from_grid": true
     }
   }
   ```
5. Implement `--dry-run` behavior and `--no-overwrite` behavior

**Files**:
- Modify: `infrastructure/baselines/measure_mipro_compile_baseline.py`

**Done when**:
- profiles_tested is dynamically computed from CALIBRATION_GRID (no hard-coded values)
- Empty CALIBRATION_GRID causes exit 1 (F11 constraint)
- Measured mode extracts execution_time_seconds from CalibrationReport
- Estimated mode uses correct formula and prints WARNING
- Output JSON matches the shared baseline result schema

**Verify**:
- `python infrastructure/baselines/measure_mipro_compile_baseline.py --dry-run` exits 0 and prints summary
- Verify estimated mode prints WARNING to stderr: `python infrastructure/baselines/measure_mipro_compile_baseline.py --dry-run 2>&1 | grep -i 'WARNING.*ESTIMATED'` matches

**Commit**:
- `spec(baseline-measurement): implement MIPRO compile mode selection and computation`

### Task 2.6: [x] Implement rollback_check.py — CLI scaffold and isolation

**Do**:
1. Create `infrastructure/rollback_check.py`
2. Add Apache-2.0 license header within first 4096 bytes
3. Add `from __future__ import annotations` as first line
4. Implement import resolution: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`
5. Import shared utilities: `from infrastructure.baselines._shared import BaselineError, validate_input_file, write_output_atomic, check_output_lock, release_lock`
6. Implement `_die()`, `main()`, `_impl()` per Rich CLI pattern
7. Set up argparse with:
   - `--target` (optional, default=60.0, type=float, help="Max revert duration in seconds")
   - `--output` (optional, default="baseline_results/rollback_check.json", help="Output JSON path")
   - `--dry-run` (flag)
   - `--verbose` (flag) — sets logging to INFO via `logging.getLogger().setLevel(logging.INFO)`
   - `--quiet` (flag) — sets logging to ERROR via `logging.getLogger().setLevel(logging.ERROR)`
8. **NOTE**: This script does NOT accept `--no-overwrite` (per FR-005/F6)
9. Implement signal handling:
   - Register atexit handler for cleanup
   - Handle SIGINT (exit 130) and SIGTERM (exit 143) with cleanup
10. Implement `_cleanup()` function that removes the isolated environment
11. Set up logging: `basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)`
12. Run `ruff format` on the file

**Files**:
- Create: `infrastructure/rollback_check.py`

**Done when**:
- File has correct license header, imports, CLI scaffolding
- Signal handlers are registered (atexit, SIGINT, SIGTERM)
- All arguments have description and help text
- Script does NOT include --no-overwrite argument
- File passes `ruff format`

**Verify**:
- `python infrastructure/rollback_check.py --help` shows all arguments
- Verify `--no-overwrite` is NOT present: `python infrastructure/rollback_check.py --help | grep 'no-overwrite'` must return nothing

**Commit**:
- `spec(baseline-measurement): scaffold rollback check CLI with signal handling`

### Task 2.7: [x] Implement rollback_check.py — Isolated environment and revert timing

**Do**:
1. Implement `create_isolated_env()` function:
   - Try `git worktree add` first (faster, shares .git)
   - Use `tempfile.mkdtemp(prefix="baseline-rollback-worktree-")` for worktree parent
   - Name format: `rollback-check-{os.getpid()}`
   - subprocess.run with timeout=30s
   - On failure: fall back to `git clone` to temp subdirectory
   - Clone uses timeout=120s
   - Returns `(path, "worktree")` or `(path, "clone")`
2. Implement cleanup function `cleanup_isolated_env(path, kind)`:
   - If worktree: `git worktree remove --force <path>`
   - If clone: `shutil.rmtree(path)`
3. Implement `_impl()` main logic:
   - Print "Creating isolated test environment..."
   - Call `create_isolated_env()`
   - cd into isolated environment
   - Create test commit: use `git commit --allow-empty -m "baseline-test-commit"` to guarantee a commit can be made even with no changes
   - Print "Test commit created: <hash>"
   - Record test_commit = HEAD
   - Start timer: `time.perf_counter()`
   - Run `git revert HEAD --no-edit` via subprocess with timeout=60.0
   - Stop timer: `duration = time.perf_counter() - start`
4. Implement verification:
   - Check: duration < target seconds
   - Verify git status is clean (no modified/untracked/staged files)
   - Check `git status --porcelain` is empty

**Files**:
- Modify: `infrastructure/rollback_check.py`

**Done when**:
- Worktree creation works (with clone fallback)
- Test commit is created and reverted
- Revert timing is measured correctly
- Signal handlers trigger cleanup on interruption
- Isolated environment is cleaned up on normal exit

**Verify**:
- `python infrastructure/rollback_check.py --dry-run` exits 0
- `python infrastructure/rollback_check.py` exits 0 and cleanup completes

**Commit**:
- `spec(baseline-measurement): implement rollback isolation and revert timing`

### Task 2.8: Implement rollback_check.py — Output and result reporting

**Do**:
1. Implement output JSON construction:
   ```json
   {
     "schema_version": "1",
     "type": "rollback_check",
     "timestamp": "<ISO8601 UTC with Z suffix>",
     "score": <float (duration in seconds)>,
     "status": "ok"|"exceeded_threshold",
     "score_description": "duration_seconds: git revert time in seconds",
     "details": {
       "duration_seconds": <float>,
       "threshold_seconds": <float>,
       "within_target": <bool>,
       "clean_status": <bool>,
       "isolation_method": "worktree"|"clone",
       "error": <string or null>
     }
   }
   ```
2. Implement status logic:
   - If duration < target AND clean_status: status="ok"
   - If duration >= target: status="exceeded_threshold"
   - If clean_status check fails: status="dirty_working_tree"
3. Implement stdout messages:
   - Success: "git revert HEAD completed in X.XXs (<threshold>s)"
   - Failure: "git revert HEAD exceeded threshold: X.XXs > 60s"
   - Cleanup: "Cleaning up test environment..."
4. Implement `--dry-run` behavior:
   - Print diagnostic summary: threshold seconds, target output path, isolation method that WOULD be used
   - Print "DRY RUN complete. No output file written."
   - Do NOT create isolated environment, do NOT write output, do NOT acquire lock
5. Write output atomically with lock (same pattern as other scripts)
6. Print resolved output path to stdout on success

**Files**:
- Modify: `infrastructure/rollback_check.py`

**Done when**:
- Output JSON matches the shared baseline result schema with rollback-specific fields
- Status is correctly determined based on duration and clean status
- Stdout messages match the required format
- Dry-run skips all git operations and prints summary only
- Cleanup is called via atexit and signal handlers

**Verify**:
- `python infrastructure/rollback_check.py --output /tmp/test-rollback.json --dry-run` exits 0 and prints diagnostic summary
- `python infrastructure/rollback_check.py --output /tmp/test-rollback.json` exits 0 and cleanup completes
- Output JSON has all required fields: schema_version, type, timestamp, score, status, score_description, details

**Commit**:
- `spec(baseline-measurement): implement rollback check output and result reporting`

### Task 2.9: [VERIFY] Adversarial Review of Phase 2 Tasks

**Do**:
1. Run `/bmad-review-adversarial-general` with `/bmad-party-mode`
2. Select the most relevant agents for reviewing all Phase 2 scripts
3. The reviewers will produce findings
4. Apply valid findings as follow-up fix tasks
5. Mark this review task complete only after findings are addressed

**Files**:
- No files created (review task)

**Done when**:
- Adversarial review completed
- All valid findings addressed (fix tasks applied or rejected with rationale)

**Verify**:
- Phase 2 scripts exist: `test -f infrastructure/baselines/run_calibration_baseline.py && test -f infrastructure/baselines/measure_mipro_compile_baseline.py && test -f infrastructure/rollback_check.py`
- All scripts are importable: `cd /mnt/bunker_data/ai/data_factory && python -c 'from infrastructure.baselines.run_calibration_baseline import main; from infrastructure.baselines.measure_mipro_compile_baseline import main as mipro_main; from infrastructure.rollback_check import main as rollback_main'`
- Adversarial review report written to `.progress.md` with findings count

**Commit**:
- `spec(baseline-measurement): adversarial review round 2 of calibration, mipro, and rollback scripts`

**Notes**:
- This task triggers an adversarial review using party mode with the most relevant agents
- Reviewers check for: calibration stage detection accuracy, LDI parsing robustness, MIPRO grid computation correctness, rollback isolation completeness, consistency across all 4 scripts (common patterns, error messages, output schema)
- After review, immediately create follow-up fix tasks for any valid findings
- Do NOT use checkbox grep for verification — these are review tasks, not implemented code tasks

---

## Phase 3: Testing & Edge Cases

Verification tasks to exercise edge cases across all scripts.

### Task 3.1: [x] Verify Spearman n=0 edge case (all NaN data)

**Do**:
1. Create a temporary test file with NaN values using Python (JSON does not support NaN literal):
   `python -c 'import json; json.dump({"baseline_composites": [float("nan"), float("nan")], "adapter_composites": [float("nan"), float("nan")]}, open("/tmp/test_nan.json", "w"))'`
2. Run `measure_spearman_baseline.py --dataset /tmp/test_nan.json`
3. Verify output: status="no_valid_data", score=null, p_value=null, n=0
4. Verify exit code is 0 (edge case is handled gracefully)

**Files**:
- No permanent files created

**Done when**:
- Script handles all-NaN input gracefully
- Output JSON has correct edge case fields

**Verify**:
- Output JSON contains `"status": "no_valid_data"` and `"n": 0`

**Commit**:
- `spec(baseline-measurement): verify spearman n=0 edge case`

### Task 3.2: [x] Verify Spearman n=1 and n=2 edge cases

**Do**:
1. Create test JSON with n=1: `{"baseline_composites": [0.5], "adapter_composites": [0.6]}`
2. Run script, verify status="single_sample_undefined", score=null, p_value=null, n=1
3. Create test JSON with n=2: `{"baseline_composites": [0.5, 0.6], "adapter_composites": [0.6, 0.7]}`
4. Run script, verify status="insufficient_samples", score=null, p_value=null, n=2

**Files**:
- No permanent files created

**Done when**:
- Both n=1 and n=2 cases produce correct edge case output

**Verify**:
- `grep -c '"status".*"single_sample_undefined"'` and `grep -c '"status".*"insufficient_samples"'`

**Commit**:
- `spec(baseline-measurement): verify spearman n=1 and n=2 edge cases`

### Task 3.3: [x] Verify Spearman constant input detection

**Do**:
1. Create test JSON with constant baseline: `{"baseline_composites": [0.5, 0.5, 0.5], "adapter_composites": [0.3, 0.6, 0.9]}`
2. Run script, verify status="constant_input", score=0.0, p_value from scipy (typically 1.0 but may vary for constant input — sanitized via _sanitize_output_dict)
3. Also test constant adapter case

**Files**:
- No permanent files created

**Done when**:
- Constant input is detected BEFORE calling scipy.stats.spearmanr
- Output includes correct edge case fields

**Verify**:
- Output JSON contains `"status": "constant_input"` and `"score": 0.0`

**Commit**:
- `spec(baseline-measurement): verify spearman constant input detection`

### Task 3.4: [x] Verify input file validation (symlink, empty, oversized, size limit, path traversal)

**Do**:
0. Create test fixtures before verification:
   - `ln -sf tests/fixtures/calibration_examples.json /tmp/symlink.json` (create symlink)
   - `touch /tmp/empty.json` (create empty file)
   - `dd if=/dev/zero of=/tmp/large_file.json bs=1M count=11` (create 11 MB file)
   - `python -c 'open("/tmp/test_binary.dat","wb").write(b"\\x00\\x01\\x02\\x03")'` (create binary file)
1. Create a symlink to a valid JSON file and run each script with it — verify exit 1 with symlink error
2. Create an empty file (0 bytes) and run each script with it — verify exit 1 with empty file error
3. Create a file > 10 MB and run each script with it — verify exit 1 with size limit error
4. Create a file with path traversal attempt (e.g., `../../etc/passwd`) and verify exit 1 with "input path outside allowed directories"
5. Verify scripts reject non-JSON files (binary data) with parse error (use `/tmp/test_binary.dat`)
6. Verify scripts handle missing file gracefully with "No such file" error

**Files**:
- No permanent files created (test fixtures in /tmp/)

**Done when**:
- All four scripts reject symlinks, empty files, files > 10 MB, and path traversal attempts with exit 1
- Error messages include the file path
- Path traversal uses `Path.relative_to()` (not string `startswith`)

**Verify**:
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/symlink.json` exits 1
- `python infrastructure/baselines/run_calibration_baseline.py --dataset /tmp/symlink.json` exits 1
- `python infrastructure/baselines/measure_mipro_compile_baseline.py --dataset /tmp/symlink.json` exits 1
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/empty.json` exits 1
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/large_file.json` exits 1 (10 MB+ file)
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_binary.dat` exits 1 with parse error
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/nonexistent_file.json` exits 1 with "No such file" message
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset ../../etc/passwd 2>&1 | grep -i 'outside allowed'` exits 1 with path traversal error

**Commit**:
- `spec(baseline-measurement): verify input file validation across all scripts`

### Task 3.5: [x] Verify calibration stage detection with fixture data

**Do**:
1. Run `run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --dry-run`
2. **IMPORTANT**: The fixture `calibration_examples.json` contains a `"style"` key in its judge_scores. Both Stage 5 and Stage 6 use `"style"` as a key. The Stage 5 keys are: ha_modernity, reasoning_depth, functionality, completeness, style. The Stage 6 keys are: parameter_effectiveness, coherence, parameter_alignment, task_completion, style. Because `"style"` is in STAGE_6_KEYS, this fixture will be detected as Stage 6. This is a known detection ambiguity — the fixture represents Stage 5 data but gets flagged as Stage 6 due to the shared `"style"` key.
3. **Note**: When Stage 5 data is misdetected as Stage 6, coherence defaults to null (since Stage 5 data has no `"coherence"` key in judge_scores). Document this in implementation.
4. Create a synthetic Stage 5 test file with only Stage 5 keys (ha_modernity, reasoning_depth, functionality, completeness) — NO style key, NO coherence key
5. Run script on Stage 5 data, verify `data_stage: "stage5"` and mean_coherence is null
6. Create a synthetic Stage 6 test file with `coherence` in judge_scores
7. Run script on Stage 6 data, verify correct coherence extraction
8. Create a mixed-stage test file with some entries having Stage 5 keys and some Stage 6 keys
9. Run script, verify warning is logged and Stage 6 weight set is used

**Files**:
- No permanent files created

**Done when**:
- Stage 6 fixture detection: script identifies calibration_examples.json as Stage 6 (style key present; known ambiguity — fixture is actually Stage 5 but flagged as Stage 6 due to shared "style" key)
- Stage 5 detection: mean_coherence is null, warning-free
- Stage 6 detection: mean_coherence is computed from judge_scores["coherence"]
- Mixed-stage: warning logged, Stage 6 weights used, null for entries without coherence

**Verify**:
- `python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --dry-run 2>&1 | grep 'data_stage'` — outputs "stage6" (known ambiguity, fixture has "style")
- Stage 5 dry-run outputs "data_stage": "stage5"
- Stage 6 dry-run outputs "data_stage": "stage6" with non-null mean_coherence
- Mixed-stage dry-run includes warning about mixed-stage data

**Commit**:
- `spec(baseline-measurement): verify calibration stage detection with fixture data`

### Task 3.6: [x] Verify MIPRO profiles_tested computation from CALIBRATION_GRID

**Do**:
1. Run `measure_mipro_compile_baseline.py --dry-run` (no --dataset, estimated mode)
2. Verify output includes correct profiles_tested computed from CALIBRATION_GRID dimensions
3. Verify total_iterations = profiles_tested × num_prompts
4. Verify the WARNING about estimated mode is printed to stderr
5. Verify duration_seconds = total_iterations × avg_latency

**Files**:
- No permanent files created

**Done when**:
- profiles_tested is dynamically computed (not hard-coded)
- total_iterations and duration_seconds are correct
- WARNING is printed to stderr in estimated mode

**Verify**:
- Output JSON contains `"profiles_tested": 4500` when CALIBRATION_GRID matches 6×6×5×5×5
- Verify profiles_tested is computed from grid by checking: `python -c 'from src.audit.calibration_schema import CALIBRATION_GRID; import math; print(math.prod(len(v) for v in CALIBRATION_GRID.values()))'` matches output
- `"estimated": true` in details

**Commit**:
- `spec(baseline-measurement): verify MIPRO grid computation and estimated mode`

### Task 3.7: [x] Verify concurrent write protection

**Do**:
1. Use a synthetic lock approach for deterministic testing (not relying on timing races):
   a. Manually create a lock file (`.lock` suffix) in `baseline_results/` with a recent mtime, pointing to `baseline_results/spearman_judge_baseline.json`
   b. Run `measure_spearman_baseline.py --dataset /tmp/test_spearman_5.json --output baseline_results/spearman_judge_baseline.json` — verify it detects the active lock and exits 1
   c. Clean up the manual lock file
2. Test stale lock detection: create a lock file with an old mtime (> 300s ago), run the script — verify it removes stale lock and proceeds
3. Verify lock file is cleaned up after the script completes normally

**Files**:
- No permanent files created

**Done when**:
- File-level locking prevents concurrent writes to the same output file
- Stale lock detection works (lock older than 300s is auto-removed)
- Stale lock symlink check works (removes symlink reference before deletion)

**Verify**:
- Script with active lock exits 1 with the expected error message
- Stale lock (old mtime) is auto-removed and script proceeds
- No lock file remains after script completes

**Commit**:
- `spec(baseline-measurement): verify concurrent write protection via file locking`

### Task 3.8: [x] Verify atomic write (no partial output on crash)

**Do**:
1. Run a script and interrupt it during the write phase (between temp file creation and rename)
2. Verify no partial/corrupt output file is left in the output directory
3. Verify the `.tmp` file is cleaned up
4. Verify no lock file is left behind (if the script crashed after acquiring lock)

**Files**:
- No permanent files created

**Done when**:
- Interrupted writes leave no corrupt output
- Temp files are cleaned up
- Lock files are cleaned up (or detected as stale)

**Verify**:
- No `.tmp` or `.lock` files remain in baseline_results/ after interrupted writes

**Commit**:
- `spec(baseline-measurement): verify atomic write safety`

### Task 3.9: [x] Verify --dry-run on all scripts

**Do**:
1. Run `--dry-run` on each of the 4 scripts with appropriate inputs:
   - Spearman: use temp file with composites (e.g., `/tmp/test_spearman_5.json`)
   - Calibration: use `tests/fixtures/calibration_examples.json`
   - MIPRO: no input needed (estimated mode)
   - Rollback: no input needed
2. Verify each script ends with "DRY RUN complete. No output file written."
3. Verify exit code is 0 for all
4. **Data-producing scripts (spearman, calibration, mipro)**: Verify each prints input file path and size, number of records, target output path
5. **Rollback**: Verify it prints threshold seconds, target output path, and isolation method

**Files**:
- No permanent files created

**Done when**:
- All 4 scripts support --dry-run correctly
- No output files are created during dry-run
- Each script prints domain-appropriate diagnostics

**Verify**:
- `test ! -f baseline_results/spearman_judge_baseline.json && test ! -f baseline_results/calibration_baseline.json && test ! -f baseline_results/mipro_compile_baseline.json && test ! -f baseline_results/rollback_check.json`

**Commit**:
- `spec(baseline-measurement): verify --dry-run on all four scripts`

### Task 3.10: [x] Verify --no-overwrite behavior

**Do**:
1. Run each of the three data-producing scripts (spearman, calibration, mipro) normally to create output files. **Do NOT run rollback_check.py** — it does NOT accept `--no-overwrite` (per FR-005/F6).
2. Run each of these three scripts again without --no-overwrite — verify each overwrites with stderr warning
3. Run each of these three scripts with --no-overwrite — verify each exits 1

**Files**:
- No permanent files created

**Done when**:
- Default behavior: overwrites with warning to stderr
- --no-overwrite flag: exits 1 with descriptive error
- rollback_check.py is excluded from this test (does not support --no-overwrite)

**Verify**:
- `python infrastructure/baselines/measure_spearman_baseline.py --output baseline_results/test_nowrite.json` exits 1 with `--no-overwrite` when output exists
- `python infrastructure/baselines/run_calibration_baseline.py --output baseline_results/test_nowrite.json` exits 1 with `--no-overwrite` when output exists
- `python infrastructure/baselines/measure_mipro_compile_baseline.py --output baseline_results/test_nowrite.json` exits 1 with `--no-overwrite` when output exists
- Script exits 0 without `--no-overwrite` when output exists

**Commit**:
- `spec(baseline-measurement): verify --no-overwrite behavior across data-producing scripts`

### Task 3.11: [x] Verify rollback cleanup on SIGINT

**Do**:
1. Run `rollback_check.py` in a way that allows sending SIGINT during the revert
2. Verify the isolated environment is cleaned up after the signal
3. Verify `git worktree list` or `ls /tmp/baseline-rollback-*` does NOT show orphaned environments

**Files**:
- No permanent files created

**Done when**:
- SIGINT triggers cleanup via signal handler
- No orphaned worktrees or clones remain

**Verify**:
- `git worktree list` shows no rollback-check-* entries
- `/tmp/baseline-rollback-*` directories do not exist after cleanup

**Commit**:
- `spec(baseline-measurement): verify rollback cleanup on SIGINT`

### Task 3.12: [x] Adversarial Review of Phase 3 Tasks

**Do**:
1. Run `/bmad-review-adversarial-general` with `/bmad-party-mode`
2. Select the most relevant agents for reviewing edge case handling
3. The reviewers will produce findings
4. Apply valid findings as follow-up fix tasks
5. Mark this review task complete only after findings are addressed

**Files**:
- No files created (review task)

**Done when**:
- Adversarial review completed
- All valid findings addressed (fix tasks applied or rejected with rationale)

**Verify**:
- All scripts exist: `test -f infrastructure/baselines/_shared.py && test -f infrastructure/baselines/measure_spearman_baseline.py && test -f infrastructure/baselines/run_calibration_baseline.py && test -f infrastructure/baselines/measure_mipro_compile_baseline.py && test -f infrastructure/rollback_check.py`
- All edge case tests pass: Spearman n=0, n=1, n=2, constant input
- Adversarial review report written to `.progress.md` with findings count

**Commit**:
- `spec(baseline-measurement): adversarial review round 3 of edge cases and verification`

**Notes**:
- This task triggers an adversarial review using party mode with the most relevant agents
- Reviewers check for: missing edge cases, inconsistent error messages, output schema gaps, NaN handling alignment (F12), idempotency concerns, security considerations (path traversal, symlink attacks)
- After review, immediately create follow-up fix tasks for any valid findings
- Do NOT use checkbox grep for verification — these are review tasks, not implemented code tasks

---

## Phase 4: Quality & Convention Compliance

Headers, formatting, type checking, and convention polish.

### Task 4.1: [x] Run ruff format on all new scripts

**Do**:
1. Run `ruff format infrastructure/baselines/` to format all scripts
2. Run `ruff format infrastructure/rollback_check.py`
3. Run `ruff format infrastructure/baselines/_shared.py`
4. Verify no formatting changes are needed (idempotent check)

**Files**:
- Modify: `infrastructure/baselines/_shared.py`
- Modify: `infrastructure/baselines/measure_spearman_baseline.py`
- Modify: `infrastructure/baselines/run_calibration_baseline.py`
- Modify: `infrastructure/baselines/measure_mipro_compile_baseline.py`
- Modify: `infrastructure/rollback_check.py`

**Done when**:
- All scripts are formatted per ruff conventions

**Verify**:
- `ruff format --check infrastructure/baselines/ infrastructure/rollback_check.py` returns "No errors found"

**Commit**:
- `spec(baseline-measurement): format all scripts with ruff`

### Task 4.2: [x] Verify Apache-2.0 license headers on all scripts

**Do**:
1. Check that each of the 5 scripts contains these 3 tokens within the first 4096 bytes:
   - `SPDX-License-Identifier:`
   - `Architect-Expert-Gap-Forge`
   - `Copyright`
2. Add missing headers if any script is missing tokens
3. **NOTE**: Do NOT rely on `scripts/check_headers.py` — this script is outside the scope of this spec. Use the grep-based verify command below.

**Files**:
- Modify: any script missing license header tokens

**Done when**:
- All 5 scripts pass header check (3 tokens in first 4096 bytes)

**Verify**:
- `for f in infrastructure/baselines/_shared.py infrastructure/baselines/measure_spearman_baseline.py infrastructure/baselines/run_calibration_baseline.py infrastructure/baselines/measure_mipro_compile_baseline.py infrastructure/rollback_check.py; do head -c 4096 "$f" | grep -c 'SPDX-License-Identifier:' | xargs -I{} echo "$f: {}"; done`
- Each file should return 1 for SPDX-License-Identifier:

**Commit**:
- `spec(baseline-measurement): verify Apache-2.0 license headers on all scripts`

### Task 4.3: [x] Verify sys.path import handling by pyright (optional)

**Do**:
1. Read `pyrightconfig.json` to check existing settings
2. **NOTE**: Design.md specifies that pyrightconfig.json's `reportMissingImports: false` handles sys.path imports for baseline scripts. This task is OPTIONAL — only perform if pyright is configured to check these paths.
3. If pyright is configured to check `infrastructure/baselines/`:
   - Verify `reportMissingImports: false` is set in pyrightconfig.json
   - Run `pyright infrastructure/baselines/` to confirm no type errors
4. If pyright is NOT configured to check these paths: skip this task

**Files**:
- May modify: `pyrightconfig.json` (only if needed)

**Done when**:
- sys.path imports in baseline scripts do not produce pyright errors
- OR this task is documented as skipped because pyright already handles it

**Verify**:
- `pyright infrastructure/baselines/` exits 0 (or task is marked skipped)

**Commit**:
- `spec(baseline-measurement): verify sys.path import handling by pyright`

### Task 4.4: [x] Verify timestamp format across all scripts (UTC with Z suffix)

**Do**:
1. Review each script's timestamp generation code
2. Ensure all scripts use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` or equivalent
3. Verify no script uses `datetime.now()` (local time)
4. Verify no script uses isoformat() without ensuring UTC and Z suffix

**Files**:
- Modify: any script using incorrect timestamp format

**Done when**:
- All 4 data-producing scripts use UTC timestamps with Z suffix
- No local time is used for timestamps

**Verify**:
- `grep -n 'datetime' infrastructure/baselines/measure_spearman_baseline.py infrastructure/baselines/run_calibration_baseline.py infrastructure/baselines/measure_mipro_compile_baseline.py infrastructure/rollback_check.py` — all should reference `timezone.utc`

**Commit**:
- `spec(baseline-measurement): verify UTC timestamps across all scripts`

### Task 4.5: [x] Verify _shared.py edge cases in write_output_atomic

**Do**:
1. Review `write_output_atomic()` for EXDEV error handling (cross-device link, errno 18)
2. Verify temp file cleanup on failure (tmp_path.unlink(missing_ok=True))
3. Verify file mode is 0o600 for both temp and output files
4. Verify fsync is called after writing and before rename

**Files**:
- No files modified (review task, fix if needed)

**Done when**:
- EXDEV (cross-device) is handled via shutil.move fallback
- Temp files are cleaned up on any failure
- File permissions are 0o600

**Verify**:
- Code review confirms all requirements above

**Commit**:
- `spec(baseline-measurement): verify atomic write robustness in _shared.py`

### Task 4.6: [x] Verify _shared.py edge cases in check_output_lock

**Do**:
1. Review `check_output_lock()` for:
   - O_CREAT|O_EXCL exclusive creation (not relying on umask)
   - Stale lock detection at 300s threshold
   - Symlink check on stale lock before removal
   - Poll interval of 0.5s
   - 30s total timeout
2. Verify `_is_lock_stale()` handles OSError (file removed between stat and check)

**Files**:
- No files modified (review task, fix if needed)

**Done when**:
- All lock handling edge cases are covered
- Stale lock symlink check is present

**Verify**:
- Code review confirms all requirements above

**Commit**:
- `spec(baseline-measurement): verify file lock handling in _shared.py`

### Task 4.7: [x] Verify _sanitize_output_dict handles nested structures

**Do**:
1. Review `_sanitize_output_dict()` and `_sanitize_list_item()` for:
   - Recursive dict handling
   - List item sanitization (including nested lists)
   - Float NaN/inf to None conversion
   - Non-float values passed through unchanged
2. Test with a deeply nested dict containing NaN floats at various levels

**Files**:
- No files modified (review task, fix if needed)

**Done when**:
- Nested dicts and lists are fully sanitized
- Non-float values are not affected

**Verify**:
- `python -c 'from infrastructure.baselines._shared import _sanitize_output_dict; print(_sanitize_output_dict({"a": float("nan"), "b": {"c": [float("inf"), "str"]}}))'` outputs correct nulls

**Commit**:
- `spec(baseline-measurement): verify JSON sanitization for nested structures`

### Task 4.8: [x] Verify output path resolution (~ expansion, relative paths)

**Do**:
1. Review each script's argument parser for path resolution
2. Ensure all path arguments use `Path(path).resolve()` for ~ expansion and relative-to-absolute conversion
3. Verify output paths resolve correctly when running from different working directories

**Files**:
- Modify: any script with incorrect path resolution

**Done when**:
- All path arguments support absolute, relative, and ~ expansion
- Output paths resolve correctly from any working directory

**Verify**:
- `python infrastructure/baselines/measure_spearman_baseline.py --dataset ~/tests/fixtures/calibration_examples.json --output ~/baseline_results/test.json --dry-run` works

**Commit**:
- `spec(baseline-measurement): verify path resolution across all scripts`

---

## Phase 5: Verification & End-to-End

Full integration verification, documentation, and final checks.

### Task 5.1: [x] Verify all scripts can execute against real fixture data

**Do**:
1. **Spearman**: Create a temp file with correct baseline_composites/adapter_composites structure:
   `echo '{"baseline_composites":[0.7,0.8,0.65,0.9],"adapter_composites":[0.78,0.85,0.7,0.92]}' > /tmp/test_spearman_5.json`
   Then run `measure_spearman_baseline.py --dataset /tmp/test_spearman_5.json`
   **NOTE**: `tests/fixtures/judge_scoring_response.json` has wrong structure (single judge response, not composites array). Do NOT use it directly.
2. Run `run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json`
3. Run `measure_mipro_compile_baseline.py` (no dataset — estimated mode)
4. Run `rollback_check.py` (creates isolated env, reverts, cleans up)
5. Verify all exit 0 and produce valid JSON output at default output paths:
   - `baseline_results/spearman_judge_baseline.json`
   - `baseline_results/calibration_baseline.json`
   - `baseline_results/mipro_compile_baseline.json`
   - `baseline_results/rollback_check.json`

**Files**:
- No files modified (temp test files in /tmp/)

**Done when**:
- All 4 scripts execute successfully against fixture or synthetic data
- Output JSON files are created at their default paths in baseline_results/
- All outputs have valid schema (schema_version, type, timestamp, score, details)

**Verify**:
- `bash -c 'set -e; python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_spearman_5.json; python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json; python infrastructure/baselines/measure_mipro_compile_baseline.py; python infrastructure/rollback_check.py'`
- Check output files exist: `test -f baseline_results/spearman_judge_baseline.json && test -f baseline_results/calibration_baseline.json && test -f baseline_results/mipro_compile_baseline.json && test -f baseline_results/rollback_check.json`

**Commit**:
- `spec(baseline-measurement): end-to-end verification against fixture data`

### Task 5.2: [x] Verify baseline_results/ JSON output schema

**Do**:
1. Read each output file in `baseline_results/` and verify the JSON schema:
   - `schema_version` is "1"
   - `type` matches the script type
   - `timestamp` is ISO8601 with Z suffix
   - `score` is a float (or null for edge cases)
   - `status` is present
   - `score_description` is present and matches the type
   - `details` contains script-specific fields
2. Verify no unexpected fields are present

**Files**:
- No files modified

**Done when**:
- All output JSON files conform to the shared baseline result schema

**Verify**:
- JSON schema validation via `python -c 'import json; [json.loads(open(f).read()) for f in ["baseline_results/spearman_judge_baseline.json", "baseline_results/calibration_baseline.json", "baseline_results/mipro_compile_baseline.json", "baseline_results/rollback_check.json"]]`

**Commit**:
- `spec(baseline-measurement): verify baseline_results JSON output schema`

### Task 5.3: [x] Verify idempotency — re-running produces same scores

**Do**:
1. Run each script that produces a score (spearman, calibration, mipro) twice with the same inputs:
   - Spearman: use `/tmp/test_spearman_5.json` (created in Task 5.1)
   - Calibration: use `tests/fixtures/calibration_examples.json`
   - MIPRO: no input file needed (estimated mode)
2. Compare the score and details fields between runs (timestamp may differ)
3. Verify scores and details are identical across runs

**Files**:
- No files modified

**Done when**:
- Re-running scripts with same inputs produces identical score and details

**Verify**:
- Spearman idempotency: `python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_spearman_5.json --output /tmp/run1.json && python infrastructure/baselines/measure_spearman_baseline.py --dataset /tmp/test_spearman_5.json --output /tmp/run2.json && diff <(python -c 'import json; d=json.load(open("/tmp/run1.json")); del d["timestamp"]; print(json.dumps(d, sort_keys=True))') <(python -c 'import json; d=json.load(open("/tmp/run2.json")); del d["timestamp"]; print(json.dumps(d, sort_keys=True))') && echo "Spearman idempotency check passed"`
- Calibration idempotency: `python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --output /tmp/cal1.json && python infrastructure/baselines/run_calibration_baseline.py --dataset tests/fixtures/calibration_examples.json --output /tmp/cal2.json && diff <(python -c 'import json; d=json.load(open("/tmp/cal1.json")); del d["timestamp"]; print(json.dumps(d, sort_keys=True))') <(python -c 'import json; d=json.load(open("/tmp/cal2.json")); del d["timestamp"]; print(json.dumps(d, sort_keys=True))') && echo "Calibration idempotency check passed"`

**Commit**:
- `spec(baseline-measurement): verify idempotency — same inputs produce same scores`

### Task 5.4: [x] Verify .gitignore includes baseline_results/ (confirmed via git ls-files)

**Do**:
1. Check that `.gitignore` contains `baseline_results/`
2. Verify no files in `baseline_results/` are tracked by git
3. Verify `git status` does not show baseline_results/ files as untracked

**Files**:
- No files modified (review task, fix .gitignore if needed)

**Done when**:
- `baseline_results/` is properly ignored by git
- No baseline_results files appear in `git status`

**Verify**:
- `git ls-files baseline_results/` returns nothing
- `git status --porcelain baseline_results/` returns nothing

**Commit**:
- `spec(baseline-measurement): verify baseline_results/ is gitignored`

### Task 5.5: Final — Commit all changes

**Do**:
1. Stage all modified and new files:
   - `requirements.txt`
   - `pyproject.toml`
   - `.gitignore`
   - `infrastructure/__init__.py` (if not exists)
   - `infrastructure/baselines/__init__.py`
   - `infrastructure/baselines/_shared.py`
   - `infrastructure/baselines/measure_spearman_baseline.py`
   - `infrastructure/baselines/run_calibration_baseline.py`
   - `infrastructure/baselines/measure_mipro_compile_baseline.py`
   - `infrastructure/rollback_check.py`
2. Commit with a summary message covering all phases
3. Verify `git status` is clean after commit

**Files**:
- All new and modified files listed above

**Done when**:
- All changes are committed
- Working tree is clean

**Verify**:
- `git status` shows "nothing to commit, working tree clean"
- **NOTE**: Use `;` instead of `&&` to prevent silent skip on first failure:
  `git status --porcelain ; test -z "$(git status --porcelain)" && echo "Clean"`

**Commit**:
- `spec(baseline-measurement): complete baseline measurement implementation — Spearman, calibration, MIPRO, rollback`

**Notes**:
- Include co-author attribution for Claude's contribution
- Ensure all adversarial review findings have been addressed before this commit
- Use `;` in verify commands (not `&&`) to prevent silent skip when first command fails
