#!/usr/bin/env bash
set -euo pipefail
# Configure git to use the repository-tracked .githooks directory as hooks path
git config core.hooksPath .githooks
echo "Git hooks path set to .githooks. Ensure .githooks/pre-commit is executable:"
echo "  chmod +x .githooks/pre-commit"
