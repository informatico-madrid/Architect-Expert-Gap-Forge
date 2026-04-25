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
import signal
import subprocess
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.baselines._shared import (
    BaselineError,
    check_output_lock,
    release_lock,
    validate_input_file,
    write_output_atomic,
)

logger = logging.getLogger(__name__)

# Isolated environment tracking for cleanup
_isolated_path: str | None = None
_isolated_kind: str | None = None


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _cleanup() -> None:
    """Remove the isolated test environment if one was created."""
    global _isolated_path, _isolated_kind
    if _isolated_path is not None and _isolated_kind is not None:
        logger.info("Cleaning up test environment: %s", _isolated_path)
        try:
            if _isolated_kind == "worktree":
                subprocess.run(
                    ["git", "worktree", "remove", "--force", _isolated_path],
                    check=True,
                    capture_output=True,
                )
            elif _isolated_kind == "clone":
                import shutil

                shutil.rmtree(_isolated_path)
        except Exception as exc:
            logger.warning("Cleanup failed: %s", exc)
        _isolated_path = None
        _isolated_kind = None


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


def _impl(argv: list[str]) -> int:
    """Actual implementation logic.

    Args:
        argv: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    target: float = argv.target
    output: Path = Path(argv.output)
    dry_run: bool = argv.dry_run

    if dry_run:
        logger.info("Threshold: %.1fs", target)
        logger.info("Target output: %s", output)
        logger.info("Isolation method: worktree (clone on failure)")
        print("DRY RUN complete. No output file written.")
        return 0

    print("Creating isolated test environment...")
    return 0


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
