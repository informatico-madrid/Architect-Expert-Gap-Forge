#!/usr/bin/env bash
#
# Test script para verificar Claude con vLLM local
# Este script NO ejecuta el ralph-loop, solo prueba claude directamente
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
[T1] Crear un archivo de prueba /tmp/test_claude_output.txt con el contenido "TEST_SUCCESS_CLAUDE_12345"
```

## Execution Rules
1. Implement EXACTLY this one task
2. Follow constitution.md rules strictly (typing, headers, naming, etc.)
3. Follow the architecture in plan.md
4. Run tests: pytest tests/ -x --tb=short
5. Run lint: ruff check src/

## CRITICAL: BATCH TOOL EXECUTION (FOR LOCAL MODELS)
- Execute ALL tool calls in a SINGLE response (parallel execution)
- Do NOT wait for tool results before generating the next tool call
- After all tools complete, output TASK_COMPLETE immediately
- This is a SINGLE TASK execution, not multiple iterations
- The loop expects ONE response per task, not multiple responses for tool calls

## When Done
- Mark the task as [x] in /mnt/bunker_data/ai/data_factory/specs/012-mejorar-cobertura-code/tasks.md
- Append your progress to /mnt/bunker_data/ai/data_factory/progress.txt

## RESPONSE FORMAT REQUIREMENTS
- Output plain text ONLY (NO JSON, NO JSONL, NO tool calls like ▸ shell or ▸ write)
- Do NOT use any tool calls - just execute the task and report the result
- If you complete the task successfully, output exactly: TASK_COMPLETE
- If all tasks are complete, output exactly: ALL_TASKS_COMPLETE
- Do NOT add any additional text after these markers

## CRITICAL: DO NOT USE TOOL CALLS
- DO NOT use ▸ shell, ▸ write, ▸ read_resource, or any other tool call format
- DO NOT use JSONL output format
- Use standard text output only
- Execute all operations directly without tool wrappers
- This is a simple test - just create the file and output TASK_COMPLETE
PROMPT_EOF
}

# ============================================================================
# Main
# ============================================================================
main() {
    log_info "Building test prompt..."
    local prompt
    prompt=$(build_test_prompt)

    log_info "Executing claude with vLLM: $RALPH_VLLM_URL"
    log_info "Model: $RALPH_VLLM_MODEL"
    echo ""

    # Execute claude with prompt piped directly
    local output
    output=$(
        echo "$prompt" | claude -p --dangerously-skip-permissions 2>&1
    ) || true

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "OUTPUT FROM CLAUDE:"
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
    if [[ -f "/tmp/test_claude_output.txt" ]]; then
        log_ok "✓ File /tmp/test_claude_output.txt was created"
        log_info "Content: $(cat /tmp/test_claude_output.txt)"
    else
        log_warn "✗ File /tmp/test_claude_output.txt was NOT created"
    fi

    echo ""
    log_info "Test complete. Check the output above for format analysis."
}

main "$@"
