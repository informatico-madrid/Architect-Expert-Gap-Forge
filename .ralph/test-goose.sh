#!/usr/bin/env bash
#
# Test script para verificar el formato de respuesta de goose
# Este script NO ejecuta el ralph-loop, solo prueba goose directamente
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# vLLM configuration
RALPH_VLLM_URL="${RALPH_VLLM_URL:-http://localhost:4000}"
RALPH_VLLM_MODEL="${RALPH_VLLM_MODEL:-qwen3-30b-a3b-thinking-fp8}"
# Use CUSTOM_VLLM_LOCAL_API_KEY if set, otherwise default to EMPTY
RALPH_VLLM_API_KEY="${RALPH_VLLM_API_KEY:-${CUSTOM_VLLM_LOCAL_API_KEY:-EMPTY}}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# Build the work prompt (simplified version from ralph-loop.sh)
# ============================================================================
build_test_prompt() {
    cat <<'PROMPT_EOF'
# Ralph Loop — Work Phase (Test)

You are the SpecKit Implementation Agent running inside a Ralph Loop.
You are 100% autonomous. Your work persists through FILES ONLY.

## CRITICAL: Read these files FIRST
1. /mnt/bunker_data/ai/data_factory/.specify/memory/constitution.md (project rules — NON-NEGOTIABLE)
2. /mnt/bunker_data/ai/data_factory/specs/012-mejorar-cobertura-code/plan.md (architectural design)
3. /mnt/bunker_data/ai/data_factory/specs/012-mejorar-cobertura-code/spec.md (feature specification)
4. /mnt/bunker_data/ai/data_factory/specs/012-mejorar-cobertura-code/tasks.md (task list with checkboxes)

## Your Current Task (index 0)
```
[T1] Crear un archivo de prueba /tmp/test_ralph_output.txt con el contenido "TASK_COMPLETE" para verificar el formato de respuesta de goose.
```

## Execution Rules
1. Implement EXACTLY this one task
2. Follow constitution.md rules strictly (typing, headers, naming, etc.)
3. Follow the architecture in plan.md
4. Run tests: pytest tests/ -x --tb=short
5. Run lint: ruff check src/
6. If the task has [VERIFY] tag: run the verification command and report results
7. Commit with a descriptive message referencing the task ID

## When Done
- Mark the task as [x] in /mnt/bunker_data/ai/data_factory/specs/012-mejorar-cobertura-code/tasks.md
- Append your progress to /mnt/bunker_data/ai/data_factory/progress.txt
- Output: TASK_COMPLETE

## If ALL tasks in tasks.md are now [x]:
- Output: ALL_TASKS_COMPLETE

## If you CANNOT complete the task:
- Do NOT output TASK_COMPLETE
- Document what blocked you in progress.txt
- The loop will retry with a fresh context

## FORBIDDEN
- Do not mark tasks [x] unless they are actually verified working
- Do not skip tests or lint checks
- Do not edit files outside the worktree
- Do not hallucinate dependencies not in plan.md
- Do not ask for human input — you are fully autonomous

## RESPONSE FORMAT REQUIREMENTS
- Output plain text ONLY (NO JSON, NO JSONL, NO tool calls like ▸ shell or ▸ write)
- Do NOT use any tool calls - just execute the task and report the result
- If you complete the task successfully, output exactly: TASK_COMPLETE
- If all tasks are complete, output exactly: ALL_TASKS_COMPLETE
- Do NOT add any additional text after these markers
PROMPT_EOF
}

# ============================================================================
# Main
# ============================================================================
main() {
    log_info "Building test prompt..."
    local prompt
    prompt=$(build_test_prompt)

    log_info "Executing goose with vLLM: $RALPH_VLLM_URL"
    log_info "Model: $RALPH_VLLM_MODEL"
    echo ""

    # Execute goose with prompt piped directly (same as ralph-loop.sh)
    # Use --no-session to avoid JSONL tool calls and get plain text output
    local output
    output=$(
        OPENAI_HOST="$RALPH_VLLM_URL" \
        OPENAI_API_KEY="$RALPH_VLLM_API_KEY" \
        GOOSE_MODEL="$RALPH_VLLM_MODEL" \
        echo "$prompt" | goose run -i - --no-session 2>&1
    ) || true

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "OUTPUT FROM GOOSE:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$output"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Check for expected response markers
    if echo "$output" | grep -q "TASK_COMPLETE"; then
        log_ok "✓ Found TASK_COMPLETE marker"
    elif echo "$output" | grep -q "ALL_TASKS_COMPLETE"; then
        log_ok "✓ Found ALL_TASKS_COMPLETE marker"
    else
        log_warn "✗ No TASK_COMPLETE or ALL_TASKS_COMPLETE marker found"
        log_warn "Expected format: TASK_COMPLETE or ALL_TASKS_COMPLETE"
    fi

    # Check if file was created
    if [[ -f "/tmp/test_ralph_output.txt" ]]; then
        log_ok "✓ File /tmp/test_ralph_output.txt was created"
        log_info "Content: $(cat /tmp/test_ralph_output.txt)"
    else
        log_warn "✗ File /tmp/test_ralph_output.txt was NOT created"
    fi

    echo ""
    log_info "Test complete. Check the output above for format analysis."
}

main "$@"
