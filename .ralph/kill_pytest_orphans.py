#!/usr/bin/env python3
"""
Gracefully terminate pytest processes using psutil.

Usage:
  .ralph/kill_pytest_orphans.py --timeout 5

Behavior:
  - Finds processes with 'pytest' in name or cmdline
  - Calls terminate(), waits up to --timeout seconds
  - If still alive, calls kill()
  - Exits 0 on success or when no processes found, non-zero on import error
"""
from __future__ import annotations

import argparse
import sys
from typing import List


def find_pytest_procs() -> List:
    try:
        import psutil
    except ImportError:
        raise

    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (p.info.get('name') or '').lower()
            cmd = ' '.join(p.info.get('cmdline') or []).lower()
            if 'pytest' in name or 'pytest' in cmd:
                procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


def terminate_and_kill(procs: List, timeout: float = 5.0) -> int:
    import psutil

    if not procs:
        print("0")
        return 0

    # Try graceful terminate
    for p in procs:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    gone, alive = psutil.wait_procs(procs, timeout=timeout)

    # Force kill remaining
    if alive:
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    print(str(len(procs)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=5.0, help='Seconds to wait after terminate()')
    parser.add_argument('--dry-run', action='store_true', help='List matching PIDs without killing')
    args = parser.parse_args()

    try:
        import psutil  # type: ignore
    except Exception:
        # Fallback to pkill if psutil is not available in the environment.
        import subprocess
        try:
            subprocess.run(["pkill", "-TERM", "-f", "pytest"], check=False)
            # give processes a moment to exit
            import time
            time.sleep(2)
            subprocess.run(["pkill", "-KILL", "-f", "pytest"], check=False)
            return 0
        except Exception:
            print('psutil not installed and pkill fallback failed', file=sys.stderr)
            return 2

    procs = find_pytest_procs()
    if not procs:
        # no matches
        return 0

    if args.dry_run:
        for p in procs:
            try:
                print(f"{p.pid} {' '.join(p.cmdline() or [])}")
            except Exception:
                print(f"{p.pid}")
        return 0

    for p in procs:
        try:
            print(f"Found pytest PID {p.pid}: {' '.join(p.cmdline() or [])}", file=sys.stderr)
        except Exception:
            print(f"Found pytest PID {p.pid}", file=sys.stderr)

    return terminate_and_kill(procs, timeout=args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
