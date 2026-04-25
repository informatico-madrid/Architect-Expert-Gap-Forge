# Architect-Expert-Gap-Forge: Rollback Check — Git revert timing measurement
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

"""Measure git revert timing in an isolated test environment.

Creates a temporary worktree (or clone), makes a test commit,
measures the time to revert it, and writes structured output.
"""

from __future__ import annotations

import argparse
import atexit
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.baselines._shared import (
    BaselineError,
    _sanitize_output_dict,
    check_output_lock,
    release_lock,
    validate_input_file,
    write_output_atomic,
)

logger = logging.getLogger(__name__)

# Isolated environment tracking for cleanup
_isolated_path: str | None = None
_isolated_kind: str | None = None
_isolated_parent: str | None = None


def create_isolated_env() -> tuple[str, str]:
    """Create an isolated test environment for rollback measurement.

    Tries git worktree first (faster, shares .git). Falls back to full clone.

    Sets _isolated_path/_isolated_kind BEFORE any git command so signal
    handlers can clean up even if SIGINT/SIGTERM arrives during creation.

    Returns:
        Tuple of (path, kind) where kind is "worktree" or "clone".
    """
    global _isolated_path, _isolated_kind, _isolated_parent
    worktree_parent = tempfile.mkdtemp(
        prefix="baseline-rollback-worktree-"
    )
    _isolated_parent = worktree_parent
    name = f"rollback-check-{os.getpid()}"
    worktree_path = os.path.join(worktree_parent, name)

    # Set cleanup state BEFORE any git command so signal handlers can
    # remove the worktree even if interrupted during create_isolated_env.
    _isolated_path = worktree_path
    _isolated_kind = "worktree"

    try:
        subprocess.run(
            ["git", "worktree", "add", worktree_path, "HEAD"],
            check=True,
            capture_output=True,
            timeout=30,
        )
        logger.info("Created worktree: %s", worktree_path)
        return (worktree_path, "worktree")
    except Exception:
        logger.info("Worktree failed, falling back to clone...")

    # Update state for clone fallback
    _isolated_path = worktree_path
    _isolated_kind = "clone"
    os.makedirs(worktree_path, exist_ok=True)
    subprocess.run(
        ["git", "clone", project_root, worktree_path],
        check=True,
        capture_output=True,
        timeout=120,
    )
    logger.info("Created clone: %s", worktree_path)
    return (worktree_path, "clone")


def cleanup_isolated_env(path: str, kind: str) -> None:
    """Remove an isolated test environment.

    Args:
        path: Path to the isolated environment.
        kind: "worktree" or "clone".
    """
    logger.info("Cleaning up test environment: %s", path)
    try:
        if kind == "worktree":
            # Double --force: first --force allows removing checked-out branches,
            # second overrides locked worktrees (reason: "initializing" etc.)
            subprocess.run(
                ["git", "worktree", "remove", "--force", "--force", path],
                capture_output=True,
            )
        elif kind == "clone":
            shutil.rmtree(path, ignore_errors=True)
    except Exception as exc:
        logger.warning("Cleanup failed: %s", exc)


def _write_error_output(
    output: Path, error_kind: str, error_detail: str, isolation_kind: str | None
) -> None:
    """Write a partial error output JSON when an operation fails.

    Ensures diagnostic information is available even when the main
    operation (commit or revert) fails.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dict = {
        "schema_version": "1",
        "type": "rollback_check",
        "timestamp": timestamp,
        "score": None,
        "status": error_kind,
        "score_description": "duration_seconds: wall-clock git revert time in seconds",
        "details": {
            "duration_seconds": None,
            "threshold_seconds": None,
            "within_target": None,
            "clean_status": None,
            "isolation_method": isolation_kind,
            "error": error_kind,
            "error_detail": error_detail,
        },
    }
    lock_path = check_output_lock(output)
    try:
        sanitized = _sanitize_output_dict(output_dict)
        write_output_atomic(output, sanitized)
    finally:
        release_lock(lock_path)
    logger.info("Wrote error output to %s", output)


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _cleanup() -> None:
    """Remove the isolated test environment if one was created."""
    global _isolated_path, _isolated_kind, _isolated_parent
    if _isolated_path is not None and _isolated_kind is not None:
        cleanup_isolated_env(_isolated_path, _isolated_kind)
        _isolated_path = None
        _isolated_kind = None
    # Remove the tempfile parent directory (worktree_parent)
    if _isolated_parent is not None:
        shutil.rmtree(_isolated_parent, ignore_errors=True)
        _isolated_parent = None


def _register_cleanup() -> None:
    """Register atexit and signal handlers for cleanup."""
    atexit.register(_cleanup)

    def _handle_sigint(signum: int, frame: object) -> None:
        _cleanup()
        sys.exit(130)

    def _handle_sigterm(signum: int, frame: object) -> None:
        _cleanup()
        sys.exit(143)

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigterm)


def _impl(argv: argparse.Namespace) -> int:
    """Actual implementation logic.

    Args:
        argv: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    target: float = argv.target
    output: Path = Path(argv.output)
    dry_run: bool = argv.dry_run

    global _isolated_path, _isolated_kind

    if argv.no_overwrite and output.exists():
        print(f"Output file already exists: {output}. Use --no-overwrite to skip.", file=sys.stderr)
        return 1

    if dry_run:
        logger.info("Threshold: %.1fs", target)
        logger.info("Target output: %s", output)
        logger.info("Isolation method: worktree (clone on failure)")
        print("DRY RUN complete. No output file written.")
        return 0

    print("Creating isolated test environment...")

    try:
        # 1. Create isolated environment (sets _isolated_path/_isolated_kind internally)
        isolated_path, isolated_kind = create_isolated_env()

        # 2. cd into isolated environment
        os.chdir(isolated_path)

        # Create a branch (worktrees have detached HEAD, git revert needs one)
        subprocess.run(
            ["git", "branch", "-f", "baseline-test-branch", "HEAD"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "checkout", "baseline-test-branch"],
            capture_output=True,
            check=True,
            timeout=10,
        )

        # 3. Create test commit with a real file change
        # Empty commits fail to revert in sparse-checkout environments
        test_file = os.path.join(isolated_path, ".baseline-test-marker")
        with open(test_file, "w") as f:
            f.write("baseline-test-marker\n")
        subprocess.run(
            ["git", "add", test_file],
            capture_output=True,
            check=True,
            timeout=10,
        )
        result = subprocess.run(
            ["git", "commit", "-m", "baseline-test-commit"],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            err = result.stderr.decode().strip()
            print(f"Error creating test commit: {err}", file=sys.stderr)
            _write_error_output(output, "commit_failed", err, isolated_kind)
            return 1

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        test_commit = result.stdout.decode().strip()
        print(f"Test commit created: {test_commit}")

        # 4. Time the revert
        start = time.perf_counter()
        result = subprocess.run(
            ["git", "revert", "HEAD", "--no-edit"],
            capture_output=True,
            timeout=60.0,
        )
        duration = time.perf_counter() - start

        if result.returncode != 0:
            err = result.stderr.decode().strip()
            print(f"Revert failed: {err}", file=sys.stderr)
            _write_error_output(output, "revert_failed", err, isolated_kind)
            return 1

        # 5. Determine status based on duration
        timing_ok = duration < target
        if timing_ok:
            status = "ok"
            print(f"git revert HEAD completed in {duration:.2f}s ({target:.0f}s)")
        else:
            status = "exceeded_threshold"
            print(f"git revert HEAD exceeded threshold: {duration:.2f}s > {target:.0f}s")

        # 6. Verify git status is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        clean_status = result.stdout.decode().strip() == ""

        if not clean_status:
            status = "dirty_working_tree"
            print("Warning: git status is not clean after revert", file=sys.stderr)

        # 6. Build and write output JSON
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rounded_duration = round(duration, 4)
        output_dict = {
            "schema_version": "1",
            "type": "rollback_check",
            "timestamp": timestamp,
            "score": rounded_duration,
            "status": status,
            "score_description": "duration_seconds: wall-clock git revert time in seconds",
            "details": {
                "duration_seconds": rounded_duration,
                "threshold_seconds": target,
                "within_target": status == "ok",
                "clean_status": clean_status,
                "isolation_method": isolated_kind,
            },
        }

        # 7. Atomic write with lock
        lock_path = check_output_lock(output)
        try:
            sanitized = _sanitize_output_dict(output_dict)
            write_output_atomic(output, sanitized)
        finally:
            release_lock(lock_path)

        print(f"Wrote output to {output}")
        print("Isolated environment cleaned up.")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        # Ensure cleanup runs even on unexpected errors
        if _isolated_path is not None and _isolated_kind is not None:
            cleanup_isolated_env(_isolated_path, _isolated_kind)
            _isolated_path = None
            _isolated_kind = None


def main(argv: list[str] | None = None) -> int:
    """Entry point for the rollback check CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(
        description="Measure git revert timing in an isolated test environment."
    )
    parser.add_argument(
        "--target",
        type=float,
        default=60.0,
        help="Max revert duration in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--output",
        default="baseline_results/rollback_check.json",
        help="Output JSON path (default: baseline_results/rollback_check.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print diagnostics without creating isolated environment",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Exit 1 if output file already exists",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set logging level to INFO",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Set logging level to ERROR",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    _register_cleanup()

    return _impl(args)


if __name__ == "__main__":
    raise SystemExit(main())
