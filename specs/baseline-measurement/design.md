# Design: Baseline Measurement

**Spec**: baseline-measurement
**Epic**: aegf-infrastructure (Story 0.1)
**Version**: 1.0 — Initial design

---

## 1. Architecture Overview

This spec creates four independent CLI scripts that read existing fixture data, perform local computation, and write structured JSON output. No runtime services, no HTTP servers, no external API calls.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Project Root                                  │
│                                                                      │
│  src/audit/schema.py          SCORING_WEIGHTS, CALIBRATION_...       │
│  src/audit/calibration_schema.py  CalibrationReport, CALIBRATION_GRID│
│  src/factory/ldi_validator.py     Factory LDI pattern               │
│  src/curation/quality_filter.py   Curation LDI pattern              │
│                                                                      │
│  tests/fixtures/                                                   │
│    calibration_examples.json    4 entries, Stage 5 data             │
│    judge_scoring_response.json  Full judge output (reference)       │
│    inference_results.json       Baseline + adapter text responses   │
│                                                                      │
│  infrastructure/  ← NEW PACKAGE                                     │
│    __init__.py                                                      │
│    dependency_check.py   (existing — Rich CLI reference)            │
│    baselines/    ← NEW SUBPACKAGE                                   │
│      __init__.py        ← NEW                                       │
│      measure_spearman_baseline.py   ← NEW (FR-002)                  │
│      run_calibration_baseline.py    ← NEW (FR-003)                  │
│      measure_mipro_compile_baseline.py  ← NEW (FR-004)              │
│    rollback_check.py      ← NEW (FR-005)                            │
│                                                                      │
│  baseline_results/  ← NEW (gitignored, runtime output)              │
│    spearman_judge_baseline.json   ← output from FR-002              │
│    calibration_baseline.json      ← output from FR-003              │
│    mipro_compile_baseline.json    ← output from FR-004              │
│                                                                      │
│  requirements.txt           ← MODIFIED (add scipy==1.17.1)          │
│  pyproject.toml             ← MODIFIED (add scipy dependency)       │
│  .gitignore                 ← MODIFIED (add baseline_results/)      │
│  pyproject.toml             ← MODIFIED (add pyright exclude)        │
└─────────────────────────────────────────────────────────────────────┘
```

**System Boundaries**:
- **Inputs**: JSON fixture files on local filesystem, CALIBRATION_GRID constant from source code
- **Processing**: Pure Python computation (scipy.stats.spearmanr, weighted averages, arithmetic)
- **Outputs**: JSON files in `baseline_results/`, stdout/stderr messages
- **External Dependencies**: scipy==1.17.1 (new), scipy depends on numpy<2.8,>=1.26.4 (already present)

---

## 2. Component Design

### 2.1 measure_spearman_baseline.py

**Purpose**: Compute Spearman rank correlation between baseline and adapter judge scores.

**Data Flow**:
```
--dataset (JSON file)
  └──> Load & validate: baseline_composites[], adapter_composites[]
       ├──> Reject: symlinks, empty files, > 10 MB
       ├──> Parse JSON
       ├──> Validate: both arrays present, same length, float values
       ├──> Filter NaN pairs (preserves index pairing)
       ├──> Edge case checks:
       │    ├──> n=0 → status="no_valid_data", rho="uncomputable"
       │    ├──> n=1 → status="single_sample_undefined", rho="uncomputable"
       │    ├──> n=2 → status="insufficient_samples", rho="uncomputable"
       │    └──> constant input → status="constant_input", rho=0.0
       └──> Determine method: n<10 → "exact", n>=10 → "asymptotic"
       └──> scipy.stats.spearmanr(baseline, adapter, method=determined_method)
            ├──> Clamp rho to [-1.0, 1.0] if outside range (log warning)
            └──> Write output JSON (atomic + fsync)
```

**File Structure**: Single file, no internal modules. Logic is linear enough to not need splitting.

**CLI Interface**:
```
measure_spearman_baseline.py --dataset <path> [--output <path>] [--dry-run] [--no-overwrite]
```

**Shared Logic**: Inherits validation and output helpers from `_shared.py` (validate_input_file, write_output_atomic, check_output_lock, release_lock). The Spearman computation itself is self-contained but uses shared I/O helpers with all scripts.

**Edge Cases**:
| Case | Detection | Output |
|------|-----------|--------|
| Symlink input | `os.path.islink()` | Exit 1 |
| Empty file | `os.path.getsize() == 0` | Exit 1 |
| File > 10 MB | `os.path.getsize() > 10_000_000` | Exit 1 |
| Missing keys | JSON schema validation | Exit 1 |
| Array type mismatch | `isinstance(..., list)` check | Exit 1 |
| Length mismatch | `len(b) != len(a)` | Exit 1 |
| All NaN | After filtering, n=0 | `p_value: null`, status="no_valid_data" |
| Single sample | After filtering, n=1 | `p_value: null`, status="single_sample_undefined" |
| Two samples | n=2 always | `p_value: null`, status="insufficient_samples" |
| Constant input | `len(set(baseline))<=1 or len(set(adapter))<=1` | rho=0.0, status="constant_input" |
| NaN in scipy result | rho outside [-1,1] | Clamped, logged |
| Non-numeric data | `isinstance(v, (int, float))` fails | Exit 1, "Data contains non-numeric values" |

**Concurrency**: Acquires lock via `check_output_lock()`, writes, then calls `release_lock(lock_path)`. Waits up to 30s, exits 1 if lock persists after stale detection.

**JSON serialization safety**: All float values that could be NaN or infinity (rho, p_value) MUST be converted before JSON dump. Use `_sanitize_output_dict(result)` before writing any output. If `scipy.stats.spearmanr` returns NaN for p_value (degenerate case), `_sanitize_output_dict` converts it to `null` in JSON. Scripts MUST document `null` as the representation for uncomputable float values (consistent with F12 alignment). If rho is outside [-1,1] (shouldn't happen but guard against it), clamp to [-1.0, 1.0] and log warning. Same guard applies to coherence scores and LDI values.

**F12: NaN handling alignment**: All scripts MUST use `null` (Python `None`) for uncomputable float values (`score`, `p_value`, etc.) — NOT the string `"uncomputable"`. The string `"uncomputable"` is reserved for non-float fields (e.g., `status` strings). Consistent `null` usage lets consumers distinguish "uncomputable float" from "meaningless numeric field" via JSON type alone.

**--dry-run behavior** (in addition to --no-overwrite specified in common section):
- Same as common --dry-run: reads input (if present), validates, computes correlation metrics
- Prints: number of valid pairs (after NaN filtering), expected method selection (exact/asymptotic), edge case status if data insufficient
- Does NOT acquire lock, does NOT write output file

**--verbose/--quiet flags**:
- `--verbose`: print each validation step to stdout (input path, grid dimensions, mode selection)
- `--quiet`: suppress all non-error output; only print errors to stderr
- Default (no flag): print summary line ("Compile baseline: 27000 iterations, estimated=true")

---

### 2.2 run_calibration_baseline.py

**Purpose**: Capture calibration quality metrics (coherence, LDI) from existing calibration results.

**Data Flow**:
```
--dataset (JSON file)
  └──> Load & validate: calibration_results[]
       ├──> Reject: symlinks, empty files, > 10 MB
       ├──> Parse JSON
       ├──> Detect stage:
       │    ├──> Check first entry for Stage 6 keys (parameter_effectiveness, coherence, etc.)
       │    ├──> If present: Stage 6, use CALIBRATION_SCORING_WEIGHTS
       │    └──> If absent: Stage 5, coherence=null, SCORING_WEIGHTS for composite
       ├──> Mixed-stage detection:
       │    └──> If entries have both Stage 5 and Stage 6 keys
       │         → Treat as Stage 6, log warning, compute coherence where available
       ├──> Extract coherence:
       │    ├──> Stage 6: judge_scores["coherence"] for each entry
       │    └──> Stage 5: null (NOT derived from composite_score)
       ├──> Validate coherence range [0.0, 1.0], log out-of-range
       ├──> Source LDI from --ldi-source (separate JSON/JSONL file):
       │    ├──> Validate via validate_input_file() (same checks as --dataset: symlink, empty, size, allowed_dirs)
       │    ├──> Auto-detect format: try json.load() whole file → JSONDecodeError → try line-by-line JSONL
       │    ├──> Parse records with "ldi" float field
       │    ├──> Skip non-numeric ldi values (log warning, exclude from mean/pass_rate)
       │    └──> Compute: ldi_pass_rate = count(ldi >= threshold) / total
       └──> Write output JSON (atomic + fsync)
```

**File Structure**: Single file. LDI parsing logic is a small helper function at the top of the file.

**CLI Interface**:
```
run_calibration_baseline.py --dataset <path> [--ldi-source <path>] [--ldi-threshold <float>] [--output <path>] [--dry-run] [--no-overwrite]
```

**Shared Logic**:
- `validate_input_file(path)` — symlink check, existence check, size check, file check — shared with all scripts
- `write_output_atomic(path, data, mode=0o600)` — temp file + rename + fsync — shared with all scripts
- `release_lock(lock_path)` — removes lock file — shared with all scripts
- Input normalization: both `{"calibration_results": [...]}` and top-level `[{...}, ...]` formats handled

**Edge Cases**:
| Case | Detection | Output |
|------|-----------|--------|
| Symlink input | `os.path.islink()` | Exit 1 |
| File not found | `not p.exists()` | Exit 1 ("Cannot read {path}: No such file") |
| Empty file | `os.path.getsize() == 0` | Exit 1 |
| File > 10 MB | `os.path.getsize() > 10_000_000` | Exit 1 |
| Missing keys | JSON schema validation | Exit 1 |
| Empty results array | `len(results) == 0` | mean_coherence=null |
| No coherence field | Stage 5 data | mean_coherence=null |
| Out-of-range coherence | Coherence < 0 or > 1 | Warn, include in mean, note in details |
| Missing --ldi-source | No arg provided | mean_ldi=null, ldi_pass_rate=null |
| Unparseable --ldi-source | JSON/JSONL error | mean_ldi=null, ldi_pass_rate=null |
| --ldi-source fails validation | validate_input_file() raises | Exit 1 (same as --dataset) |
| Non-numeric ldi value | isinstance(ldi, float) fails | Skip record, log warning, exclude from mean/pass_rate |
| Mixed-stage data | Both Stage 5 and 6 keys | Warn, treat as Stage 6, use per-entry weight sets |
| 0 LDI records | Parseable but empty array | mean_ldi=null, ldi_pass_rate=null |
| Negative LDI value | Record check | Log warning, include in mean (LDI can be negative for certain text types) |

**Stage Detection Logic**:
```python
STAGE_6_KEYS = {"parameter_effectiveness", "coherence", "parameter_alignment", "task_completion", "style"}

def detect_stage(results):
    """Detect data stage by checking ALL entries for Stage 6 keys.
    Per FR-003.2: if ANY result entry contains Stage 6 keys, treat as Stage 6."""
    if not results:
        return "unknown"
    # Check all entries for any Stage 6 key presence
    has_stage6 = False
    for entry in results:
        judge_scores = entry.get("judge_scores", {})
        if STAGE_6_KEYS.intersection(judge_scores.keys()):
            has_stage6 = True
            break
    # Detect mixed-stage
    has_stage5 = False
    for entry in results:
        judge_scores = entry.get("judge_scores", {})
        if not STAGE_6_KEYS.intersection(judge_scores.keys()):
            has_stage5 = True
            break
    if has_stage6 and has_stage5:
        log.warning("Mixed-stage data detected; using Stage 6 weight set for all entries.")
    return "stage6" if has_stage6 else "stage5"
```

**--no-overwrite behavior** (all scripts):
- Check: `Path(output).exists() and Path(output).stat().st_size > 0`
- If exists and flag NOT provided: print to stderr `"Output file exists: {path}. Overwriting."`
- If exists and flag IS provided: exit 1 with `"Output file already exists: {path}. Use --no-overwrite to prevent overwriting."`

**--dry-run behavior** (all scripts):
- Read input, validate, compute summary stats, print to stdout:
  - Input file path and resolved size
  - Number of records detected
  - Target output path (full resolved path)
  - Edge case status if data is insufficient (same as normal run)
  - Final line: `"DRY RUN complete. No output file written."`
- Exit 0 without writing output file, without acquiring lock

---

### 2.3 measure_mipro_compile_baseline.py

**Purpose**: Measure or estimate MIPROv2 compile duration without running actual grid search.

**Data Flow**:
```
[--dataset <CalibrationReport JSON>]
  └──> Load CalibrationReport (optional)
       ├──> Parse JSON
       ├──> Check for statistics.execution_time_seconds
       ├──> If present and non-null:
       │    └──> measured mode: score = execution_time_seconds
       └──> If missing/malformed/null:
            └──> estimated mode: score = total_iterations × avg_latency_seconds
                 ├──> total_iterations = profiles_tested × num_prompts
                 │    └──> profiles_tested computed dynamically: product of all CALIBRATION_GRID dimension lengths
                 │    └──> num_prompts: --num-prompts > prompt_count > 6
                 └──> avg_latency: --avg-latency > 0.5 (UNVERIFIED PLACEHOLDER)
                       └──> Print WARNING to stderr about placeholder
  └──> Write output JSON (atomic + fsync)
```

**File Structure**: Single file. CALIBRATION_GRID parsing is a helper function.

**CLI Interface**:
```
measure_mipro_compile_baseline.py [--dataset <CalibrationReport>] [--num-prompts <int>] [--avg-latency <float>] [--output <path>] [--dry-run] [--no-overwrite]
```

**Shared Logic**:
- `write_output_atomic(path, data)` — shared with all scripts
- `check_output_lock(output_path)` — shared with all scripts

**Mode Selection**:
```python
# Priority chain for mode selection:
# 1. Has valid CalibrationReport with execution_time_seconds → "measured"
# 2. No report or report malformed → "estimated"
# Estimated mode requires manual --avg-latency override for accuracy
```

**Edge Cases**:
| Case | Detection | Output |
|------|-----------|--------|
| Missing --dataset | No arg provided | estimated mode |
| Malformed report JSON | JSON parse error | estimated mode, warn |
| Missing statistics key | Dict check | estimated mode, warn |
| execution_time_seconds is null | Value check | estimated mode, warn |
| profiles_tested wrong | Product of CALIBRATION_GRID dimensions | Warn, use actual product |
| Negative avg_latency | Value check | Clamp to 0.0, warn |
| num_prompts = 0 or negative | Arg validation | Exit 1: "num-prompts must be positive" |
| avg_latency negative | Value check | Clamp to 0.0, warn (total_iterations will be 0) |

**Constraint**: `profiles_tested` MUST be computed dynamically as `math.prod(len(v) for v in CALIBRATION_GRID.values())`. Hard-coding the value 4500 is prohibited. If CALIBRATION_GRID dimensions change, the script must reflect the new product at runtime.

**Constraint (F11)**: If CALIBRATION_GRID is empty or missing keys at runtime, exit 1 with `"CALIBRATION_GRID is empty — cannot compute profiles_tested"`. Do NOT fall back to estimated mode with profiles_tested=0 (which would produce a misleading 0-second estimate).

**Constraint**: `num_prompts` MUST be validated to be >= 1. `avg_latency` defaults to 0.5 but can be overridden via CLI. If `avg_latency` is negative, clamp to 0.0 and warn.

---

### 2.4 rollback_check.py

**Purpose**: Verify git revert completes in under 60 seconds in an isolated environment.

**Data Flow**:
```
  └──> Create isolated environment
       ├──> Prefer: git worktree add (fast, lightweight)
       └──> Fallback: git clone to temp directory
       ├──> cd into isolated environment
       ├──> git add (empty file or trivial change)
       ├──> git commit -m "baseline-test-commit"
       ├──> test_commit = HEAD
       ├──> Start timer: time.perf_counter()
       ├──> git revert HEAD --no-edit (subprocess with timeout=60.0 to prevent infinite hang)
       ├──> Stop timer
       ├──> Check: duration < 60.0s
       ├──> Verify: git status clean (no modified/untracked/staged files)
       └──> Cleanup: remove worktree/clone
            ├──> atexit handler for normal exit
            └──> SIGINT/SIGTERM handler for interruption
```

**File Structure**: Single file. Cleanup logic in helper functions at the top.

**CLI Interface**:
```
rollback_check.py [--target <seconds>] [--output <path>] [--dry-run]
```

**F6: CLI difference from other scripts**: rollback_check.py does NOT accept `--no-overwrite` because it is not expected to be run repeatedly against the same output. The `--target` and `--output` flags are specific to this script. Document this difference in the README or help text to avoid user confusion.

**Isolation Strategy**:
```python
# Priority: worktree > clone
# worktree: faster, shares .git, lightweight
# clone: slower, complete copy, more isolation
# Choice depends on repo size and available disk space

def create_isolated_env():
    """Create test commit environment without affecting main repo.
    Git worktree creates the directory itself; do NOT pre-create with mkdtemp.
    """
    # Try worktree first — git worktree add creates the directory
    # Use parent temp dir; git worktree add creates the worktree sub-directory inside it
    worktree_parent = tempfile.mkdtemp(prefix="baseline-rollback-worktree-")
    worktree_name = f"rollback-check-{os.getpid()}"
    worktree_path = Path(worktree_parent) / worktree_name
    try:
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path)],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path.cwd())  # ensure we're in the main repo
        )
        if result.returncode == 0:
            return worktree_path, "worktree"
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        pass
    # Fallback: clone to temp subdirectory with its own timeout
    clone_base = tempfile.mkdtemp(prefix="baseline-rollback-clone-")
    clone_path = Path(clone_base) / "repo"
    try:
        subprocess.run(
            ["git", "clone", str(Path.cwd()), str(clone_path)],
            check=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        _die("git clone timed out after 120s — repo may be too large")
    except subprocess.CalledProcessError as e:
        _die(f"git clone failed: {e.stderr.strip()}")
    return clone_path, "clone"
```

**Edge Cases**:
| Case | Detection | Output |
|------|-----------|--------|
| Worktree add fails | Return code check | Fallback to clone |
| Clone fails | Return code check | Exit 1 |
| git revert fails | Return code check | Exit 1 |
| Revert > 60s | Timer check | Exit 1 |
| Clean status fails | git status check | Exit 1 |
| SIGINT during revert | Signal handler | Cleanup, exit 1 |
| Cleanup fails | Exception handler | Log warning, exit 0 |

---

## 3. Module Structure

```
infrastructure/
├── __init__.py                           # Existing
├── dependency_check.py                   # Existing (Rich CLI reference)
├── rollback_check.py                     # NEW — standalone script
└── baselines/
    ├── __init__.py                       # NEW — makes baselines a package
    ├── _shared.py                        # NEW — shared utilities
    │   ├── BaselineError                 # Exception (testable)
    │   ├── validate_input_file()         # symlink, empty, size, path traversal
    │   ├── write_output_atomic()         # mode=0o600, temp → rename → fsync
    │   ├── check_output_lock()           # TOCTOU-safe, stale detection
    │   ├── release_lock()                # best-effort cleanup
    │   ├── MAX_INPUT_SIZE                # 10 MB constant
    │   ├── LOCK_TIMEOUT_SECONDS          # 30s constant
    │   ├── LOCK_POLL_INTERVAL            # 0.5s constant
    │   └── LOCK_STALE_SECONDS            # 300s constant
    ├── measure_spearman_baseline.py      # NEW — FR-002
    ├── run_calibration_baseline.py       # NEW — FR-003
    └── measure_mipro_compile_baseline.py # NEW — FR-004
```

**Design Decision: Shared module vs independent scripts**:

| Aspect | Shared Module `_shared.py` | Independent Scripts |
|--------|---------------------------|-------------------|
| Code reuse | High (validate, write, lock) | Low (duplicate in each) |
| Import complexity | Requires sys.path manipulation (same as src/ imports) | Each resolves own path |
| Testing | Requires shared module tests | Self-contained |
| Risk | Circular imports, coupling | Slightly more code, cleaner boundaries |
| Decision | **Yes** — small, simple helpers | |

**Shared module rationale**:
- `validate_input_file()`, `write_output_atomic()`, `check_output_lock()` are identical across all 4 scripts
- DRYing these into a shared module reduces code by ~100 lines total
- The shared module has the same import path challenge as src/ imports (both use sys.path manipulation)
- No circular import risk: shared module has NO external imports beyond stdlib
- Minimal test surface: 3 simple functions, no complex logic

**Shared module contents** (`infrastructure/baselines/_shared.py`):
```python
"""Shared utilities for baseline measurement scripts.

All helper functions raise BaselineError instead of calling sys.exit()
so they can be unit-tested without subprocess mocking. Each script's
main() catches BaselineError, prints to stderr, and calls sys.exit(1).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────
MAX_INPUT_SIZE = 10_000_000       # 10 MB
DEFAULT_OUTPUT_DIR = "baseline_results"
LOCK_TIMEOUT_SECONDS = 30
LOCK_POLL_INTERVAL = 0.5
LOCK_STALE_SECONDS = 300           # 5 min — stale lock threshold
TEMP_FILE_MODE = 0o600
LOCK_FILE_MODE = 0o600

# ── Exceptions ─────────────────────────────────────────────────────────
class BaselineError(Exception):
    """Raised by helpers on fatal errors; caught in each script's main()."""

# ── Input validation ───────────────────────────────────────────────────
def validate_input_file(path: str | Path, allowed_dirs: tuple[str, ...] | None = None) -> None:
    """Validate input file is a regular file (not symlink, not empty, under size limit, in allowed dir).

    Args:
        path: Path to validate.
        allowed_dirs: Tuple of allowed parent directories. If None, defaults to
            the project root (parent of infrastructure/). Each script may pass
            a more restrictive set.
    """
    p = Path(path).resolve()
    if p.is_symlink():
        raise BaselineError(f"Input file is a symlink: {p}. Refusing to follow symlinks for security.")
    if not p.is_file():
        raise BaselineError(f"Input is not a regular file: {p}.")
    size = p.stat().st_size
    if size == 0:
        raise BaselineError(f"Input file is empty: {p}.")
    if size > MAX_INPUT_SIZE:
        raise BaselineError(f"Input file exceeds 10 MB limit: {p} ({size} bytes).")
    # Path traversal: reject if resolved path is outside allowed directories
    if allowed_dirs is None:
        # Default: allow files under the project root (parent of infrastructure/)
        allowed_dirs = (str(Path(__file__).resolve().parent.parent),)
    allowed_resolved = [Path(d).resolve() for d in allowed_dirs]
    for allowed in allowed_resolved:
        try:
            p.relative_to(allowed)  # Raises ValueError if not relative
        except ValueError:
            raise BaselineError(f"Input path outside allowed directories: {p}")

# ── Atomic output ──────────────────────────────────────────────────────
def write_output_atomic(path: str | Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: temp file (mode 0o600) → rename → fsync.
    On failure, cleans up temp file to prevent accumulation of artifacts.

    R3: Caller should validate that the output directory is not a symlink
    before calling this function. Each script validates the output parent path
    (checks for symlinks, checks isdir) before calling this function.
    """
    p = Path(path).resolve()  # R2: resolve to handle symlinked output dirs
    os.makedirs(p.parent, exist_ok=True)  # R2 CRITICAL: no follow_symlinks — output parent must be validated by caller
    tmp_path = p.with_suffix(p.suffix + ".tmp")
    try:
        with open(tmp_path, "w", mode=TEMP_FILE_MODE) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)  # F7: support non-ASCII
            f.flush()
            os.fsync(f.fileno())
        os.rename(str(tmp_path), str(p))
    except OSError as e:
        # R2: EXDEV — cross-device link (NFS, bind mount, tmpfs)
        if e.errno == 18:
            import shutil
            shutil.move(str(tmp_path), str(p))
        else:
            tmp_path.unlink(missing_ok=True)
            raise
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

# ── File locking ───────────────────────────────────────────────────────
def check_output_lock(output_path: str | Path) -> Path:
    """Acquire exclusive lock; returns lock_path. Retries on FileExistsError (TOCTOU safe).
    Creates output directory if missing (F9: avoids race between mkdir and lock).
    """
    p = Path(output_path).resolve()
    os.makedirs(p.parent, exist_ok=True)  # F9: ensure dir exists before lock acquisition
    lock_path = p.with_suffix(p.suffix + ".lock")
    waited = 0.0
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL, LOCK_FILE_MODE)  # R3: explicit mode, not relying on umask
            os.close(fd)
            return lock_path
        except FileExistsError:
            # Check for stale lock (no writer holding the fd)
            if _is_lock_stale(lock_path):
                # R3: symlink check before remove — prevent deleting through symlink
                if lock_path.is_symlink():
                    lock_path.unlink()  # remove symlink target reference, not target
                else:
                    os.remove(lock_path)
                continue  # retry creation
            if waited >= LOCK_TIMEOUT_SECONDS:
                raise BaselineError(f"Another process is writing to {p}. Exiting.")
            time.sleep(LOCK_POLL_INTERVAL)
            waited += LOCK_POLL_INTERVAL

def release_lock(lock_path: Path) -> None:
    """Remove lock file. No-op if lock_path does not exist."""
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass  # Best-effort: log if needed, but don't fail

def _is_lock_stale(lock_path: Path) -> bool:
    """Heuristic: if lock file is older than LOCK_STALE_SECONDS, assume stale.

    **F4: mtime granularity caveat**: st_mtime resolution is 1s on most filesystems,
    1ns on modern Linux ext4/xfs. On filesystems with coarse granularity (FAT32,
    NFS with default settings), two locks created within the same second may appear
    simultaneous, causing false stale detection. LOCK_STALE_SECONDS=300 is large
    enough that granularity noise is negligible.
    """
    try:
        mtime = lock_path.stat().st_mtime
        return (time.time() - mtime) > LOCK_STALE_SECONDS
    except OSError:
        return False

# ── JSON serialization helpers ─────────────────────────────────────────
def _make_json_safe(value: Any) -> Any:
    """Ensure float values are JSON-serializable. NaN/inf → string fallback."""
    import math
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None  # JSON-safe null; caller should use string alternative in details
    return value

def _sanitize_output_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize dict and lists: replace NaN/inf floats with None (null).

    R3: Also handles list values — if any output dict contains a list of floats,
    NaN values inside lists would otherwise pass through unsanitized and produce
    invalid JSON (bare NaN literal, not null).
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            result[k] = None
        elif isinstance(v, dict):
            result[k] = _sanitize_output_dict(v)
        elif isinstance(v, list):  # R3: handle nested lists
            result[k] = [_sanitize_list_item(item) for item in v]
        else:
            result[k] = v
    return result


def _sanitize_list_item(v: Any) -> Any:
    """Sanitize a single list item: recurse if dict/list, sanitize float."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    elif isinstance(v, dict):
        return _sanitize_output_dict(v)
    elif isinstance(v, list):
        return [_sanitize_list_item(item) for item in v]
    return v
```

**Usage in each script** (relative import from same package):
```python
from __future__ import annotations
import sys
import logging
from pathlib import Path

# Resolve project root for src/ imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import shared utilities (relative — same package)
from ._shared import (
    BaselineError,
    validate_input_file,
    write_output_atomic,
    check_output_lock,
    release_lock,
)

def main(argv: list[str] | None = None) -> int:
    try:
        return _impl(argv)
    except BaselineError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # Fallback: prevent raw tracebacks from leaking to user
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2

def _impl(argv: list[str] | None = None) -> int:
    # ... actual implementation ...
    return 0
```

**Score semantics**: The `score` field has different meanings per script type:
- Spearman: rho (correlation coefficient, range [-1, 1])
- Calibration: mean_coherence (range [0, 1], or null if Stage 5 data)
- MIPRO: duration_seconds (wall-clock seconds)

The `score_description` field (Section 4.3) provides human-readable context. Consumers MUST read this to interpret `score`. The `status` field (`"ok"` or edge case code) is a cheaper discriminator than checking `score` type. Both are required in all output JSON.

**Usage in `rollback_check.py`** (sibling in `infrastructure/`, not in baselines/):
```python
# Resolve project root for src/ imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import shared utilities — sibling directory at infrastructure/
from infrastructure.baselines._shared import (
    BaselineError,
    validate_input_file,
    check_output_lock,
    release_lock,
)

# rollback_check.py uses validate_input_file for its own input validation
# with a permissive allowed_dirs default (project root), since it only reads
# git metadata files that are always under the project root.
```

---

## 4. Data Flow Details

### 4.1 Common Input Validation Pipeline

All scripts share this validation sequence:
```
Input path → Resolve → Symlink check → Exist check → Size check → Read → Parse → Schema validate
```

### 4.2 Common Output Write Pipeline

All scripts share this write sequence:
```
Build result dict → Acquire lock → Sanitize (NaN/inf) → Write to temp → fsync → Rename → Release lock
```
**Lock lifecycle**: Lock acquired immediately before write, released immediately after rename. `release_lock()` uses `try/except` so cleanup failure doesn't propagate. If the script crashes between lock and release, stale detection (300s) handles orphaned locks.

**R3: Output path confirmation**: On success, each script MUST print the resolved output path to stdout. This is critical because `baseline_results/` is gitignored and not tracked — developers running the script need to know where to find the output. Example: `"Wrote output to /path/to/project/baseline_results/spearman_judge_baseline.json"`.

### 4.3 Output JSON Schema

All scripts output to `baseline_results/<name>_baseline.json`:
```json
{
  "schema_version": "1",
  "type": "spearman_baseline|calibration_baseline|mipro_compile",
  "timestamp": "2026-04-25T00:00:00Z",
  "score": <float or "uncomputable">,
  "status": "ok|uncomputable",
  "score_description": "<human-readable score semantics>",
  "details": { /* script-specific fields */ }
}
```

**score_description field**: Consumers MUST read this to interpret `score` without needing to understand the `type` semantics. Values:
- `"spearman_baseline"` → score_description: `"rho: Spearman rank correlation, range [-1, 1]"`
- `"calibration_baseline"` → score_description: `"mean_coherence: average coherence score, range [0, 1]"`
- `"mipro_compile"` → score_description: `"duration_seconds: wall-clock compile time in seconds"`

### 4.4 Spearman Input Format

```json
{
  "baseline_composites": [0.72, 0.81, 0.65, 0.90],
  "adapter_composites": [0.78, 0.85, 0.70, 0.92]
}
```

Each composite is a pre-computed weighted score: `sum(judge_scores[dim] * weight for dim, weight in SCORING_WEIGHTS.items())`.

If input has `judge_scores` instead of pre-computed composites, the script derives them using SCORING_WEIGHTS.

**Normalization caveat**: `SCORING_WEIGHTS` sums to 0.95, not 1.0. The pre-computed `composite_score` in fixture data may differ from a recomputation by ~0.01 due to this. Always prefer the pre-computed `composite_score` when available; only recompute from `judge_scores` when the field is missing. Note: `adjusted_score` may include additional penalties (e.g., length-based) beyond the weighted sum.

### 4.5 Calibration Input Format

```json
{
  "calibration_results": [
    {
      "profile": { "temperature": 0.6, "top_k": 20, ... },
      "exam_id": "calibration_prompt_001",
      "judge_scores": { "coherence": 0.85, "style": 0.72, ... },
      "composite_score": 0.79,
      "adjusted_score": 0.81,
      "response_length": 342,
      "timestamp": "2026-03-19T00:00:00Z"
    }
  ]
}
```

### 4.6 LDI Source Format (JSON)

```json
[
  { "ldi": 0.15, "record_id": "001" },
  { "ldi": 0.08, "record_id": "002" }
]
```

### 4.7 LDI Source Format (JSONL)

```
{"ldi": 0.15, "record_id": "001"}
{"ldi": 0.08, "record_id": "002"}
```

---

## 5. Technical Decisions

### Decision 1: Shared Module vs Independent Scripts

**Decision**: Create `infrastructure/baselines/_shared.py` with 4 utility functions.

**Rationale**:
- Three functions (`validate_input_file`, `write_output_atomic`, `check_output_lock`) are identical across all scripts
- DRY reduces ~100 lines of duplicate code
- No complex logic in shared module → low coupling risk
- Same import path challenge as src/ imports → consistent approach

**Alternatives considered**:
- A: All scripts fully independent — rejected because shared logic is trivially testable and DRY
- B: Full utility package `infrastructure/baselines/utils/` — rejected because 4 functions don't warrant a sub-package

### Decision 2: No Internal Refactoring of src/audit/

**Decision**: Baseline scripts are read-only consumers of `src/audit/schema.py` and `src/audit/calibration_schema.py`.

**Rationale**:
- Requirements.md explicitly states "scripts must not modify src/audit/schema.py"
- Adding logic to src/audit/ would cross the boundary between "production audit code" and "baseline measurement"
- Baseline scripts are infrastructure tools, not part of the core audit pipeline

**Alternatives considered**:
- A: Extract common scoring logic into a new `src/baselines/` module — rejected because baseline scripts should be independent infrastructure tools
- B: Modify `src/audit/scorecard.py` to add baseline-specific functions — rejected because this couples baseline to production code

### Decision 3: Symlink Rejection Over Symlink Following

**Decision**: Reject all symlink input files with exit 1.

**Rationale**:
- Baseline scripts process ML evaluation data — supply chain attacks via symlinks to sensitive files are a real threat
- No legitimate use case for following symlinks in a measurement tool
- Explicit rejection is safer than following with validation

**Alternatives considered**:
- A: Follow symlinks with additional validation — rejected because the validation is complex and error-prone
- B: Symlink following with `--allow-symlinks` flag — rejected because the feature doesn't justify the risk

### Decision 4: 10 MB Input Size Limit

**Decision**: Reject input files exceeding 10 MB.

**Rationale**:
- Calibration results for 27,000 iterations with full JSON would be ~50-100 MB
- However, 10 MB is a reasonable default for "reference datasets"
- Users with larger datasets can preprocess/aggregate before passing to baseline scripts
- DoS protection: reading unlimited files could exhaust memory

**Alternatives considered**:
- A: No limit — rejected because of memory exhaustion risk
- B: 100 MB limit — rejected because typical calibration fixtures are small (< 5 MB), and the limit should be conservative

### Decision 5: Atomic Writes with fsync

**Decision**: Write to temp file → rename → fsync → unlock.

**Rationale**:
- Atomic writes prevent partial/corrupt output on interrupt
- fsync ensures data is flushed to disk
- rename is atomic on POSIX systems
- Lock file prevents concurrent write collisions

**Alternatives considered**:
- A: Direct write — rejected because power interruption could corrupt output
- B: Write + close — rejected because close doesn't guarantee disk flush

### Decision 6: File Locking for Concurrent Safety

**Decision**: O_CREAT|O_EXCL file locking with 30s wait timeout.

**Rationale**:
- Multiple baseline scripts might run in parallel (e.g., in CI)
- File-level locking (O_EXCL) is more reliable than PID-based locking
- 30s timeout prevents indefinite blocking
- Lock file is removed immediately after write completes

**Alternatives considered**:
- A: flock() — rejected because O_EXCL is simpler and universally available
- B: PID-based lock files — rejected because PID reuse could cause false locks

### Decision 7: Rollback Isolation via Worktree

**Decision**: Prefer git worktree over clone for isolation.

**Rationale**:
- Worktrees are faster (share .git directory)
- Lightweight (~seconds vs ~minutes for clone)
- More reliable in CI environments
- Clone fallback if worktree is unavailable

**Alternatives considered**:
- A: Always clone — rejected because cloning is slow and disk-intensive
- B: Use `--isolate` flag in git — rejected because it doesn't exist as a single command

### Decision 8: MIPRO Estimated Mode Placeholder

**Decision**: Default avg_latency = 0.5s with explicit WARNING and "estimated" flag.

**Rationale**:
- No grid execution happens — we can't measure actual latency
- 0.5s is a reasonable default placeholder (500ms per profile compile is conservative)
- WARNING to stderr makes the uncertainty visible
- "estimated: true" in output JSON marks it as non-measured
- --avg-latency flag allows override with measured values

**Alternatives considered**:
- A: Fail without report — rejected because estimated mode provides useful reference
- B: Auto-detect latency — rejected because auto-detection is impossible without execution

### Decision 9: Mixed-Stage Dataset Handling

**Decision**: If both Stage 5 and Stage 6 entries present, treat as Stage 6 with warning.

**Rationale**:
- Stage 6 is the more feature-complete stage (includes coherence)
- Treating as Stage 6 enables coherence extraction where available
- Logging a warning alerts the user to data inconsistency
- Entries without coherence data get null for that field

**Alternatives considered**:
- A: Reject mixed-stage data — rejected because this would discard valid data
- B: Process separately per stage — rejected because mean_coherence would be ambiguous

---

## 5.5 Logging Strategy (R4)

All scripts use Python's `logging` module with this configuration:

```python
logging.basicConfig(
    level=logging.WARNING,        # Default: WARNING and above
    format="%(levelname)s: %(message)s",  # Simple format, no timestamp/module
    stream=sys.stderr,            # Logs go to stderr, separate from stdout output
)
log = logging.getLogger(__name__)
```

- `--verbose` flag: sets level to `logging.INFO`
- `--quiet` flag: sets level to `logging.ERROR`
- `log.warning()` is used for non-fatal issues (e.g., mixed-stage data, estimated mode)
- `BaselineError` exceptions are caught in `main()` and printed to stderr (not via logging)
- All structured output (JSON) goes to stdout (or a file via `--output`)

## 5.6 Signal Handling for Baseline Scripts (R4)

While `rollback_check.py` has explicit SIGINT/SIGTERM handlers, the three baseline scripts rely on:
- `main()`'s `except Exception` fallback for unhandled errors
- `KeyboardInterrupt` (Ctrl-C) will propagate as a traceback — this is acceptable for interactive use
- For CI/automation, scripts should be run with a wrapper that adds timeout (e.g., `timeout 300 python script.py`)

This is documented so implementers know that signal handling for baseline scripts is intentionally minimal.

## 6. Error Handling Strategy

### 6.1 Common Error Pattern

All scripts follow this error handling hierarchy:

```
1. Argument validation → argparse handles most cases
2. File existence → "Cannot read {path}: No such file"
3. File type → "Input file is a symlink: {path}"
4. File size → "Input file exceeds 10 MB limit: {path} ({size} bytes)"
5. File empty → "Input file is empty: {path}"
6. JSON parse → "Cannot parse JSON: {path}: {error}"
7. Schema → "Expected top-level keys: {expected}, got {actual}"
8. Array length → "Array length mismatch: baseline has N, adapter has M"
9. Computation → "Scipy computation failed: {error}"
10. Write → "Cannot write output: {path}: {error}"
```

### 6.2 Graceful Degradation

| Component | Failure | Behavior |
|-----------|---------|----------|
| LDI source | Missing/unparseable | mean_ldi=null, ldi_pass_rate=null, exit 0 |
| Coherence data | Stage 5 data | mean_coherence=null, exit 0 |
| CalibrationReport | Malformed/missing | Fall back to estimated mode |
| execution_time_seconds | null in report | Fall back to estimated mode |
| Spike in calibration | Coherence out of [0,1] | Log warning, include in mean |

### 6.3 Signal Handling (rollback_check.py only)

```python
import signal
import atexit

_cleanup_done = False

def _cleanup():
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    try:
        cleanup_isolated_env(worktree_path)
    except Exception as e:
        print(f"Warning: cleanup failed: {e}", file=sys.stderr)

signal.signal(signal.SIGINT, lambda s, f: _cleanup() or sys.exit(130))
signal.signal(signal.SIGTERM, lambda s, f: _cleanup() or sys.exit(143))
atexit.register(_cleanup)
```

---

## 7. Concurrency Model

### 7.1 File-Level Locking

**Mechanism**: `os.open(lock_path, O_CREAT | O_EXCL)`

**Flow**:
1. Before any output write, script checks for `<output>.lock` file
2. If lock exists: wait 0.5s, recheck, up to 30s total
3. After 30s: exit 1 with "Another process is writing to {path}"
4. If no lock: create exclusive lock, proceed with write
5. After write + rename: remove lock file

**Lock file naming**: `<output_basename>.lock` (e.g., `spearman_judge_baseline.json.lock`)

### 7.2 Concurrent Script Scenarios

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Spearman + Calibration parallel | Same output dir | Different output files, lock per file |
| Spearman re-run during Calibration | Overlap in output dir | Different output files |
| Calibration re-run (idempotent) | Same output file | Lock protects against partial overwrite |
| All 4 scripts parallel | All writing to baseline_results/ | Lock per output file |

### 7.3 Lock File Cleanup

Lock files are removed by `release_lock()` immediately after successful write. If the script crashes:
- **Stale lock detection**: `_is_lock_stale()` checks if lock file mtime > 300s old → auto-removes and retries (TOCTOU-safe)
- **Young stale lock** (< 300s): waiting script exits 1 after 30s timeout
- **Manual cleanup**: `rm baseline_results/*.lock` if lock is truly orphaned

---

## 8. Path Resolution

### 8.1 Project Root Resolution

All scripts that import from `src/` resolve the project root:

```python
from pathlib import Path
import sys

# Resolve project root (parent of infrastructure/)
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from src.audit.schema import SCORING_WEIGHTS
from src.audit.calibration_schema import CALIBRATION_GRID
```

**Note**: `infrastructure/` is 3 levels deep from script:
- `infrastructure/baselines/<script>` → `parent` = `baselines/`
- `infrastructure/baselines/<script>` → `parent.parent` = `infrastructure/`
- `infrastructure/baselines/<script>` → `parent.parent.parent` = project root
```
infrastructure/baselines/<script>
  → parent: baselines/
  → parent.parent: infrastructure/
  → parent.parent.parent: project root
```

### 8.2 Path Argument Resolution

All path arguments are resolved consistently:
- **Absolute paths**: used as-is
- **Relative paths**: resolved from current working directory (CWD)
- **~ expansion**: `Path(path).expanduser()` applied via `Path.resolve()`
- **Output paths**: resolved relative to CWD

### 8.3 Pyright Configuration

The project uses `pyrightconfig.json` (not pyproject.toml) for pyright configuration. The existing `reportMissingImports: false` setting already handles the sys.path import issue — no additional exclusion is needed. Scripts in `infrastructure/baselines/` will type-check normally for their own code; only the src/ imports will be silently unresolved.

---

## 9. Implementation Phases

### Phase 1: Dependency & Structure (US-1, US-6)

**Files to create**:
- `infrastructure/__init__.py` — if not exists (verify)
- `infrastructure/baselines/__init__.py` — NEW
- `infrastructure/baselines/_shared.py` — NEW
- `baseline_results/` — NEW directory
- `baseline_results/.gitkeep` — optional (directory is gitignored)

**Files to modify**:
- `requirements.txt` — add `scipy==1.17.1` (numpy already present)
- `pyproject.toml` — add `scipy==1.17.1` to dependencies; add `infrastructure/baselines/` to pyright exclude
- `.gitignore` — add `baseline_results/`
- `infrastructure/dependency_check.py` — add scipy to PACKAGE_IMPORT_MAP

**Gating prerequisite**: Verify `scipy==1.17.1` installs on Python 3.14.3 before proceeding.

### Phase 2: Spearman Baseline (US-2, FR-002)

**Files to create**:
- `infrastructure/baselines/measure_spearman_baseline.py`

**Dependencies**: Phase 1 complete, scipy installed.

**Key implementation steps**:
1. Rich CLI scaffold (main, _die, logging, argparse)
2. Shared imports from _shared.py
3. Input validation (symlink, size, empty, JSON parse, schema)
4. NaN filtering (preserve pairing)
5. Edge case handling (n=0,1,2, constant)
6. scipy.stats.spearmanr call
7. Output JSON construction and atomic write

### Phase 3: Calibration Baseline (US-3, FR-003)

**Files to create**:
- `infrastructure/baselines/run_calibration_baseline.py`

**Dependencies**: Phase 1 complete.

**Key implementation steps**:
1. Rich CLI scaffold
2. Stage detection logic
3. Coherence extraction (Stage 5 vs 6)
4. LDI sourcing from --ldi-source
5. Mean coherence computation
6. LDI pass rate computation
7. Output JSON construction and atomic write

### Phase 4: MIPRO Compile Baseline (US-4, FR-004)

**Files to create**:
- `infrastructure/baselines/measure_mipro_compile_baseline.py`

**Dependencies**: Phase 1 complete.

**Key implementation steps**:
1. Rich CLI scaffold
2. CALIBRATION_GRID import
3. profiles_tested calculation (product of dimensions)
4. CalibrationReport parsing (measured mode)
5. Estimated mode fallback
6. Output JSON construction and atomic write

### Phase 5: Rollback Verification (US-5, FR-005)

**Files to create**:
- `infrastructure/rollback_check.py`

**Dependencies**: Phase 1 complete.

**Key implementation steps**:
1. Rich CLI scaffold
2. Isolated environment creation (worktree → clone fallback)
3. Test commit creation
4. Git revert HEAD timing
5. Clean status verification
6. Cleanup with signal handlers
7. Output results

### Phase 6: Convention Compliance (US-6, FR-006)

**Actions**:
1. Run `ruff format` on all new scripts
2. Run `pyright` (excluding infrastructure/baselines/)
3. Verify license headers (scripts/check_headers.py)
4. Test --dry-run on all scripts
5. Test --no-overwrite behavior

---

## 10. Failure Modes and Mitigations

| Failure | Likelihood | Impact | Mitigation |
|---------|-----------|--------|------------|
| scipy install fails | Low | Blocker | Gating prerequisite in US-1, escalate immediately |
| Calibration fixture empty | Medium | null result | Graceful null output, exit 0 |
| No CalibrationReport | High | Estimated mode | WARNING to stderr, "estimated" flag |
| LDI data unavailable | Medium | null LDI | Graceful null output, exit 0 |
| Mixed-stage data | Low | Coherence partial | Treat as Stage 6, log warning |
| Concurrent script execution | Medium | File corruption | O_EXCL locking, 30s timeout |
| Large input file | Low | Memory exhaustion | 10 MB limit enforced |
| Symlink attack | Low | Data leak | Symlink rejection enforced |
| Rollback worktree fails | Low | Fallback to clone | Automatic fallback |
| SIGINT during revert | Low | Orphaned worktree | Signal handler, atexit cleanup |
| Disk full during write | Low | Corrupt output | Atomic write, lock prevents partial |
| Floating-point discrepancy | Medium | Score mismatch | Prefer pre-computed, fallback to SCORING_WEIGHTS |

---

## 11. Output File Format

### 11.1 Spearman Output

```json
{
  "schema_version": "1",
  "type": "spearman_baseline",
  "timestamp": "2026-04-25T00:00:00Z",
  "score": 0.85,
  "status": "ok",
  "score_description": "rho: Spearman rank correlation, range [-1, 1]",
  "details": {
    "p_value": 0.001,
    "n": 4,
    "method": "exact",
    "reason": null
  }
}
```

**Timestamp note**: Use `datetime.now(timezone.utc)` (NOT `datetime.now()`) to ensure UTC output matching the `Z` suffix. R4: this prevents timezone-dependent output variation across machines.

**Status field**: `status: "ok"` is present in all output examples. When computation fails due to edge cases, `status` is set to the specific edge case code and `score` is `null` (F12: null for uncomputable float values). `p_value` and other numeric fields are also `null`. The `status` and `reason` fields convey the edge case details.

Edge case example (F12: null for uncomputable floats, R4: score_description + status present):
```json
{
  "schema_version": "1",
  "type": "spearman_baseline",
  "timestamp": "2026-04-25T00:00:00Z",
  "score": null,
  "score_description": "rho: Spearman rank correlation, range [-1, 1]",
  "status": "no_valid_data",
  "details": {
    "p_value": null,
    "n": 0,
    "method": "exact",
    "reason": "All data points are NaN or non-numeric"
  }
}
```

### 11.2 Calibration Output

```json
{
  "schema_version": "1",
  "type": "calibration_baseline",
  "timestamp": "2026-04-25T00:00:00Z",
  "score": 0.78,
  "status": "ok",
  "score_description": "mean_coherence: average coherence score, range [0, 1]",
  "details": {
    "mean_coherence": 0.78,
    "mean_ldi": 0.12,
    "ldi_pass_rate": 0.85,
    "grid_config": {
      "temperature": [0.3, 0.5, 0.6, 0.7, 0.9, 1.1],
      "top_k": [5, 10, 20, 40, 60, 80],
      "min_p": [0.0, 0.02, 0.05, 0.1, 0.15],
      "repetition_penalty": [1.0, 1.05, 1.1, 1.15, 1.2],
      "presence_penalty": [0.0, 0.5, 1.0, 1.5, 2.0]
    }
  }
}
```

### 11.3 MIPRO Output

```json
{
  "schema_version": "1",
  "type": "mipro_compile",
  "timestamp": "2026-04-25T00:00:00Z",
  "score": 13500.0,
  "status": "ok",
  "score_description": "duration_seconds: wall-clock compile time in seconds",
  "details": {
    "grid_config": { ... },
    "total_iterations": 27000,
    "profiles_tested": 4500,
    "source": "estimated",
    "avg_latency_seconds": 0.5,
    "duration_seconds": 13500.0,
    "estimated": true,
    "profiles_tested_computed_from_grid": true
  }
}
```

---

## 12. Constraints and Assumptions

### Constraints
- Python >= 3.12 (pyproject.toml)
- Apache-2.0 license header on all scripts
- Rich CLI pattern (typed main, _die, logging, SystemExit)
- Atomic writes for all output files
- File-level locking for concurrent safety
- Symlink rejection for all input files
- 10 MB input size limit

### Assumptions
- Fixture files exist at expected paths
- CALIBRATION_GRID in src/audit/calibration_schema.py is stable
- SCORING_WEIGHTS in src/audit/schema.py is stable
- git worktree is available (fall back to clone)
- No concurrent script execution in manual mode
- Python 3.14.3 environment has scipy==1.17.1 wheels

### CI Constraints (documented, not fixed in code)
- **Shallow clones**: `git worktree` fails on shallow clones (`--depth=1`). CI systems using shallow clones must fall back to `git clone`, which is slower. The rollback_check.py script accepts this as a known limitation.
- **Lock files in CI**: `*.lock` files must be added to `.gitignore`. In CI, lock file contention between parallel jobs is expected — the 30s timeout and 300s stale threshold are tuned for manual use. In CI, consider using per-job output directories to avoid lock contention entirely.
- **CWD for rollback_check.py**: `rollback_check.py` must be invoked from the project root (or with `sys.path` set correctly). Running from `infrastructure/` directly will break imports. Other baseline scripts in `baselines/` have the same constraint.
- **sys.path fragility**: All scripts use `sys.path.insert(0, ...)` for src/ imports. This is the same pattern used by existing code in the project but breaks test isolation if multiple scripts are imported in the same test process.

### Risks
- **scipy installation**: Python 3.14.3 may not have scipy wheels → escalate immediately
- **Floating-point precision**: SCORING_WEIGHTS sum to 0.95, not 1.0 → documented, scripts use pre-computed values when available
- **Stage detection fragility**: Depends on specific key names in judge_scores → documented in requirements
- **MIPRO estimate accuracy**: 0.5s placeholder may be far from actual → explicitly flagged as "estimated"
- **Rollback timing**: 60s threshold may be unrealistic for large repos → measurable, configurable

---

## 13. Testing Strategy (Epic 1 Scope)

This spec does NOT include tests (explicitly out of scope). The following test plan is for Epic 1 implementers:

### Unit Tests (infrastructure/baselines/_shared.py)
- `validate_input_file()`: symlinks, empty files, size limits, missing files, directories
- `write_output_atomic()`: writes correct JSON, creates parent dirs, fsyncs, atomic rename
- `check_output_lock()`: acquires lock, waits, fails after timeout

### Unit Tests (per script)
- Input validation edge cases (all FR edge cases)
- Spearman: n=0/1/2, constant input, NaN filtering, score clamping
- Calibration: stage detection, mixed-stage, coherence extraction, LDI parsing
- MIPRO: measured mode, estimated mode, grid config parsing

### Integration Tests
- All scripts against real fixture files
- Concurrent execution of multiple scripts
- Atomic write during interrupt (signal during fsync)
- Rollback worktree cleanup on normal and abnormal exit

### Verification Contract Tests
- Output JSON schema validation
- Score range validation
- Idempotency: same inputs → same output (except timestamp)
