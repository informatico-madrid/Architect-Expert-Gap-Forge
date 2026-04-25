# Architect-Expert-Gap-Forge: Baseline Measurement Shared Utilities
#
# Copyright (c) 2026 — Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared utilities for baseline measurement scripts.

All helper functions raise BaselineError instead of calling sys.exit()
so they can be unit-tested without subprocess mocking. Each script's
main() catches BaselineError, prints to stderr, and calls sys.exit(1).
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────
MAX_INPUT_SIZE = 10_000_000  # 10 MB
DEFAULT_OUTPUT_DIR = "baseline_results"
LOCK_TIMEOUT_SECONDS = 30
LOCK_POLL_INTERVAL = 0.5
LOCK_STALE_SECONDS = 300  # 5 min — stale lock threshold
TEMP_FILE_MODE = 0o600
LOCK_FILE_MODE = 0o600


# ── Exceptions ─────────────────────────────────────────────────────────
class BaselineError(Exception):
    """Raised by helpers on fatal errors; caught in each script's main()."""


# ── Input validation ───────────────────────────────────────────────────
def validate_input_file(
    path: str | Path, allowed_dirs: tuple[str, ...] | None = None
) -> None:
    """Validate input file is a regular file (not symlink, not empty, under size limit, in allowed dir).

    Args:
        path: Path to validate.
        allowed_dirs: Tuple of allowed parent directories. If None, defaults to
            the project root (parent of infrastructure/). Each script may pass
            a more restrictive set.

    Raises:
        BaselineError: If the file fails any validation check.
    """
    p = Path(path)
    if p.is_symlink():
        raise BaselineError(
            f"Input file is a symlink: {p}. Refusing to follow symlinks for security."
        )
    p = p.resolve()
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
        allowed_dirs = (str(Path(__file__).resolve().parent.parent.parent),)
    allowed_resolved = [Path(d).resolve() for d in allowed_dirs]
    for allowed in allowed_resolved:
        try:
            p.relative_to(allowed)  # Raises ValueError if not relative
        except ValueError:
            raise BaselineError(f"Input path outside allowed directories: {p}")


# ── Atomic output ──────────────────────────────────────────────────────
def write_output_atomic(path: str | Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: temp file (mode 0o600) -> rename -> fsync.

    On failure, cleans up temp file to prevent accumulation of artifacts.

    R3: Caller should validate that the output directory is not a symlink
    before calling this function. Each script validates the output parent path
    (checks for symlinks, checks isdir) before calling this function.
    """
    p = Path(path).resolve()  # R2: resolve to handle symlinked output dirs
    os.makedirs(
        p.parent, exist_ok=True
    )  # R2 CRITICAL: no follow_symlinks -- output parent must be validated by caller
    tmp_path = p.with_suffix(p.suffix + ".tmp")
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, TEMP_FILE_MODE)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)  # F7: support non-ASCII
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            os.close(fd)
            raise
        os.rename(str(tmp_path), str(p))
    except OSError as e:
        # R2: EXDEV -- cross-device link (NFS, bind mount, tmpfs)
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
    os.makedirs(
        p.parent, exist_ok=True
    )  # F9: ensure dir exists before lock acquisition
    lock_path = p.with_suffix(p.suffix + ".lock")
    waited = 0.0
    while True:
        try:
            fd = os.open(
                str(lock_path), os.O_CREAT | os.O_EXCL, LOCK_FILE_MODE
            )  # R3: explicit mode, not relying on umask
            os.close(fd)
            return lock_path
        except FileExistsError:
            # Check for stale lock (no writer holding the fd)
            if _is_lock_stale(lock_path):
                # R3: symlink check before remove -- prevent deleting through symlink
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
    """Ensure float values are JSON-serializable. NaN/inf -> None (null).

    Uses isinstance(v, (int, float)) which catches numpy floats (numpy.float64
    is a subclass of Python's float) AND Python built-in floats. Also catches
    numpy integers that may be passed through via Any-typed dict values.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            if math.isnan(value) or math.isinf(value):
                return None
        except (TypeError, ValueError):
            pass
    return value


def _is_float_like(v: Any) -> bool:
    """Check if value is a float-like type (including numpy float64, numpy.float32).

    Uses math.isnan()/math.isinf() which work on any float-like type, unlike
    isinstance(v, float) which returns False for numpy float types.
    Explicitly excludes bool and int types (including numpy integer types).
    """
    if isinstance(v, (bool, int)):
        return False
    try:
        math.isnan(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    try:
        math.isinf(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def _sanitize_output_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize dict and lists: replace NaN/inf floats with None (null).

    R3: Also handles list values -- if any output dict contains a list of floats,
    NaN values inside lists would otherwise pass through unsanitized and produce
    invalid JSON (bare NaN literal, not null).

    Uses math.isnan()/math.isinf() for float detection to catch numpy float types
    (numpy.float64, numpy.float32) that isinstance(v, float) misses.

    This function is MANDATORY: every script must call it before json.dump().
    Python's json.dumps() has allow_nan=True by default, producing invalid
    JSON literals like NaN or Inf instead of null.

    Args:
        d: Dictionary to sanitize.

    Returns:
        A new dictionary with all NaN/inf float values replaced by None.
    """
    result: dict[str, Any] = {}
    for k, v in d.items():
        if _is_float_like(v):
            try:
                if math.isnan(v) or math.isinf(v):  # type: ignore[arg-type]
                    result[k] = None
                else:
                    result[k] = v
            except (TypeError, ValueError):
                result[k] = v
        elif isinstance(v, dict):
            result[k] = _sanitize_output_dict(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_list_item(item) for item in v]
        else:
            result[k] = v
    return result


def _sanitize_list_item(v: Any) -> Any:
    """Sanitize a single list item: recurse if dict/list, sanitize float.

    Uses _is_float_like() to catch numpy float types (numpy.float64, numpy.float32).
    """
    if _is_float_like(v):
        try:
            if math.isnan(v) or math.isinf(v):  # type: ignore[arg-type]
                return None
        except (TypeError, ValueError):
            pass
        return v
    elif isinstance(v, dict):
        return _sanitize_output_dict(v)
    elif isinstance(v, list):
        return [_sanitize_list_item(item) for item in v]
    return v
